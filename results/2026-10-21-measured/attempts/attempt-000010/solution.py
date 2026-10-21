"""Streaming mean and sample variance (Welford), mergeable across shards."""

import math


class RunningStats:
    def __init__(self):
        self._n = 0
        self._mean = 0.0
        self._m2 = 0.0

    def push(self, x):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("x must be a finite number")
        self._n += 1
        delta = x - self._mean
        self._mean += delta / self._n
        self._m2 += delta * (x - self._mean)

    @property
    def count(self):
        return self._n

    @property
    def mean(self):
        if self._n < 1:
            raise ValueError("mean needs at least one value")
        return self._mean

    @property
    def variance(self):
        if self._n < 2:
            raise ValueError("variance needs at least two values")
        return self._m2 / (self._n - 1)

    @property
    def stdev(self):
        return math.sqrt(self.variance)

    def merge(self, other):
        result = RunningStats()
        na, nb = self._n, other._n
        n = na + nb
        if n == 0:
            return result
        if na == 0:
            result._n, result._mean, result._m2 = other._n, other._mean, other._m2
            return result
        if nb == 0:
            result._n, result._mean, result._m2 = self._n, self._mean, self._m2
            return result
        delta = other._mean - self._mean
        result._n = n
        result._mean = self._mean + delta * nb / n
        # Chan et al. parallel combination: the spread between the two means
        # contributes delta^2 * na * nb / n to the combined sum of squares.
        result._m2 = self._m2 + other._m2 + delta * delta * na * nb / n
        return result
