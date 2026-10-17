"""
solution.py

Roman numeral conversion utilities.

Provides:
    to_roman(value: int) -> str
    from_roman(text: str) -> int

Rules:
    - Accepts integers in range 1..3999 inclusive for to_roman.
    - bool is explicitly rejected (even though bool is a subclass of int).
    - Non-integer types raise ValueError.
    - from_roman accepts only nonempty, uppercase, canonical Roman numeral
      strings representing values in 1..3999. Any deviation (lowercase,
      whitespace, invalid symbols, invalid repetition, noncanonical
      subtractive notation, etc.) raises ValueError.
"""

# Ordered list of (value, numeral) pairs, largest first, including
# subtractive combinations, used for greedy conversion to Roman numerals.
_VALUE_NUMERAL_PAIRS = [
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

# Mapping of single Roman numeral characters to their integer values,
# used for the initial (non-canonical-checked) parse step.
_CHAR_VALUES = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
    "D": 500,
    "M": 1000,
}


def to_roman(value: int) -> str:
    """
    Convert an integer in the range 1..3999 to its canonical uppercase
    Roman numeral representation.

    Raises:
        ValueError: if value is not an int (bool is rejected too), or if
            value is outside the range 1..3999.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("value must be an int (not bool) in range 1..3999")
    if not (1 <= value <= 3999):
        raise ValueError("value must be in range 1..3999")

    remaining = value
    parts = []
    for amount, numeral in _VALUE_NUMERAL_PAIRS:
        if amount == 0:
            continue
        count, remaining = divmod(remaining, amount)
        if count:
            parts.append(numeral * count)
        if remaining == 0:
            break
    return "".join(parts)


def from_roman(text: str) -> int:
    """
    Convert a canonical uppercase Roman numeral string to its integer
    value (range 1..3999).

    Only strictly canonical forms are accepted:
        - uppercase letters only (I, V, X, L, C, D, M)
        - nonempty
        - no whitespace
        - correct use of subtractive notation (IV, IX, XL, XC, CD, CM)
        - no invalid repetition (e.g. IIII, VV, LL, DD, etc.)

    Any other input (including wrong types) raises ValueError.
    """
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if text == "":
        raise ValueError("text must be a nonempty Roman numeral")

    # Reject anything with characters outside the valid numeral set
    # (this also rejects whitespace and lowercase letters).
    for ch in text:
        if ch not in _CHAR_VALUES:
            raise ValueError(f"invalid Roman numeral character: {ch!r}")

    # Parse using the standard subtractive-pair algorithm.
    total = 0
    i = 0
    n = len(text)
    while i < n:
        current = _CHAR_VALUES[text[i]]
        if i + 1 < n:
            next_val = _CHAR_VALUES[text[i + 1]]
            if current < next_val:
                total += next_val - current
                i += 2
                continue
        total += current
        i += 1

    if not (1 <= total <= 3999):
        raise ValueError("Roman numeral value out of range 1..3999")

    # Canonical check: regenerating the numeral from the parsed value
    # must reproduce the exact same string. This rejects noncanonical
    # forms like IIII, VV, IIX, VX, etc.
    if to_roman(total) != text:
        raise ValueError(f"not a canonical Roman numeral: {text!r}")

    return total
