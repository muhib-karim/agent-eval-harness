import math
import time
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int, ttl: float, clock=time.monotonic):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if isinstance(ttl, bool):
            raise ValueError("ttl must be a positive finite number")
        try:
            ttl_ok = math.isfinite(ttl) and ttl > 0
        except TypeError:
            ttl_ok = False
        if not ttl_ok:
            raise ValueError("ttl must be a positive finite number")
        self._capacity = capacity
        self._ttl = ttl
        self._clock = clock
        # key -> value, ordered by recency (least recent first)
        self._data = OrderedDict()
        # key -> expiry, ordered by last put time (earliest expiry first,
        # since ttl is constant and the clock is nondecreasing)
        self._exp = OrderedDict()

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
        self._data[key] = value
        self._data.move_to_end(key)
        self._exp[key] = now + self._ttl
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
