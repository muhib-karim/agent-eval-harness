import math
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")

        try:
            valid_window = math.isfinite(window_s) and window_s > 0
        except (TypeError, OverflowError, ValueError):
            valid_window = False
        if not valid_window:
            raise ValueError("window_s must be positive and finite")

        self.limit = limit
        self.window_s = window_s
        self._history = {}  # key -> (last call time, accepted timestamps)

    def allow(self, key, now: float) -> bool:
        try:
            valid_time = math.isfinite(now)
        except (TypeError, OverflowError, ValueError):
            valid_time = False
        if not valid_time:
            raise ValueError("now must be finite")

        entry = self._history.get(key)
        if entry is None:
            accepted = deque([now])
            self._history[key] = (now, accepted)
            return True

        last_time, accepted = entry
        if now < last_time:
            raise ValueError("time must be nondecreasing for each key")

        cutoff = now - self.window_s
        while accepted and accepted[0] <= cutoff:
            accepted.popleft()

        allowed = len(accepted) < self.limit
        if allowed:
            accepted.append(now)

        # Denied calls also establish the latest time for this key.
        self._history[key] = (now, accepted)
        return allowed
