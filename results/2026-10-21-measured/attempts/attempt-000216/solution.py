def get_path(data, path: str, default=None):
    """
    Navigate through nested data structures using dot and bracket notation.

    Args:
        data: The data structure to navigate
        path: Path string (e.g., "users[0].name", "$.users[01].name")
        default: Value to return on missing keys/indices or type mismatches

    Returns:
        The value at the path, or default if not found/invalid

    Raises:
        ValueError: If path syntax is malformed
    """

    # Handle empty path or '$'
    if not path or path == '$':
        return data

    # Remove leading '$' if present
    if path.startswith('$'):
        path = path[1:]

    # Empty after removing '$'
    if not path:
        return data

    # Check for whitespace
    if any(c.isspace() for c in path):
        raise ValueError("Whitespace not allowed in path")

    current = data
    i = 0

    while i < len(path):
        if path[i] == '.':
            i += 1

            # Check for repeated dots or trailing dot
            if i >= len(path):
                raise ValueError("Trailing dot in path")

            if path[i] == '.':
                raise ValueError("Repeated dots in path")

            if path[i] == '[':
                raise ValueError("Bracket immediately after dot")

            # Parse identifier
            if not (path[i].isalpha() or path[i] == '_'):
                raise ValueError(f"Invalid identifier start at position {i}")

            start = i
            while i < len(path) and (path[i].isalnum() or path[i] == '_'):
                i += 1

            key = path[start:i]

            # Apply key to dict
            if not isinstance(current, dict):
                return default

            if key not in current:
                return default

            current = current[key]

        elif path[i] == '[':
            i += 1

            # Parse bracket index
            if i >= len(path):
                raise ValueError("Unclosed bracket in path")

            if path[i] == ']':
                raise ValueError("Empty brackets in path")

            if not path[i].isdigit():
                raise ValueError(f"Invalid bracket content at position {i}")

            start = i
            while i < len(path) and path[i].isdigit():
                i += 1

            if i >= len(path) or path[i] != ']':
                raise ValueError("Unclosed bracket in path")

            index_str = path[start:i]
            index = int(index_str)

            i += 1  # Skip ']'

            # Check what comes after bracket
            if i < len(path) and path[i] != '.' and path[i] != '[':
                raise ValueError(f"Invalid character after bracket at position {i}")

            # Apply index to list
            if not isinstance(current, list):
                return default

            if index < 0 or index >= len(current):
                return default

            current = current[index]

        elif path[i].isalpha() or path[i] == '_':
            # Identifier at start or after another identifier (no dot)
            if i > 0 and not (path[i-1] == ']'):
                raise ValueError(f"Identifier not preceded by dot at position {i}")

            start = i
            while i < len(path) and (path[i].isalnum() or path[i] == '_'):
                i += 1

            key = path[start:i]

            # Apply key to dict
            if not isinstance(current, dict):
                return default

            if key not in current:
                return default

            current = current[key]

        else:
            raise ValueError(f"Invalid character at position {i}: {path[i]}")

    return current
