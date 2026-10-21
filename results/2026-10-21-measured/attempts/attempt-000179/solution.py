"""
solution.py

A sliding-window rate limiter using only the Python standard library.

SlidingWindowLimiter(limit, window_s).allow(key, now) -> bool

Semantics:
- `limit` must be a positive int (bool excluded) or ValueError is raised.
- `window_s` must be a finite, positive float (or int) or ValueError is raised.
- Each hashable `key` has its own independent history of accepted timestamps.
- A call at time `now` is accepted if the number of previously accepted
  timestamps for that key within (now - window_s, now] is less than `limit`.
- Timestamps <= now - window_s are discarded (expired) before counting.
- Denied calls do NOT consume capacity (they are not added to history).
- For a given key, `now` values across ALL calls (accepted or denied) must be
  finite and non-decreasing; a decreasing time raises ValueError without
  mutating any state. Equal timestamps are allowed.
- A new key may start at any finite time, including negative numbers.
- The real system clock is never consulted; `now` is always supplied by the
  caller.
"""

from collections import deque
import math
from typing import Any, Deque, Dict, Hashable


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float) -> None:
        # Validate limit: must be int, not bool, and positive.
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("limit must be a positive integer (not bool)")
        if limit <= 0:
            raise ValueError("limit must be a positive integer")

        # Validate window_s: must be a real number, finite, and positive.
        if isinstance(window_s, bool) or not isinstance(window_s, (int, float)):
            raise ValueError("window_s must be a positive finite number")
        if isinstance(window_s, float) and (math.isnan(window_s) or math.isinf(window_s)):
            raise ValueError("window_s must be finite")
        if window_s <= 0:
            raise ValueError("window_s must be positive")

        self._limit: int = limit
        self._window_s: float = float(window_s)

        # Per-key accepted timestamp history (monotonic queue of accepted times).
        self._history: Dict[Hashable, Deque[float]] = {}

        # Per-key last seen `now` value (across accepted and denied calls),
        # used to enforce the non-decreasing constraint.
        self._last_time: Dict[Hashable, float] = {}

    def allow(self, key: Hashable, now: float) -> bool:
        # Validate `now`: must be a real number and finite.
        if isinstance(now, bool) or not isinstance(now, (int, float)):
            raise ValueError("now must be a finite real number")
        now_f = float(now)
        if math.isnan(now_f) or math.isinf(now_f):
            raise ValueError("now must be finite")

        # Enforce non-decreasing times per key, including denied calls.
        last = self._last_time.get(key)
        if last is not None and now_f < last:
            raise ValueError("now must be non-decreasing per key")

        # All validation passed; now we may mutate state.
        self._last_time[key] = now_f

        history = self._history.get(key)
        if history is None:
            history = deque()
            self._history[key] = history

        # Discard expired timestamps: those <= now - window_s.
        threshold = now_f - self._window_s
        while history and history[0] <= threshold:
            history.popleft()

        if len(history) < self._limit:
            history.append(now_f)
            return True

        return False
