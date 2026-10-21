"""Bug-fix starters, external reference directories and validate-task --reference."""

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest
import yaml

from agent_eval.cli import main
from agent_eval.engine import run_config
from agent_eval.runners.base import RunnerError, generation_prompt
from agent_eval.runners.http import HTTPRunner
from agent_eval.runners.local import CLIRunner, MockRunner
from agent_eval.specs import load_task

BUGGY = "def answer():\n    return 41\n"


@pytest.fixture
def bugfix_task(task_path: Path) -> Path:
    (task_path.parent / "starter.py").write_text(BUGGY)
    spec = yaml.safe_load(task_path.read_text())
    spec.update(starter="starter.py", category="bug-fix", prompt="answer() is off by one.")
    task_path.write_text(yaml.safe_dump(spec))
    return task_path


def test_missing_starter_is_rejected(bugfix_task: Path) -> None:
    (bugfix_task.parent / "starter.py").unlink()
    with pytest.raises(ValueError, match="missing task file: starter.py"):
        load_task(bugfix_task)


def test_prompt_embeds_starter_source(bugfix_task: Path) -> None:
    task = load_task(bugfix_task)
    prompt = generation_prompt(task, BUGGY)
    assert prompt.startswith("Fix the bug described below in solution.py.")
    assert "answer() is off by one." in prompt
    assert "```python\n" + BUGGY + "```" in prompt
    assert generation_prompt(task).startswith("Implement this Python task")


def test_http_runner_sends_the_starter(
    bugfix_task: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_KEY", "k")
    monkeypatch.setenv("TEST_BASE", str(httpx.URL(scheme="https", host="endpoint.invalid")))
    (workdir / "solution.py").write_text(BUGGY)
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content)["messages"][0]["content"])
        reply = "```python\ndef answer():\n    return 42\n```"
        return httpx.Response(200, json={"choices": [{"message": {"content": reply}}]})

    runner = HTTPRunner(
        {"model": "m", "base_url_env": "TEST_BASE", "api_key_env": "TEST_KEY"},
        transport=httpx.MockTransport(handler),
    )
    asyncio.run(runner.generate(load_task(bugfix_task), workdir))
    assert "return 41" in seen[0]
    assert "return 42" in (workdir / "solution.py").read_text()


def test_engine_places_starter_for_cli_agents(bugfix_task: Path, tmp_path: Path) -> None:
    agent = tmp_path / "fixer.py"
    agent.write_text(
        "import sys\nfrom pathlib import Path\n"
        "assert Path(sys.argv[1]).read_text().startswith('Fix the bug')\n"
        "source = Path('solution.py').read_text()\n"
        "Path('solution.py').write_text(source.replace('41', '42'))\n"
    )
    config = tmp_path / "fix.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "models": [
                    {
                        "name": "fixer",
                        "runner": "cli",
                        "options": {"command": [sys.executable, str(agent), "{prompt_file}"]},
                    }
                ],
                "tasks": [str(bugfix_task)],
            }
        )
    )
    out = tmp_path / "out"
    [attempt] = asyncio.run(run_config(config, out))
    assert attempt.outcome == "pass", (out / attempt.artifacts / "test.log").read_text()
    assert attempt.category == "bug-fix"
    hashes = json.loads((out / "metadata.json").read_text())["task_hashes"]["answer"]
    assert any(path.endswith("starter.py") for path in hashes)


def test_cli_runner_prompt_for_bug_fix(bugfix_task: Path, workdir: Path) -> None:
    (workdir / "solution.py").write_text(BUGGY)
    runner = CLIRunner(
        {
            "command": [
                sys.executable,
                "-c",
                "import sys; print(open(sys.argv[1]).read())",
                "{prompt_file}",
            ]
        }
    )
    result = asyncio.run(runner.generate(load_task(bugfix_task), workdir))
    assert "which is in this directory" in result.raw_output


def test_mock_reference_dir_is_relative_to_the_config(task_path: Path, tmp_path: Path) -> None:
    (task_path.parent / "reference.py").unlink()
    refs = tmp_path / "refs"
    refs.mkdir()
    (refs / "answer.py").write_text("def answer():\n    return 42\n")
    config = tmp_path / "demo.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "models": [
                    {"name": "ref", "runner": "mock", "options": {"reference_dir": "refs"}},
                    {"name": "nodir", "runner": "mock", "options": {"reference_dir": "none"}},
                ],
                "tasks": [str(task_path.relative_to(tmp_path))],
            }
        )
    )
    out = tmp_path / "out"
    attempts = {row.model: row for row in asyncio.run(run_config(config, out))}
    assert attempts["ref"].outcome == "pass"
    assert attempts["nodir"].outcome == "error"
    assert attempts["nodir"].error == "no reference solution for task answer"
    hashes = json.loads((out / "metadata.json").read_text())["task_hashes"]["answer"]
    assert str(refs / "answer.py") in hashes
    # The resolved config keeps what the user wrote, not a machine path.
    assert "reference_dir: refs" in (out / "config.resolved.yaml").read_text()


def test_mock_runner_reports_missing_reference(task_path: Path, workdir: Path) -> None:
    runner = MockRunner({"reference_dir": str(workdir / "absent")}, task_path=task_path)
    with pytest.raises(RunnerError, match="no reference solution"):
        asyncio.run(runner.generate(load_task(task_path), workdir))


def test_validate_task_with_external_reference(
    task_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (task_path.parent / "reference.py").unlink()
    good, bad = tmp_path / "good.py", tmp_path / "bad.py"
    good.write_text("def answer():\n    return 42\n")
    bad.write_text("def answer():\n    return 0\n")
    assert main(["validate-task", str(task_path), "--reference", str(good)]) == 0
    assert "pass: 1/1" in capsys.readouterr().out
    assert main(["validate-task", str(task_path), "--reference", str(bad)]) == 1
    capsys.readouterr()
    assert main(["validate-task", str(task_path)]) == 2
    assert "missing task file: reference.py" in capsys.readouterr().err
