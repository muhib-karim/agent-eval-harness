def parse_ini(text: str) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current_section = ""

    for line_number, line in enumerate(text.split("\n"), start=1):
        if line.endswith("\r"):
            line = line[:-1]
        line = line.strip()

        if not line or line.startswith((";", "#")):
            continue

        if line.startswith("["):
            if not line.endswith("]"):
                raise ValueError(f"Malformed section header on line {line_number}")

            name = line[1:-1].strip()
            if not name:
                raise ValueError(f"Empty section name on line {line_number}")

            current_section = name
            sections.setdefault(name, {})
            continue

        if "=" not in line:
            raise ValueError(f"Invalid line {line_number}")

        key, value = line.split("=", 1)
        key = key.strip().lower()
        value = value.strip()

        if not key:
            raise ValueError(f"Empty key on line {line_number}")

        section = sections.setdefault(current_section, {})
        if key in section:
            raise ValueError(f"Duplicate key on line {line_number}")

        section[key] = value

    return sections
