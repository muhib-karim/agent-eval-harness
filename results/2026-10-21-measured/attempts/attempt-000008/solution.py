"""A small memoizing decorator with hit/miss counters."""

import functools


def memoize(func):
    cache = {}
    stats = {"hits": 0, "misses": 0}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Include keyword arguments in the key. Sorting by name makes the key
        # independent of keyword order (names are unique, so values are never
        # compared). Positional and keyword arguments are kept in separate
        # components, so a positional spelling and a keyword spelling of the
        # same argument may be cached separately.
        key = (args, tuple(sorted(kwargs.items())))
        # Hashing the key (in the membership test) raises TypeError for
        # unhashable arguments before func is called.
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
