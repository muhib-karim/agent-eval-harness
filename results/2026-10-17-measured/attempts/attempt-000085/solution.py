import math
from collections import deque

class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if isinstance(window_s, bool) or not isinstance(window_s, (int, float)):
            raise ValueError("window_s must be a positive finite number")
        window_s = float(window_s)
        if not math.isfinite(window_s) or window_s <= 0:
            raise ValueError("window_s must be a positive finite number")
        self.limit = limit
        self.window_s = window_s
        self._histories = {}
        self._last = {}

    def allow(self, key, now: float) -> bool:
        if isinstance(now, bool) or not isinstance(now, (int, float)):
            raise ValueError("now must be a finite number")
        now = float(now)
        if not math.isfinite(now):
            raise ValueError("now must be a finite number")

        if key in self._last and now < self._last[key]:
            raise ValueError("time must be nondecreasing per key")

        history = self._histories.get(key)
        if history is None:
            history = deque()
            self._histories[key] = history

        cutoff = now - self.window_s
        while history and history[0] <= cutoff:
            history.popleft()

        # Update last seen time (denied calls also count for ordering)
        self._last[key] = now

        if len(history) < self.limit:
            history.append(now)
            return True
        return False
