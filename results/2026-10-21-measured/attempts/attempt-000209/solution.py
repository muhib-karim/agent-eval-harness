def parse_ini(text: str) -> dict[str, dict[str, str]]:
    """
    Parse INI file format with specific rules.

    Returns a dictionary where keys are section names and values are
    dictionaries of key-value pairs.
    """
    lines = text.split("\n")
    result = {}
    current_section = ""
    section_keys = {}  # Track keys per section to detect duplicates
    seen_sections = {}  # Track order of section first appearance

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

            # Section name must be non-empty
            if not section_name:
                raise ValueError(f"line {line_num}")

            current_section = section_name

            # Track first appearance of section
            if current_section not in seen_sections:
                seen_sections[current_section] = line_num
                result[current_section] = {}
                section_keys[current_section] = set()

            continue

        # Must be a key=value line
        if "=" not in line:
            raise ValueError(f"line {line_num}")

        # Split on first "="
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Key must be non-empty
        if not key:
            raise ValueError(f"line {line_num}")

        # Lowercase the key for case-insensitive comparison
        key_lower = key.lower()

        # Check for duplicate key in current section
        if key_lower in section_keys.get(current_section, set()):
            raise ValueError(f"line {line_num}")

        # Initialize section tracking if needed
        if current_section not in section_keys:
            section_keys[current_section] = set()
        if current_section not in result:
            result[current_section] = {}

        # Add the key-value pair
        section_keys[current_section].add(key_lower)
        result[current_section][key_lower] = value

    # Remove empty string section if it has no keys
    if "" in result and not result[""]:
        del result[""]

    # Reorder result to maintain first-seen order
    ordered_result = {}
    for section in sorted(seen_sections.keys(), key=lambda s: seen_sections[s]):
        if section in result:
            ordered_result[section] = result[section]

    # Add empty section at the end if it exists and has keys
    if "" in result and result[""]:
        ordered_result[""] = result[""]

    return ordered_result
