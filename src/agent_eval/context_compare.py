"""Offline paired analysis of two context variants. No model calls or causal claims."""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from agent_eval.results import Attempt
from agent_eval.stats import DEFAULT_RESAMPLES, DEFAULT_SEED, paired_bootstrap_diff


def compare_context(
    full: Sequence[Attempt],
    trimmed: Sequence[Attempt],
    *,
    seed: int = DEFAULT_SEED,
    resamples: int = DEFAULT_RESAMPLES,
) -> dict[str, Any]:
    """Compare complete, identically paired task/repeat sets; trimmed minus full.

    Exactly one model label per input is required. Labels may differ to identify the
    variants; callers must verify provider/model/settings and task hashes themselves.
    """

    def indexed(rows: Sequence[Attempt]) -> dict[tuple[str, int], Attempt]:
        if not rows or len({row.model for row in rows}) != 1:
            raise ValueError("each variant needs attempts from exactly one model label")
        result = {(row.task_id, row.repeat): row for row in rows}
        if len(result) != len(rows):
            raise ValueError("duplicate task/repeat pair")
        return result

    first, second = indexed(full), indexed(trimmed)
    if first.keys() != second.keys():
        raise ValueError("variants must have identical task/repeat pairs; no silent intersection")
    keys = sorted(first)
    if any(first[key].runner != second[key].runner for key in keys):
        raise ValueError("paired attempts must use the same runner")
    scores: list[dict[str, float]] = []
    for rows in (first, second):
        tasks: dict[str, list[float]] = defaultdict(list)
        for (task, _), row in rows.items():
            tasks[task].append(float(row.outcome == "pass"))
        scores.append({task: statistics.fmean(values) for task, values in tasks.items()})
    diff, low, high = paired_bootstrap_diff(scores[1], scores[0], seed=seed, resamples=resamples)

    # Missing usage is unknown, never zero and never a partial total presented as complete.
    def total(rows: Sequence[Attempt], field: str) -> int | None:
        values = [getattr(row, field) for row in rows]
        return None if any(value is None for value in values) else sum(values)

    usage = {}
    for field in ("input_tokens", "output_tokens"):
        a, b = total(full, field), total(trimmed, field)
        usage[field] = {
            "full": a,
            "trimmed": b,
            "difference": None if a is None or b is None else b - a,
        }
    return {
        "direction": "trimmed minus full",
        "tasks": len(scores[0]),
        "pairs": len(keys),
        "pass_at_1": {
            "full": statistics.fmean(scores[0].values()),
            "trimmed": statistics.fmean(scores[1].values()),
            "difference": diff,
            "ci_low": low,
            "ci_high": high,
            "seed": seed,
            "resamples": resamples,
            "method": "paired task-level percentile bootstrap, 95% interval",
        },
        "mean_paired_wall_time_difference_s": statistics.fmean(
            second[key].wall_time_s - first[key].wall_time_s for key in keys
        ),
        "usage": usage,
        "note": "Descriptive comparison only. Verify identical task hashes, model and settings; "
        "counterbalance run order. This does not establish a context effect or equivalence.",
    }
