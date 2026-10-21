import pytest
from solution import parse_ini


def test_empty_input() -> None:
    assert parse_ini("") == {}
    assert parse_ini("\n  \n; only a comment\n# another\n") == {}


def test_basic_sections_and_whitespace() -> None:
    text = "[server]\n  host = example.test  \nport=8080\n\n[client]\nretries = 3\n"
    assert parse_ini(text) == {
        "server": {"host": "example.test", "port": "8080"},
        "client": {"retries": "3"},
    }


def test_split_at_first_equals_and_keep_comment_chars_in_values() -> None:
    result = parse_ini("[a]\nurl = x=1&y=2\nnote = keep ; this # too\nempty =\n")
    assert result == {"a": {"url": "x=1&y=2", "note": "keep ; this # too", "empty": ""}}


def test_global_keys_and_empty_sections() -> None:
    assert parse_ini("name = top\n[empty]\n") == {"": {"name": "top"}, "empty": {}}
    assert parse_ini("[only]\n") == {"only": {}}


def test_keys_lowercased_sections_case_sensitive() -> None:
    result = parse_ini("[Main]\nKey = 1\n[main]\nKEY = 2\n")
    assert result == {"Main": {"key": "1"}, "main": {"key": "2"}}


def test_repeated_section_continues_in_first_seen_order() -> None:
    result = parse_ini("[a]\nx = 1\n[b]\ny = 2\n[a]\nz = 3\n")
    assert result == {"a": {"x": "1", "z": "3"}, "b": {"y": "2"}}
    assert list(result) == ["a", "b"]
    assert list(result["a"]) == ["x", "z"]


def test_crlf_line_endings() -> None:
    assert parse_ini("[s]\r\nk = v\r\n") == {"s": {"k": "v"}}


def test_section_name_is_stripped() -> None:
    assert parse_ini("[  spaced name  ]\nk=v") == {"spaced name": {"k": "v"}}


@pytest.mark.parametrize(
    "text,line",
    [
        ("[a]\njust words\n", 2),
        ("[a]\n = value\n", 2),
        ("ok = 1\n\n[a\n", 3),
        ("[]\n", 1),
        ("[   ]\n", 1),
        ("[a]x\n", 1),
    ],
)
def test_errors_report_line_numbers(text: str, line: int) -> None:
    with pytest.raises(ValueError, match=rf"line {line}\b"):
        parse_ini(text)


def test_duplicate_key_case_insensitive() -> None:
    with pytest.raises(ValueError, match=r"line 3\b"):
        parse_ini("[a]\nKey = 1\nkey = 2\n")


def test_duplicate_key_across_repeated_section() -> None:
    with pytest.raises(ValueError, match=r"line 4\b"):
        parse_ini("[a]\nk = 1\n[a]\nk = 2\n")
