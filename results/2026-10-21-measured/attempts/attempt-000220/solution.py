def levenshtein(a: str, b: str, max_distance: int | None = None) -> int:
    """
    Return the minimum number of single-character insertions, deletions and substitutions
    that turn a into b.

    If max_distance is given and the true distance exceeds it, return max_distance + 1.
    Otherwise return the true distance.
    """
    # Type checking
    if not isinstance(a, str):
        raise TypeError(f"a must be str, not {type(a).__name__}")
    if not isinstance(b, str):
        raise TypeError(f"b must be str, not {type(b).__name__}")

    # Validate max_distance
    if max_distance is not None:
        if not isinstance(max_distance, int) or isinstance(max_distance, bool):
            raise ValueError("max_distance must be a non-negative int or None")
        if max_distance < 0:
            raise ValueError("max_distance must be a non-negative int or None")

    # Optimize by ensuring a is the shorter string
    if len(a) > len(b):
        a, b = b, a

    len_a = len(a)
    len_b = len(b)

    # Early exit: if difference in lengths exceeds max_distance
    if max_distance is not None and len_b - len_a > max_distance:
        return max_distance + 1

    # Use only O(min(len(a), len(b))) extra memory
    # We need two rows for the dynamic programming approach
    prev_row = list(range(len_a + 1))
    curr_row = [0] * (len_a + 1)

    for j in range(1, len_b + 1):
        curr_row[0] = j

        # Determine the range to compute based on max_distance
        if max_distance is not None:
            # Only compute cells that could potentially lead to a solution within max_distance
            min_i = max(1, j - max_distance)
            max_i = min(len_a, j + max_distance)
        else:
            min_i = 1
            max_i = len_a

        for i in range(1, min_i):
            curr_row[i] = max_distance + 1 if max_distance is not None else len_b

        for i in range(min_i, max_i + 1):
            if a[i - 1] == b[j - 1]:
                curr_row[i] = prev_row[i - 1]
            else:
                curr_row[i] = 1 + min(
                    prev_row[i],      # deletion
                    curr_row[i - 1],  # insertion
                    prev_row[i - 1]   # substitution
                )

        for i in range(max_i + 1, len_a + 1):
            curr_row[i] = max_distance + 1 if max_distance is not None else len_b

        # Swap rows
        prev_row, curr_row = curr_row, prev_row

    result = prev_row[len_a]

    # Check if we need to return max_distance + 1
    if max_distance is not None and result > max_distance:
        return max_distance + 1

    return result
