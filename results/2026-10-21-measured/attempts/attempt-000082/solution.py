import math
from collections import deque
from numbers import Real


class SlidingWindowLimiter:
    """Per-key sliding window rate limiter.

    Accepts at most `limit` calls per key in the half-open window
    (now - window_s, now]. Denied calls do not consume capacity.
    """

    def __init__(self, limit, window_s):
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("limit must be a positive integer")
        if limit <= 0:
            raise ValueError("limit must be a positive integer")

        if isinstance(window_s, bool) or not isinstance(window_s, Real):
            raise ValueError("window_s must be a positive finite number")
        try:
            window_f = float(window_s)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("window_s must be a positive finite number")
        if not math.isfinite(window_f) or window_f <= 0:
            raise ValueError("window_s must be a positive finite number")

        self._limit = limit
        self._window = window_s
        # key -> deque of accepted timestamps (sorted, nondecreasing)
        self._history = {}
        # key -> last observed time (accepted or denied)
        self._last_time = {}

    @property
    def limit(self):
        return self._limit

    @property
    def window_s(self):
        return self._window

    @staticmethod
    def _validate_time(now):
        if isinstance(now, bool) or not isinstance(now, Real):
            raise ValueError("now must be a finite real number")
        try:
            f = float(now)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("now must be a finite real number")
        if not math.isfinite(f):
            raise ValueError("now must be a finite real number")

    def allow(self, key, now):
        # Validate the time before touching any state.
        self._validate_time(now)

        last = self._last_time.get(key)
        if last is not None and now < last:
            raise ValueError("time must be nondecreasing per key")

        # From here on the call is valid; record the observed time.
        self._last_time[key] = now

        hist = self._history.get(key)
        if hist is None:
            hist = deque()
            self._history[key] = hist

        cutoff = now - self._window
        # Discard timestamps that have fallen out of the window (<= cutoff).
        while hist and hist[0] <= cutoff:
            hist.popleft()

        if len(hist) < self._limit:
            hist.append(now)
            return True
        return False
