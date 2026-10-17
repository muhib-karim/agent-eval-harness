import re

_ROMAN_VALUES = [
    (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
    (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
    (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'),
    (1, 'I')
]

_ROMAN_REGEX = re.compile(
    r'^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$'
)

def to_roman(value: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Input must be an integer")
    if not (1 <= value <= 3999):
        raise ValueError("Value out of range")
    result = []
    for arabic, roman in _ROMAN_VALUES:
        count = value // arabic
        result.append(roman * count)
        value -= arabic * count
    return ''.join(result)

def from_roman(text: str) -> int:
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    if not text or not _ROMAN_REGEX.match(text):
        raise ValueError("Invalid Roman numeral")
    total = 0
    i = 0
    for arabic, roman in _ROMAN_VALUES:
        while text.startswith(roman, i):
            total += arabic
            i += len(roman)
    if i != len(text):
        raise ValueError("Invalid Roman numeral")
    return total
