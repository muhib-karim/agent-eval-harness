"""Merge closed integer intervals."""

from typing import Iterable, List, Tuple


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def merge_intervals(intervals: Iterable) -> List[Tuple[int, int]]:
    """Return sorted, disjoint closed intervals.

    Intervals that overlap or share an endpoint are merged.

    Raises ValueError for a pair of the wrong length, non-integer
    endpoints, or start > end. The input and its members are not
    mutated, and one-shot iterables are supported.
    """
    parsed: List[Tuple[int, int]] = []

    for item in intervals:
        # Strings and bytes are not treated as pairs.
        if isinstance(item, (str, bytes, bytearray)):
            raise ValueError(f"invalid interval: {item!r}")
        try:
            pair = tuple(item)
        except TypeError:
            raise ValueError(f"interval must be a pair: {item!r}") from None

        if len(pair) != 2:
            raise ValueError(f"interval must have exactly 2 endpoints: {item!r}")

        start, end = pair
        if not _is_int(start) or not _is_int(end):
            raise ValueError(f"interval endpoints must be integers: {item!r}")
        if start > end:
            raise ValueError(f"interval start greater than end: {item!r}")

        parsed.append((int(start), int(end)))

    if not parsed:
        return []

    parsed.sort()
    merged: List[Tuple[int, int]] = []
    cur_start, cur_end = parsed[0]

    for start, end in parsed[1:]:
        if start <= cur_end:
            # Overlapping or touching: extend the current interval.
            if end > cur_end:
                cur_end = end
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end

    merged.append((cur_start, cur_end))
    return merged
