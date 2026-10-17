def merge_intervals(intervals):
    """
    Merge a collection of closed integer intervals.

    Parameters
    ----------
    intervals : iterable of pairs of int
        Each pair represents a closed interval [start, end].

    Returns
    -------
    list[tuple[int, int]]
        Sorted list of disjoint, merged closed intervals.

    Raises
    ------
    ValueError
        If any pair does not have exactly two elements, if the
        endpoints are not integers (bool is explicitly rejected),
        or if start > end for any interval.
    """
    normalized = []

    for pair in intervals:
        try:
            start, end = pair
        except (TypeError, ValueError):
            raise ValueError(
                "Each interval must be a pair (start, end) of two elements"
            )

        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
        ):
            raise ValueError("Interval endpoints must be integers (not bool)")

        if start > end:
            raise ValueError(f"Invalid interval: start ({start}) > end ({end})")

        normalized.append((start, end))

    # Sort by start, then end, to process intervals in order.
    normalized.sort(key=lambda iv: (iv[0], iv[1]))

    merged = []
    for start, end in normalized:
        if merged and start <= merged[-1][1]:
            prev_start, prev_end = merged[-1]
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    return merged
