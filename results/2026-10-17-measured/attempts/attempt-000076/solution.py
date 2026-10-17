def merge_intervals(intervals):
    items = []
    for pair in intervals:
        try:
            a, b = pair
        except (TypeError, ValueError):
            raise ValueError("Each interval must be a pair of length 2")
        if len(tuple(pair)) != 2:
            raise ValueError("Each interval must be a pair of length 2")
        if isinstance(a, bool) or isinstance(b, bool):
            raise ValueError("Endpoint must be an integer, not bool")
        if not isinstance(a, int) or not isinstance(b, int):
            raise ValueError("Endpoint must be an integer")
        if a > b:
            raise ValueError("Start must not be greater than end")
        items.append((a, b))
    if not items:
        return []
    items.sort()
    merged = [items[0]]
    for start, end in items[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 1:
            if end > last_end:
                merged[-1] = (last_start, end)
        else:
            merged.append((start, end))
    return merged
