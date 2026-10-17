import time
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int, ttl: float, clock=time.monotonic):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if not isinstance(ttl, (int, float)) or isinstance(ttl, bool) or ttl <= 0 or ttl != ttl or ttl == float('inf'):
            raise ValueError("ttl must be positive and finite")
        self.capacity = capacity
        self.ttl = float(ttl)
        self.clock = clock
        # Maps key -> (value, expiry)
        self._data = OrderedDict()

    def _purge(self) -> None:
        now = self.clock()
        expired = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in expired:
            del self._data[k]

    def put(self, key, value) -> None:
        self._purge()
        expiry = self.clock() + self.ttl
        if key in self._data:
            del self._data[key]
        self._data[key] = (value, expiry)
        while len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def get(self, key, default=None):
        self._purge()
        if key in self._data:
            value, expiry = self._data[key]
            del self._data[key]
            self._data[key] = (value, expiry)
            return value
        return default

    def __len__(self) -> int:
        self._purge()
        return len(self._data)
