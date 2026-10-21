"""Resuming an interrupted run fills in only the attempts it never recorded."""

import asyncio
import json
from pathlib import Path

import pytest
import yaml

from agent_eval.cli import main
from agent_eval.engine import recover_attempts, run_config
from agent_eval.results import load_attempts


def interrupt(out: Path, keep: int, *, partial: bool) -> list[str]:
    """Keep the first ``keep`` recorded lines, optionally plus half of the next one."""
    lines = (out / "results.jsonl").read_text().splitlines(keepends=True)
    tail = lines[keep][: len(lines[keep]) // 2] if partial else ""
    (out / "results.jsonl").write_text("".join(lines[:keep]) + tail)
    return lines


def test_resume_runs_only_missing_attempts(config_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "run"
    first = asyncio.run(run_config(config_path, out))
    assert len(first) == 4
    original = interrupt(out, 2, partial=True)
    kept = {json.loads(line)["attempt_id"] for line in original[:2]}
    # Leftover artifacts of the interrupted attempts are replaced, not an error.
    (out / "attempts" / "attempt-000004" / "stale.txt").write_text("stale")

    resumed = asyncio.run(run_config(config_path, out, resume=True))

    assert sorted(a.attempt_id for a in resumed) == sorted(a.attempt_id for a in first)
    rows = load_attempts(out / "results.jsonl")
    assert len(rows) == 4 and {r.attempt_id for r in rows[:2]} == kept
    assert not (out / "attempts" / "attempt-000004" / "stale.txt").exists()
    metadata = json.loads((out / "metadata.json").read_text())
    assert len(metadata["resumed_at"]) == 1
    assert (out / "report.html").is_file()
    # A complete run resumes to a no-op.
    again = asyncio.run(run_config(config_path, out, resume=True))
    assert len(again) == 4 and len(load_attempts(out / "results.jsonl")) == 4


def test_resume_without_existing_output_starts_fresh(config_path: Path, tmp_path: Path) -> None:
    assert len(asyncio.run(run_config(config_path, tmp_path / "new", resume=True))) == 4


def test_resume_refuses_a_changed_config(config_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "run"
    asyncio.run(run_config(config_path, out))
    config = yaml.safe_load(config_path.read_text())
    config["repeats"] = 3
    config_path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="config differs"):
        asyncio.run(run_config(config_path, out, resume=True))


def test_resume_refuses_changed_tasks(config_path: Path, task_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "run"
    asyncio.run(run_config(config_path, out))
    hidden = task_path.parent / "hidden.py"
    hidden.write_text(hidden.read_text() + "\n# edited\n")
    with pytest.raises(ValueError, match="task files changed"):
        asyncio.run(run_config(config_path, out, resume=True))


def test_resume_needs_results(config_path: Path, tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError, match="no results.jsonl"):
        asyncio.run(run_config(config_path, tmp_path / "empty", resume=True))


def test_recover_rejects_corruption_before_the_last_line(config_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "run"
    asyncio.run(run_config(config_path, out))
    lines = (out / "results.jsonl").read_text().splitlines(keepends=True)
    (out / "results.jsonl").write_text(lines[0] + "{broken\n" + "".join(lines[1:]))
    with pytest.raises(ValueError, match="invalid attempt on line 2"):
        recover_attempts(out / "results.jsonl")
    (out / "results.jsonl").write_text(lines[0] + lines[0])
    with pytest.raises(ValueError, match="duplicate"):
        recover_attempts(out / "results.jsonl")


def test_cli_resume(config_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "run"
    assert main(["run", str(config_path), "--out", str(out)]) == 0
    interrupt(out, 1, partial=False)
    assert main(["run", str(config_path), "--out", str(out), "--resume"]) == 0
    assert "Completed 4 attempts" in capsys.readouterr().out
    assert main(["run", str(config_path), "--resume"]) == 2
    assert "--resume needs --out" in capsys.readouterr().err
