"""LRU cache with a fixed time-to-live (TTL) for every entry."""

import math
import numbers
import threading
import time
from collections import OrderedDict

__all__ = ["LRUCache"]


class LRUCache:
    """Least-recently-used cache where entries also expire after a fixed TTL.

    Every ``put`` sets the entry's expiry to ``clock() + ttl``.  Since the TTL
    is constant and the clock never goes backwards, expiry order is the same
    as the order of the most recent ``put``.  This lets expired entries be
    purged cheaply from the front of a second ordered mapping.
    """

    def __init__(self, capacity, ttl, clock=time.monotonic):
        if (
            isinstance(capacity, bool)
            or not isinstance(capacity, int)
            or capacity <= 0
        ):
            raise ValueError("capacity must be a positive integer")

        if isinstance(ttl, bool) or not isinstance(ttl, numbers.Real):
            raise ValueError("ttl must be a positive finite number")
        try:
            ttl_f = float(ttl)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("ttl must be a positive finite number")
        if not math.isfinite(ttl_f) or ttl_f <= 0:
            raise ValueError("ttl must be a positive finite number")

        if not callable(clock):
            raise ValueError("clock must be callable")

        self._capacity = capacity
        self._ttl = ttl
        self._clock = clock
        # key -> [value, expiry], ordered by recency (LRU first).
        self._data = OrderedDict()
        # key -> expiry, ordered by expiry (earliest first).
        self._exp = OrderedDict()
        self._lock = threading.RLock()

    def _purge(self, now):
        """Remove all entries whose expiry is at or before ``now``."""
        exp = self._exp
        data = self._data
        while exp:
            key, expiry = next(iter(exp.items()))
            if now >= expiry:
                exp.popitem(last=False)
                data.pop(key, None)
            else:
                break

    def put(self, key, value):
        hash(key)  # Raises TypeError early if the key is unhashable.
        with self._lock:
            now = self._clock()
            self._purge(now)
            expiry = now + self._ttl

            if key in self._data:
                entry = self._data[key]
                entry[0] = value
                entry[1] = expiry
                self._data.move_to_end(key)
                self._exp[key] = expiry
                self._exp.move_to_end(key)
            else:
                self._data[key] = [value, expiry]
                self._exp[key] = expiry
                # All remaining entries are live after the purge, so the
                # front of the recency order is the LRU live entry.
                while len(self._data) > self._capacity:
                    old_key, _ = self._data.popitem(last=False)
                    self._exp.pop(old_key, None)

    def get(self, key, default=None):
        with self._lock:
            now = self._clock()
            self._purge(now)
            entry = self._data.get(key)
            if entry is None:
                return default
            if now >= entry[1]:  # Defensive check; the purge covers this.
                del self._data[key]
                self._exp.pop(key, None)
                return default
            self._data.move_to_end(key)
            return entry[0]

    def __len__(self):
        with self._lock:
            self._purge(self._clock())
            return len(self._data)

    def __contains__(self, key):
        with self._lock:
            self._purge(self._clock())
            return key in self._data

    @property
    def capacity(self):
        return self._capacity

    @property
    def ttl(self):
        return self._ttl
