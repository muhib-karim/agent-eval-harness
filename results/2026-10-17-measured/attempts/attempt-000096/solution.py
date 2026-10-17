def merge_intervals(intervals):
    interval_list = []
    for item in intervals:
        try:
            if len(item) != 2:
                raise ValueError("pair of the wrong length")
        except TypeError:
            raise ValueError("pair of the wrong length")
        start, end = item
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("non-integer endpoints")
        if start > end:
            raise ValueError("start > end")
        interval_list.append((start, end))
    if not interval_list:
        return []
    interval_list.sort()
    merged = []
    current_start, current_end = interval_list[0]
    for start, end in interval_list[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    merged.append((current_start, current_end))
    return merged
