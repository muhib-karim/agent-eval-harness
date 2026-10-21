def merge_intervals(intervals):
    """
    Merge a collection of closed integer intervals.

    Parameters
    ----------
    intervals : iterable of pairs of int
        Each pair (start, end) represents a closed interval [start, end].
        `start` and `end` must be integers (bool is not accepted) and
        start <= end.

    Returns
    -------
    list[tuple[int, int]]
        Sorted list of disjoint closed intervals, with overlapping or
        touching (sharing an endpoint) intervals merged together.

    Raises
    ------
    ValueError
        If any element is not a pair, contains non-integer endpoints
        (bool included), or has start > end.
    """
    validated = []

    for item in intervals:
        # Must be a pair (length 2), without consuming/mutating original
        try:
            length = len(item)
        except TypeError:
            # Could be an iterator-like item without len; try to unpack safely
            item = tuple(item)
            length = len(item)

        if length != 2:
            raise ValueError(f"Interval must have exactly 2 elements, got {length}")

        start, end = item[0], item[1]

        # Reject bools explicitly, since bool is a subclass of int
        if isinstance(start, bool) or isinstance(end, bool):
            raise ValueError("Interval endpoints must be int, not bool")

        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("Interval endpoints must be integers")

        if start > end:
            raise ValueError(f"Interval start {start} cannot exceed end {end}")

        validated.append((start, end))

    if not validated:
        return []

    # Sort by start, then by end, without mutating original data
    validated.sort(key=lambda pair: (pair[0], pair[1]))

    merged = [validated[0]]

    for start, end in validated[1:]:
        last_start, last_end = merged[-1]

        if start <= last_end:
            # Overlapping or touching (shared endpoint) -> merge
            new_end = max(last_end, end)
            merged[-1] = (last_start, new_end)
        else:
            merged.append((start, end))

    return merged
