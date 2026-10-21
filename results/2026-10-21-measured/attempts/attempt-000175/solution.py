"""
solution.py

An LRU (Least Recently Used) cache with per-entry TTL (time-to-live) support.

Usage:
    cache = LRUCache(capacity=100, ttl=30.0)
    cache.put("key", "value")
    cache.get("key")  # -> "value"
"""

import math
import time
from collections import OrderedDict


class LRUCache:
    """
    A fixed-capacity cache combining LRU eviction with TTL-based expiry.

    - capacity: maximum number of *live* entries the cache may hold.
    - ttl: time-to-live (in the same units as `clock()`), applied each time
      a key is inserted or updated via `put`. `get` does NOT refresh the TTL.
    - clock: a zero-argument callable returning a nondecreasing number,
      used to determine "now". Defaults to time.monotonic.
    """

    def __init__(self, capacity: int, ttl: float, clock=time.monotonic):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")

        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
            raise ValueError("ttl must be a positive finite number")
        if not math.isfinite(ttl) or ttl <= 0:
            raise ValueError("ttl must be a positive finite number")

        if not callable(clock):
            raise ValueError("clock must be callable")

        self._capacity = capacity
        self._ttl = float(ttl)
        self._clock = clock
        # Maps key -> (value, expiry_time). Order reflects recency:
        # least-recently-used entries are at the front (OrderedDict's start),
        # most-recently-used entries are at the end.
        self._data = OrderedDict()

    def _purge_expired(self, now=None):
        """Remove all entries whose expiry has passed (expiry <= now)."""
        if now is None:
            now = self._clock()
        expired_keys = [k for k, (_, expiry) in self._data.items() if now >= expiry]
        for k in expired_keys:
            del self._data[k]

    def put(self, key, value):
        """Insert or update `key` with `value`, resetting its TTL and recency."""
        now = self._clock()
        # Purge expired entries before considering eviction.
        self._purge_expired(now)

        expiry = now + self._ttl

        if key in self._data:
            # Updating an existing key: refresh value, expiry, and recency.
            self._data[key] = (value, expiry)
            self._data.move_to_end(key)
        else:
            if len(self._data) >= self._capacity:
                # Evict the least recently used live entry.
                self._data.popitem(last=False)
            self._data[key] = (value, expiry)

    def get(self, key, default=None):
        """
        Return the live value for `key`, marking it as most recently used.
        Does NOT extend the TTL. Returns `default` if missing or expired.
        """
        now = self._clock()
        self._purge_expired(now)

        if key not in self._data:
            return default

        value, expiry = self._data[key]
        # Mark as most recently used without touching expiry.
        self._data.move_to_end(key)
        return value

    def __len__(self):
        """Number of live (non-expired) entries currently in the cache."""
        self._purge_expired()
        return len(self._data)

    def __contains__(self, key):
        """Check whether `key` is present and live, without affecting recency."""
        self._purge_expired()
        return key in self._data

    def __repr__(self):
        self._purge_expired()
        items = ", ".join(f"{k!r}: {v!r}" for k, (v, _) in self._data.items())
        return f"LRUCache(capacity={self._capacity}, ttl={self._ttl}, items={{{items}}})"
