"""Sliding-window rate limiter keyed by hashable keys."""

import math
from collections import deque
from numbers import Real


class SlidingWindowLimiter:
    """Accept at most `limit` calls per key within any window (now - window_s, now]."""

    def __init__(self, limit, window_s):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if isinstance(window_s, bool) or not isinstance(window_s, Real):
            raise ValueError("window_s must be a positive finite number")
        try:
            w = float(window_s)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("window_s must be a positive finite number")
        if not math.isfinite(w) or w <= 0:
            raise ValueError("window_s must be a positive finite number")
        self._limit = limit
        self._window = window_s
        # key -> [last_seen_time, deque of accepted timestamps]
        self._state = {}

    def allow(self, key, now):
        if isinstance(now, bool) or not isinstance(now, Real):
            raise ValueError("now must be a finite number")
        try:
            nf = float(now)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("now must be a finite number")
        if not math.isfinite(nf):
            raise ValueError("now must be a finite number")

        entry = self._state.get(key)  # raises TypeError if key is unhashable
        if entry is not None and now < entry[0]:
            raise ValueError("time must be nondecreasing per key")

        if entry is None:
            entry = [now, deque()]
            self._state[key] = entry
        else:
            entry[0] = now

        q = entry[1]
        cutoff = now - self._window
        while q and q[0] <= cutoff:
            q.popleft()

        if len(q) < self._limit:
            q.append(now)
            return True
        return False
