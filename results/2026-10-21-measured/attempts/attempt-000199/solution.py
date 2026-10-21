"""A small memoizing decorator with hit/miss counters."""

import functools


def memoize(func):
    cache = {}
    stats = {"hits": 0, "misses": 0}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Create a cache key that includes both args and sorted kwargs items
        # to ensure different keyword arguments produce different cache entries
        key = (args, tuple(sorted(kwargs.items())))
        if key in cache:
            stats["hits"] += 1
            return cache[key]
        result = func(*args, **kwargs)
        stats["misses"] += 1
        cache[key] = result
        return result

    def cache_info():
        return stats["hits"], stats["misses"]

    def cache_clear():
        cache.clear()
        stats["hits"] = stats["misses"] = 0

    wrapper.cache_info = cache_info
    wrapper.cache_clear = cache_clear
    return wrapper
