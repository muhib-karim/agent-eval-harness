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
        # key -> (time of last call, accepted timestamps)
        self._state = {}

    def allow(self, key, now: float) -> bool:
        try:
            valid_time = math.isfinite(now)
        except (TypeError, ValueError, OverflowError):
            valid_time = False
        if not valid_time:
            raise ValueError("now must be finite")

        state = self._state.get(key)
        if state is None:
            accepted = deque([now])
            self._state[key] = (now, accepted)
            return True

        last_time, accepted = state
        if now < last_time:
            raise ValueError("time must be nondecreasing for each key")

        cutoff = now - self.window_s
        while accepted and accepted[0] <= cutoff:
            accepted.popleft()

        allowed = len(accepted) < self.limit
        if allowed:
            accepted.append(now)

        # Record every valid call, including denied calls.
        self._state[key] = (now, accepted)
        return allowed
