import re


def to_roman(value: int) -> str:
    """Convert an integer in the range 1..3999 to a canonical uppercase Roman numeral."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("value must be an int (not bool)")
    if not (1 <= value <= 3999):
        raise ValueError("value must be between 1 and 3999 inclusive")

    numerals = [
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
    ]

    result = []
    remaining = value
    for val, sym in numerals:
        if remaining <= 0:
            break
        count, remaining = divmod(remaining, val)
        if count:
            result.append(sym * count)

    return "".join(result)


_ROMAN_PATTERN = re.compile(
    r"^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$"
)

_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def from_roman(text: str) -> int:
    """Convert a canonical uppercase Roman numeral string to its integer value."""
    if not isinstance(text, str) or text == "":
        raise ValueError("text must be a nonempty string")

    if not _ROMAN_PATTERN.match(text):
        raise ValueError("text is not a valid canonical Roman numeral")

    total = 0
    i = 0
    n = len(text)
    while i < n:
        current = _VALUES[text[i]]
        if i + 1 < n:
            nxt = _VALUES[text[i + 1]]
            if current < nxt:
                total += nxt - current
                i += 2
                continue
        total += current
        i += 1

    if not (1 <= total <= 3999):
        raise ValueError("resulting value out of range")

    return total
