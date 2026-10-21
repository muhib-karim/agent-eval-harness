import pytest
from solution import levenshtein


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("kitten", "sitting", 3),
        ("flaw", "lawn", 2),
        ("intention", "execution", 5),
        ("abc", "abc", 0),
        ("abc", "cba", 2),
    ],
)
def test_classic_pairs(a: str, b: str, expected: int) -> None:
    assert levenshtein(a, b) == expected


def test_empty_strings() -> None:
    assert levenshtein("", "") == 0
    assert levenshtein("", "abc") == 3
    assert levenshtein("abcd", "") == 4


def test_symmetric() -> None:
    assert levenshtein("sunday", "saturday") == levenshtein("saturday", "sunday") == 3


def test_unicode_code_points_and_case() -> None:
    assert levenshtein("café", "cafe") == 1
    assert levenshtein("naïve", "naive") == 1
    assert levenshtein("A", "a") == 1


def test_bound_reached_returns_true_distance() -> None:
    assert levenshtein("kitten", "sitting", max_distance=3) == 3
    assert levenshtein("same", "same", max_distance=0) == 0


def test_bound_exceeded_returns_bound_plus_one() -> None:
    assert levenshtein("kitten", "sitting", max_distance=2) == 3
    assert levenshtein("abc", "xyz", max_distance=0) == 1
    assert levenshtein("", "abcdef", max_distance=2) == 3


@pytest.mark.parametrize("bad", [-1, True, 1.5, "2"])
def test_invalid_bound(bad: object) -> None:
    with pytest.raises(ValueError):
        levenshtein("a", "b", max_distance=bad)  # type: ignore[arg-type]


def test_non_string_arguments() -> None:
    with pytest.raises(TypeError):
        levenshtein(["a"], "a")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        levenshtein("a", None)  # type: ignore[arg-type]


def test_medium_strings_are_fast_enough() -> None:
    a = "ab" * 500
    b = "ba" * 500
    assert levenshtein(a, b) == 2


def test_long_strings_with_small_bound() -> None:
    a = "x" * 20_000
    b = "x" * 19_990 + "y" * 10
    assert levenshtein(a, b, max_distance=5) == 6
    assert levenshtein(a, a, max_distance=1) == 0
