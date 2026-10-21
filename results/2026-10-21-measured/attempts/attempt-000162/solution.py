def parse_ini(text: str) -> dict:
    """
    Parse a restricted INI dialect into a dict of dicts.

    Rules:
      - Lines are split on "\n"; a trailing "\r" is stripped from each line.
      - After stripping surrounding whitespace:
          * empty lines and lines starting with ";" or "#" are ignored,
          * "[name]" starts/continues a section (name must be non-empty),
          * otherwise the line must be "key = value" (split at first "="),
            with a non-empty key.
      - Keys are case-insensitive and stored lowercased.
      - Section names are case-sensitive.
      - Key/value pairs before any section go into the "" section, which is
        only present in the result if it ends up with at least one key.
      - Every declared section appears in the result, even if empty.
      - Order of first appearance is preserved for both sections and keys.

    Raises ValueError (message contains the 1-based line number) for:
      - a line that is neither blank, comment, section header, nor key/value,
      - an empty key,
      - an empty or malformed section header,
      - a duplicate key within the same section (including across repeated
        headers for that section).
    """
    sections: dict[str, dict[str, str]] = {}
    current = ""

    lines = text.split("\n")
    for i, raw_line in enumerate(lines, start=1):
        # strip a trailing "\r" (from "\r\n" line endings)
        line = raw_line[:-1] if raw_line.endswith("\r") else raw_line
        stripped = line.strip()

        if stripped == "" or stripped.startswith(";") or stripped.startswith("#"):
            continue

        if stripped.startswith("["):
            if not stripped.endswith("]"):
                raise ValueError(f"malformed section header on line {i}")
            name = stripped[1:-1].strip()
            if name == "":
                raise ValueError(f"empty section name on line {i}")
            if name not in sections:
                sections[name] = {}
            current = name
            continue

        if "=" not in stripped:
            raise ValueError(
                f"invalid line {i}: expected blank, comment, section, or key=value"
            )

        key, value = stripped.split("=", 1)
        key = key.strip().lower()
        value = value.strip()

        if key == "":
            raise ValueError(f"empty key on line {i}")

        if current not in sections:
            sections[current] = {}

        if key in sections[current]:
            raise ValueError(f"duplicate key '{key}' on line {i}")

        sections[current][key] = value

    return sections
