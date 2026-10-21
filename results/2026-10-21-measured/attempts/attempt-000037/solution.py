"""Roman numeral conversion utilities (standard library only)."""

_TABLE = (
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

_VALID_CHARS = frozenset("MDCLXVI")


def to_roman(value: int) -> str:
    """Convert an integer in 1..3999 to a canonical uppercase Roman numeral."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("value must be an integer")
    if not 1 <= value <= 3999:
        raise ValueError("value must be in range 1..3999")
    n = int(value)
    parts = []
    for num, sym in _TABLE:
        if n == 0:
            break
        count, n = divmod(n, num)
        if count:
            parts.append(sym * count)
    return "".join(parts)


def from_roman(text: str) -> int:
    """Convert a canonical uppercase Roman numeral (1..3999) to an integer."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if not text:
        raise ValueError("empty Roman numeral")
    for ch in text:
        if ch not in _VALID_CHARS:
            raise ValueError(f"invalid Roman numeral character: {ch!r}")

    pos = 0
    total = 0
    length = len(text)
    for num, sym in _TABLE:
        while text.startswith(sym, pos):
            total += num
            pos += len(sym)
            if total > 3999:
                raise ValueError("Roman numeral out of range")
    if pos != length:
        raise ValueError(f"invalid Roman numeral: {text!r}")
    if not 1 <= total <= 3999:
        raise ValueError("Roman numeral out of range")
    if to_roman(total) != text:
        raise ValueError(f"noncanonical Roman numeral: {text!r}")
    return total


__all__ = ["to_roman", "from_roman"]
