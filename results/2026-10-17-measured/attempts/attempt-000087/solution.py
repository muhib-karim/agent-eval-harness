import math
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if (
            isinstance(window_s, bool)
            or not isinstance(window_s, (int, float))
            or not math.isfinite(window_s)
            or window_s <= 0
        ):
            raise ValueError("window_s must be positive and finite")
        self.limit = limit
        self.window_s = float(window_s)
        self.history = {}
        self.last_time = {}

    def allow(self, key, now: float) -> bool:
        if (
            isinstance(now, bool)
            or not isinstance(now, (int, float))
            or not math.isfinite(now)
        ):
            raise ValueError("now must be a finite number")
        now = float(now)

        if key in self.last_time:
            if now < self.last_time[key]:
                raise ValueError("time must be nondecreasing per key")
        else:
            self.history[key] = deque()
        self.last_time[key] = now

        dq = self.history[key]
        threshold = now - self.window_s
        while dq and dq[0] <= threshold:
            dq.popleft()

        if len(dq) < self.limit:
            dq.append(now)
            return True
        return False
