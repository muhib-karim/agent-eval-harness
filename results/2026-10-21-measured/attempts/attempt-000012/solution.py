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

    def _copy(self):
        result = RunningStats()
        result._n = self._n
        result._mean = self._mean
        result._m2 = self._m2
        return result

    def merge(self, other):
        if not isinstance(other, RunningStats):
            raise TypeError("other must be a RunningStats instance")
        if other._n == 0:
            return self._copy()
        if self._n == 0:
            return other._copy()

        n_a = self._n
        n_b = other._n
        n = n_a + n_b
        delta = other._mean - self._mean

        result = RunningStats()
        result._n = n
        result._mean = self._mean + delta * (n_b / n)
        # Chan et al. parallel combination: the between-group term accounts
        # for the difference in means of the two partitions.
        result._m2 = self._m2 + other._m2 + delta * delta * (n_a * n_b / n)
        return result
