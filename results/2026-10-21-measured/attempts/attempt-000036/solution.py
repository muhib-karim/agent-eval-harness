import math
from collections import deque


class SlidingWindowLimiter:
    """Sliding-window rate limiter with independent history per key.

    A call at time `now` is accepted if fewer than `limit` accepted calls
    exist in the half-open window (now - window_s, now].
    """

    def __init__(self, limit, window_s):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if isinstance(window_s, bool):
            raise ValueError("window_s must be a positive finite number")
        try:
            w = float(window_s)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("window_s must be a positive finite number")
        if not math.isfinite(w) or w <= 0:
            raise ValueError("window_s must be a positive finite number")
        self._limit = limit
        self._window = window_s
        self._hist = {}   # key -> deque of accepted timestamps
        self._last = {}   # key -> last seen timestamp (accepted or denied)

    @staticmethod
    def _validate_time(now):
        if isinstance(now, bool):
            raise ValueError("time must be a finite number")
        try:
            f = float(now)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("time must be a finite number")
        if not math.isfinite(f):
            raise ValueError("time must be a finite number")

    def allow(self, key, now):
        self._validate_time(now)
        hash(key)  # raise TypeError early for unhashable keys, before any change
        last = self._last.get(key)
        if last is not None and now < last:
            raise ValueError("time must be nondecreasing per key")

        # Validation passed; now mutate state.
        self._last[key] = now
        dq = self._hist.get(key)
        if dq is None:
            dq = deque()
            self._hist[key] = dq

        cutoff = now - self._window
        while dq and dq[0] <= cutoff:
            dq.popleft()

        if len(dq) < self._limit:
            dq.append(now)
            return True
        return False
