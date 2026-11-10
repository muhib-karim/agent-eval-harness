"""Withhold tests until generation ends, then grade in a fresh subprocess."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent_eval.isolation import Sandbox
from agent_eval.process import ProcessResult, run_process
from agent_eval.specs import TaskSpec, task_file

Outcome = Literal["pass", "fail", "error", "timeout"]

# Import the installed pytest before putting the generated source directory on sys.path.
_PYTEST_BOOTSTRAP = (
    "import os,sys,pytest; sys.path.insert(0,os.getcwd()); "
    "raise SystemExit(pytest.main(sys.argv[1:]))"
)


PREFLIGHT_TIMEOUT_S = 60.0
# A container may first have to pull its image.
SANDBOX_PREFLIGHT_TIMEOUT_S = 600.0
_PREFLIGHT = ["-I", "-c", "import pytest"]
# Interpreters already seen to import pytest; one process grades with one interpreter.
_checked: set[str] = set()


@dataclass(frozen=True)
class Grade:
    outcome: Outcome
    passed: int = 0
    total: int = 0
    log: str = ""


def parse_junit(path: Path, returncode: int, log: str) -> Grade:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return Grade("error", log=log + "\nMissing or invalid test result XML.")
    cases = list(root.iter("testcase"))
    errors = sum(case.find("error") is not None for case in cases)
    passed = sum(
        all(case.find(tag) is None for tag in ("error", "failure", "skipped")) for case in cases
    )
    if errors or returncode not in (0, 1) or not cases:
        outcome: Outcome = "error"
    elif returncode == 0 and passed == len(cases):
        outcome = "pass"
    else:
        outcome = "fail"
    return Grade(outcome, passed, len(cases), log)


def _environment() -> dict[str, str]:
    """What a grading process inherits: enough to start, and no pytest plugins."""
    env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "LANG") if key in os.environ}
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _failure(result: ProcessResult, timeout_s: float) -> str:
    if result.timed_out:
        return f"timed out after {timeout_s:g} s"
    lines = [line.strip() for line in result.output.splitlines() if line.strip()]
    return f"exit {result.returncode}" + (f": {lines[-1][:200]}" if lines else "")


async def check_pytest(sandbox: Sandbox | None = None) -> None:
    """Raise ValueError unless the interpreter that will grade can import pytest.

    Called before any generation. Without it, a missing pytest shows up only as an ``error``
    on every attempt, after each generation has been paid for, and the run still exits 0.
    It starts the interpreter exactly as ``grade`` does: isolated mode, which ignores the
    user site, on the host, or the image's ``python`` in a container."""
    if sandbox is None:
        if sys.executable in _checked:
            return
        result = await run_process(
            [sys.executable, *_PREFLIGHT],
            Path(tempfile.gettempdir()),
            PREFLIGHT_TIMEOUT_S,
            _environment(),
        )
        if not result.timed_out and result.returncode == 0:
            _checked.add(sys.executable)
            return
        raise ValueError(
            f"cannot grade: {sys.executable} cannot import pytest "
            f"({_failure(result, PREFLIGHT_TIMEOUT_S)}); install the grade extra into that "
            "interpreter: pip install 'agent-eval-harness[grade]'"
        )
    with tempfile.TemporaryDirectory(
        prefix="agent-eval-preflight-", ignore_cleanup_errors=True
    ) as directory:
        result = await sandbox.run(
            ["python", *_PREFLIGHT], Path(directory), SANDBOX_PREFLIGHT_TIMEOUT_S, _environment()
        )
    if result.timed_out or result.returncode != 0:
        raise ValueError(
            f"cannot grade: python -I -c 'import pytest' failed in the image "
            f"{sandbox.options.image} ({_failure(result, SANDBOX_PREFLIGHT_TIMEOUT_S)}); "
            "use an image whose python has pytest, such as one built from this "
            "repository's Dockerfile"
        )


async def grade(
    task: TaskSpec, task_path: Path, workdir: Path, sandbox: Sandbox | None = None
) -> Grade:
    """With a ``sandbox``, pytest runs in a container on the image's ``python``."""
    entrypoint = workdir / task.entrypoint
    if entrypoint.is_symlink() or not entrypoint.is_file():
        return Grade("error", log="Entrypoint is missing or is a symlink.")
    # Whatever is left of it goes with the workdir; a failed removal must not change the grade.
    with tempfile.TemporaryDirectory(
        prefix="_hidden_", dir=workdir, ignore_cleanup_errors=True
    ) as hidden:
        test_dir = Path(hidden)
        for index, filename in enumerate(task.hidden_tests):
            shutil.copyfile(task_file(task_path, filename), test_dir / f"test_{index:03d}.py")
        junit_path = test_dir / "results.xml"
        # Disable generated config and plugins; this is not a security boundary.
        command = [
            sys.executable,
            "-I",
            "-c",
            _PYTEST_BOOTSTRAP,
            "-q",
            "-p",
            "no:cacheprovider",
            "--noconftest",
            "--import-mode=importlib",
            "-c",
            # The container is Linux whatever the host is; os.devnull is "nul" on Windows.
            os.devnull if sandbox is None else "/dev/null",
            "--rootdir",
            str(workdir),
            "--tb=short",
            f"--junitxml={junit_path}",
            str(test_dir),
        ]
        env = _environment()
        if sandbox is None:
            result = await run_process(command, workdir, task.timeout_s, env)
        else:
            command[0] = "python"
            result = await sandbox.run(command, workdir, task.timeout_s, env)
        if result.timed_out:
            return Grade("timeout", log=result.output)
        return parse_junit(junit_path, result.returncode, result.output)
