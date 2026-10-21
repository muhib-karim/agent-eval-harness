def parse_ini(text: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    current = ""
    for lineno, raw in enumerate(text.split("\n"), start=1):
        if raw.endswith("\r"):
            raw = raw[:-1]
        line = raw.strip()
        if not line or line[0] in ";#":
            continue
        if line[0] == "[":
            close = line.find("]")
            if close != len(line) - 1:
                raise ValueError(f"line {lineno}: malformed section header")
            name = line[1:-1].strip()
            if not name or "[" in name:
                raise ValueError(f"line {lineno}: invalid section name")
            current = name
            result.setdefault(current, {})
            continue
        if "=" not in line:
            raise ValueError(f"line {lineno}: expected key = value")
        key, value = line.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if not key:
            raise ValueError(f"line {lineno}: empty key")
        section = result.setdefault(current, {})
        if key in section:
            raise ValueError(f"line {lineno}: duplicate key {key!r}")
        section[key] = value
    return result
