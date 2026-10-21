"""Roman numeral conversion utilities.

Provides ``to_roman`` and ``from_roman`` for canonical uppercase Roman
numerals in the range 1..3999.
"""

import re

__all__ = ["to_roman", "from_roman"]

_MIN_VALUE = 1
_MAX_VALUE = 3999

# Value/symbol pairs ordered from largest to smallest, including the
# canonical subtractive forms.
_NUMERALS = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)

# Strict canonical grammar for Roman numerals 1..3999.
# ``fullmatch`` is used so that trailing newlines or other characters are
# rejected; the empty string is rejected separately.
_CANONICAL_RE = re.compile(
    r"M{0,3}"
    r"(?:CM|CD|D?C{0,3})"
    r"(?:XC|XL|L?X{0,3})"
    r"(?:IX|IV|V?I{0,3})"
)


def to_roman(value: int) -> str:
    """Convert an integer in 1..3999 to a canonical uppercase Roman numeral.

    Raises:
        ValueError: if ``value`` is a bool, not an int, or out of range.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            "value must be an int (not bool), got {!r}".format(type(value).__name__)
        )
    if value < _MIN_VALUE or value > _MAX_VALUE:
        raise ValueError(
            "value must be between {} and {}, got {}".format(
                _MIN_VALUE, _MAX_VALUE, value
            )
        )

    remaining = value
    parts = []
    for amount, symbol in _NUMERALS:
        if remaining == 0:
            break
        count, remaining = divmod(remaining, amount)
        if count:
            parts.append(symbol * count)
    return "".join(parts)


def from_roman(text: str) -> int:
    """Convert a canonical uppercase Roman numeral to an integer in 1..3999.

    Only nonempty, uppercase, canonical forms are accepted. Whitespace,
    lowercase letters, unknown symbols, invalid repetitions, and
    noncanonical subtractive forms all raise ``ValueError``.

    Raises:
        ValueError: if ``text`` is not a str or is not a canonical numeral.
    """
    if not isinstance(text, str):
        raise ValueError(
            "text must be a str, got {!r}".format(type(text).__name__)
        )
    if not text:
        raise ValueError("Roman numeral must not be empty")
    if _CANONICAL_RE.fullmatch(text) is None:
        raise ValueError("invalid Roman numeral: {!r}".format(text))

    total = 0
    index = 0
    length = len(text)
    for amount, symbol in _NUMERALS:
        symbol_len = len(symbol)
        while text.startswith(symbol, index):
            total += amount
            index += symbol_len
    if index != length:
        # Should be unreachable given the regex, but guard anyway.
        raise ValueError("invalid Roman numeral: {!r}".format(text))

    # Round-trip check guarantees the input was the canonical spelling.
    if total < _MIN_VALUE or total > _MAX_VALUE or to_roman(total) != text:
        raise ValueError("invalid Roman numeral: {!r}".format(text))
    return total
