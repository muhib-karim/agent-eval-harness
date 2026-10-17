import math
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float):
        # Validate limit: must be a positive integer, not bool
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        # Validate window_s: must be positive and finite
        if not isinstance(window_s, (int, float)) or isinstance(window_s, bool):
            raise ValueError("window_s must be a positive finite number")
        if not math.isfinite(window_s) or window_s <= 0:
            raise ValueError("window_s must be a positive finite number")

        self.limit = limit
        self.window_s = float(window_s)

        # Per-key state:
        #   timestamps: deque of accepted call timestamps (sorted, since nondecreasing)
        #   last_time: last time seen (accepted or denied) for this key
        self._timestamps = {}
        self._last_time = {}

    def allow(self, key, now: float) -> bool:
        # Validate time
        if not isinstance(now, (int, float)) or isinstance(now, bool):
            raise ValueError("now must be a finite number")
        if not math.isfinite(now):
            raise ValueError("now must be a finite number")

        # Check per-key nondecreasing invariant
        if key in self._last_time:
            if now < self._last_time[key]:
                raise ValueError("time must be nondecreasing per key")

        # Update last_time only after validation passes
        self._last_time[key] = now

        # Get or create deque for this key
        if key in self._timestamps:
            timestamps = self._timestamps[key]
        else:
            timestamps = deque()
            self._timestamps[key] = timestamps

        # Discard accepted timestamps <= now - window_s
        cutoff = now - self.window_s
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        # Check capacity
        if len(timestamps) < self.limit:
            timestamps.append(now)
            return True
        else:
            return False
