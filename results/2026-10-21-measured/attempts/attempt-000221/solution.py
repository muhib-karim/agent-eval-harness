def levenshtein(a: str, b: str, max_distance: int | None = None) -> int:
    """
    Calculate the Levenshtein distance between two strings.

    Returns the minimum number of single-character insertions, deletions and 
    substitutions that turn a into b.

    If max_distance is given and the true distance exceeds it, returns max_distance + 1.
    Otherwise returns the true distance.

    Raises ValueError if max_distance is not None, non-negative int or bool.
    Raises TypeError if a or b is not a string.
    """
    # Type checking
    if not isinstance(a, str):
        raise TypeError(f"a must be str, not {type(a).__name__}")
    if not isinstance(b, str):
        raise TypeError(f"b must be str, not {type(b).__name__}")

    # Validate max_distance
    if max_distance is not None:
        if isinstance(max_distance, bool):
            raise ValueError("max_distance must be a non-negative int, not bool")
        if not isinstance(max_distance, int):
            raise ValueError(f"max_distance must be a non-negative int, not {type(max_distance).__name__}")
        if max_distance < 0:
            raise ValueError("max_distance must be non-negative")

    # Optimize by swapping so that a is the shorter string
    if len(a) > len(b):
        a, b = b, a

    len_a = len(a)
    len_b = len(b)

    # If one string is empty, distance is length of the other
    if len_a == 0:
        distance = len_b
        if max_distance is not None and distance > max_distance:
            return max_distance + 1
        return distance

    # Use O(min(len(a), len(b))) space with two rows
    # prev_row represents the previous row, curr_row represents current row
    prev_row = list(range(len_a + 1))
    curr_row = [0] * (len_a + 1)

    for i in range(1, len_b + 1):
        curr_row[0] = i

        # Early termination if max_distance is set
        min_in_row = i

        for j in range(1, len_a + 1):
            # Calculate cost of substitution
            cost = 0 if a[j - 1] == b[i - 1] else 1

            # Calculate minimum of three operations
            curr_row[j] = min(
                prev_row[j] + 1,      # deletion
                curr_row[j - 1] + 1,  # insertion
                prev_row[j - 1] + cost  # substitution
            )

            min_in_row = min(min_in_row, curr_row[j])

        # Early exit if minimum distance in row exceeds max_distance
        if max_distance is not None and min_in_row > max_distance:
            return max_distance + 1

        # Swap rows for next iteration
        prev_row, curr_row = curr_row, prev_row

    distance = prev_row[len_a]

    if max_distance is not None and distance > max_distance:
        return max_distance + 1

    return distance
