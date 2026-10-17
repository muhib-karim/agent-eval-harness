import time
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int, ttl: float, clock=time.monotonic):
        # Validate capacity
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")

        # Validate ttl
        if not isinstance(ttl, (int, float)) or ttl <= 0 or not (ttl < float('inf')):
            raise ValueError("ttl must be positive and finite")

        self.capacity = capacity
        self.ttl = ttl
        self.clock = clock
        self.cache = OrderedDict()  # key -> (value, expiry_time)

    def _purge_expired(self):
        """Remove all expired entries from cache."""
        current_time = self.clock()
        expired_keys = [
            key for key, (value, expiry) in self.cache.items()
            if current_time >= expiry
        ]
        for key in expired_keys:
            del self.cache[key]

    def _is_live(self, key):
        """Check if a key exists and is not expired."""
        if key not in self.cache:
            return False
        value, expiry = self.cache[key]
        return self.clock() < expiry

    def put(self, key, value):
        """Insert or update a key-value pair and reset its expiry."""
        self._purge_expired()

        expiry_time = self.clock() + self.ttl

        # If key already exists, remove it first to update recency
        if key in self.cache:
            del self.cache[key]

        # Add the key-value pair (OrderedDict maintains insertion order)
        self.cache[key] = (value, expiry_time)

        # If capacity is exceeded, evict the least recently used live entry
        while len(self.cache) > self.capacity:
            # Remove the first (oldest) entry
            self.cache.popitem(last=False)

    def get(self, key, default=None):
        """Get a value and mark it as most recently used without extending TTL."""
        self._purge_expired()

        if key not in self.cache:
            return default

        value, expiry = self.cache[key]

        # Check if the entry is expired
        if self.clock() >= expiry:
            del self.cache[key]
            return default

        # Move to end to mark as most recently used (without extending TTL)
        self.cache.move_to_end(key)

        return value

    def __len__(self):
        """Return the count of live entries only."""
        self._purge_expired()
        return len(self.cache)
