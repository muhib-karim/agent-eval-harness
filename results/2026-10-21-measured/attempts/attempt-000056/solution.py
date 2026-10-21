"""A small memoizing decorator with hit/miss counters."""

import functools


def _make_key(args, kwargs):
    """Build a hashable cache key from positional and keyword arguments.

    Keyword arguments are sorted by name so that calls differing only in the
    order of keyword arguments share a single cache entry.  Because keyword
    names are unique strings, sorting never needs to compare the values.
    """
    if kwargs:
        return (args, tuple(sorted(kwargs.items())))
    return (args, ())


def memoize(func):
    cache = {}
    stats = {"hits": 0, "misses": 0}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = _make_key(args, kwargs)
        # Hashing the key here raises TypeError for unhashable arguments
        # before func is ever called.
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
