def parse_ini(text):
    result = {}
    section = ""
    for number, raw in enumerate(text.split("\n"), 1):
        line = raw[:-1] if raw.endswith("\r") else raw
        line = line.strip()
        if not line or line[0] in ";#":
            continue
        if line.startswith("["):
            if not line.endswith("]") or "]" in line[1:-1]:
                raise ValueError(f"line {number}: malformed section header")
            section = line[1:-1].strip()
            if not section:
                raise ValueError(f"line {number}: empty section name")
            result.setdefault(section, {})
            continue
        if "=" not in line:
            raise ValueError(f"line {number}: expected key = value")
        key, value = line.split("=", 1)
        key = key.strip().lower()
        if not key:
            raise ValueError(f"line {number}: empty key")
        values = result.setdefault(section, {})
        if key in values:
            raise ValueError(f"line {number}: duplicate key {key!r}")
        values[key] = value.strip()
    return result
