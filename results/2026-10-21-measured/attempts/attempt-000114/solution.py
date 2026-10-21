def parse_ini(text: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    current = ""  # current section name; "" section created lazily
    for lineno, raw in enumerate(text.split("\n"), start=1):
        if raw.endswith("\r"):
            raw = raw[:-1]
        line = raw.strip()
        if not line or line[0] in ";#":
            continue
        if line[0] == "[":
            if not line.endswith("]") or len(line) < 2:
                raise ValueError(f"line {lineno}: malformed section header")
            name = line[1:-1].strip()
            if not name:
                raise ValueError(f"line {lineno}: empty section name")
            if "[" in name or "]" in name:
                raise ValueError(f"line {lineno}: malformed section header")
            current = name
            if current not in result:
                result[current] = {}
            continue
        if "=" not in line:
            raise ValueError(f"line {lineno}: invalid line")
        key, value = line.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if not key:
            raise ValueError(f"line {lineno}: empty key")
        if current not in result:
            result[current] = {}
        section = result[current]
        if key in section:
            raise ValueError(f"line {lineno}: duplicate key {key!r}")
        section[key] = value
    return result
