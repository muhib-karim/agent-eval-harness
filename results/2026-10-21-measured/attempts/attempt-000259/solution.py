def merge_intervals(intervals) -> list[tuple[int, int]]:
    validated = []

    for pair in intervals:
        try:
            endpoints = tuple(pair)
        except TypeError as exc:
            raise ValueError("each interval must be a pair of endpoints") from exc

        if len(endpoints) != 2:
            raise ValueError("each interval must have exactly two endpoints")

        start, end = endpoints
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
        ):
            raise ValueError("interval endpoints must be integers, not bools")
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
