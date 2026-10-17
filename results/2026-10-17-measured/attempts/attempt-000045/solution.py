import re

def get_path(data, path: str, default=None):
    """
    Navigate through nested data structures using dot and bracket notation.

    Args:
        data: The data structure to navigate
        path: Path string like "users[0].name" or "$.users[01].name"
        default: Value to return for missing keys/indices or type mismatches

    Returns:
        The value at the path, default if not found, or None if explicitly None

    Raises:
        ValueError: If path syntax is malformed
    """

    # Normalize path
    if path == '' or path == '$':
        return data

    # Remove leading $ if present
    if path.startswith('$'):
        path = path[1:]
        if path == '':
            return data
        if not path.startswith('.') and not path.startswith('['):
            raise ValueError("Invalid path syntax")

    # Check for invalid whitespace
    if any(c.isspace() for c in path):
        raise ValueError("Whitespace not allowed in path")

    # Tokenize the path
    tokens = []
    i = 0

    while i < len(path):
        if path[i] == '.':
            # Dot must be followed by identifier
            i += 1
            if i >= len(path):
                raise ValueError("Trailing dot")
            if not (path[i].isalpha() or path[i] == '_'):
                raise ValueError("Invalid identifier after dot")

            # Extract identifier
            start = i
            while i < len(path) and (path[i].isalnum() or path[i] == '_'):
                i += 1
            identifier = path[start:i]
            tokens.append(('key', identifier))

        elif path[i] == '[':
            # Extract bracket index
            i += 1
            if i >= len(path) or not path[i].isdigit():
                raise ValueError("Invalid bracket index")

            start = i
            while i < len(path) and path[i].isdigit():
                i += 1

            if i >= len(path) or path[i] != ']':
                raise ValueError("Unclosed bracket")

            index_str = path[start:i]
            # Check for negative (starts with -)
            if index_str.startswith('-'):
                raise ValueError("Negative index not allowed")

            index = int(index_str)
            i += 1  # Skip closing bracket

            tokens.append(('index', index))

            # After bracket, must have dot or another bracket or end
            if i < len(path):
                if path[i] == '.':
                    pass  # OK, will be handled next iteration
                elif path[i] == '[':
                    pass  # OK, will be handled next iteration
                else:
                    raise ValueError("Invalid character after bracket")

        else:
            # Must start with identifier (no leading dot for first component)
            if not (path[i].isalpha() or path[i] == '_'):
                raise ValueError("Invalid path syntax")

            start = i
            while i < len(path) and (path[i].isalnum() or path[i] == '_'):
                i += 1
            identifier = path[start:i]
            tokens.append(('key', identifier))

    # Validate token sequence: no consecutive dots, no trailing dots
    current = data

    for token_type, token_value in tokens:
        if token_type == 'key':
            if not isinstance(current, dict):
                return default
            if token_value not in current:
                return default
            current = current[token_value]

        elif token_type == 'index':
            if not isinstance(current, list):
                return default
            if token_value < 0 or token_value >= len(current):
                return default
            current = current[token_value]

    return current
