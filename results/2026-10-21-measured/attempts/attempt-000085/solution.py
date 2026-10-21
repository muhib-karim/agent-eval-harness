"""Roman numeral conversion utilities.

Provides ``to_roman`` and ``from_roman`` for integers in the range 1..3999,
using canonical uppercase Roman numerals with the standard subtractive forms
(IV, IX, XL, XC, CD, CM).
"""

import re

__all__ = ["to_roman", "from_roman"]

_MIN_VALUE = 1
_MAX_VALUE = 3999

# Ordered from largest to smallest for greedy conversion.
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

# Pattern describing exactly the canonical Roman numerals for 1..3999.
# Note: this pattern also matches the empty string, so emptiness is
# checked separately.
_CANONICAL_PATTERN = re.compile(
    r"M{0,3}"
    r"(CM|CD|D?C{0,3})"
    r"(XC|XL|L?X{0,3})"
    r"(IX|IV|V?I{0,3})"
)


def _validate_int(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            "value must be an int (not bool), got {!r}".format(type(value).__name__)
        )
    if value < _MIN_VALUE or value > _MAX_VALUE:
        raise ValueError(
            "value must be in range {}..{}, got {}".format(_MIN_VALUE, _MAX_VALUE, value)
        )


def to_roman(value: int) -> str:
    """Convert an integer in 1..3999 to its canonical uppercase Roman numeral.

    Raises ValueError for bools, non-integers, or out-of-range values.
    """
    _validate_int(value)
    remaining = value
    parts = []
    for magnitude, symbol in _NUMERALS:
        if remaining == 0:
            break
        count, remaining = divmod(remaining, magnitude)
        if count:
            parts.append(symbol * count)
    return "".join(parts)


def from_roman(text: str) -> int:
    """Convert a canonical uppercase Roman numeral (1..3999) to an integer.

    Only nonempty, canonical, uppercase forms are accepted. Whitespace,
    lowercase letters, unknown symbols, invalid repetitions, and
    noncanonical subtractive forms all raise ValueError. Non-string input
    also raises ValueError.
    """
    if not isinstance(text, str):
        raise ValueError(
            "text must be a str, got {!r}".format(type(text).__name__)
        )
    if not text:
        raise ValueError("Roman numeral must be nonempty")
    if _CANONICAL_PATTERN.fullmatch(text) is None:
        raise ValueError("invalid Roman numeral: {!r}".format(text))

    total = 0
    index = 0
    length = len(text)
    for magnitude, symbol in _NUMERALS:
        symbol_len = len(symbol)
        while text.startswith(symbol, index):
            total += magnitude
            index += symbol_len
            if index >= length:
                break
        if index >= length:
            break

    # Defensive round-trip check: guarantees canonical form and range.
    if index != length or to_roman(total) != text:
        raise ValueError("invalid Roman numeral: {!r}".format(text))
    return total
