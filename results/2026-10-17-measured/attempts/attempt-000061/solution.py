import re


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_INDEX = re.compile(r"\[([0-9]+)\]")


def get_path(data, path: str, default=None):
    if not isinstance(path, str):
        raise ValueError("path must be a string")
    if path == "" or path == "$":
        return data

    # Parse the entire path before accessing data, so malformed syntax always
    # raises ValueError, even if an earlier lookup would be missing.
    components = []
    pos = 1 if path.startswith("$") else 0

    while pos < len(path):
        char = path[pos]

        if char == ".":
            match = _IDENTIFIER.match(path, pos + 1)
            if match is None:
                raise ValueError("malformed path")
            components.append(("key", match.group()))
        elif char == "[":
            match = _INDEX.match(path, pos)
            if match is None:
                raise ValueError("malformed path")
            components.append(("index", match.group(1)))
        elif pos == 0:
            match = _IDENTIFIER.match(path, pos)
            if match is None:
                raise ValueError("malformed path")
            components.append(("key", match.group()))
        else:
            raise ValueError("malformed path")

        pos = match.end()

    if not components:
        raise ValueError("malformed path")

    current = data
    for kind, value in components:
        if kind == "key":
            if not isinstance(current, dict) or value not in current:
                return default
            current = current[value]
        else:
            if not isinstance(current, list) or not current:
                return default

            # Compare before converting, avoiding Python's limit on converting
            # exceptionally long digit strings to integers.
            digits = value.lstrip("0") or "0"
            largest = str(len(current) - 1)
            if len(digits) > len(largest) or (
                len(digits) == len(largest) and digits > largest
            ):
                return default
            current = current[int(digits)]

    return current
