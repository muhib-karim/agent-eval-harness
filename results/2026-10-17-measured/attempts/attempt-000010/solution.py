import math
import time
from collections import OrderedDict

_MISSING = object()


class LRUCache:
    def __init__(self, capacity, ttl, clock=time.monotonic):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
            raise ValueError("ttl must be a positive finite number")
        try:
            ttl_f = float(ttl)
        except (OverflowError, ValueError, TypeError):
            raise ValueError("ttl must be a positive finite number")
        if not math.isfinite(ttl_f) or ttl_f <= 0:
            raise ValueError("ttl must be a positive finite number")
        if not callable(clock):
            raise ValueError("clock must be callable")
        self._capacity = capacity
        self._ttl = ttl_f
        self._clock = clock
        # key -> [value, expiry], ordered by recency (LRU first)
        self._data = OrderedDict()
        # key -> expiry, ordered by expiry (earliest first)
        self._exp = OrderedDict()

    def _purge(self, now):
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
        hash(key)  # ensure hashable (raises TypeError otherwise)
        now = self._clock()
        self._purge(now)
        expiry = now + self._ttl
        data = self._data
        if key in data:
            data[key] = [value, expiry]
            data.move_to_end(key)
            self._exp[key] = expiry
            self._exp.move_to_end(key)
        else:
            data[key] = [value, expiry]
            self._exp[key] = expiry
        while len(data) > self._capacity:
            old_key, _ = data.popitem(last=False)
            self._exp.pop(old_key, None)

    def get(self, key, default=None):
        now = self._clock()
        self._purge(now)
        entry = self._data.get(key, _MISSING)
        if entry is _MISSING:
            return default
        if now >= entry[1]:
            del self._data[key]
            self._exp.pop(key, None)
            return default
        self._data.move_to_end(key)
        return entry[0]

    def __contains__(self, key):
        now = self._clock()
        self._purge(now)
        entry = self._data.get(key, _MISSING)
        return entry is not _MISSING and now < entry[1]

    def __len__(self):
        self._purge(self._clock())
        return len(self._data)

    @property
    def capacity(self):
        return self._capacity

    @property
    def ttl(self):
        return self._ttl
