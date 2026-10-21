"""Binary-search helpers over an ascending list."""


def _left(items, target, n):
    """First index i in [0, n] such that items[i] >= target."""
    lo, hi = 0, n
    while lo < hi:
        mid = (lo + hi) // 2
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def _right(items, target, n):
    """First index i in [0, n] such that items[i] > target."""
    lo, hi = 0, n
    while lo < hi:
        mid = (lo + hi) // 2
        if items[mid] <= target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def find_first(items, target):
    """Index of the first element equal to target, or -1."""
    n = len(items)
    index = _left(items, target, n)
    if index < n and items[index] == target:
        return index
    return -1


def find_last(items, target):
    """Index of the last element equal to target, or -1."""
    n = len(items)
    # _right gives the index one past the last element <= target,
    # so the last occurrence (if any) sits just before it.
    index = _right(items, target, n) - 1
    if index >= 0 and items[index] == target:
        return index
    return -1


def count_range(items, low, high):
    """Number of elements x with low <= x <= high."""
    if low > high:
        return 0
    n = len(items)
    return _right(items, high, n) - _left(items, low, n)
