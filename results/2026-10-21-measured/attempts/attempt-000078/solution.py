"""Levenshtein edit distance with optional early termination.

levenshtein(a, b, max_distance=None) returns the minimum number of
single-character insertions, deletions and substitutions turning a into b.
If max_distance is given and the true distance exceeds it, max_distance + 1
is returned instead.

The implementation uses a banded dynamic-programming approach: only cells
whose row/column indices differ by at most max_distance are evaluated, and
the computation aborts as soon as every cell in the current band exceeds the
limit. Memory usage is two rows of length min(len(a), len(b)) + 1.
"""

from __future__ import annotations


def levenshtein(a: str, b: str, max_distance: int | None = None) -> int:
    # ----- argument validation -------------------------------------------
    if not isinstance(a, str) or not isinstance(b, str):
        raise TypeError("levenshtein() arguments a and b must be str")
    if max_distance is not None:
        if isinstance(max_distance, bool) or not isinstance(max_distance, int):
            raise ValueError("max_distance must be a non-negative int or None")
        if max_distance < 0:
            raise ValueError("max_distance must be a non-negative int or None")

    # ----- trivial cases ---------------------------------------------------
    if a == b:
        return 0

    # Strip common prefix (cheap, and shrinks the problem).
    start = 0
    la, lb = len(a), len(b)
    limit = la if la < lb else lb
    while start < limit and a[start] == b[start]:
        start += 1
    # Strip common suffix.
    end_a, end_b = la, lb
    while end_a > start and end_b > start and a[end_a - 1] == b[end_b - 1]:
        end_a -= 1
        end_b -= 1
    a = a[start:end_a]
    b = b[start:end_b]

    # Make `a` the longer string so rows iterate over the longer one and the
    # DP rows (memory) are sized by the shorter one.
    if len(a) < len(b):
        a, b = b, a
    n, m = len(a), len(b)

    if max_distance is not None and n - m > max_distance:
        return max_distance + 1
    if m == 0:
        return n  # (n <= max_distance here if a limit was given)

    # ----- banded dynamic programming --------------------------------------
    k = n if max_distance is None else max_distance  # half-width of band
    INF = n + m + 1  # larger than any achievable distance

    prev = list(range(m + 1))  # row 0: distance from "" to b[:j]
    if k + 1 <= m:
        for j in range(k + 1, m + 1):
            prev[j] = INF
    cur = [INF] * (m + 1)

    for i in range(1, n + 1):
        ca = a[i - 1]
        lo = i - k
        if lo < 1:
            lo = 1
            cur[0] = i
        else:
            cur[lo - 1] = INF
        hi = i + k
        if hi > m:
            hi = m

        best = INF
        left = cur[lo - 1]
        diag = prev[lo - 1]
        for j in range(lo, hi + 1):
            up = prev[j]
            if ca == b[j - 1]:
                v = diag
                if up + 1 < v:
                    v = up + 1
                if left + 1 < v:
                    v = left + 1
            else:
                v = diag + 1
                if up + 1 < v:
                    v = up + 1
                if left + 1 < v:
                    v = left + 1
            cur[j] = v
            if v < best:
                best = v
            left = v
            diag = up

        if hi < m:
            cur[hi + 1] = INF

        if best > k:
            return k + 1

        prev, cur = cur, prev

    result = prev[m]
    if max_distance is not None and result > max_distance:
        return max_distance + 1
    return result


if __name__ == "__main__":
    # Small self-check.
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("", "abc") == 3
    assert levenshtein("abc", "abc") == 0
    assert levenshtein("flaw", "lawn") == 2
    assert levenshtein("kitten", "sitting", 2) == 3
    assert levenshtein("kitten", "sitting", 3) == 3
    assert levenshtein("kitten", "sitting", 0) == 1
    assert levenshtein("Abc", "abc") == 1
    assert levenshtein("a" * 20000, "a" * 19990 + "b" * 10, 5) == 6
    print("ok")
