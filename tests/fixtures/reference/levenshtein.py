def levenshtein(a, b, max_distance=None):
    if not isinstance(a, str) or not isinstance(b, str):
        raise TypeError("arguments must be str")
    if max_distance is not None and (type(max_distance) is not int or max_distance < 0):
        raise ValueError("max_distance must be a non-negative int")
    if len(a) < len(b):
        a, b = b, a
    bound = max_distance
    if bound is not None and len(a) - len(b) > bound:
        return bound + 1
    big = len(a) + len(b) + 1
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        if bound is None:
            lo, hi = 1, len(b)
        else:
            lo, hi = max(1, i - bound), min(len(b), i + bound)
        current = [big] * (len(b) + 1)
        if lo == 1:
            current[0] = i
        for j in range(lo, hi + 1):
            cost = 0 if ca == b[j - 1] else 1
            current[j] = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
        if bound is not None and min(current[max(0, lo - 1) : hi + 1]) > bound:
            return bound + 1
        previous = current
    result = previous[len(b)]
    if bound is not None and result > bound:
        return bound + 1
    return result
