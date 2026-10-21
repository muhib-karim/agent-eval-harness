import pytest
from memo import memoize


def counted():  # type: ignore[no-untyped-def]
    calls: list[tuple[object, ...]] = []

    @memoize
    def scale(x, factor=1):  # type: ignore[no-untyped-def]
        """Multiply x by factor."""
        calls.append((x, factor))
        return x * factor

    return scale, calls


def test_reported_case() -> None:
    scale, _ = counted()
    assert scale(3, factor=2) == 6
    assert scale(3, factor=10) == 30


def test_keyword_only_differences_are_separate_entries() -> None:
    scale, calls = counted()
    scale(2, factor=3)
    scale(2, factor=4)
    scale(2, factor=3)
    assert calls == [(2, 3), (2, 4)]
    assert scale.cache_info() == (1, 2)


def test_keyword_order_does_not_matter() -> None:
    scale, calls = counted()
    assert scale(x=5, factor=2) == 10
    assert scale(factor=2, x=5) == 10
    assert len(calls) == 1
    assert scale.cache_info() == (1, 1)


def test_positional_calls_are_cached() -> None:
    scale, calls = counted()
    assert [scale(4), scale(4), scale(5)] == [4, 4, 5]
    assert calls == [(4, 1), (5, 1)]
    assert scale.cache_info() == (1, 2)


def test_positional_and_keyword_spellings_are_correct() -> None:
    scale, _ = counted()
    assert scale(2, 7) == 14
    assert scale(2, factor=7) == 14
    assert scale(2) == 2


def test_unhashable_arguments_raise_without_calling() -> None:
    scale, calls = counted()
    assert scale((1, 2), factor=2) == (1, 2, 1, 2)
    with pytest.raises(TypeError):
        scale([1, 2])
    with pytest.raises(TypeError):
        scale(1, factor=[2])
    assert calls == [((1, 2), 2)]


def test_exceptions_are_not_cached() -> None:
    attempts: list[int] = []

    @memoize
    def flaky(x):  # type: ignore[no-untyped-def]
        attempts.append(x)
        if len(attempts) == 1:
            raise RuntimeError("first call fails")
        return x

    with pytest.raises(RuntimeError):
        flaky(1)
    assert flaky(1) == 1
    assert attempts == [1, 1]
    assert flaky.cache_info() == (0, 1)


def test_cache_clear_resets_entries_and_counters() -> None:
    scale, calls = counted()
    scale(1, factor=2)
    scale(1, factor=2)
    scale.cache_clear()
    assert scale.cache_info() == (0, 0)
    scale(1, factor=2)
    assert len(calls) == 2


def test_metadata_is_preserved() -> None:
    scale, _ = counted()
    assert scale.__name__ == "scale"
    assert scale.__doc__ == "Multiply x by factor."
    assert callable(scale.__wrapped__)


def test_none_results_are_cached() -> None:
    seen: list[int] = []

    @memoize
    def nothing(x):  # type: ignore[no-untyped-def]
        seen.append(x)

    nothing(1)
    nothing(1)
    assert seen == [1]
    assert nothing.cache_info() == (1, 1)
