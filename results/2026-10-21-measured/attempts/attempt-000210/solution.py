def parse_ini(text: str) -> dict[str, dict[str, str]]:
    lines = text.split("\n")
    result = {}
    current_section = ""
    seen_sections = set()
    section_keys = {}  # Track keys per section to detect duplicates

    for line_num, line in enumerate(lines, 1):
        # Remove trailing \r if present
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
            if line != f"[{section_name}]" and line != f"[ {section_name} ]":
                # More careful check: the original line should be exactly [name] with optional whitespace
                if line.lstrip("[").rstrip("]").strip() != section_name:
                    raise ValueError(f"line {line_num}")

            current_section = section_name

            # Add section if not seen before
            if current_section not in seen_sections:
                result[current_section] = {}
                section_keys[current_section] = set()
                seen_sections.add(current_section)

            continue

        # Must be a key=value line
        if "=" not in line:
            raise ValueError(f"line {line_num}")

        # Split on first "="
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            raise ValueError(f"line {line_num}")

        # Normalize key to lowercase
        key_lower = key.lower()

        # Initialize current section if not seen
        if current_section not in seen_sections:
            result[current_section] = {}
            section_keys[current_section] = set()
            seen_sections.add(current_section)

        # Check for duplicate key in same section
        if key_lower in section_keys[current_section]:
            raise ValueError(f"line {line_num}")

        # Add key-value pair
        result[current_section][key_lower] = value
        section_keys[current_section].add(key_lower)

    # Remove empty string section if it has no keys
    if "" in result and not result[""]:
        del result[""]

    return result
