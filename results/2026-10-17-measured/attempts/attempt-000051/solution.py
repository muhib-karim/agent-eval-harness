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
        # Map from key to list of accepted timestamps
        self.history = defaultdict(list)
        # Map from key to last time we saw it (for validation)
        self.last_time = {}

    def allow(self, key, now: float) -> bool:
        # Validate now
        if not isinstance(now, (int, float)) or isinstance(now, bool):
            raise ValueError("now must be finite")
        if not math.isfinite(now):
            raise ValueError("now must be finite")

        # Validate nondecreasing time per key
        if key in self.last_time:
            if now < self.last_time[key]:
                raise ValueError("time must be nondecreasing per key")

        # Update last seen time for this key
        self.last_time[key] = now

        # Calculate window boundary
        window_start = now - self.window_s

        # Remove timestamps outside the window (timestamps <= window_start)
        if key in self.history:
            self.history[key] = [ts for ts in self.history[key] if ts > window_start]

        # Check if we can accept this call
        if len(self.history[key]) < self.limit:
            # Accept the call
            self.history[key].append(now)
            return True
        else:
            # Deny the call (but don't change state beyond what we already did)
            return False
