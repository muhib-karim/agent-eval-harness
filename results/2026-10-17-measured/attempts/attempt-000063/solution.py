import re


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_INDEX = re.compile(r"\[([0-9]+)\]")


def get_path(data, path: str, default=None):
    if not isinstance(path, str):
        raise ValueError("path must be a string")
    if path == "" or path == "$":
        return data

    tokens = []
    has_root = path.startswith("$")
    pos = 1 if has_root else 0
    first = True

    # Parse the entire path before accessing data, so malformed syntax always
    # raises ValueError, even when an earlier lookup would fail.
    while pos < len(path):
        char = path[pos]

        if char == ".":
            if first and not has_root:
                raise ValueError("invalid path")
            pos += 1
            match = _IDENTIFIER.match(path, pos)
            if match is None:
                raise ValueError("invalid path")
            tokens.append(("key", match.group()))
        elif char == "[":
            match = _INDEX.match(path, pos)
            if match is None:
                raise ValueError("invalid path")
            tokens.append(("index", match.group(1)))
        else:
            if not first or has_root:
                raise ValueError("invalid path")
            match = _IDENTIFIER.match(path, pos)
            if match is None:
                raise ValueError("invalid path")
            tokens.append(("key", match.group()))

        pos = match.end()
        first = False

    if first:
        raise ValueError("invalid path")

    value = data
    for kind, component in tokens:
        if kind == "key":
            if not isinstance(value, dict) or component not in value:
                return default
            value = value[component]
        else:
            if not isinstance(value, list):
                return default

            # Compare before converting to int so arbitrarily long valid
            # indices remain valid syntax and simply count as out of range.
            digits = component.lstrip("0") or "0"
            largest = str(len(value) - 1)
            if len(digits) > len(largest) or (
                len(digits) == len(largest) and digits > largest
            ):
                return default
            value = value[int(digits)]

    return value
