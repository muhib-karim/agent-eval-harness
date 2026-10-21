def levenshtein(a, b, max_distance=None):
    if not isinstance(a, str) or not isinstance(b, str):
        raise TypeError("a and b must be str")
    if max_distance is not None:
        if isinstance(max_distance, bool) or not isinstance(max_distance, int):
            raise ValueError("max_distance must be a non-negative int")
        if max_distance < 0:
            raise ValueError("max_distance must be a non-negative int")

    if a == b:
        return 0

    # Strip common prefix
    start = 0
    la, lb = len(a), len(b)
    lim = min(la, lb)
    while start < lim and a[start] == b[start]:
        start += 1
    # Strip common suffix
    ea, eb = la, lb
    while ea > start and eb > start and a[ea - 1] == b[eb - 1]:
        ea -= 1
        eb -= 1
    a = a[start:ea]
    b = b[start:eb]

    # Ensure b is the shorter string (memory O(len(b)))
    if len(a) < len(b):
        a, b = b, a
    m, n = len(a), len(b)

    if max_distance is not None:
        k = max_distance
        if m - n > k:
            return k + 1
    else:
        k = m

    if n == 0:
        return m  # m - n <= k guaranteed here

    big = k + 1
    prev = [j if j <= k else big for j in range(n + 1)]
    cur = [big] * (n + 1)

    for i in range(1, m + 1):
        ca = a[i - 1]
        lo = i - k
        if lo < 1:
            lo = 1
        hi = i + k
        if hi > n:
            hi = n
        if lo == 1:
            first = i if i <= k else big
        else:
            first = big
        cur[lo - 1] = first
        rowmin = first
        left = first
        for j in range(lo, hi + 1):
            cost = prev[j - 1] + (ca != b[j - 1])
            x = prev[j] + 1
            if x < cost:
                cost = x
            x = left + 1
            if x < cost:
                cost = x
            if cost > big:
                cost = big
            cur[j] = cost
            left = cost
            if cost < rowmin:
                rowmin = cost
        if hi < n:
            cur[hi + 1] = big
        if rowmin > k:
            return big
        prev, cur = cur, prev

    result = prev[n]
    return result if result <= k else big
