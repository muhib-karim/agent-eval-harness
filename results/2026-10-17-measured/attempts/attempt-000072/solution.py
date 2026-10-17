import re

_ROMAN_PATTERN = re.compile(
    r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})"
)

_ROMAN_VALUES = (
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

_SYMBOL_VALUES = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
    "D": 500,
    "M": 1000,
}


def to_roman(value: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 3999:
        raise ValueError("value must be an integer from 1 to 3999")

    parts = []
    for amount, numeral in _ROMAN_VALUES:
        count, value = divmod(value, amount)
        parts.append(numeral * count)
    return "".join(parts)


def from_roman(text: str) -> int:
    if not isinstance(text, str) or not text or _ROMAN_PATTERN.fullmatch(text) is None:
        raise ValueError("text must be a canonical uppercase Roman numeral")

    total = 0
    for index, symbol in enumerate(text):
        value = _SYMBOL_VALUES[symbol]
        if index + 1 < len(text) and value < _SYMBOL_VALUES[text[index + 1]]:
            total -= value
        else:
            total += value
    return total
