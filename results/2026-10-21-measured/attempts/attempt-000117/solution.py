def merge_intervals(intervals):
    items = []
    for item in intervals:
        try:
            pair = tuple(item)
        except TypeError:
            raise ValueError("each interval must be a pair of integers")
        if len(pair) != 2:
            raise ValueError("each interval must have exactly two endpoints")
        start, end = pair
        for v in (start, end):
            if not isinstance(v, int) or isinstance(v, bool):
                raise ValueError("endpoints must be integers (bool is invalid)")
        if start > end:
            raise ValueError("interval start must not exceed end")
        items.append((start, end))

    if not items:
        return []

    items.sort()
    merged = []
    cur_start, cur_end = items[0]
    for s, e in items[1:]:
        if s <= cur_end:
            if e > cur_end:
                cur_end = e
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = s, e
    merged.append((cur_start, cur_end))
    return merged
