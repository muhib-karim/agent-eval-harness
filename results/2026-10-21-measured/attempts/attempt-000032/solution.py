import math
import time
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity, ttl, clock=time.monotonic):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
            raise ValueError("ttl must be a positive finite number")
        try:
            ok = math.isfinite(ttl) and ttl > 0
        except (TypeError, OverflowError):
            ok = False
        if not ok:
            raise ValueError("ttl must be a positive finite number")
        if not callable(clock):
            raise ValueError("clock must be callable")
        self._capacity = capacity
        self._ttl = ttl
        self._clock = clock
        # key -> value, ordered by recency (LRU first)
        self._data = OrderedDict()
        # key -> expiry, ordered by expiry (earliest first); valid since ttl is
        # constant and the clock is nondecreasing
        self._expiry = OrderedDict()

    def _purge(self, now):
        exp = self._expiry
        data = self._data
        while exp:
            key, when = next(iter(exp.items()))
            if now >= when:
                exp.popitem(last=False)
                data.pop(key, None)
            else:
                break

    def put(self, key, value):
        hash(key)  # raise TypeError for unhashable keys
        now = self._clock()
        self._purge(now)
        self._data[key] = value
        self._data.move_to_end(key)
        self._expiry[key] = now + self._ttl
        self._expiry.move_to_end(key)
        while len(self._data) > self._capacity:
            old_key, _ = self._data.popitem(last=False)
            self._expiry.pop(old_key, None)

    def get(self, key, default=None):
        now = self._clock()
        self._purge(now)
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return default

    def __contains__(self, key):
        now = self._clock()
        self._purge(now)
        return key in self._data

    def __len__(self):
        self._purge(self._clock())
        return len(self._data)

    def __repr__(self):
        return "LRUCache(capacity=%r, ttl=%r, size=%d)" % (
            self._capacity, self._ttl, len(self._data))
