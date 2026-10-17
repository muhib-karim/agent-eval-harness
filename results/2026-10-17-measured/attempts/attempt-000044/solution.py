def get_path(data, path: str, default=None):
    """
    Navigate through nested data structures using dot notation and bracket indices.

    Args:
        data: The data structure to navigate
        path: A string path like "users[0].name" or "$.users[01].name"
        default: Value to return for missing keys/indices or type mismatches

    Returns:
        The value at the path, None if present, or default if missing/invalid

    Raises:
        ValueError: If path syntax is malformed
    """

    # Empty path or '$' returns data
    if not path or path == '$':
        return data

    # Remove leading '$' if present
    if path.startswith('$'):
        path = path[1:]
        if path and path[0] not in '.[]':
            raise ValueError("Invalid path: identifier must follow '$' with a dot")

    # Check for whitespace
    if any(c.isspace() for c in path):
        raise ValueError("Path contains whitespace")

    current = data
    i = 0

    while i < len(path):
        if path[i] == '.':
            i += 1

            # Check for repeated dots or trailing dot
            if i >= len(path):
                raise ValueError("Path ends with a dot")
            if path[i] == '.':
                raise ValueError("Repeated dots in path")
            if path[i] == '[':
                raise ValueError("Bracket immediately after dot")

            # Parse identifier
            identifier_start = i
            while i < len(path) and (path[i].isalnum() or path[i] == '_'):
                i += 1

            if i == identifier_start:
                raise ValueError("Expected identifier after dot")

            identifier = path[identifier_start:i]

            # Validate identifier format
            if not (path[identifier_start].isalpha() or path[identifier_start] == '_'):
                raise ValueError(f"Invalid identifier: {identifier}")

            # Apply identifier (dict key)
            if not isinstance(current, dict):
                return default

            if identifier not in current:
                return default

            current = current[identifier]

        elif path[i] == '[':
            i += 1

            # Parse index
            index_start = i
            while i < len(path) and path[i].isdigit():
                i += 1

            if i == index_start:
                raise ValueError("Expected digits inside brackets")
            if i >= len(path) or path[i] != ']':
                raise ValueError("Missing closing bracket")

            index_str = path[index_start:i]
            index = int(index_str)  # Handles leading zeros correctly

            i += 1  # Skip closing bracket

            # Check what comes after bracket
            if i < len(path):
                if path[i] == '[':
                    # Bracket after bracket is OK, will be handled in next iteration
                    pass
                elif path[i] == '.':
                    # Dot after bracket is OK, will be handled in next iteration
                    pass
                else:
                    # Identifier immediately after bracket without dot
                    raise ValueError("Identifier must follow bracket with a dot")

            # Apply index (list index)
            if not isinstance(current, list):
                return default

            if index < 0 or index >= len(current):
                return default

            current = current[index]

        else:
            raise ValueError(f"Unexpected character: {path[i]}")

    return current
