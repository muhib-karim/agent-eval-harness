"""Resuming an interrupted run fills in only the attempts it never recorded."""

import asyncio
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from agent_eval import __version__
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


def test_resume_repairs_a_final_line_without_newline(config_path: Path, tmp_path: Path) -> None:
    """A kill can cut off only the newline of the last record; the next must not join it."""
    out = tmp_path / "run"
    asyncio.run(run_config(config_path, out))
    lines = (out / "results.jsonl").read_text().splitlines(keepends=True)
    (out / "results.jsonl").write_text("".join(lines[:2]).removesuffix("\n"))

    resumed = asyncio.run(run_config(config_path, out, resume=True))

    assert len(resumed) == 4
    text = (out / "results.jsonl").read_text()
    assert text.endswith("\n") and len(text.splitlines()) == 4
    assert len(load_attempts(out / "results.jsonl")) == 4


def test_recover_drops_a_partial_line_without_rewriting_the_file(
    config_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rewriting the whole file to drop its tail would lose every record if killed midway."""
    out = tmp_path / "run"
    asyncio.run(run_config(config_path, out))
    original = interrupt(out, 2, partial=True)

    def rewritten(self: Path, data: bytes) -> int:
        raise AssertionError(f"{self.name} was rewritten")

    monkeypatch.setattr(Path, "write_bytes", rewritten)
    assert len(recover_attempts(out / "results.jsonl")) == 2
    assert (out / "results.jsonl").read_text() == "".join(original[:2])


@pytest.mark.parametrize(
    "filename,content",
    [
        ("config.resolved.yaml", ""),
        ("config.resolved.yaml", "- not\n- a mapping\n"),
        ("config.resolved.yaml", "isolation: docker\n"),
        ("metadata.json", "[]"),
    ],
)
def test_resume_rejects_damaged_run_files(
    config_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    filename: str,
    content: str,
) -> None:
    out = tmp_path / "run"
    assert main(["run", str(config_path), "--out", str(out)]) == 0
    (out / filename).write_text(content)
    capsys.readouterr()
    assert main(["run", str(config_path), "--out", str(out), "--resume"]) == 2
    assert f"cannot resume: {filename} is damaged" in capsys.readouterr().err


def test_resume_records_its_own_provenance(config_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "run"
    asyncio.run(run_config(config_path, out))
    before = json.loads((out / "metadata.json").read_text())
    interrupt(out, 2, partial=False)
    # A comment changes the file's hash but not the resolved config, so the resume goes ahead.
    config_path.write_text(config_path.read_text() + "# reviewed\n")

    asyncio.run(run_config(config_path, out, resume=True))

    after = json.loads((out / "metadata.json").read_text())
    assert after["config_sha256"] == before["config_sha256"]
    [resume] = after["resumes"]
    assert resume["config_sha256"] == hashlib.sha256(config_path.read_bytes()).hexdigest()
    assert resume["config_sha256"] != before["config_sha256"]
    assert resume["at"] == after["resumed_at"][0]
    assert resume["harness_version"] == __version__
    assert set(resume) == {"at", "config_sha256", "harness_version", "python_version", "platform"}
