import math
import statistics

import pytest
from running_stats import RunningStats


def stats_of(values: list[float]) -> RunningStats:
    stats = RunningStats()
    for value in values:
        stats.push(value)
    return stats


def test_reported_merge_case() -> None:
    merged = stats_of([1, 2, 3]).merge(stats_of([10, 11, 12]))
    assert merged.count == 6
    assert merged.mean == pytest.approx(6.5)
    assert merged.variance == pytest.approx(25.1)


def test_merge_matches_pushing_everything() -> None:
    left, right = [2.5, -1.0, 4.0, 4.0], [100.0, 98.5, 101.25]
    merged = stats_of(left).merge(stats_of(right))
    assert merged.variance == pytest.approx(statistics.variance(left + right))
    assert merged.stdev == pytest.approx(statistics.stdev(left + right))


def test_merge_with_single_values() -> None:
    merged = stats_of([1.0]).merge(stats_of([3.0]))
    assert merged.variance == pytest.approx(2.0)


def test_merge_with_empty_either_side() -> None:
    full = stats_of([1, 2, 4])
    assert full.merge(RunningStats()).variance == pytest.approx(full.variance)
    assert RunningStats().merge(full).mean == pytest.approx(full.mean)
    assert RunningStats().merge(RunningStats()).count == 0


def test_merge_leaves_inputs_unchanged() -> None:
    a, b = stats_of([1, 2]), stats_of([7, 9])
    merged = a.merge(b)
    assert merged is not a and merged is not b
    assert (a.count, a.mean, b.count, b.mean) == (2, 1.5, 2, 8.0)


def test_push_regression() -> None:
    stats = stats_of([2, 4, 4, 4, 5, 5, 7, 9])
    assert stats.count == 8
    assert stats.mean == pytest.approx(5.0)
    assert stats.variance == pytest.approx(32 / 7)
    assert stats.stdev == pytest.approx(math.sqrt(32 / 7))


def test_large_offset_is_stable() -> None:
    values = [1e9 + x for x in (4.0, 7.0, 13.0, 16.0)]
    stats = stats_of(values[:2]).merge(stats_of(values[2:]))
    assert stats.variance == pytest.approx(30.0, rel=1e-6)


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), "1", None])
def test_push_rejects_invalid(bad: object) -> None:
    stats = RunningStats()
    with pytest.raises(ValueError):
        stats.push(bad)  # type: ignore[arg-type]
    assert stats.count == 0


def test_too_few_values_raise() -> None:
    with pytest.raises(ValueError):
        _ = RunningStats().mean
    with pytest.raises(ValueError):
        _ = stats_of([1.0]).variance
    with pytest.raises(ValueError):
        _ = stats_of([1.0]).merge(RunningStats()).stdev
