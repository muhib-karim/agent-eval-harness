def merge_intervals(intervals) -> list[tuple[int, int]]:
    """
    Merge overlapping and touching intervals.

    Args:
        intervals: An iterable of pairs of integer endpoints

    Returns:
        A sorted list of disjoint closed intervals (tuples)

    Raises:
        ValueError: If a pair has wrong length, non-integer endpoints, or start > end
    """
    # Convert to list to allow iteration without mutation concerns
    interval_list = list(intervals)

    # Handle empty input
    if not interval_list:
        return []

    # Validate and convert all intervals
    validated_intervals = []
    for pair in interval_list:
        # Check if it's an iterable pair
        try:
            pair_list = list(pair)
        except TypeError:
            raise ValueError("Each interval must be a pair of integers")

        # Check pair length
        if len(pair_list) != 2:
            raise ValueError("Each interval must be a pair of integers")

        start, end = pair_list

        # Check types - bool is a subclass of int in Python, so we need to exclude it explicitly
        if isinstance(start, bool) or isinstance(end, bool):
            raise ValueError("Interval endpoints must be integers, not booleans")

        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("Interval endpoints must be integers")

        # Check start <= end
        if start > end:
            raise ValueError("Interval start must be <= end")

        validated_intervals.append((start, end))

    # Sort intervals by start point, then by end point
    sorted_intervals = sorted(validated_intervals)

    # Merge overlapping and touching intervals
    merged = []
    current_start, current_end = sorted_intervals[0]

    for start, end in sorted_intervals[1:]:
        # Check if intervals overlap or touch (current_end >= start - 1 means they touch or overlap)
        # Since we're dealing with closed intervals [a,b] and [c,d]:
        # They touch or overlap if b >= c - 1, but actually for closed intervals [a,b] and [c,d]
        # they overlap or touch if b >= c - 1 (they touch when b = c - 1 in continuous sense)
        # But in discrete integers, [1,2] and [3,4] don't touch, but [1,3] and [3,5] do touch at 3
        # So intervals [a,b] and [c,d] (where a <= c due to sorting) touch/overlap if b >= c - 1

        if current_end >= start - 1:
            # Merge by extending the current interval
            current_end = max(current_end, end)
        else:
            # No overlap, save current interval and start a new one
            merged.append((current_start, current_end))
            current_start, current_end = start, end

    # Don't forget to add the last interval
    merged.append((current_start, current_end))

    return merged
