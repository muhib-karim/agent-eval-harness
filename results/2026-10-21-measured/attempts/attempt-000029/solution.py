"""Levenshtein edit distance with optional upper bound."""


def levenshtein(a: str, b: str, max_distance: "int | None" = None) -> int:
    if not isinstance(a, str) or not isinstance(b, str):
        raise TypeError("a and b must be str")
    if max_distance is not None:
        if isinstance(max_distance, bool) or not isinstance(max_distance, int):
            raise ValueError("max_distance must be a non-negative int")
        if max_distance < 0:
            raise ValueError("max_distance must be a non-negative int")

    # Strip common prefix.
    start = 0
    limit = min(len(a), len(b))
    while start < limit and a[start] == b[start]:
        start += 1
    # Strip common suffix.
    ea, eb = len(a), len(b)
    while ea > start and eb > start and a[ea - 1] == b[eb - 1]:
        ea -= 1
        eb -= 1
    a = a[start:ea]
    b = b[start:eb]

    # Make a the shorter string (columns), b the longer (rows).
    if len(a) > len(b):
        a, b = b, a
    n, m = len(a), len(b)

    if max_distance is None:
        if n == 0:
            return m
        prev = list(range(n + 1))
        cur = [0] * (n + 1)
        for i in range(1, m + 1):
            bc = b[i - 1]
            cur[0] = i
            for j in range(1, n + 1):
                cost = 0 if a[j - 1] == bc else 1
                x = prev[j - 1] + cost
                y = prev[j] + 1
                if y < x:
                    x = y
                y = cur[j - 1] + 1
                if y < x:
                    x = y
                cur[j] = x
            prev, cur = cur, prev
        return prev[n]

    k = max_distance
    if m - n > k:
        return k + 1
    if n == 0:
        return m  # m <= k here

    big = k + 1
    prev = [j if j <= k else big for j in range(n + 1)]
    cur = [big] * (n + 1)
    for i in range(1, m + 1):
        bc = b[i - 1]
        lo = i - k
        if lo < 1:
            lo = 1
        hi = i + k
        if hi > n:
            hi = n
        if lo == 1:
            cur[0] = i if i <= k else big
        else:
            cur[lo - 1] = big
        row_min = cur[lo - 1]
        for j in range(lo, hi + 1):
            cost = 0 if a[j - 1] == bc else 1
            x = prev[j - 1] + cost
            y = prev[j] + 1
            if y < x:
                x = y
            y = cur[j - 1] + 1
            if y < x:
                x = y
            if x > big:
                x = big
            cur[j] = x
            if x < row_min:
                row_min = x
        if hi < n:
            cur[hi + 1] = big
        if row_min > k:
            return big
        prev, cur = cur, prev
    d = prev[n]
    return d if d <= k else big
