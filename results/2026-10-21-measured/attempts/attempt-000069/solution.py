"""Merge closed integer intervals."""

from typing import Iterable, List, Tuple


def _validate_endpoint(value) -> int:
    """Return value as a plain int, or raise ValueError if not a valid integer endpoint."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"interval endpoint must be an integer (not bool), got {value!r}")
    return int(value)


def merge_intervals(intervals: Iterable) -> List[Tuple[int, int]]:
    """
    Merge an iterable of closed integer intervals.

    Each element of ``intervals`` must be a pair ``(start, end)`` of integers
    with ``start <= end``. Overlapping and touching intervals are merged.
    The result is a sorted list of disjoint ``(start, end)`` tuples.

    Raises:
        ValueError: if a pair has the wrong length, has non-integer endpoints
            (bool is rejected), or has ``start > end``.
    """
    if intervals is None:
        raise ValueError("intervals must be an iterable of pairs")

    normalized: List[Tuple[int, int]] = []

    # Iterate exactly once so one-shot iterables (generators, etc.) work,
    # and never mutate the input or its members.
    for item in intervals:
        try:
            pair = tuple(item)
        except TypeError:
            raise ValueError(f"interval must be a pair of integers, got {item!r}") from None
        if len(pair) != 2:
            raise ValueError(f"interval must have exactly 2 endpoints, got {len(pair)}: {item!r}")
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
            # Overlapping or touching (start == cur_end): extend the current interval.
            if end > cur_end:
                cur_end = end
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))

    return merged
