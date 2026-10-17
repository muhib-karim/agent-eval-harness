import math
from collections import deque
from numbers import Real


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float):
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("limit must be a positive integer (not bool)")
        if limit <= 0:
            raise ValueError("limit must be a positive integer")

        if isinstance(window_s, bool) or not isinstance(window_s, Real):
            raise ValueError("window_s must be a positive finite number")
        window_s = float(window_s)
        if not math.isfinite(window_s) or window_s <= 0:
            raise ValueError("window_s must be a positive finite number")

        self.limit = limit
        self.window_s = window_s
        # key -> deque of accepted timestamps
        self._history = {}
        # key -> last seen time (for monotonicity check), across accepted and denied calls
        self._last_time = {}

    def allow(self, key, now: float) -> bool:
        if isinstance(now, bool) or not isinstance(now, Real):
            raise ValueError("now must be a finite real number")
        now = float(now)
        if not math.isfinite(now):
            raise ValueError("now must be finite")

        last_time = self._last_time.get(key)
        if last_time is not None and now < last_time:
            raise ValueError("time must be nondecreasing per key")

        # Validation passed; now update last_time (state change allowed on valid input,
        # even if the call is denied, since that's not "changing state" in a way that
        # affects validity -- but spec says denied calls do not consume capacity.
        # Updating last_time is necessary to track monotonicity.)
        self._last_time[key] = now

        dq = self._history.get(key)
        if dq is None:
            dq = deque()
            self._history[key] = dq

        threshold = now - self.window_s
        while dq and dq[0] <= threshold:
            dq.popleft()

        if len(dq) < self.limit:
            dq.append(now)
            return True
        else:
            return False
