import math

import pytest
from search import count_range, find_first, find_last


class Probe(list):  # type: ignore[type-arg]
    """A list that counts element reads and forbids iteration."""

    def __init__(self, values: list[int]) -> None:
        super().__init__(values)
        self.reads = 0

    def __getitem__(self, index):  # type: ignore[no-untyped-def]
        if isinstance(index, slice):
            raise AssertionError("slicing is not allowed")
        self.reads += 1
        return super().__getitem__(index)

    def __iter__(self):  # type: ignore[no-untyped-def]
        raise AssertionError("iteration is not allowed")


def test_find_last_reported_cases() -> None:
    assert find_last([1, 2, 2, 3], 2) == 2
    assert find_last([5], 5) == 0


def test_find_last_runs_and_ends() -> None:
    items = [1, 1, 1, 4, 4, 9]
    assert find_last(items, 1) == 2
    assert find_last(items, 4) == 4
    assert find_last(items, 9) == 5


def test_find_last_absent() -> None:
    assert find_last([], 3) == -1
    assert find_last([1, 3, 5], 0) == -1
    assert find_last([1, 3, 5], 4) == -1
    assert find_last([1, 3, 5], 6) == -1


def test_find_first_regression() -> None:
    items = [1, 2, 2, 2, 7]
    assert find_first(items, 2) == 1
    assert find_first(items, 1) == 0
    assert find_first(items, 7) == 4
    assert find_first(items, 3) == -1
    assert find_first([], 1) == -1


def test_count_range_regression() -> None:
    items = [1, 2, 2, 3, 5, 8]
    assert count_range(items, 2, 3) == 3
    assert count_range(items, 0, 100) == 6
    assert count_range(items, 4, 4) == 0
    assert count_range(items, 5, 2) == 0
    assert count_range([], 0, 1) == 0


@pytest.mark.parametrize("target", [-1, 0, 3, 7, 10])
def test_all_agree_with_linear_scan(target: int) -> None:
    items = [0, 0, 3, 3, 3, 7, 10, 10]
    present = [i for i, x in enumerate(items) if x == target]
    assert find_first(items, target) == (present[0] if present else -1)
    assert find_last(items, target) == (present[-1] if present else -1)


def test_find_last_is_logarithmic() -> None:
    probe = Probe(list(range(0, 200_000, 2)))
    assert find_last(probe, 123_456) == 61_728
    assert probe.reads <= 2 * math.ceil(math.log2(len(probe))) + 4


def test_find_first_and_count_stay_logarithmic() -> None:
    probe = Probe([5] * 100_000)
    assert find_first(probe, 5) == 0
    assert count_range(probe, 5, 5) == 100_000
    assert probe.reads <= 4 * math.ceil(math.log2(100_000)) + 8
