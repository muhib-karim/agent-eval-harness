"""A small memoizing decorator with hit/miss counters."""

import functools


def memoize(func):
    cache = {}
    stats = {"hits": 0, "misses": 0}

    def make_key(args, kwargs):
        # Sort keyword arguments by name so that call-site ordering does not
        # matter. Names are unique strings, so values are never compared.
        # Positional and keyword parts occupy separate slots, so they cannot
        # be confused with each other.
        return (args, tuple(sorted(kwargs.items())))

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = make_key(args, kwargs)
        # Hashing happens here; unhashable arguments raise TypeError
        # before func is called.
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
