import re

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

_VALUES = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
    "D": 500,
    "M": 1000,
}

_CANONICAL_RE = re.compile(
    r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})"
)


def to_roman(value: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("value must be an integer between 1 and 3999")
    if value < 1 or value > 3999:
        raise ValueError("value must be between 1 and 3999")

    result = []
    remaining = value
    for number, symbol in _NUMERALS:
        count, remaining = divmod(remaining, number)
        if count:
            result.append(symbol * count)
    return "".join(result)


def from_roman(text: str) -> int:
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if not text:
        raise ValueError("text must not be empty")
    if any(ch not in _VALUES for ch in text):
        raise ValueError("invalid Roman numeral")
    if _CANONICAL_RE.fullmatch(text) is None:
        raise ValueError("noncanonical Roman numeral")

    total = 0
    i = 0
    while i < len(text):
        current = _VALUES[text[i]]
        if i + 1 < len(text) and current < _VALUES[text[i + 1]]:
            total += _VALUES[text[i + 1]] - current
            i += 2
        else:
            total += current
            i += 1

    if total < 1 or total > 3999:
        raise ValueError("value out of range")
    return total
