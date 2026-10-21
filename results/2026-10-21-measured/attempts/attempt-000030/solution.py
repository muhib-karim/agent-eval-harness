def levenshtein(a, b, max_distance=None):
    if not isinstance(a, str) or not isinstance(b, str):
        raise TypeError("a and b must be str")
    if max_distance is not None:
        if isinstance(max_distance, bool) or not isinstance(max_distance, int):
            raise ValueError("max_distance must be a non-negative int")
        if max_distance < 0:
            raise ValueError("max_distance must be a non-negative int")

    # Make s the longer string (rows), t the shorter (columns).
    if len(a) < len(b):
        s, t = b, a
    else:
        s, t = a, b

    # Strip common prefix and suffix via index offsets (no slicing copies).
    start = 0
    s_end = len(s)
    t_end = len(t)
    while start < t_end and s[start] == t[start]:
        start += 1
    while t_end > start and s[s_end - 1] == t[t_end - 1]:
        s_end -= 1
        t_end -= 1

    m = s_end - start
    n = t_end - start

    if max_distance is None:
        if n == 0:
            return m
        prev = list(range(n + 1))
        cur = [0] * (n + 1)
        for i in range(1, m + 1):
            sc = s[start + i - 1]
            cur[0] = i
            for j in range(1, n + 1):
                cost = prev[j - 1] + (sc != t[start + j - 1])
                ins = cur[j - 1] + 1
                dele = prev[j] + 1
                if ins < cost:
                    cost = ins
                if dele < cost:
                    cost = dele
                cur[j] = cost
            prev, cur = cur, prev
        return prev[n]

    k = max_distance
    big = k + 1
    if m - n > k:
        return big
    if n == 0:
        return m if m <= k else big

    prev = [big] * (n + 1)
    cur = [big] * (n + 1)
    for j in range(0, min(n, k) + 1):
        prev[j] = j

    for i in range(1, m + 1):
        sc = s[start + i - 1]
        lo = i - k
        if lo < 1:
            lo = 1
        hi = i + k
        if hi > n:
            hi = n
        if lo > hi:
            return big
        if lo == 1:
            cur[0] = i if i <= k else big
        else:
            cur[lo - 1] = big
        row_min = big
        for j in range(lo, hi + 1):
            cost = prev[j - 1] + (sc != t[start + j - 1])
            ins = cur[j - 1] + 1
            dele = prev[j] + 1
            if ins < cost:
                cost = ins
            if dele < cost:
                cost = dele
            if cost > big:
                cost = big
            cur[j] = cost
            if cost < row_min:
                row_min = cost
        if row_min > k:
            return big
        prev, cur = cur, prev

    result = prev[n]
    return result if result <= k else big
