import pytest
from slug import slugify


def test_reported_cases() -> None:
    assert slugify("Hello -- World") == "hello-world"
    assert slugify("Tom & Jerry") == "tom-jerry"


def test_simple_titles() -> None:
    assert slugify("Hello World") == "hello-world"
    assert slugify("Python 3.12 Release") == "python-3-12-release"


def test_accents_are_transliterated() -> None:
    assert slugify("Crème Brûlée") == "creme-brulee"
    assert slugify("Ångström façade") == "angstrom-facade"


def test_runs_of_mixed_separators_collapse() -> None:
    assert slugify("a  _-_  b...c") == "a-b-c"
    assert slugify("one/two\\three\tfour\nfive") == "one-two-three-four-five"


def test_leading_and_trailing_separators_are_stripped() -> None:
    assert slugify("  --Already Sluggy--  ") == "already-sluggy"
    assert slugify("!!!wow!!!") == "wow"


def test_non_ascii_only_input_gives_empty_slug() -> None:
    assert slugify("日本語") == ""
    assert slugify("") == ""
    assert slugify(" - ") == ""


def test_max_length_cuts_and_strips_trailing_dash() -> None:
    assert slugify("Hello wonderful world", max_length=6) == "hello"
    assert slugify("Hello wonderful world", max_length=15) == "hello-wonderful"
    assert slugify("abc", max_length=10) == "abc"


@pytest.mark.parametrize("bad", [0, -3, True, 2.5, "5"])
def test_invalid_max_length(bad: object) -> None:
    with pytest.raises(ValueError):
        slugify("abc", max_length=bad)  # type: ignore[arg-type]


def test_non_string_text() -> None:
    with pytest.raises(TypeError):
        slugify(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        slugify(b"bytes")  # type: ignore[arg-type]
