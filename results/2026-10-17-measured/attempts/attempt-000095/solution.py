def merge_intervals(intervals):
    if intervals is None:
        return []
    collected = []
    try:
        iterator = iter(intervals)
    except TypeError:
        raise ValueError("Input must be an iterable of pairs")
    for item in iterator:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("Each interval must be a pair of length 2")
        start, end = item
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("Endpoints must be integers (bool is invalid)")
        if start > end:
            raise ValueError("Start must be <= end")
        collected.append((start, end))
    if not collected:
        return []
    collected.sort()
    merged = []
    for start, end in collected:
        if not merged or merged[-1][1] < start - 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [tuple(iv) for iv in merged]
