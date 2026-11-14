import asyncio
import contextlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from agent_eval import grader
from agent_eval.cli import main
from agent_eval.grader import check_pytest, grade, parse_junit
from agent_eval.process import run_process
from agent_eval.specs import load_task


@pytest.mark.parametrize(
    "source,outcome,passed,total",
    [
        ("def answer(): return 42", "pass", 1, 1),
        ("def answer(): return 0", "fail", 0, 1),
        ("syntax error !", "error", 0, 1),
        ("def answer():\n    while True: pass", "timeout", 0, 0),
    ],
)
def test_grade_outcomes(
    task_path: Path, workdir: Path, source: str, outcome: str, passed: int, total: int
) -> None:
    # Only the infinite loop needs a short deadline; the others keep the fixture's 3 s
    # so a slow machine doesn't turn a pass/fail/error into a timeout.
    task = load_task(task_path)
    if outcome == "timeout":
        task = task.model_copy(update={"timeout_s": 0.7})
    (workdir / task.entrypoint).write_text(source)
    result = asyncio.run(grade(task, task_path, workdir))
    assert result.outcome == outcome, result.log
    assert (result.passed, result.total) == (passed, total)
    assert not list(workdir.glob("_hidden_*"))


def test_missing_and_symlink_entrypoint(task_path: Path, workdir: Path) -> None:
    task = load_task(task_path)
    assert asyncio.run(grade(task, task_path, workdir)).outcome == "error"
    (workdir / task.entrypoint).symlink_to(task_path.parent / "reference.py")
    assert asyncio.run(grade(task, task_path, workdir)).outcome == "error"


def test_grader_ignores_generated_config_and_does_not_inherit_secrets(
    task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SECRET_FOR_TEST", "do-not-inherit")
    (workdir / "solution.py").write_text(
        "import os\nassert 'SECRET_FOR_TEST' not in os.environ\ndef answer(): return 42"
    )
    (workdir / "conftest.py").write_text("raise RuntimeError('must not load')")
    (workdir / "pytest.py").write_text("raise RuntimeError('must not load')")
    (workdir / "pytest.ini").write_text("[pytest]\naddopts = --no-such-option\n")
    result = asyncio.run(grade(load_task(task_path), task_path, workdir))
    assert result.outcome == "pass", result.log


@pytest.mark.parametrize(
    "xml,code,outcome,passed,total",
    [
        ("invalid", 0, "error", 0, 0),
        ("<testsuites/>", 5, "error", 0, 0),
        ("<testsuite><testcase/><testcase><skipped/></testcase></testsuite>", 0, "fail", 1, 2),
        ("<testsuite><testcase><failure/></testcase></testsuite>", 1, "fail", 0, 1),
        ("<testsuite><testcase><error/></testcase></testsuite>", 2, "error", 0, 1),
        ("<testsuite><testcase/></testsuite>", 3, "error", 1, 1),
    ],
)
def test_junit(tmp_path: Path, xml: str, code: int, outcome: str, passed: int, total: int) -> None:
    path = tmp_path / "result.xml"
    path.write_text(xml)
    result = parse_junit(path, code, "log")
    assert (result.outcome, result.passed, result.total) == (outcome, passed, total)


@pytest.mark.skipif(os.name != "posix", reason="process-group semantics are POSIX-specific")
def test_timeout_kills_descendants(tmp_path: Path) -> None:
    marker = tmp_path / "orphan.txt"
    child = "import time,pathlib; time.sleep(0.6); pathlib.Path('orphan.txt').touch()"
    parent = (
        f"import subprocess,time,sys; subprocess.Popen([sys.executable,'-c',{child!r}]); "
        "time.sleep(10)"
    )

    async def run() -> None:
        result = await run_process([sys.executable, "-c", parent], tmp_path, 0.2)
        assert result.timed_out
        await asyncio.sleep(0.7)
        assert not marker.exists()

    asyncio.run(run())


def test_cancellation_cleans_up(tmp_path: Path) -> None:
    async def run() -> None:
        task = asyncio.create_task(
            run_process([sys.executable, "-c", "import time; time.sleep(30)"], tmp_path, 30)
        )
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=5)

    asyncio.run(run())


