import pytest
from solution import compare, parse


def test_parse_plain_version() -> None:
    assert parse("1.2.3") == (1, 2, 3, (), ())
    assert parse("0.0.0") == (0, 0, 0, (), ())


def test_parse_prerelease_and_build() -> None:
    assert parse("1.0.0-alpha.1+build.007") == (1, 0, 0, ("alpha", 1), ("build", "007"))
    assert parse("1.0.0+20130313144700") == (1, 0, 0, (), ("20130313144700",))
    assert parse("1.0.0-x-y-z.--") == (1, 0, 0, ("x-y-z", "--"), ())


def test_parse_mixed_identifier_is_string() -> None:
    assert parse("2.0.0-0a.10") == (2, 0, 0, ("0a", 10), ())


@pytest.mark.parametrize(
    "text",
    [
        "1.2",
        "1.2.3.4",
        "01.2.3",
        "1.02.3",
        "1.2.03",
        "v1.2.3",
        " 1.2.3",
        "1.2.3 ",
        "1.2.3-",
        "1.2.3+",
        "1.2.3-alpha..1",
        "1.2.3-01",
        "1.2.3-al_pha",
        "1.2.3+build..1",
        "-1.2.3",
        "1.2.x",
        "",
    ],
)
def test_parse_rejects_invalid(text: str) -> None:
    with pytest.raises(ValueError):
        parse(text)


def test_parse_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        parse(123)  # type: ignore[arg-type]


def test_compare_numeric_fields_numerically() -> None:
    assert compare("1.10.0", "1.9.0") == 1
    assert compare("2.0.0", "10.0.0") == -1
    assert compare("1.2.3", "1.2.3") == 0


def test_prerelease_is_lower_than_release() -> None:
    assert compare("1.0.0-alpha", "1.0.0") == -1
    assert compare("1.0.0", "1.0.0-rc.1") == 1


def test_spec_precedence_chain() -> None:
    chain = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]
    for low, high in zip(chain, chain[1:], strict=False):
        assert compare(low, high) == -1, (low, high)
        assert compare(high, low) == 1, (high, low)


def test_ascii_order_for_alphanumeric_identifiers() -> None:
    assert compare("1.0.0-Beta", "1.0.0-alpha") == -1
    assert compare("1.0.0-alpha-2", "1.0.0-alpha2") == -1


def test_build_metadata_is_ignored() -> None:
    assert compare("1.0.0+a", "1.0.0+b") == 0
    assert compare("1.0.0-rc.1+x", "1.0.0-rc.1") == 0


def test_compare_validates_inputs() -> None:
    with pytest.raises(ValueError):
        compare("1.0", "1.0.0")
    with pytest.raises(ValueError):
        compare("1.0.0", "1.0.0-01")
