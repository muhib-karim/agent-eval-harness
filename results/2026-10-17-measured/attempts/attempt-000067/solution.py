import math
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")

        try:
            valid_window = math.isfinite(window_s) and window_s > 0
        except (TypeError, ValueError, OverflowError):
            valid_window = False
        if not valid_window:
            raise ValueError("window_s must be positive and finite")

        self.limit = limit
        self.window_s = window_s
        self._state = {}

    def allow(self, key, now: float) -> bool:
        try:
            finite = math.isfinite(now)
        except (TypeError, ValueError, OverflowError):
            finite = False
        if not finite:
            raise ValueError("now must be finite")

        entry = self._state.get(key)
        if entry is not None and now < entry[0]:
            raise ValueError("times must be nondecreasing per key")

        if entry is None:
            timestamps = deque()
        else:
            timestamps = entry[1]

        cutoff = now - self.window_s
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        allowed = len(timestamps) < self.limit
        if allowed:
            timestamps.append(now)

        self._state[key] = (now, timestamps)
        return allowed
