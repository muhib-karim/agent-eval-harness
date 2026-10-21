"""Merge closed integer intervals.

merge_intervals(intervals) -> list[tuple[int, int]]
"""

from numbers import Integral
from typing import Iterable, List, Tuple


def _is_int(value) -> bool:
    """True for genuine integers (bool is explicitly rejected)."""
    return isinstance(value, Integral) and not isinstance(value, bool)


def _validate_pair(item, index: int) -> Tuple[int, int]:
    """Validate a single interval and return it as a (start, end) tuple."""
    # Strings/bytes are iterable but never valid interval pairs.
    if isinstance(item, (str, bytes, bytearray)):
        raise ValueError(
            f"interval at position {index} must be a pair of integers, got {item!r}"
        )
    try:
        pair = tuple(item)
    except TypeError:
        raise ValueError(
            f"interval at position {index} must be a pair of integers, got {item!r}"
        ) from None

    if len(pair) != 2:
        raise ValueError(
            f"interval at position {index} must have exactly 2 endpoints, "
            f"got {len(pair)}"
        )

    start, end = pair
    if not _is_int(start) or not _is_int(end):
        raise ValueError(
            f"interval at position {index} has non-integer endpoint(s): {pair!r}"
        )
    if start > end:
        raise ValueError(
            f"interval at position {index} has start > end: {pair!r}"
        )
    return (int(start), int(end))


def merge_intervals(intervals: Iterable) -> List[Tuple[int, int]]:
    """Merge overlapping or touching closed intervals.

    Args:
        intervals: an iterable (possibly one-shot) of integer pairs (start, end).

    Returns:
        A sorted list of disjoint closed intervals as (start, end) tuples.

    Raises:
        ValueError: if an item is not a pair of length 2, has non-integer
            endpoints (bool counts as non-integer), or has start > end.
    """
    if intervals is None:
        raise ValueError("intervals must be an iterable of integer pairs, got None")

    # Iterate exactly once (supports generators / one-shot iterables) and
    # build a fresh list of tuples so the input and its members are never
    # mutated.
    validated: List[Tuple[int, int]] = []
    for index, item in enumerate(intervals):
        validated.append(_validate_pair(item, index))

    if not validated:
        return []

    validated.sort()

    merged: List[Tuple[int, int]] = []
    cur_start, cur_end = validated[0]
    for start, end in validated[1:]:
        if start <= cur_end:
            # Overlapping or touching (shared endpoint) -> extend current.
            if end > cur_end:
                cur_end = end
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))

    return merged


if __name__ == "__main__":
    # Simple self-checks.
    assert merge_intervals([]) == []
    assert merge_intervals([(1, 3), (2, 6), (8, 10), (15, 18)]) == [(1, 6), (8, 10), (15, 18)]
    assert merge_intervals([(1, 4), (4, 5)]) == [(1, 5)]
    assert merge_intervals([(5, 5)]) == [(5, 5)]
    assert merge_intervals([(-5, -1), (-2, 3)]) == [(-5, 3)]
    assert merge_intervals(iter([[3, 4], [1, 2]])) == [(1, 2), (3, 4)]
    assert merge_intervals([(1, 2), (3, 4)]) == [(1, 2), (3, 4)]

    for bad in ([(1, 2, 3)], [(1,)], [(True, 2)], [(1, 2.0)], [(3, 1)], ["ab"], [5]):
        try:
            merge_intervals(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad!r}")

    original = [[1, 3], [2, 4]]
    snapshot = [list(p) for p in original]
    merge_intervals(original)
    assert original == snapshot
    print("ok")
