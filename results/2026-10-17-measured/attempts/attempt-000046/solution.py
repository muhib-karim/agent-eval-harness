import time
import math
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int, ttl: float, clock=time.monotonic):
        # Validate capacity
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")

        # Validate ttl
        if not isinstance(ttl, (int, float)) or ttl <= 0 or math.isinf(ttl) or math.isnan(ttl):
            raise ValueError("ttl must be positive and finite")

        self.capacity = capacity
        self.ttl = ttl
        self.clock = clock
        self.cache = OrderedDict()  # Maps key -> (value, expiry_time)

    def _purge_expired(self):
        """Remove all expired entries."""
        current_time = self.clock()
        expired_keys = [
            key for key, (value, expiry) in self.cache.items()
            if current_time >= expiry
        ]
        for key in expired_keys:
            del self.cache[key]

    def put(self, key, value):
        """Insert or update a key-value pair with TTL reset."""
        self._purge_expired()

        expiry_time = self.clock() + self.ttl

        # If key already exists, remove it first to update recency
        if key in self.cache:
            del self.cache[key]
        # If we're at capacity, evict the least recently used entry
        elif len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)  # Remove oldest (first) item

        # Insert the new item (OrderedDict maintains insertion order)
        self.cache[key] = (value, expiry_time)

    def get(self, key, default=None):
        """Retrieve a value and mark it as most recently used without extending TTL."""
        self._purge_expired()

        if key not in self.cache:
            return default

        value, expiry = self.cache[key]

        # Check if expired
        if self.clock() >= expiry:
            del self.cache[key]
            return default

        # Mark as most recently used by moving to end
        self.cache.move_to_end(key)

        return value

    def __len__(self):
        """Return count of live (non-expired) entries."""
        self._purge_expired()
        return len(self.cache)
