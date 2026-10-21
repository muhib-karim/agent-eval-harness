import math
from collections import deque


class SlidingWindowLimiter:
    """
    Sliding-window rate limiter.

    Accepts at most `limit` calls per key in the half-open interval
    (now - window_s, now].  Denied calls do not consume capacity.
    Times must be finite and nondecreasing per key (including denied calls).
    """

    def __init__(self, limit, window_s):
        # Validate limit: positive int, not bool
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("limit must be a positive integer")
        if limit <= 0:
            raise ValueError("limit must be a positive integer")

        # Validate window: positive, finite real number (not bool)
        if isinstance(window_s, bool) or not isinstance(window_s, (int, float)):
            raise ValueError("window_s must be a positive finite number")
        window_f = float(window_s)
        if not math.isfinite(window_f) or window_f <= 0:
            raise ValueError("window_s must be a positive finite number")

        self._limit = limit
        self._window = window_f
        self._history = {}   # key -> deque of accepted timestamps
        self._last_time = {}  # key -> last seen timestamp (accepted or denied)

    @property
    def limit(self):
        return self._limit

    @property
    def window_s(self):
        return self._window

    @staticmethod
    def _validate_time(now):
        if isinstance(now, bool) or not isinstance(now, (int, float)):
            raise ValueError("now must be a finite real number")
        now_f = float(now)
        if not math.isfinite(now_f):
            raise ValueError("now must be finite")
        return now_f

    def allow(self, key, now):
        # Validate time before touching any state.
        now_f = self._validate_time(now)

        last = self._last_time.get(key)
        if last is not None and now_f < last:
            raise ValueError("time must be nondecreasing per key")

        # Record this call's time (applies to accepted and denied calls alike).
        self._last_time[key] = now_f

        hist = self._history.get(key)
        if hist is None:
            hist = deque()
            self._history[key] = hist

        cutoff = now_f - self._window
        # Discard timestamps that are <= now - window_s (outside the window).
        while hist and hist[0] <= cutoff:
            hist.popleft()

        if len(hist) < self._limit:
            hist.append(now_f)
            return True
        return False
