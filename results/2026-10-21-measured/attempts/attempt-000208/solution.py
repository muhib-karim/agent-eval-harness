def parse_ini(text: str) -> dict[str, dict[str, str]]:
    lines = text.split("\n")
    result = {}
    current_section = ""
    section_keys = {}  # Track keys in each section to detect duplicates

    for line_num, line in enumerate(lines, 1):
        # Remove trailing \r
        if line.endswith("\r"):
            line = line[:-1]

        # Strip surrounding whitespace
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith(";") or line.startswith("#"):
            continue

        # Check for section header
        if line.startswith("["):
            if not line.endswith("]"):
                raise ValueError(f"line {line_num}")

            section_name = line[1:-1].strip()

            if not section_name:
                raise ValueError(f"line {line_num}")

            # Check for extra characters after ]
            if line.count("[") != 1 or line.count("]") != 1:
                raise ValueError(f"line {line_num}")

            # Check if there's anything after the closing ]
            closing_bracket_pos = line.rfind("]")
            if closing_bracket_pos != len(line) - 1:
                raise ValueError(f"line {line_num}")

            current_section = section_name

            # Initialize section if not already present
            if current_section not in result:
                result[current_section] = {}
                section_keys[current_section] = set()

            continue

        # Must be a key=value line
        if "=" not in line:
            raise ValueError(f"line {line_num}")

        # Split on first "="
        eq_pos = line.index("=")
        key = line[:eq_pos].strip()
        value = line[eq_pos + 1:].strip()

        if not key:
            raise ValueError(f"line {line_num}")

        # Lowercase the key for case-insensitivity
        key_lower = key.lower()

        # Initialize current section if it doesn't exist
        if current_section not in result:
            result[current_section] = {}
            section_keys[current_section] = set()

        # Check for duplicate key in current section
        if key_lower in section_keys[current_section]:
            raise ValueError(f"line {line_num}")

        # Add the key-value pair
        result[current_section][key_lower] = value
        section_keys[current_section].add(key_lower)

    # Remove empty "" section if it has no keys
    if "" in result and not result[""]:
        del result[""]

    return result
