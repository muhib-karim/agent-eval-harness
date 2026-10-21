def levenshtein(a: str, b: str, max_distance: "int | None" = None) -> int:
    """
    Compute the Levenshtein edit distance between two strings.

    If max_distance is given and the true distance exceeds it, return
    max_distance + 1. Uses a banded dynamic programme with two rows,
    so extra memory is O(min(len(a), len(b))) and time is
    O(min(len(a), len(b)) * max_distance) when a bound is supplied.
    """
    if not isinstance(a, str) or not isinstance(b, str):
        raise TypeError("levenshtein() arguments must be str")

    if max_distance is not None:
        if isinstance(max_distance, bool) or not isinstance(max_distance, int):
            raise ValueError("max_distance must be a non-negative int or None")
        if max_distance < 0:
            raise ValueError("max_distance must be non-negative")

    # Strip common prefix.
    n, m = len(a), len(b)
    lim = n if n < m else m
    p = 0
    while p < lim and a[p] == b[p]:
        p += 1
    # Strip common suffix.
    s = 0
    while s < lim - p and a[n - 1 - s] == b[m - 1 - s]:
        s += 1
    if p or s:
        a = a[p:n - s]
        b = b[p:m - s]
        n, m = len(a), len(b)

    # Make b the shorter string (row width is m + 1).
    if n < m:
        a, b = b, a
        n, m = m, n

    if max_distance is None:
        k = n
    else:
        k = max_distance
        if n - m > k:
            return k + 1

    if m == 0:
        return n  # guaranteed <= k here (or k is n)

    INF = k + 1

    prev = [INF] * (m + 1)
    for j in range(min(m, k) + 1):
        prev[j] = j
    cur = [INF] * (m + 1)

    bounded = max_distance is not None

    for i in range(1, n + 1):
        ca = a[i - 1]
        lo = i - k if i - k > 0 else 0
        hi = i + k if i + k < m else m

        if lo == 0:
            cur[0] = i
            left = i
            start = 1
        else:
            cur[lo - 1] = INF
            left = INF
            start = lo

        diag = prev[start - 1]
        for j in range(start, hi + 1):
            up = prev[j]
            cost = diag + (ca != b[j - 1])
            if up + 1 < cost:
                cost = up + 1
            if left + 1 < cost:
                cost = left + 1
            cur[j] = cost
            left = cost
            diag = up

        if hi < m:
            cur[hi + 1] = INF

        if bounded:
            if min(cur[lo:hi + 1]) > k:
                return k + 1

        prev, cur = cur, prev

    result = prev[m]
    if bounded and result > k:
        return k + 1
    return result
