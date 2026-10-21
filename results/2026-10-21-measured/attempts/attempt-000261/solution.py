def merge_intervals(intervals) -> list[tuple[int, int]]:
    """Return sorted, disjoint closed intervals."""
    validated = []

    for pair in intervals:
        try:
            start, end = pair
        except (TypeError, ValueError) as exc:
            raise ValueError("each interval must have exactly two endpoints") from exc

        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
        ):
            raise ValueError("interval endpoints must be integers")
        if start > end:
            raise ValueError("interval start must not exceed end")

        validated.append((start, end))

    validated.sort()
    merged = []

    for start, end in validated:
        if merged and start <= merged[-1][1]:
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))

    return merged
