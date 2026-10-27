"""Versioned attempts and task-macro-averaged comparison statistics."""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from agent_eval.grader import Outcome
from agent_eval.isolation import IsolationRecord
from agent_eval.specs import StrictModel
from agent_eval.stats import (
    DEFAULT_CONFIDENCE,
    DEFAULT_RESAMPLES,
    DEFAULT_SEED,
    bootstrap_mean_ci,
    paired_bootstrap_diff,
)

UNCATEGORIZED = "uncategorized"


class Attempt(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    attempt_id: str
    model: str
    runner: str
    task_id: str
    repeat: int = Field(ge=1)
    outcome: Outcome
    tests_passed: int = Field(default=0, ge=0)
    tests_total: int = Field(default=0, ge=0)
    wall_time_s: float = Field(ge=0, allow_inf_nan=False)
    generation_time_s: float = Field(ge=0, allow_inf_nan=False)
    grading_time_s: float = Field(ge=0, allow_inf_nan=False)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    error: str | None = None
    artifacts: str
    # Added in 1.3.0; absent in older result files, which load as uncategorized.
    category: str | None = None
    # Added after 1.3.0; absent in older result files, which predate isolation.
    isolation: IsolationRecord | None = None

    @model_validator(mode="after")
    def consistent_test_counts(self) -> Attempt:
        if self.tests_passed > self.tests_total:
            raise ValueError("passed test count exceeds total test count")
        return self


class TaskScore(StrictModel):
    task_id: str
    attempts: int
    passed: int
    pass_at_1: float


class CategoryScore(StrictModel):
    category: str
    tasks: int
    attempts: int
    passed: int
    pass_at_1: float


class BootstrapInfo(StrictModel):
    method: Literal["task-level percentile bootstrap"] = "task-level percentile bootstrap"
    seed: int
    resamples: int
    confidence: float


class Comparison(StrictModel):
    """Paired task-level bootstrap of ``model_a - model_b`` for overlapping intervals."""

    model_a: str
    model_b: str
    shared_tasks: int
    diff: float
    ci_low: float
    ci_high: float
    significant: bool
    note: str


class ModelSummary(StrictModel):
    model: str
    attempts: int
    passed: int
    outcomes: dict[str, int]
    pass_at_1: float
    pass_at_k: dict[int, float]
    pass_at_1_ci: tuple[float, float]
    mean_wall_time_s: float
    median_wall_time_s: float
    wall_times_s: list[float]
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    input_tokens_reported: int
    output_tokens_reported: int
    cost_reported: int
    tasks: list[TaskScore]
    categories: list[CategoryScore]


class Summary(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    attempts: int
    task_ids: list[str]
    task_categories: dict[str, str]
    models: list[ModelSummary]
    bootstrap: BootstrapInfo
    comparisons: list[Comparison]


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased estimator: 1 - choose(n-c, k) / choose(n, k)."""
    if not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("require 0 <= c <= n and 1 <= k <= n")
    if n - c < k:
        return 1.0
    # Stable when c/n is small; avoid subtracting nearly equal floating values.
    return -math.expm1(sum(math.log1p(-c / (n - i)) for i in range(k)))


def load_attempts(path: Path) -> list[Attempt]:
    attempts: list[Attempt] = []
    seen: set[str] = set()
    repeats: set[tuple[str, str, int]] = set()
    with path.open(encoding="utf-8") as stream:
        for index, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                attempt = Attempt.model_validate_json(line)
            except ValueError as exc:
                raise ValueError(f"invalid attempt on line {index}") from exc
            if attempt.attempt_id in seen:
                raise ValueError(f"duplicate attempt id on line {index}")
            identity = (attempt.model, attempt.task_id, attempt.repeat)
            if identity in repeats:
                raise ValueError(f"duplicate model/task/repeat on line {index}")
            repeats.add(identity)
            seen.add(attempt.attempt_id)
            attempts.append(attempt)
    if not attempts:
        raise ValueError("results contain no attempts")
    return attempts


def summarize(
    attempts: list[Attempt],
    ks: tuple[int, ...] = (1, 2, 5, 10),
    *,
    seed: int = DEFAULT_SEED,
    resamples: int = DEFAULT_RESAMPLES,
    confidence: float = DEFAULT_CONFIDENCE,
) -> Summary:
    if not attempts or any(k < 1 for k in ks):
        raise ValueError("need attempts and positive k values")
    if len({row.attempt_id for row in attempts}) != len(attempts):
        raise ValueError("duplicate attempt id")
    if len({(row.model, row.task_id, row.repeat) for row in attempts}) != len(attempts):
        raise ValueError("duplicate model/task/repeat")
    categories: dict[str, str] = {}
    for attempt in attempts:
        category = attempt.category or UNCATEGORIZED
        if categories.setdefault(attempt.task_id, category) != category:
            raise ValueError(f"task {attempt.task_id} has conflicting categories")
    grouped: dict[str, list[Attempt]] = defaultdict(list)
    for attempt in attempts:
        grouped[attempt.model].append(attempt)
    models: list[ModelSummary] = []
    for model, items in sorted(grouped.items()):
        tasks: dict[str, list[Attempt]] = defaultdict(list)
        for item in items:
            tasks[item.task_id].append(item)
        scores = []
        for task, rows in sorted(tasks.items()):
            passed = sum(row.outcome == "pass" for row in rows)
            scores.append(
                TaskScore(
                    task_id=task, attempts=len(rows), passed=passed, pass_at_1=passed / len(rows)
                )
            )
        estimates = {
            k: statistics.mean(pass_at_k(s.attempts, s.passed, k) for s in scores)
            for k in sorted(set(ks) | {1})
            if all(s.attempts >= k for s in scores)
        }
        by_category: dict[str, list[TaskScore]] = defaultdict(list)
        for score in scores:
            by_category[categories[score.task_id]].append(score)
        category_scores = [
            CategoryScore(
                category=name,
                tasks=len(rows),
                attempts=sum(s.attempts for s in rows),
                passed=sum(s.passed for s in rows),
                pass_at_1=statistics.mean(s.pass_at_1 for s in rows),
            )
            for name, rows in sorted(by_category.items())
        ]
        ci = bootstrap_mean_ci(
            [s.pass_at_1 for s in scores], seed=seed, resamples=resamples, confidence=confidence
        )
        times = [row.wall_time_s for row in items]
        ins = [row.input_tokens for row in items if row.input_tokens is not None]
        outs = [row.output_tokens for row in items if row.output_tokens is not None]
        costs = [row.cost_usd for row in items if row.cost_usd is not None]
        models.append(
            ModelSummary(
                model=model,
                attempts=len(items),
                passed=sum(s.passed for s in scores),
                outcomes={
                    state: sum(r.outcome == state for r in items)
                    for state in ("pass", "fail", "error", "timeout")
                },
                pass_at_1=estimates[1],
                pass_at_k=estimates,
                pass_at_1_ci=ci,
                mean_wall_time_s=statistics.mean(times),
                median_wall_time_s=statistics.median(times),
                wall_times_s=times,
                input_tokens=sum(ins) if ins else None,
                output_tokens=sum(outs) if outs else None,
                cost_usd=sum(costs) if costs else None,
                input_tokens_reported=len(ins),
                output_tokens_reported=len(outs),
                cost_reported=len(costs),
                tasks=scores,
                categories=category_scores,
            )
        )
    models.sort(key=lambda m: (-m.pass_at_1, m.mean_wall_time_s, m.model))
    return Summary(
        attempts=len(attempts),
        task_ids=sorted(categories),
        task_categories=dict(sorted(categories.items())),
        models=models,
        bootstrap=BootstrapInfo(seed=seed, resamples=resamples, confidence=confidence),
        comparisons=compare_overlapping(
            models, seed=seed, resamples=resamples, confidence=confidence
        ),
    )


def compare_overlapping(
    models: list[ModelSummary], *, seed: int, resamples: int, confidence: float
) -> list[Comparison]:
    """Paired bootstrap for every model pair whose marginal intervals overlap."""
    comparisons: list[Comparison] = []
    for index, first in enumerate(models):
        for second in models[index + 1 :]:
            (a_low, a_high), (b_low, b_high) = first.pass_at_1_ci, second.pass_at_1_ci
            if a_high < b_low or b_high < a_low:
                continue
            a = {s.task_id: s.pass_at_1 for s in first.tasks}
            b = {s.task_id: s.pass_at_1 for s in second.tasks}
            shared = set(a) & set(b)
            if not shared:
                continue
            diff, low, high = paired_bootstrap_diff(
                a, b, seed=seed, resamples=resamples, confidence=confidence
            )
            significant = low > 0 or high < 0
            level = f"{confidence:.0%}"
            note = (
                f"Intervals overlap, but the paired {level} interval for the difference "
                f"excludes zero: {first.model} differs from {second.model}."
                if significant
                else f"Intervals overlap and the paired {level} interval for the difference "
                f"includes zero: no reliable difference between {first.model} and "
                f"{second.model} on these {len(shared)} tasks."
            )
            comparisons.append(
                Comparison(
                    model_a=first.model,
                    model_b=second.model,
                    shared_tasks=len(shared),
                    diff=diff,
                    ci_low=low,
                    ci_high=high,
                    significant=significant,
                    note=note,
                )
            )
    return comparisons


def summary_json(summary: Summary) -> str:
    return json.dumps(summary.model_dump(mode="json"), indent=2) + "\n"
