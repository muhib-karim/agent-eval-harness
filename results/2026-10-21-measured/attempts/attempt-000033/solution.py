"""LRU cache with per-entry time-to-live (TTL) expiry."""

import math
import numbers
import time
from collections import OrderedDict

__all__ = ["LRUCache"]

_MISSING = object()


class LRUCache:
    """LRU cache where each entry expires ``ttl`` seconds after its last put."""

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
        # key -> [value, expiry]; order = recency (LRU first, MRU last)
        self._data = OrderedDict()
        # key -> None; order = expiry order (earliest first). Because ttl is
        # constant and the clock is nondecreasing, the order in which keys
        # were last put is also the order in which they expire.
        self._expiry_order = OrderedDict()

    @property
    def capacity(self):
        return self._capacity

    @property
    def ttl(self):
        return self._ttl

    def _purge(self, now):
        """Remove every entry whose expiry is <= now."""
        data = self._data
        order = self._expiry_order
        while order:
            key = next(iter(order))
            if data[key][1] <= now:
                del order[key]
                del data[key]
            else:
                break

    def put(self, key, value):
        """Insert or update ``key``, reset its expiry, and mark it MRU."""
        hash(key)  # raise TypeError early for unhashable keys
        now = self._clock()
        self._purge(now)
        expiry = now + self._ttl
        data = self._data
        if key in data:
            entry = data[key]
            entry[0] = value
            entry[1] = expiry
            data.move_to_end(key)
            self._expiry_order.move_to_end(key)
        else:
            data[key] = [value, expiry]
            self._expiry_order[key] = None
            # All remaining entries are live after the purge, so the front
            # of the recency order is the least recently used live entry.
            while len(data) > self._capacity:
                old_key, _ = data.popitem(last=False)
                del self._expiry_order[old_key]

    def get(self, key, default=None):
        """Return the live value for ``key`` (marking it MRU) or ``default``.

        Does not extend the entry's TTL.
        """
        now = self._clock()
        self._purge(now)
        entry = self._data.get(key, _MISSING)
        if entry is _MISSING:
            return default
        self._data.move_to_end(key)
        return entry[0]

    def __len__(self):
        self._purge(self._clock())
        return len(self._data)

    def __contains__(self, key):
        """Membership test for live entries; does not affect recency."""
        self._purge(self._clock())
        return key in self._data

    def __repr__(self):
        return "LRUCache(capacity=%r, ttl=%r)" % (self._capacity, self._ttl)
