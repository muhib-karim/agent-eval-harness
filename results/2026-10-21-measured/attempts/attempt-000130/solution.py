import math
from collections import deque
from numbers import Real


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if not isinstance(window_s, Real):
            raise ValueError("window_s must be a real number")
        try:
            w = float(window_s)
        except (OverflowError, TypeError, ValueError):
            raise ValueError("invalid window_s")
        if not math.isfinite(w) or w <= 0:
            raise ValueError("window_s must be positive and finite")
        self._limit = limit
        self._window = w
        # key -> [deque of accepted timestamps, last seen time]
        self._state = {}

    def allow(self, key, now: float) -> bool:
        # Look up key first (raises TypeError for unhashable, before any change)
        entry = self._state.get(key)

        if not isinstance(now, Real):
            raise ValueError("time must be a real number")
        try:
            t = float(now)
        except (OverflowError, TypeError, ValueError):
            raise ValueError("invalid time")
        if not math.isfinite(t):
            raise ValueError("time must be finite")

        if entry is None:
            entry = [deque(), t]
            self._state[key] = entry
        else:
            if t < entry[1]:
                raise ValueError("time must be nondecreasing per key")
            entry[1] = t

        dq = entry[0]
        cutoff = t - self._window
        while dq and dq[0] <= cutoff:
            dq.popleft()

        if len(dq) < self._limit:
            dq.append(t)
            return True
        return False
