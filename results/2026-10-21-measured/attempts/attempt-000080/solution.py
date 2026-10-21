import math
import time
from collections import OrderedDict


class LRUCache:
    """LRU cache with per-entry TTL expiry and an injectable monotonic clock."""

    __slots__ = ("_capacity", "_ttl", "_clock", "_data")

    def __init__(self, capacity, ttl, clock=time.monotonic):
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise ValueError("capacity must be a positive integer")
        if capacity <= 0:
            raise ValueError("capacity must be a positive integer")

        if isinstance(ttl, bool):
            raise ValueError("ttl must be a positive finite number")
        try:
            ttl_value = float(ttl)
        except (TypeError, ValueError):
            raise ValueError("ttl must be a positive finite number")
        if math.isnan(ttl_value) or math.isinf(ttl_value) or ttl_value <= 0:
            raise ValueError("ttl must be a positive finite number")

        if not callable(clock):
            raise ValueError("clock must be callable")

        self._capacity = capacity
        self._ttl = ttl_value
        self._clock = clock
        self._data = OrderedDict()  # key -> (value, expiry)

    # ------------------------------------------------------------------ helpers

    def _now(self):
        return self._clock()

    def _purge(self, now=None):
        """Remove every entry whose expiry has been reached."""
        if now is None:
            now = self._now()
        if not self._data:
            return
        dead = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in dead:
            del self._data[k]

    # ---------------------------------------------------------------- public API

    @property
    def capacity(self):
        return self._capacity

    @property
    def ttl(self):
        return self._ttl

    def put(self, key, value):
        now = self._now()
        self._purge(now)
        if key in self._data:
            del self._data[key]
        self._data[key] = (value, now + self._ttl)
        while len(self._data) > self._capacity:
            self._data.popitem(last=False)

    def get(self, key, default=None):
        entry = self._data.get(key)
        if entry is None and key not in self._data:
            return default
        value, expiry = entry
        if self._now() >= expiry:
            del self._data[key]
            return default
        self._data.move_to_end(key)
        return value

    def pop(self, key, default=None):
        entry = self._data.pop(key, None)
        if entry is None:
            return default
        value, expiry = entry
        if self._now() >= expiry:
            return default
        return value

    def delete(self, key):
        """Remove key if present. Returns True if a live entry was removed."""
        return self.pop(key, _MISSING) is not _MISSING

    def clear(self):
        self._data.clear()

    def keys(self):
        self._purge()
        return list(self._data.keys())

    def items(self):
        self._purge()
        return [(k, v) for k, (v, _) in self._data.items()]

    def __contains__(self, key):
        entry = self._data.get(key)
        if entry is None and key not in self._data:
            return False
        if self._now() >= entry[1]:
            del self._data[key]
            return False
        return True

    def __len__(self):
        self._purge()
        return len(self._data)

    def __iter__(self):
        return iter(self.keys())

    def __repr__(self):
        return "LRUCache(capacity=%r, ttl=%r, size=%d)" % (
            self._capacity, self._ttl, len(self))


_MISSING = object()
