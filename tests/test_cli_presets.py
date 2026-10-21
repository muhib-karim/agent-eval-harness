"""Agent CLI presets, exercised with a fake CLI instead of a real agent."""

import asyncio
import json
import os
import stat
import sys
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from agent_eval.engine import run_config
from agent_eval.runners.base import RunnerError
from agent_eval.runners.local import CLIOptions, CLIRunner
from agent_eval.runners.presets import PRESETS, parse_usage
from agent_eval.specs import load_task

# Records what it was given, writes a correct solution and prints claude-style JSON.
FAKE = """#!{python}
import json, os, sys
from pathlib import Path
record = {{"argv": sys.argv[1:], "cwd": os.getcwd(), "env": dict(os.environ),
           "home_entries": sorted(os.listdir(os.environ.get("HOME", ".")))}}
Path("solution.py").write_text("def answer():\\n    return 42\\n")
print(json.dumps({{"type": "result", "usage": {{"input_tokens": 11, "output_tokens": 7}},
                  "total_cost_usd": 0.25, "record": record}}))
raise SystemExit(int(os.environ.get("FAKE_EXIT", "0")))
"""


@pytest.fixture
def fake_cli(tmp_path: Path) -> Path:
    path = tmp_path / "bin" / "fake-agent"
    path.parent.mkdir()
    path.write_text(FAKE.format(python=sys.executable))
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def run(options: dict[str, object], task_path: Path, workdir: Path) -> tuple[dict, object]:  # type: ignore[type-arg]
    runner = CLIRunner(options)
    generation = asyncio.run(runner.generate(load_task(task_path), workdir))
    return json.loads(generation.raw_output)["record"], generation


@pytest.mark.parametrize(
    "preset,expected",
    [
        (
            "claude-code",
            [
                "-p",
                "{prompt}",
                "--output-format",
                "json",
                "--permission-mode",
                "acceptEdits",
                "--allowedTools",
                "Read,Edit,Write",
            ],
        ),
        (
            "codex",
            ["exec", "--full-auto", "--skip-git-repo-check", "--cd", "{workdir}", "{prompt}"],
        ),
        ("opencode", ["run", "{prompt}"]),
    ],
)
def test_preset_command_templates(
    preset: str, expected: list[str], fake_cli: Path, task_path: Path, workdir: Path
) -> None:
    record, _ = run(
        {
            "preset": preset,
            "executable": str(fake_cli),
            "model": "some/model-1",
            "extra_args": ["--flag", "{entrypoint}"],
        },
        task_path,
        workdir,
    )
    prompt = (workdir / "_agent_prompt.txt").read_text()
    assert "answer()" in prompt
    filled = [
        part.replace("{prompt}", prompt).replace("{workdir}", str(workdir)) for part in expected
    ]
    assert record["argv"] == [*filled, "--flag", "solution.py", "--model", "some/model-1"]
    assert Path(record["cwd"]).resolve() == workdir.resolve()
    assert (workdir / "solution.py").read_text().endswith("return 42\n")


