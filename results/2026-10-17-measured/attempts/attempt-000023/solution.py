def merge_intervals(intervals):
    """
    Merge overlapping and touching closed integer intervals.

    Args:
        intervals: an iterable of pairs (start, end) of integers.

    Returns:
        A sorted list of disjoint closed intervals (as tuples) where any
        overlapping or touching (adjacent, i.e. no gap) intervals have
        been merged together.

    Raises:
        ValueError: if any item is not a pair, if endpoints are not
            integers (bool excluded), or if start > end for any pair.
    """
    validated = []

    for item in intervals:
        # Must be a pair of exactly two elements.
        try:
            items = list(item)
        except TypeError:
            raise ValueError(f"Invalid interval (not iterable): {item!r}")

        if len(items) != 2:
            raise ValueError(f"Invalid interval (wrong length): {item!r}")

        start, end = items

        # Reject bools explicitly, even though bool is a subclass of int.
        if isinstance(start, bool) or isinstance(end, bool):
            raise ValueError(f"Invalid interval (bool endpoint): {item!r}")

        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError(f"Invalid interval (non-integer endpoint): {item!r}")

        if start > end:
            raise ValueError(f"Invalid interval (start > end): {item!r}")

        validated.append((start, end))

    if not validated:
        return []

    validated.sort(key=lambda pair: (pair[0], pair[1]))

    merged = [validated[0]]

    for start, end in validated[1:]:
        last_start, last_end = merged[-1]

        # Merge if overlapping or touching (no gap between them).
        if start <= last_end + 1:
            if end > last_end:
                merged[-1] = (last_start, end)
            # else fully contained; nothing to do
        else:
            merged.append((start, end))

    return merged
