"""A small memoizing decorator with hit/miss counters."""

import functools


def memoize(func):
    cache = {}
    stats = {"hits": 0, "misses": 0}

    def make_key(args, kwargs):
        # Keyword arguments are included in the key, sorted by name so that
        # calls that pass the same keyword arguments in a different order
        # share a single cache entry. Positional and keyword arguments are
        # kept in separate parts of the key so they cannot collide.
        return (args, tuple(sorted(kwargs.items())))

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = make_key(args, kwargs)
        # Hashing the key raises TypeError for unhashable arguments before
        # func is called.
        hash(key)
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
