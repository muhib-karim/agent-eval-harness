def merge_intervals(intervals) -> list[tuple[int, int]]:
    """Return sorted, disjoint closed intervals."""
    validated = []

    for pair in intervals:
        try:
            start, end = pair
        except (TypeError, ValueError) as exc:
            raise ValueError("Each interval must contain exactly two endpoints") from exc

        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
        ):
            raise ValueError("Interval endpoints must be integers, not bools")
        if start > end:
            raise ValueError("Interval start must not exceed its end")

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
