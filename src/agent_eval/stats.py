"""Seeded task-level bootstrap confidence intervals for task-macro pass rates.

Pass@1 is averaged over tasks, so the unit of resampling is the task: each replicate
draws ``len(tasks)`` tasks with replacement and averages their per-task pass rates.
The interval is the percentile interval of those replicate means. Repeats within a task
are kept together, so the interval reflects uncertainty about the task sample rather
than pretending repeated attempts are independent tasks.
"""

from __future__ import annotations

import random
import statistics
from collections.abc import Mapping, Sequence

DEFAULT_SEED = 20261021
DEFAULT_RESAMPLES = 2000
DEFAULT_CONFIDENCE = 0.95


def _check(resamples: int, confidence: float) -> None:
    if resamples < 1:
        raise ValueError("resamples must be positive")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")


def percentile(sorted_values: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile of already sorted values, ``0 <= q <= 1``."""
    if not sorted_values:
        raise ValueError("need at least one value")
    if not 0 <= q <= 1:
        raise ValueError("q must be between 0 and 1")
    position = q * (len(sorted_values) - 1)
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def bootstrap_mean_ci(
    values: Sequence[float],
    *,
    seed: int = DEFAULT_SEED,
    resamples: int = DEFAULT_RESAMPLES,
    confidence: float = DEFAULT_CONFIDENCE,
) -> tuple[float, float]:
    """Percentile bootstrap interval for the mean of ``values`` (one value per task)."""
    _check(resamples, confidence)
    if not values:
        raise ValueError("need at least one value")
    rng = random.Random(seed)
    n = len(values)
    means = sorted(statistics.fmean(rng.choices(values, k=n)) for _ in range(resamples))
    tail = (1 - confidence) / 2
    return percentile(means, tail), percentile(means, 1 - tail)


def paired_bootstrap_diff(
    first: Mapping[str, float],
    second: Mapping[str, float],
    *,
    seed: int = DEFAULT_SEED,
    resamples: int = DEFAULT_RESAMPLES,
    confidence: float = DEFAULT_CONFIDENCE,
) -> tuple[float, float, float]:
    """Mean difference ``first - second`` over shared tasks and its paired bootstrap interval.

    Resampling the same tasks for both models removes between-task variance that the two
    marginal intervals double count, so overlapping marginal intervals can still hide a
    difference whose paired interval excludes zero.
    """
    shared = sorted(set(first) & set(second))
    if not shared:
        raise ValueError("models share no tasks")
    diffs = [first[task] - second[task] for task in shared]
    low, high = bootstrap_mean_ci(diffs, seed=seed, resamples=resamples, confidence=confidence)
    return statistics.fmean(diffs), low, high
