def parse_ini(text: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    current: str | None = None  # None means no section seen yet (implicit "" section)

    lines = text.split("\n")
    for idx, raw in enumerate(lines, start=1):
        if raw.endswith("\r"):
            raw = raw[:-1]
        line = raw.strip()

        # Blank lines and full-line comments
        if not line or line[0] in (";", "#"):
            continue

        # Section header
        if line.startswith("["):
            if not line.endswith("]"):
                raise ValueError(f"line {idx}: malformed section header {line!r}")
            name = line[1:-1].strip()
            if not name:
                raise ValueError(f"line {idx}: empty section name")
            if "[" in name or "]" in name:
                raise ValueError(f"line {idx}: malformed section header {line!r}")
            if name not in result:
                result[name] = {}
            current = name
            continue

        # Key/value line
        if "=" not in line:
            raise ValueError(f"line {idx}: expected 'key = value' or section header, got {line!r}")
        key, value = line.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if not key:
            raise ValueError(f"line {idx}: empty key")

        section_name = current if current is not None else ""
        if section_name not in result:
            # Only reachable for the implicit "" section
            result[section_name] = {}
        section = result[section_name]
        if key in section:
            raise ValueError(
                f"line {idx}: duplicate key {key!r} in section {section_name!r}"
            )
        section[key] = value

    # Drop the implicit "" section if it has no keys (it is never created
    # without a key, but be defensive).
    if "" in result and not result[""]:
        del result[""]

    return result
