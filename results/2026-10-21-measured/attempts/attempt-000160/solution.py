def parse_ini(text: str) -> dict[str, dict[str, str]]:
    lines = text.split("\n")
    sections: dict[str, dict[str, str]] = {}
    current = ""

    for i, raw in enumerate(lines, start=1):
        line = raw[:-1] if raw.endswith("\r") else raw
        line = line.strip()

        if line == "" or line.startswith(";") or line.startswith("#"):
            continue

        if line.startswith("["):
            if len(line) < 2 or not line.endswith("]"):
                raise ValueError(f"Malformed section header at line {i}")
            name = line[1:-1].strip()
            if not name:
                raise ValueError(f"Empty section name at line {i}")
            current = name
            if current not in sections:
                sections[current] = {}
            continue

        if "=" in line:
            idx = line.index("=")
            key = line[:idx].strip()
            value = line[idx + 1:].strip()

            if not key:
                raise ValueError(f"Empty key at line {i}")

            key = key.lower()

            if current not in sections:
                sections[current] = {}

            if key in sections[current]:
                raise ValueError(f"Duplicate key '{key}' at line {i}")

            sections[current][key] = value
            continue

        raise ValueError(f"Invalid line at line {i}")

    if "" in sections and not sections[""]:
        del sections[""]

    return sections
