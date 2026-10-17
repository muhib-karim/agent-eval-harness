"""Roman numeral conversion utilities (standard library only)."""

_PAIRS = (
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

_SYMBOLS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def to_roman(value: int) -> str:
    """Convert an integer in 1..3999 to its canonical uppercase Roman numeral."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("value must be an int (not bool)")
    if not 1 <= value <= 3999:
        raise ValueError("value must be in range 1..3999")
    parts = []
    remaining = value
    for amount, symbol in _PAIRS:
        if remaining == 0:
            break
        count, remaining = divmod(remaining, amount)
        if count:
            parts.append(symbol * count)
    return "".join(parts)


def from_roman(text: str) -> int:
    """Convert a canonical uppercase Roman numeral (1..3999) to an integer."""
    if not isinstance(text, str):
        raise ValueError("text must be a str")
    if not text:
        raise ValueError("empty Roman numeral")
    for ch in text:
        if ch not in _SYMBOLS:
            raise ValueError(f"invalid Roman numeral character: {ch!r}")

    total = 0
    n = len(text)
    for i, ch in enumerate(text):
        v = _SYMBOLS[ch]
        if i + 1 < n and v < _SYMBOLS[text[i + 1]]:
            total -= v
        else:
            total += v

    if not 1 <= total <= 3999:
        raise ValueError("Roman numeral out of range 1..3999")
    if to_roman(total) != text:
        raise ValueError("noncanonical Roman numeral")
    return total