def test_presets_are_found_on_path(
    fake_cli: Path, task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (fake_cli.parent / "opencode").symlink_to(fake_cli)
    monkeypatch.setenv("PATH", f"{fake_cli.parent}{os.pathsep}{os.environ['PATH']}")
    record, _ = run({"preset": "opencode"}, task_path, workdir)
    assert record["argv"][0] == "run"


def test_environment_is_an_allow_list(
    fake_cli: Path, task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key-value")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key-value")
    monkeypatch.setenv("UNLISTED_SECRET", "do-not-forward")
    monkeypatch.setenv("EXTRA_SETTING", "forwarded")
    record, _ = run(
        {
            "preset": "claude-code",
            "executable": str(fake_cli),
            "env_passthrough": ["EXTRA_SETTING"],
        },
        task_path,
        workdir,
    )
    env = record["env"]
    assert env["ANTHROPIC_API_KEY"] == "anthropic-key-value"
    assert env["EXTRA_SETTING"] == "forwarded"
    assert "OPENAI_API_KEY" not in env and "UNLISTED_SECRET" not in env
    assert env["PATH"] == os.environ["PATH"]


def test_plain_command_also_gets_only_the_allow_list(
    fake_cli: Path, task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UNLISTED_SECRET", "do-not-forward")
    record, _ = run({"command": [str(fake_cli), "{prompt_file}"]}, task_path, workdir)
    assert "UNLISTED_SECRET" not in record["env"]
    assert record["argv"] == [str(workdir / "_agent_prompt.txt")]


def test_isolated_home_is_private_and_removed(
    fake_cli: Path, task_path: Path, workdir: Path
) -> None:
    record, _ = run(
        {"preset": "codex", "executable": str(fake_cli), "isolate_home": True}, task_path, workdir
    )
    home = Path(record["env"]["HOME"])
    assert home != Path.home() and record["home_entries"] == []
    assert record["env"]["XDG_CONFIG_HOME"] == record["env"]["TMPDIR"] == str(home)
    assert not home.exists()
    assert not home.resolve().is_relative_to(workdir.resolve())


def test_claude_usage_is_parsed(fake_cli: Path, task_path: Path, workdir: Path) -> None:
    _, generation = run({"preset": "claude-code", "executable": str(fake_cli)}, task_path, workdir)
    assert (generation.input_tokens, generation.output_tokens, generation.cost_usd) == (  # type: ignore[attr-defined]
        11,
        7,
        0.25,
    )
    _, generation = run({"preset": "codex", "executable": str(fake_cli)}, task_path, workdir)
    assert generation.input_tokens is None and generation.cost_usd is None  # type: ignore[attr-defined]


def test_non_zero_exit_keeps_output_and_usage(
    fake_cli: Path, task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_EXIT", "3")
    runner = CLIRunner(
        {"preset": "claude-code", "executable": str(fake_cli), "env_passthrough": ["FAKE_EXIT"]}
    )
    with pytest.raises(RunnerError, match="agent exited with code 3") as caught:
        asyncio.run(runner.generate(load_task(task_path), workdir))
    assert caught.value.generation.output_tokens == 7
    assert '"record"' in caught.value.raw_output


def test_preset_timeout_defaults_and_override() -> None:
    assert CLIOptions(preset="codex").timeout() == PRESETS["codex"].timeout_s == 600
    assert CLIOptions(preset="codex", timeout_s=30).timeout() == 30
    assert CLIOptions(command=["agent"]).timeout() == 120


def test_preset_timeout_kills_the_agent(task_path: Path, workdir: Path, tmp_path: Path) -> None:
    sleeper = tmp_path / "sleeper"
    sleeper.write_text(
        f"#!{sys.executable}\nimport time\nprint('started', flush=True)\ntime.sleep(30)\n"
    )
    sleeper.chmod(0o755)
    runner = CLIRunner({"preset": "opencode", "executable": str(sleeper), "timeout_s": 0.3})
    with pytest.raises(RunnerError) as caught:
        asyncio.run(runner.generate(load_task(task_path), workdir))
    assert caught.value.timed_out and "started" in caught.value.raw_output


@pytest.mark.parametrize(
    "options,message",
    [
        ({}, "exactly one of preset or command"),
        ({"preset": "codex", "command": ["x"]}, "exactly one of preset or command"),
        ({"command": []}, "command cannot be empty"),
        ({"command": ["agent"], "model": "m"}, "apply only to presets"),
        ({"preset": "aider"}, "Input should be"),
        ({"preset": "codex", "extra_args": ["{secret}"]}, "unsupported command placeholder"),
        ({"preset": "codex", "env_passthrough": ["BAD-NAME"]}, "String should match pattern"),
        ({"preset": "codex", "isolate": True}, "Extra inputs are not permitted"),
    ],
)
def test_invalid_options(options: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        CLIOptions.model_validate(options)


@pytest.mark.parametrize(
    "output,expected",
    [
        ('{"usage": {"input_tokens": 1, "output_tokens": 2}, "total_cost_usd": 3}', (1, 2, 3.0)),
        ('log line\n{"usage": {"input_tokens": 5}}', (5, None, None)),
        (
            '{"usage": {"input_tokens": -1, "output_tokens": true}, "total_cost_usd": -2}',
            (None, None, None),
        ),
        ('{"usage": [], "total_cost_usd": true}', (None, None, None)),
        ('{"total_cost_usd": NaN}', (None, None, None)),
        ("[1, 2]", (None, None, None)),
        ("not json", (None, None, None)),
        ("", (None, None, None)),
    ],
)
def test_parse_claude_usage(output: str, expected: tuple[object, ...]) -> None:
    assert parse_usage("claude-json", output) == expected


def test_engine_redacts_forwarded_credentials(
    fake_cli: Path, task_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "fake-forwarded-credential-value")
    monkeypatch.setenv("SHORT_VALUE", "x")
    config = tmp_path / "agents.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "models": [
                    {
                        "name": "codex-fake",
                        "runner": "cli",
                        "options": {
                            "preset": "codex",
                            "executable": str(fake_cli),
                            "env_passthrough": ["SHORT_VALUE"],
                        },
                    }
                ],
                "tasks": [str(task_path)],
            }
        )
    )
    out = tmp_path / "out"
    [attempt] = asyncio.run(run_config(config, out))
    assert attempt.outcome == "pass"
    output = (out / attempt.artifacts / "model-output.txt").read_text()
    assert "fake-forwarded-credential-value" not in output
    assert "[REDACTED]" in output
