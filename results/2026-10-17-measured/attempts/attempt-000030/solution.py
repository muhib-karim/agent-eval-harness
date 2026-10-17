"""
solution.py

A simple LRU cache with per-entry TTL (time-to-live) expiry.

LRUCache(capacity: int, ttl: float, clock=time.monotonic)

- capacity must be a positive integer (bool is rejected even though bool
  is technically an int subclass).
- ttl must be a positive, finite number (bool rejected as well).
- put(key, value) inserts/updates an entry and sets its expiry to
  clock() + ttl.  This also marks the key as most-recently-used.
- get(key, default=None) returns the live value for key (marking it as
  most-recently-used) without extending its TTL, or `default` if the key
  is missing or expired.
- An entry is considered expired once clock() >= expiry.
- Expired entries are purged before eviction decisions and before
  computing len(cache).
- When inserting would push the cache beyond capacity, the least
  recently used *live* entry is evicted.
- len(cache) reports only the count of currently live entries.
"""

import math
import time
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int, ttl: float, clock=time.monotonic):
        # Validate capacity: must be a positive int, not a bool.
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("capacity must be a positive integer")

        # Validate ttl: must be a positive, finite number, not a bool.
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
            raise ValueError("ttl must be a positive, finite number")
        if not math.isfinite(ttl) or ttl <= 0:
            raise ValueError("ttl must be positive and finite")

        self.capacity = capacity
        self.ttl = ttl
        self.clock = clock

        # Maps key -> (value, expiry_time). Order reflects recency:
        # least-recently-used is at the front, most-recently-used at the end.
        self._data: "OrderedDict[object, tuple]" = OrderedDict()

    def _purge_expired(self) -> None:
        """Remove all entries whose expiry has passed."""
        now = self.clock()
        expired_keys = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in expired_keys:
            del self._data[k]

    def put(self, key, value) -> None:
        """Insert or update `key` with `value`, resetting its TTL and
        marking it as most-recently-used."""
        self._purge_expired()

        expiry = self.clock() + self.ttl

        if key in self._data:
            # Remove old entry first so re-inserting moves it to the end.
            del self._data[key]

        self._data[key] = (value, expiry)
        self._data.move_to_end(key)

        # Evict least-recently-used live entries if over capacity.
        while len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def get(self, key, default=None):
        """Return the live value for `key`, marking it as most-recently-used.
        Does not extend the TTL. Returns `default` if missing or expired."""
        self._purge_expired()

        if key not in self._data:
            return default

        value, _expiry = self._data[key]
        self._data.move_to_end(key)
        return value

    def __len__(self) -> int:
        """Return the number of currently live entries."""
        self._purge_expired()
        return len(self._data)
