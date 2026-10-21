def levenshtein(a: str, b: str, max_distance: int | None = None) -> int:
    if not isinstance(a, str) or not isinstance(b, str):
        raise TypeError("a and b must be str")
    if max_distance is not None:
        if isinstance(max_distance, bool) or not isinstance(max_distance, int) or max_distance < 0:
            raise ValueError("max_distance must be a non-negative int")

    # Make b the shorter string (distance is symmetric).
    if len(b) > len(a):
        a, b = b, a
    n, m = len(a), len(b)
    k = max_distance

    if k is not None and n - m > k:
        return k + 1
    if m == 0:
        return n  # here n <= k if k is given

    if k is None or k >= n:
        # Plain two-row DP, O(m) memory.
        prev = list(range(m + 1))
        for i in range(1, n + 1):
            ca = a[i - 1]
            cur = [i] + [0] * m
            for j in range(1, m + 1):
                v = prev[j - 1] + (ca != b[j - 1])
                t = prev[j] + 1
                if t < v:
                    v = t
                t = cur[j - 1] + 1
                if t < v:
                    v = t
                cur[j] = v
            prev = cur
        return prev[m]

    # Banded DP, values capped at INF = k + 1.
    INF = k + 1
    prev = [INF] * (m + 1)
    cur = [INF] * (m + 1)
    for j in range(min(m, k) + 1):
        prev[j] = j
    for i in range(1, n + 1):
        ca = a[i - 1]
        lo = max(1, i - k)
        hi = min(m, i + k)
        if lo == 1:
            cur[0] = i if i <= k else INF
        else:
            cur[lo - 1] = INF
        rowmin = cur[lo - 1]
        for j in range(lo, hi + 1):
            v = prev[j - 1] + (ca != b[j - 1])
            t = prev[j] + 1
            if t < v:
                v = t
            t = cur[j - 1] + 1
            if t < v:
                v = t
            if v > INF:
                v = INF
            cur[j] = v
            if v < rowmin:
                rowmin = v
        if hi + 1 <= m:
            cur[hi + 1] = INF
        if rowmin > k:
            return INF
        prev, cur = cur, prev
    d = prev[m]
    return d if d <= k else INF
