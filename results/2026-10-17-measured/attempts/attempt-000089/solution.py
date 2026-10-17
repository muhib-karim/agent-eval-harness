def to_roman(value: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("value must be an integer in 1..3999")
    if value < 1 or value > 3999:
        raise ValueError("value must be in 1..3999")

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
    n = value
    for num, symbol in numerals:
        while n >= num:
            result.append(symbol)
            n -= num
    return "".join(result)


def from_roman(text: str) -> int:
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if not text:
        raise ValueError("empty Roman numeral")

    values = {
        "I": 1,
        "V": 5,
        "X": 10,
        "L": 50,
        "C": 100,
        "D": 500,
        "M": 1000,
    }

    for ch in text:
        if ch not in values:
            raise ValueError("invalid Roman numeral character")

    # Validate canonical uppercase form by converting to integer then back.
    total = 0
    i = 0
    n = len(text)
    while i < n:
        cur = values[text[i]]
        if i + 1 < n and values[text[i + 1]] > cur:
            total -= cur
        else:
            total += cur
        i += 1

    if total < 1 or total > 3999:
        raise ValueError("Roman numeral out of range")

    if to_roman(total) != text:
        raise ValueError("noncanonical Roman numeral")

    return total
