import math
import time
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int, ttl: float, clock=time.monotonic):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")

        try:
            ttl = float(ttl)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("ttl must be positive and finite") from exc
        if ttl <= 0 or not math.isfinite(ttl):
            raise ValueError("ttl must be positive and finite")

        self.capacity = capacity
        self.ttl = ttl
        self.clock = clock
        self._entries = OrderedDict()

    def _purge_expired(self, now):
        expired = [
            key
            for key, (_, expiry) in self._entries.items()
            if now >= expiry
        ]
        for key in expired:
            del self._entries[key]

    def put(self, key, value):
        now = self.clock()
        self._purge_expired(now)

        self._entries[key] = (value, now + self.ttl)
        self._entries.move_to_end(key)

        if len(self._entries) > self.capacity:
            self._entries.popitem(last=False)

    def get(self, key, default=None):
        entry = self._entries.get(key)
        if entry is None:
            return default

        value, expiry = entry
        if self.clock() >= expiry:
            del self._entries[key]
            return default

        self._entries.move_to_end(key)
        return value

    def __len__(self):
        self._purge_expired(self.clock())
        return len(self._entries)
