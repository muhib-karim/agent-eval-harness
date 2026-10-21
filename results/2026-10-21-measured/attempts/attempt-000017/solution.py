def parse_ini(text: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    current = ""
    default: dict[str, str] = {}

    def get_section(name: str) -> dict[str, str]:
        if name == "":
            return default
        return result[name]

    for lineno, raw in enumerate(text.split("\n"), start=1):
        if raw.endswith("\r"):
            raw = raw[:-1]
        line = raw.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        if line.startswith("["):
            if not line.endswith("]") or len(line) < 2:
                raise ValueError(f"line {lineno}: malformed section header")
            name = line[1:-1].strip()
            if not name:
                raise ValueError(f"line {lineno}: empty section name")
            if name not in result:
                result[name] = {}
            current = name
            continue
        if "=" not in line:
            raise ValueError(f"line {lineno}: invalid line")
        key, value = line.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if not key:
            raise ValueError(f"line {lineno}: empty key")
        section = get_section(current)
        if key in section:
            raise ValueError(f"line {lineno}: duplicate key {key!r}")
        section[key] = value

    if default:
        final: dict[str, dict[str, str]] = {"": default}
        final.update(result)
        return final
    return result
