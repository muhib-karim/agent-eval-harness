"""Merge closed integer intervals."""

from numbers import Integral
from typing import Iterable, List, Tuple


def _validate_endpoint(value) -> int:
    """Return value as an int if it is a valid integer endpoint, else raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"interval endpoint must be an integer (not bool), got {value!r}")
    return int(value)


def merge_intervals(intervals: Iterable) -> List[Tuple[int, int]]:
    """Merge overlapping and touching closed intervals.

    Args:
        intervals: an iterable (possibly one-shot) of pairs ``(start, end)``
            with integer endpoints and ``start <= end``.

    Returns:
        A new list of disjoint ``(start, end)`` tuples sorted by start,
        where overlapping or touching intervals have been merged.

    Raises:
        ValueError: if a member is not a pair of length 2, if an endpoint
            is not an integer (bool is rejected), or if ``start > end``.
    """
    normalized: List[Tuple[int, int]] = []

    # Iterate exactly once so one-shot iterables (generators, iterators) work.
    for item in intervals:
        try:
            pair = tuple(item)
        except TypeError:
            raise ValueError(f"interval must be a pair of integers, got {item!r}") from None
        if len(pair) != 2:
            raise ValueError(f"interval must have exactly 2 endpoints, got {len(pair)}: {pair!r}")
        start = _validate_endpoint(pair[0])
        end = _validate_endpoint(pair[1])
        if start > end:
            raise ValueError(f"interval start must not exceed end, got ({start}, {end})")
        normalized.append((start, end))

    if not normalized:
        return []

    normalized.sort()

    merged: List[Tuple[int, int]] = []
    cur_start, cur_end = normalized[0]
    for start, end in normalized[1:]:
        if start <= cur_end:
            # Overlapping or touching (shared endpoint): extend current interval.
            if end > cur_end:
                cur_end = end
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))

    return merged
