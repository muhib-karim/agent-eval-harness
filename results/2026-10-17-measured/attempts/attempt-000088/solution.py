def to_roman(value: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("value must be an int")
    if value < 1 or value > 3999:
        raise ValueError("value must be in range 1..3999")

    val = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")
    ]

    result = []
    for num, sym in val:
        while value >= num:
            result.append(sym)
            value -= num
    return "".join(result)


def from_roman(text: str) -> int:
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if not text:
        raise ValueError("text must not be empty")

    valid_chars = set("IVXLCDM")
    for ch in text:
        if ch not in valid_chars:
            raise ValueError("invalid character")

    values = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50,
        'C': 100, 'D': 500, 'M': 1000
    }

    total = 0
    i = 0
    n = len(text)
    while i < n:
        if i + 1 < n and values[text[i]] < values[text[i + 1]]:
            total += values[text[i + 1]] - values[text[i]]
            i += 2
        else:
            total += values[text[i]]
            i += 1

    if total < 1 or total > 3999:
        raise ValueError("value out of range")

    if to_roman(total) != text:
        raise ValueError("noncanonical roman numeral")

    return total