@pytest.mark.skipif(os.name != "posix", reason="the output pipe is connected only on POSIX")
def test_cancellation_during_pipe_setup_kills_the_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Between spawning the command and waiting for it, connecting the output pipe is an
    await. A cancellation delivered there must not leave the command running."""
    spawned: list[asyncio.subprocess.Process] = []
    spawn = asyncio.create_subprocess_exec

    async def recording_spawn(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await spawn(*args, **kwargs)
        spawned.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", recording_spawn)

    async def run() -> None:
        loop = asyncio.get_running_loop()
        connect = loop.connect_read_pipe
        task = asyncio.current_task()
        assert task is not None

        async def cancelled_while_connecting(*args: Any, **kwargs: Any) -> Any:
            # Delivered at the next suspension, inside the real connect_read_pipe.
            task.cancel()
            return await connect(*args, **kwargs)

        monkeypatch.setattr(loop, "connect_read_pipe", cancelled_while_connecting)
        with pytest.raises(asyncio.CancelledError):
            await run_process([sys.executable, "-c", "import time; time.sleep(30)"], tmp_path, 30)
        task.uncancel()
        [process] = spawned
        assert process.returncode is not None, "the command was left running"

    try:
        asyncio.run(run())
    finally:
        for process in spawned:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)


@pytest.mark.skipif(os.name != "posix", reason="process-group semantics are POSIX-specific")
def test_exit_is_not_delayed_by_background_children(tmp_path: Path) -> None:
    marker = tmp_path / "orphan.txt"
    code = (
        "import subprocess,sys; "
        "subprocess.Popen([sys.executable,'-c','import time,pathlib; time.sleep(1); "
        "pathlib.Path(\"orphan.txt\").touch()']); print('done')"
    )

    async def run() -> None:
        start = time.perf_counter()
        result = await run_process([sys.executable, "-c", code], tmp_path, 10)
        assert not result.timed_out and result.returncode == 0
        assert result.output == "done\n"
        assert time.perf_counter() - start < 5
        await asyncio.sleep(1.3)
        assert not marker.exists()

    asyncio.run(run())


@pytest.mark.skipif(os.name != "posix", reason="replaces file descriptor 0")
def test_children_do_not_inherit_stdin(tmp_path: Path) -> None:
    # An open pipe on the harness's stdin would block a child that inherited it.
    read_fd, write_fd = os.pipe()
    saved = os.dup(0)
    os.dup2(read_fd, 0)
    try:
        code = "import sys; print(repr(sys.stdin.read()))"
        result = asyncio.run(run_process([sys.executable, "-c", code], tmp_path, 5))
    finally:
        os.dup2(saved, 0)
        for fd in (saved, read_fd, write_fd):
            os.close(fd)
    assert not result.timed_out
    assert result.output == "''\n"


@pytest.mark.skipif(os.name != "posix", reason="setsid is POSIX-specific")
def test_descendant_outside_process_group_cannot_hang_harness(tmp_path: Path) -> None:
    pid_file = tmp_path / "escaped.pid"
    code = (
        "import os,time\n"
        "if os.fork() == 0:\n"
        "    os.setsid()\n"
        f"    open({str(pid_file)!r}, 'w').write(str(os.getpid()))\n"
        "    time.sleep(30)\n"
        "    os._exit(0)\n"
        "print('leader done', flush=True)\n"
        "time.sleep(0.3)\n"
    )

    async def run() -> None:
        start = time.perf_counter()
        result = await run_process([sys.executable, "-c", code], tmp_path, 10)
        assert time.perf_counter() - start < 5
        assert not result.timed_out
        assert "leader done" in result.output

    try:
        asyncio.run(run())
    finally:
        with contextlib.suppress(OSError, ValueError):
            os.kill(int(pid_file.read_text()), signal.SIGKILL)


def test_output_is_capped_without_blocking_the_writer(tmp_path: Path) -> None:
    code = "import sys; sys.stdout.write('x' * 5_000_000); print('end')"
    result = asyncio.run(
        run_process([sys.executable, "-c", code], tmp_path, 10, max_output_bytes=1000)
    )
    assert not result.timed_out and result.returncode == 0
    assert result.output.startswith("x" * 1000 + "\n[agent-eval: output truncated after 1000")
    assert len(result.output) < 1100


def test_missing_command_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        asyncio.run(run_process([str(tmp_path / "absent")], tmp_path, 1))


def test_preflight_fails_fast_without_pytest(
    config_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A grading interpreter without pytest would turn every attempt into an error after its
    generation had been paid for, and the run would still exit 0."""
    bare = tmp_path / "bare"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(bare)], check=True)
    python = bare / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    monkeypatch.setattr(sys, "executable", str(python))
    out = tmp_path / "run"
    assert main(["run", str(config_path), "--out", str(out)]) == 2
    err = capsys.readouterr().err
    assert f"{python} cannot import pytest" in err
    assert "No module named 'pytest'" in err and "agent-eval-harness[grade]" in err
    assert not out.exists()


def test_preflight_reports_an_interpreter_that_hangs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slow = tmp_path / "slow-python"
    slow.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(30)\n")
    slow.chmod(0o755)
    monkeypatch.setattr(sys, "executable", str(slow))
    monkeypatch.setattr(grader, "PREFLIGHT_TIMEOUT_S", 0.3)
    with pytest.raises(ValueError, match=r"cannot import pytest \(timed out after 0.3 s\)"):
        asyncio.run(check_pytest())


def test_preflight_runs_once_per_interpreter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(grader, "_checked", set())
    asyncio.run(check_pytest())

    async def unexpected(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the interpreter was checked again")

    monkeypatch.setattr(grader, "run_process", unexpected)
    asyncio.run(check_pytest())


def test_preflight_cache_can_be_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    """A long-lived embedding can make the next run check the interpreter again."""
    monkeypatch.setattr(grader, "_checked", set())
    calls: list[list[str]] = []
    real = grader.run_process

    async def counting(command: list[str], *args: Any, **kwargs: Any) -> Any:
        calls.append(command)
        return await real(command, *args, **kwargs)

    monkeypatch.setattr(grader, "run_process", counting)
    asyncio.run(check_pytest())
    asyncio.run(check_pytest())
    assert len(calls) == 1
    grader.reset_preflight_cache()
    asyncio.run(check_pytest())
    assert len(calls) == 2
