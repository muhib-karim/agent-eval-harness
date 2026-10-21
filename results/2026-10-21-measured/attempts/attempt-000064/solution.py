def parse_ini(text: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    default: dict[str, str] = {}
    current: dict[str, str] | None = None  # None means the "" section
    current_name: str | None = None

    lines = text.split("\n")
    for idx, raw in enumerate(lines, start=1):
        if raw.endswith("\r"):
            raw = raw[:-1]
        line = raw.strip()
        if not line or line[0] in ";#":
            continue
        if line.startswith("["):
            if not line.endswith("]"):
                raise ValueError(f"line {idx}: malformed section header")
            name = line[1:-1].strip()
            if not name:
                raise ValueError(f"line {idx}: empty section name")
            if "[" in name or "]" in name:
                raise ValueError(f"line {idx}: malformed section header")
            if name not in result:
                result[name] = {}
            current = result[name]
            current_name = name
            continue
        if "=" not in line:
            raise ValueError(f"line {idx}: expected section header or key=value")
        key, value = line.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if not key:
            raise ValueError(f"line {idx}: empty key")
        target = current if current is not None else default
        if key in target:
            raise ValueError(f"line {idx}: duplicate key {key!r}")
        target[key] = value

    if default:
        out: dict[str, dict[str, str]] = {"": default}
        out.update(result)
        return out
    return result
