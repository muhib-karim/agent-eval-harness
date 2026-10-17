import math
from collections import defaultdict

class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError
        if isinstance(window_s, bool) or not isinstance(window_s, (int, float)) or not (0 < window_s < float('inf')):
            raise ValueError
        self.limit = limit
        self.window_s = float(window_s)
        self.histories = defaultdict(list)
        self.last_times = {}

    def allow(self, key, now: float) -> bool:
        if not math.isfinite(now):
            raise ValueError
        if key in self.last_times and now < self.last_times[key]:
            raise ValueError
        self.last_times[key] = now
        cutoff = now - self.window_s
        history = self.histories[key]
        while history and history[0] <= cutoff:
            history.pop(0)
        if len(history) < self.limit:
            history.append(now)
            return True
        return False
