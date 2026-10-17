import time
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int, ttl: float, clock=time.monotonic):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if not isinstance(ttl, (int, float)) or isinstance(ttl, bool):
            raise ValueError("ttl must be a positive finite number")
        if ttl != ttl or ttl in (float("inf"), float("-inf")) or ttl <= 0:
            raise ValueError("ttl must be a positive finite number")
        self.capacity = capacity
        self.ttl = ttl
        self.clock = clock
        self._data = OrderedDict()  # key -> (value, expiry)
        self._now = self.clock()

    def _refresh_time(self):
        t = self.clock()
        if t > self._now:
            self._now = t
        return self._now

    def _purge(self):
        now = self._refresh_time()
        expired = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in expired:
            del self._data[k]

    def put(self, key, value):
        now = self._refresh_time()
        if key in self._data:
            del self._data[key]
        self._data[key] = (value, now + self.ttl)
        self._purge()
        while len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def get(self, key, default=None):
        now = self._refresh_time()
        if key in self._data:
            value, exp = self._data[key]
            if now >= exp:
                del self._data[key]
                return default
            del self._data[key]
            self._data[key] = (value, exp)
            return value
        return default

    def __len__(self):
        self._purge()
        return len(self._data)
