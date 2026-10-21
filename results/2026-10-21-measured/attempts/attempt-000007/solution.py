"""A small memoizing decorator with hit/miss counters."""

import functools


def memoize(func):
    cache = {}
    stats = {"hits": 0, "misses": 0}

    def make_key(args, kwargs):
        # Keyword arguments are sorted by name so that call order does not matter.
        # Names are unique strings, so sorting never compares the values.
        key = (args, tuple(sorted(kwargs.items(), key=lambda item: item[0])))
        hash(key)  # raise TypeError for unhashable arguments before calling func
        return key

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = make_key(args, kwargs)
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
