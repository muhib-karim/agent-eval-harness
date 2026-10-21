import math
import time
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int, ttl: float, clock=time.monotonic):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        try:
            ok = ttl > 0 and math.isfinite(ttl)
        except TypeError:
            ok = False
        if not ok:
            raise ValueError("ttl must be positive and finite")
        self._capacity = capacity
        self._ttl = ttl
        self._clock = clock
        # Recency order: least recently used first.
        self._data = OrderedDict()   # key -> value
        # Expiry order: oldest put first. Because the clock is nondecreasing and
        # ttl is constant, this is also ascending order of expiry time.
        self._exp = OrderedDict()    # key -> expiry

    def _purge(self, now):
        exp = self._exp
        while exp:
            key = next(iter(exp))
            if exp[key] <= now:
                del exp[key]
                del self._data[key]
            else:
                break

    def put(self, key, value):
        now = self._clock()
        self._purge(now)
        expiry = now + self._ttl
        if key in self._data:
            self._data[key] = value
            self._data.move_to_end(key)
        else:
            self._data[key] = value
        self._exp[key] = expiry
        self._exp.move_to_end(key)
        while len(self._data) > self._capacity:
            old, _ = self._data.popitem(last=False)
            del self._exp[old]

    def get(self, key, default=None):
        now = self._clock()
        self._purge(now)
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return default

    def __contains__(self, key):
        self._purge(self._clock())
        return key in self._data

    def __len__(self):
        self._purge(self._clock())
        return len(self._data)
