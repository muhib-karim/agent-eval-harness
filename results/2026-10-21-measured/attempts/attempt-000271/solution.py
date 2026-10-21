import math
import time
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int, ttl: float, clock=time.monotonic):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")

        try:
            if not math.isfinite(ttl) or ttl <= 0:
                raise ValueError
            ttl = float(ttl)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("ttl must be positive and finite") from None

        self.capacity = capacity
        self.ttl = ttl
        self.clock = clock
        self._entries = OrderedDict()

    def _purge_expired(self, now):
        for key, (_, expiry) in list(self._entries.items()):
            if now >= expiry:
                del self._entries[key]

    def put(self, key, value):
        now = self.clock()
        expiry = now + self.ttl

        if key in self._entries:
            self._entries[key] = (value, expiry)
            self._entries.move_to_end(key)
            return

        if len(self._entries) >= self.capacity:
            self._purge_expired(now)
            if len(self._entries) >= self.capacity:
                self._entries.popitem(last=False)

        self._entries[key] = (value, expiry)

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
