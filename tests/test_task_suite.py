"""Every bundled task is solvable, and its hidden tests actually test something.

Reference solutions live in tests/fixtures/reference/<task_id>.py, outside the shipped
task directories, and are used only here and by the offline mock demo.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from agent_eval.engine import validate_task
from agent_eval.grader import Grade, grade
from agent_eval.specs import load_task

ROOT = Path(__file__).resolve().parent.parent
REFERENCES = ROOT / "tests" / "fixtures" / "reference"
TASK_PATHS = sorted((ROOT / "tasks").glob("*/task.yaml"))
CATEGORIES = {"algorithms", "parsing", "stateful", "bug-fix"}
EMPTY_MODULE = ""
# Imports succeed and every call returns None, so only tests that assert nothing pass.
PERMISSIVE_STUB = "def __getattr__(name):\n    return lambda *args, **kwargs: None\n"


def grade_source(task_path: Path, source: str) -> Grade:
    task = load_task(task_path)

    async def run() -> Grade:
        with tempfile.TemporaryDirectory(prefix="agent-eval-suite-") as directory:
            workdir = Path(directory)
            (workdir / task.entrypoint).write_text(source, encoding="utf-8")
            return await grade(task, task_path, workdir)

    return asyncio.run(run())


def test_suite_shape() -> None:
    tasks = [load_task(path) for path in TASK_PATHS]
    assert len(tasks) >= 16
    assert {task.category for task in tasks} == CATEGORIES
    assert sum(task.category == "bug-fix" for task in tasks) >= 4
    for task in tasks:
        assert (task.starter is not None) == (task.category == "bug-fix"), task.id


def test_references_are_kept_out_of_task_directories() -> None:
    for path in TASK_PATHS:
        task = load_task(path)
        assert not (path.parent / task.reference).exists(), task.id
        assert (REFERENCES / f"{task.id}.py").is_file(), task.id
    assert {p.stem for p in REFERENCES.glob("*.py")} == {load_task(p).id for p in TASK_PATHS}


@pytest.mark.parametrize("task_path", TASK_PATHS, ids=lambda p: p.parent.name)
def test_reference_passes_every_hidden_test(task_path: Path) -> None:
    task = load_task(task_path)
    result = asyncio.run(validate_task(task_path, REFERENCES / f"{task.id}.py"))
    assert result.outcome == "pass", result.log
    assert result.total >= 8


@pytest.mark.parametrize("task_path", TASK_PATHS, ids=lambda p: p.parent.name)
@pytest.mark.parametrize("source", [EMPTY_MODULE, PERMISSIVE_STUB], ids=["empty", "stub"])
def test_no_hidden_test_passes_on_a_stub(task_path: Path, source: str) -> None:
    result = grade_source(task_path, source)
    assert result.outcome != "pass"
    assert result.passed == 0, result.log


@pytest.mark.parametrize(
    "task_path",
    [p for p in TASK_PATHS if load_task(p).starter is not None],
    ids=lambda p: p.parent.name,
)
def test_bug_fix_starter_fails_the_bug_and_passes_regressions(task_path: Path) -> None:
    task = load_task(task_path)
    assert task.starter is not None
    result = grade_source(task_path, (task_path.parent / task.starter).read_text("utf-8"))
    assert result.outcome == "fail", result.log
    assert 0 < result.passed < result.total
