import re


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def get_path(data, path: str, default=None):
    if not isinstance(path, str):
        raise ValueError("path must be a string")
    if path == "" or path == "$":
        return data

    parts = []
    pos = 0
    has_root = path.startswith("$")
    if has_root:
        pos = 1

    while pos < len(path):
        char = path[pos]

        if char == ".":
            if not parts and not has_root:
                raise ValueError("path cannot start with a dot")
            pos += 1
            match = _IDENTIFIER.match(path, pos)
            if match is None:
                raise ValueError("expected an identifier after a dot")
            parts.append(("key", match.group()))
            pos = match.end()

        elif char == "[":
            end = path.find("]", pos + 1)
            if end == -1:
                raise ValueError("unclosed index")
            digits = path[pos + 1:end]
            if not digits or not all("0" <= c <= "9" for c in digits):
                raise ValueError("invalid index")
            parts.append(("index", digits))
            pos = end + 1

        elif not parts and not has_root:
            match = _IDENTIFIER.match(path, pos)
            if match is None:
                raise ValueError("invalid path")
            parts.append(("key", match.group()))
            pos = match.end()

        else:
            raise ValueError("invalid path syntax")

    for kind, value in parts:
        if kind == "key":
            if not isinstance(data, dict) or value not in data:
                return default
            data = data[value]
        else:
            if not isinstance(data, list) or not data:
                return default

            # Check the bound before converting, so arbitrarily long valid
            # indices do not exceed Python's integer-conversion limit.
            normalized = value.lstrip("0") or "0"
            maximum = str(len(data) - 1)
            if len(normalized) > len(maximum) or (
                len(normalized) == len(maximum) and normalized > maximum
            ):
                return default
            data = data[int(normalized)]

    return data
