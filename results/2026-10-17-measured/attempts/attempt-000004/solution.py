"""Merge closed integer intervals."""

from typing import Iterable, List, Tuple


def _validate_endpoint(value) -> int:
    # bool is a subclass of int, so it has to be rejected explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"interval endpoint must be an integer, got {value!r}")
    return int(value)


def merge_intervals(intervals: Iterable) -> List[Tuple[int, int]]:
    """Return sorted, disjoint closed intervals.

    Intervals that overlap or share an endpoint are merged. The input and its
    members are never mutated. One-shot iterables are supported because the
    input is consumed exactly once.
    """
    if intervals is None:
        raise ValueError("intervals must be an iterable of pairs")
    try:
        iterator = iter(intervals)
    except TypeError:
        raise ValueError("intervals must be an iterable of pairs") from None

    parsed: List[Tuple[int, int]] = []
    for item in iterator:
        # Strings and bytes have a length but are not valid pairs.
        if isinstance(item, (str, bytes, bytearray)):
            raise ValueError(f"interval must be a pair of integers, got {item!r}")
        try:
            pair = tuple(item)
        except TypeError:
            raise ValueError(
                f"interval must be a pair of integers, got {item!r}"
            ) from None
        if len(pair) != 2:
            raise ValueError(
                f"interval must have exactly 2 endpoints, got {len(pair)}"
            )
        start = _validate_endpoint(pair[0])
        end = _validate_endpoint(pair[1])
        if start > end:
            raise ValueError(f"interval start {start} is greater than end {end}")
        parsed.append((start, end))

    if not parsed:
        return []

    parsed.sort()
    merged: List[Tuple[int, int]] = []
    cur_start, cur_end = parsed[0]
    for start, end in parsed[1:]:
        if start <= cur_end:  # overlapping or touching endpoints
            if end > cur_end:
                cur_end = end
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))
    return merged
