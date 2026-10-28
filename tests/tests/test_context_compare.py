from pathlib import Path

import pytest

from agent_eval.cli import main
from agent_eval.context_compare import compare_context
from agent_eval.results import Attempt


def row(task: str = "t", repeat: int = 1, **changes: object) -> Attempt:
    data: dict[str, object] = dict(
        attempt_id=f"{task}-{repeat}",
        model="variant",
        runner="mock",
        task_id=task,
        repeat=repeat,
        outcome="pass",
        wall_time_s=2,
        generation_time_s=1,
        grading_time_s=1,
        artifacts="local",
    )
    return Attempt.model_validate(data | changes)


def test_direction_pairing_macro_and_unknown_usage() -> None:
    full = [row(), row(repeat=2), row("other", outcome="fail")]
    trimmed = [row("other"), row(repeat=2, outcome="error"), row(outcome="fail")]
    result = compare_context(full, trimmed, resamples=100)
    assert result["pairs"] == 3
    assert result["pass_at_1"]["difference"] == 0  # Task macro, not pooled attempts.
    assert result["usage"]["input_tokens"]["difference"] is None
    assert result == compare_context(full, trimmed, resamples=100)


def test_complete_usage_and_latency() -> None:
    result = compare_context(
        [row(input_tokens=10, output_tokens=5)],
        [row(input_tokens=0, output_tokens=5, wall_time_s=1)],
    )
    assert result["usage"]["input_tokens"] == {"full": 10, "trimmed": 0, "difference": -10}
    assert result["mean_paired_wall_time_difference_s"] == -1
    assert result["pass_at_1"]["ci_low"] == 0


@pytest.mark.parametrize(
    "full,trimmed,match",
    [
        ([], [], "exactly one"),
        ([row(), row(model="other", repeat=2)], [row()], "exactly one"),
        ([row(), row()], [row()], "duplicate"),
        ([row()], [row(repeat=2)], "identical"),
        ([row()], [row(runner="cli")], "same runner"),
    ],
)
def test_reject_incomparable_inputs(
    full: list[Attempt], trimmed: list[Attempt], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        compare_context(full, trimmed)


def test_cli_offline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "results.jsonl"
    path.write_text(row().model_dump_json() + "\n")
    assert main(["compare-context", str(path), str(path)]) == 0
    assert '"difference": 0.0' in capsys.readouterr().out
    out = tmp_path / "comparison.json"
    assert main(["compare-context", str(path), str(path), "--out", str(out)]) == 0
    assert out.read_text().startswith("{")
