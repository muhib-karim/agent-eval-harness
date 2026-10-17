"""Merge closed integer intervals."""

from typing import Iterable, List, Tuple


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def merge_intervals(intervals: Iterable) -> List[Tuple[int, int]]:
    """Return sorted, disjoint closed intervals covering the input intervals.

    Overlapping intervals and intervals sharing an endpoint are merged.
    Raises ValueError for malformed pairs, non-integer endpoints, or start > end.
    The input and its members are never mutated.
    """
    if intervals is None:
        raise ValueError("intervals must be an iterable of pairs")
    try:
        iterator = iter(intervals)
    except TypeError:
        raise ValueError("intervals must be an iterable of pairs") from None

    normalized: List[Tuple[int, int]] = []
    for item in iterator:
        if isinstance(item, (str, bytes, bytearray)):
            raise ValueError("each interval must be a pair of integers")
        try:
            pair = tuple(item)  # copy; never mutates the member
        except TypeError:
            raise ValueError("each interval must be a pair of integers") from None
        if len(pair) != 2:
            raise ValueError("each interval must have exactly two endpoints")
        start, end = pair
        if not _is_int(start) or not _is_int(end):
            raise ValueError("interval endpoints must be integers (not bool)")
        start, end = int(start), int(end)
        if start > end:
            raise ValueError("interval start must not exceed end")
        normalized.append((start, end))

    if not normalized:
        return []

    normalized.sort()
    merged: List[Tuple[int, int]] = []
    cur_start, cur_end = normalized[0]
    for start, end in normalized[1:]:
        if start <= cur_end:  # overlap or touching endpoint
            if end > cur_end:
                cur_end = end
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))
    return merged
