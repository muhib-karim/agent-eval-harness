def levenshtein(a: str, b: str, max_distance: int | None = None) -> int:
    if not isinstance(a, str) or not isinstance(b, str):
        raise TypeError("a and b must be strings")
    if max_distance is not None and (
        isinstance(max_distance, bool)
        or not isinstance(max_distance, int)
        or max_distance < 0
    ):
        raise ValueError("max_distance must be a non-negative int or None")

    if len(a) < len(b):
        a, b = b, a

    n, m = len(a), len(b)
    if max_distance is not None:
        if n - m > max_distance:
            return max_distance + 1
        if max_distance == 0:
            return int(a != b)

    # Remove matching ends without creating substring copies.
    start = 0
    while start < m and a[start] == b[start]:
        start += 1

    a_end, b_end = n, m
    while b_end > start and a[a_end - 1] == b[b_end - 1]:
        a_end -= 1
        b_end -= 1

    n = a_end - start
    m = b_end - start
    if m == 0:
        if max_distance is not None and n > max_distance:
            return max_distance + 1
        return n

    if max_distance is None or max_distance >= n:
        previous = list(range(m + 1))
        for i in range(1, n + 1):
            current = [i]
            char_a = a[start + i - 1]
            for j in range(1, m + 1):
                current.append(
                    min(
                        previous[j] + 1,
                        current[j - 1] + 1,
                        previous[j - 1] + (char_a != b[start + j - 1]),
                    )
                )
            previous = current
        return previous[m]

    # Only cells within max_distance of the diagonal can be part of
    # an edit sequence short enough to matter.
    limit = max_distance
    over_limit = limit + 1
    previous_start = 0
    previous = list(range(min(m, limit) + 1))

    for i in range(1, n + 1):
        row_start = max(0, i - limit)
        row_end = min(m, i + limit)
        current = []
        row_min = over_limit
        char_a = a[start + i - 1]

        for j in range(row_start, row_end + 1):
            if j == 0:
                value = i
            else:
                deletion = (
                    previous[j - previous_start] + 1
                    if previous_start <= j < previous_start + len(previous)
                    else over_limit
                )
                insertion = current[-1] + 1 if j > row_start else over_limit
                substitution = (
                    previous[j - 1 - previous_start]
                    + (char_a != b[start + j - 1])
                    if previous_start <= j - 1 < previous_start + len(previous)
                    else over_limit
                )
                value = min(deletion, insertion, substitution, over_limit)

            current.append(value)
            row_min = min(row_min, value)

        if row_min > limit:
            return over_limit
        previous, previous_start = current, row_start

    return previous[m - previous_start]
