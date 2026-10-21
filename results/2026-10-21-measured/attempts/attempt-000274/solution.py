import math
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")

        try:
            if isinstance(window_s, (str, bytes, bytearray)):
                raise ValueError
            window = float(window_s)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("window_s must be positive and finite") from exc

        if not math.isfinite(window) or window <= 0:
            raise ValueError("window_s must be positive and finite")

        self.limit = limit
        self.window_s = window
        self._history = {}

    def allow(self, key, now: float) -> bool:
        try:
            if isinstance(now, (str, bytes, bytearray)):
                raise ValueError
            timestamp = float(now)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("now must be finite") from exc

        if not math.isfinite(timestamp):
            raise ValueError("now must be finite")

        entry = self._history.get(key)
        if entry is not None and timestamp < entry[0]:
            raise ValueError("time must be nondecreasing for each key")

        if entry is None:
            accepted = deque()
        else:
            accepted = entry[1]

        cutoff = timestamp - self.window_s
        while accepted and accepted[0] <= cutoff:
            accepted.popleft()

        allowed = len(accepted) < self.limit
        if allowed:
            accepted.append(timestamp)

        self._history[key] = (timestamp, accepted)
        return allowed
