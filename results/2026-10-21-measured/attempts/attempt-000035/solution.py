import math
from collections import deque
from numbers import Real


class SlidingWindowLimiter:
    """Sliding-window rate limiter with independent per-key history.

    For each key, at most `limit` calls are accepted within the half-open
    window (now - window_s, now]. Denied calls do not consume capacity.
    """

    def __init__(self, limit: int, window_s: float):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if isinstance(window_s, bool) or not isinstance(window_s, Real):
            raise ValueError("window_s must be a positive finite number")
        try:
            w = float(window_s)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("window_s must be a positive finite number")
        if not math.isfinite(w) or w <= 0:
            raise ValueError("window_s must be a positive finite number")
        self._limit = limit
        self._window = window_s
        self._history = {}  # key -> deque of accepted timestamps
        self._last = {}     # key -> last seen timestamp (accepted or denied)

    @staticmethod
    def _validate_time(now):
        if isinstance(now, bool) or not isinstance(now, Real):
            raise ValueError("time must be a finite real number")
        try:
            f = float(now)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("time must be a finite real number")
        if not math.isfinite(f):
            raise ValueError("time must be a finite real number")

    def allow(self, key, now: float) -> bool:
        hash(key)  # raises TypeError for unhashable keys before any state change
        self._validate_time(now)
        last = self._last.get(key)
        if last is not None and now < last:
            raise ValueError("time must be nondecreasing per key")

        # Validation passed; mutate state from here on.
        self._last[key] = now
        dq = self._history.get(key)
        if dq is None:
            dq = deque()
            self._history[key] = dq

        cutoff = now - self._window
        while dq and dq[0] <= cutoff:
            dq.popleft()

        if len(dq) < self._limit:
            dq.append(now)
            return True
        return False
