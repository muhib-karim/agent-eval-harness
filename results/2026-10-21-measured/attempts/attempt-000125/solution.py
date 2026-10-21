def levenshtein(a: str, b: str, max_distance: int | None = None) -> int:
    if not isinstance(a, str) or not isinstance(b, str):
        raise TypeError("a and b must be str")
    if max_distance is not None:
        if isinstance(max_distance, bool) or not isinstance(max_distance, int) or max_distance < 0:
            raise ValueError("max_distance must be a non-negative int")

    # make b the shorter string
    if len(a) < len(b):
        a, b = b, a
    n, m = len(a), len(b)

    if max_distance is None:
        if m == 0:
            return n
        prev = list(range(m + 1))
        for i in range(1, n + 1):
            ca = a[i - 1]
            cur = [i] + [0] * m
            left = i
            for j in range(1, m + 1):
                v = prev[j - 1] + (ca != b[j - 1])
                t = prev[j] + 1
                if t < v:
                    v = t
                t = left + 1
                if t < v:
                    v = t
                cur[j] = v
                left = v
            prev = cur
        return prev[m]

    k = max_distance
    cap = k + 1
    if n - m > k:
        return cap
    if m == 0:
        return n if n <= k else cap

    prev = [cap] * (m + 1)
    for j in range(min(m, k) + 1):
        prev[j] = j
    cur = [cap] * (m + 1)
    for i in range(1, n + 1):
        ca = a[i - 1]
        lo = max(1, i - k)
        hi = min(m, i + k)
        if lo == 1:
            cur[0] = i if i < cap else cap
        else:
            cur[lo - 1] = cap
        best = cur[lo - 1] if lo == 1 else cap
        left = cur[lo - 1]
        for j in range(lo, hi + 1):
            v = prev[j - 1] + (ca != b[j - 1])
            t = prev[j] + 1
            if t < v:
                v = t
            t = left + 1
            if t < v:
                v = t
            if v > cap:
                v = cap
            cur[j] = v
            left = v
            if v < best:
                best = v
        if best > k:
            return cap
        prev, cur = cur, prev
    r = prev[m]
    return r if r <= k else cap
