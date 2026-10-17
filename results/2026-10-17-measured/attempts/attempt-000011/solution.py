import math
import numbers
import time
from collections import OrderedDict

_MISSING = object()


class LRUCache:
    def __init__(self, capacity, ttl, clock=time.monotonic):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if isinstance(ttl, bool) or not isinstance(ttl, numbers.Real):
            raise ValueError("ttl must be a positive finite number")
        try:
            ttl_f = float(ttl)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("ttl must be a positive finite number")
        if not math.isfinite(ttl_f) or not ttl > 0:
            raise ValueError("ttl must be a positive finite number")
        if not callable(clock):
            raise ValueError("clock must be callable")
        self._capacity = capacity
        self._ttl = ttl
        self._clock = clock
        # key -> [value, expiry]; order = recency (front = LRU)
        self._data = OrderedDict()
        # key -> None; order = expiry (front = earliest expiry).
        # Valid because ttl is constant and clock is nondecreasing.
        self._expiry_order = OrderedDict()

    def _purge(self, now):
        data = self._data
        eo = self._expiry_order
        while eo:
            key = next(iter(eo))
            if data[key][1] <= now:
                del eo[key]
                del data[key]
            else:
                break

    def put(self, key, value):
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
        while len(data) > self._capacity:
            old_key, _ = data.popitem(last=False)
            del self._expiry_order[old_key]

    def get(self, key, default=None):
        now = self._clock()
        self._purge(now)
        entry = self._data.get(key, _MISSING)
        if entry is _MISSING:
            return default
        if entry[1] <= now:
            del self._data[key]
            del self._expiry_order[key]
            return default
        self._data.move_to_end(key)
        return entry[0]

    def __len__(self):
        self._purge(self._clock())
        return len(self._data)

    def __contains__(self, key):
        now = self._clock()
        self._purge(now)
        entry = self._data.get(key, _MISSING)
        return entry is not _MISSING and entry[1] > now

    def __repr__(self):
        return "LRUCache(capacity=%r, ttl=%r)" % (self._capacity, self._ttl)
