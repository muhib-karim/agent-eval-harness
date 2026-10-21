def to_roman(value: int) -> str:
    """Convert an integer (1-3999) to uppercase canonical Roman numeral."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Input must be an integer, not bool or other type")
    if value < 1 or value > 3999:
        raise ValueError("Input must be in range 1-3999")

    # Mapping of values to Roman numerals in descending order
    # Includes subtractive forms
    val_to_roman = [
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

    result = []
    for val, numeral in val_to_roman:
        count = value // val
        if count:
            result.append(numeral * count)
            value -= val * count

    return ''.join(result)


def from_roman(text: str) -> int:
    """Convert an uppercase canonical Roman numeral to an integer (1-3999)."""
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    if not text:
        raise ValueError("Input cannot be empty")
    if not text.isupper():
        raise ValueError("Roman numeral must be uppercase")
    if text != text.strip():
        raise ValueError("Roman numeral cannot contain whitespace")

    # Define valid Roman numeral characters
    valid_chars = set('IVXLCDM')
    if not all(c in valid_chars for c in text):
        raise ValueError("Invalid characters in Roman numeral")

    # Mapping of Roman numerals to their values
    roman_to_val = {
        'I': 1,
        'V': 5,
        'X': 10,
        'L': 50,
        'C': 100,
        'D': 500,
        'M': 1000,
    }

    # Canonical subtractive forms: only these are allowed
    canonical_subtractive = {
        'IV': 4,
        'IX': 9,
        'XL': 40,
        'XC': 90,
        'CD': 400,
        'CM': 900,
    }

    # Process the Roman numeral
    result = 0
    i = 0
    prev_value = float('inf')

    while i < len(text):
        # Check for two-character subtractive form
        if i + 1 < len(text):
            two_char = text[i:i+2]
            if two_char in canonical_subtractive:
                value = canonical_subtractive[two_char]
                # Check order: subtractive form value must be less than previous value
                if value >= prev_value:
                    raise ValueError("Invalid Roman numeral order")
                result += value
                prev_value = value
                i += 2
                continue

        # Single character
        char = text[i]
        value = roman_to_val[char]

        # Check for invalid repetitions
        # I, X, C, M can repeat up to 3 times consecutively
        # V, L, D cannot repeat
        if char in 'VLD':
            if i > 0 and text[i-1] == char:
                raise ValueError("Invalid repetition in Roman numeral")
        elif char in 'IXCM':
            repetition_count = 1
            j = i - 1
            while j >= 0 and text[j] == char:
                repetition_count += 1
                j -= 1
            if repetition_count > 3:
                raise ValueError("Invalid repetition in Roman numeral")

        # Check order: value must be <= previous value (unless in subtractive form)
        if value > prev_value:
            raise ValueError("Invalid Roman numeral order")

        result += value
        prev_value = value
        i += 1

    # Verify the result is in valid range
    if result < 1 or result > 3999:
        raise ValueError("Roman numeral value out of range 1-3999")

    # Verify it's canonical by converting back and comparing
    if to_roman(result) != text:
        raise ValueError("Roman numeral is not in canonical form")

    return result
