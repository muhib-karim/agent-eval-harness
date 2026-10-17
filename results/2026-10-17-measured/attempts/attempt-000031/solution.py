import math
from collections import deque
from numbers import Real


class SlidingWindowLimiter:
    """
    A sliding-window rate limiter.

    Each key has an independent history of accepted call timestamps.
    At most `limit` calls are allowed within any (now - window_s, now]
    interval, per key.
    """

    def __init__(self, limit: int, window_s: float):
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("limit must be an int, not bool")
        if limit <= 0:
            raise ValueError("limit must be a positive integer")

        if isinstance(window_s, bool) or not isinstance(window_s, Real):
            raise ValueError("window_s must be a real number")
        window_s = float(window_s)
        if not math.isfinite(window_s) or window_s <= 0:
            raise ValueError("window_s must be positive and finite")

        self._limit = limit
        self._window_s = window_s
        # key -> (deque of accepted timestamps, last_seen_time)
        self._history: dict = {}
        self._last_time: dict = {}

    def allow(self, key, now: float) -> bool:
        if isinstance(now, bool) or not isinstance(now, Real):
            raise ValueError("now must be a real number")
        now = float(now)
        if not math.isfinite(now):
            raise ValueError("now must be finite")

        # Check nondecreasing constraint per key, without mutating state yet.
        if key in self._last_time:
            if now < self._last_time[key]:
                raise ValueError("now must be nondecreasing per key")

        # Validation passed; now we may update state.
        self._last_time[key] = now

        dq = self._history.get(key)
        if dq is None:
            dq = deque()
            self._history[key] = dq

        threshold = now - self._window_s
        # Discard accepted timestamps <= threshold (i.e., outside the window).
        while dq and dq[0] <= threshold:
            dq.popleft()

        if len(dq) < self._limit:
            dq.append(now)
            return True
        else:
            return False
