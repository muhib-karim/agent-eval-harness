def merge_intervals(intervals):
    """
    Merge overlapping and touching closed intervals.

    Args:
        intervals: An iterable of pairs (start, end) representing closed intervals.

    Returns:
        A sorted list of disjoint tuples (start, end).

    Raises:
        ValueError: If a pair has wrong length, non-integer endpoints, or start > end.
    """
    validated = []
    if intervals is None:
        return []

    for pair in intervals:
        # Check if it's a pair (has length 2)
        try:
            if isinstance(pair, (str, bytes)):
                raise ValueError("Invalid interval: string is not a valid interval pair")
            length = len(pair)
        except TypeError:
            raise ValueError("Invalid interval: endpoints must be a pair")

        if length != 2:
            raise ValueError(f"Invalid interval: expected 2 elements, got {length}")

        # Convert to list access to handle any sequence/I iterable
        items = list(pair)
        start, end = items[0], items[1]

        # Validate endpoints are integers (not bool)
        for val in (start, end):
            if isinstance(val, bool) or not isinstance(val, int):
                raise ValueError(f"Invalid endpoint: {val!r} is not an integer")

        # Validate start <= end
        if start > end:
            raise ValueError(f"Invalid interval: start {start} > end {end}")

        validated.append((start, end))

    if not validated:
        return []

    # Sort by start, then end
    validated.sort(key=lambda x: (x[0], x[1]))

    # Merge intervals
    merged = [validated[0]]
    for start, end in validated[1:]:
        last_start, last_end = merged[-1]
        # Merge if overlapping or touching (start <= last_end + 1 covers touching)
        if start <= last_end:
            # Extend the current interval
            if end > last_end:
                merged[-1] = (last_start, end)
        else:
            merged.append((start, end))

    return merged

def merge_intervals(intervals):
    """
    Merge overlapping and touching closed intervals.

    Args:
        intervals: An iterable of pairs (start, end) representing closed intervals.

    Returns:
        A sorted list of disjoint tuples (start, end).

    Raises:
        ValueError: If a pair has wrong length, non-integer endpoints, or start > end.
    """
    validated = []
    if intervals is None:
        return []

    for pair in intervals:
        # Check if it's a pair (has length 2)
        try:
            if isinstance(pair, (str, bytes)):
                raise ValueError("Invalid interval: string is not a valid interval pair")
            length = len(pair)
        except TypeError:
            raise ValueError("Invalid interval: endpoints must be a pair")

        if length != 2:
            raise ValueError(f"Invalid interval: expected 2 elements, got {length}")

        # Convert to list to handle any iterable pair
        items = list(pair)
        start, end = items[0], items[1]

        # Validate endpoints are integers (not bool)
        for val in (start, end):
            if isinstance(val, bool) or not isinstance(val, int):
                raise ValueError(f"Invalid endpoint: {val!r} is not an integer")

        # Validate start <= end
        if start > end:
            raise ValueError(f"Invalid interval: start {start} > end {end}")

        validated.append((start, end))

    if not validated:
        return []

    # Sort by start, then end
    validated.sort(key=lambda x: (x[0], x[1]))

    # Merge intervals
    merged = [validated[0]]
    for start, end in validated[1:]:
        last_start, last_end = merged[-1]
        # Merge if overlapping or touching (start <= last_end)
        if start <= last_end:
            if end > last_end:
                merged[-1] = (last_start, end)
        else:
            merged.append((start, end))

    return merged
