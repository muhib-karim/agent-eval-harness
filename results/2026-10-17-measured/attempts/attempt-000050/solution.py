import math
from collections import defaultdict


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float):
        # Validate limit
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise ValueError("limit must be a positive integer")
        if limit <= 0:
            raise ValueError("limit must be a positive integer")

        # Validate window_s
        if not isinstance(window_s, (int, float)) or isinstance(window_s, bool):
            raise ValueError("window_s must be positive and finite")
        if window_s <= 0 or not math.isfinite(window_s):
            raise ValueError("window_s must be positive and finite")

        self.limit = limit
        self.window_s = window_s
        # Store timestamps for each key
        self.history = defaultdict(list)
        # Store the last time we saw each key (for monotonicity check)
        self.last_time = {}

    def allow(self, key, now: float) -> bool:
        # Validate now
        if not isinstance(now, (int, float)) or isinstance(now, bool):
            raise ValueError("now must be finite")
        if not math.isfinite(now):
            raise ValueError("now must be finite")

        # Check time monotonicity per key
        if key in self.last_time:
            if now < self.last_time[key]:
                raise ValueError("Time must be nondecreasing per key")

        # Update last time for this key (before any potential state change on error)
        self.last_time[key] = now

        # Calculate the window start time
        window_start = now - self.window_s

        # Remove timestamps outside the window (timestamps <= window_start)
        self.history[key] = [ts for ts in self.history[key] if ts > window_start]

        # Check if we can accept this call
        if len(self.history[key]) < self.limit:
            self.history[key].append(now)
            return True
        else:
            return False
