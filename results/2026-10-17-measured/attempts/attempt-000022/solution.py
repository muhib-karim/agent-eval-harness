def merge_intervals(intervals):
    """
    Merge a collection of closed integer intervals into a sorted list of
    disjoint closed intervals, merging overlapping or touching intervals.

    :param intervals: an iterable of pairs (start, end) of integers.
    :return: a sorted list of tuples (start, end) representing merged,
             disjoint closed intervals.
    :raises ValueError: if any pair has the wrong length, contains
             non-integer (or bool) endpoints, or has start > end.
    """
    parsed = []

    for item in intervals:
        try:
            a, b = item
        except (TypeError, ValueError):
            raise ValueError(
                "Each interval must be an iterable of exactly two elements"
            )

        for v in (a, b):
            if isinstance(v, bool) or not isinstance(v, int):
                raise ValueError("Interval endpoints must be integers")

        if a > b:
            raise ValueError("Interval start must be <= end")

        parsed.append((a, b))

    if not parsed:
        return []

    parsed.sort(key=lambda pair: (pair[0], pair[1]))

    merged = []
    for start, end in parsed:
        if merged and start <= merged[-1][1] + 1:
            prev_start, prev_end = merged[-1]
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    return merged
