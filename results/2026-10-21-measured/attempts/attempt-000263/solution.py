def get_path(data, path: str, default=None):
    if path == "" or path == "$":
        return data

    def is_start(char):
        return "A" <= char <= "Z" or "a" <= char <= "z" or char == "_"

    def is_continue(char):
        return is_start(char) or "0" <= char <= "9"

    tokens = []
    length = len(path)
    pos = 0

    if path[0] == "$":
        pos = 1
        if path[pos] == ".":
            pos += 1
            if pos == length or not is_start(path[pos]):
                raise ValueError("Invalid path")
        elif path[pos] != "[":
            raise ValueError("Invalid path")

    # Parse the entire path before accessing data, so malformed syntax always
    # raises ValueError, even when an earlier lookup would fail.
    while pos < length:
        if path[pos] == "[":
            pos += 1
            start = pos
            while pos < length and "0" <= path[pos] <= "9":
                pos += 1
            if pos == start or pos == length or path[pos] != "]":
                raise ValueError("Invalid path")
            digits = path[start:pos].lstrip("0") or "0"
            tokens.append((True, digits))
            pos += 1
        else:
            if not is_start(path[pos]):
                raise ValueError("Invalid path")
            start = pos
            pos += 1
            while pos < length and is_continue(path[pos]):
                pos += 1
            tokens.append((False, path[start:pos]))

        if pos == length:
            break
        if path[pos] == ".":
            pos += 1
            if pos == length or not is_start(path[pos]):
                raise ValueError("Invalid path")
        elif path[pos] != "[":
            raise ValueError("Invalid path")

    current = data
    for is_index, value in tokens:
        if is_index:
            if not isinstance(current, list):
                return default
            # Compare lengths before converting to avoid Python's limit on
            # converting arbitrarily long digit strings to integers.
            if len(value) > len(str(len(current))):
                return default
            index = int(value)
            if index >= len(current):
                return default
            current = current[index]
        else:
            if not isinstance(current, dict) or value not in current:
                return default
            current = current[value]

    return current
