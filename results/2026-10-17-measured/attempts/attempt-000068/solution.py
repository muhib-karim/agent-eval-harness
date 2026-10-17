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
        self._history = {}  # key -> (accepted timestamps, time of last call)

    def allow(self, key, now: float) -> bool:
        try:
            finite = math.isfinite(now)
        except (TypeError, ValueError, OverflowError):
            finite = False
        if not finite:
            raise ValueError("now must be finite")

        entry = self._history.get(key)
        if entry is not None and now < entry[1]:
            raise ValueError("time must be nondecreasing for each key")

        if entry is None:
            accepted = deque()
        else:
            accepted = entry[0]

        cutoff = now - self.window_s
        while accepted and accepted[0] <= cutoff:
            accepted.popleft()

        allowed = len(accepted) < self.limit
        if allowed:
            accepted.append(now)

        # Record every valid call, including denied calls, for time ordering.
        self._history[key] = (accepted, now)
        return allowed
