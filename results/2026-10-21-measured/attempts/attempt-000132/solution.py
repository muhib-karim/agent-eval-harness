import math
import numbers
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if isinstance(window_s, bool) or not isinstance(window_s, numbers.Real):
            raise ValueError("window_s must be a positive finite number")
        try:
            w = float(window_s)
        except (OverflowError, ValueError, TypeError):
            raise ValueError("window_s must be a positive finite number")
        if not math.isfinite(w) or w <= 0:
            raise ValueError("window_s must be a positive finite number")
        self._limit = limit
        self._window = window_s
        # key -> [deque of accepted timestamps, last seen time]
        self._state = {}

    @staticmethod
    def _check_time(now):
        if isinstance(now, bool) or not isinstance(now, numbers.Real):
            raise ValueError("now must be a finite real number")
        try:
            f = float(now)
        except (OverflowError, ValueError, TypeError):
            raise ValueError("now must be a finite real number")
        if not math.isfinite(f):
            raise ValueError("now must be a finite real number")

    def allow(self, key, now: float) -> bool:
        self._check_time(now)
        state = self._state.get(key)  # raises TypeError for unhashable key, no state change
        if state is not None and now < state[1]:
            raise ValueError("time must be nondecreasing per key")
        if state is None:
            state = [deque(), now]
            self._state[key] = state
        stamps = state[0]
        state[1] = now
        cutoff = now - self._window
        while stamps and stamps[0] <= cutoff:
            stamps.popleft()
        if len(stamps) < self._limit:
            stamps.append(now)
            return True
        return False
