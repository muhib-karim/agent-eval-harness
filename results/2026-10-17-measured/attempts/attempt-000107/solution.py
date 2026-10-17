ROMAN_NUMERALS = [
    (1000, 'M'),
    (900, 'CM'),
    (500, 'D'),
    (400, 'CD'),
    (100, 'C'),
    (90, 'XC'),
    (50, 'L'),
    (40, 'XL'),
    (10, 'X'),
    (9, 'IX'),
    (5, 'V'),
    (4, 'IV'),
    (1, 'I'),
]

def to_roman(value: int) -> str:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError
    if not 1 <= value <= 3999:
        raise ValueError
    result = ''
    for num, roman in ROMAN_NUMERALS:
        while value >= num:
            result += roman
            value -= num
    return result

ROMAN_TO_INT = {to_roman(i): i for i in range(1, 4000)}

def from_roman(text: str) -> int:
    if not isinstance(text, str):
        raise ValueError
    if text not in ROMAN_TO_INT:
        raise ValueError
    return ROMAN_TO_INT[text]
