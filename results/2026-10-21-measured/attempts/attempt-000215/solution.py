import re

def get_path(data, path: str, default=None):
    """
    Navigate through nested data structures using dot notation and bracket indices.

    Supports:
    - Empty path or '$' returns data
    - Dot-separated identifiers (A-Za-z_][A-Za-z0-9_]*)
    - Zero-based bracket indices [digits] for lists

    Examples: users[0].name, $.users[01].name, [0][1].x, $[0]

    Returns default for missing keys, out-of-range indices, or type mismatches.
    Raises ValueError for malformed syntax.
    """

    # Handle empty path or '$'
    if path == '' or path == '$':
        return data

    # Remove leading '$.' or '$' if present
    if path.startswith('$'):
        path = path[1:]
        if path.startswith('.'):
            path = path[1:]

    # Check for any whitespace
    if any(c.isspace() for c in path):
        raise ValueError("Whitespace not allowed in path")

    # Tokenize the path
    tokens = []
    i = 0
    while i < len(path):
        if path[i] == '.':
            # Dot separator
            if i == 0 or i == len(path) - 1:
                raise ValueError("Leading or trailing dot")
            if path[i + 1] == '.':
                raise ValueError("Repeated dots")
            if path[i + 1] == '[':
                raise ValueError("Dot cannot be immediately followed by bracket")
            i += 1
        elif path[i] == '[':
            # Bracket index
            j = i + 1
            if j >= len(path):
                raise ValueError("Unclosed bracket")
            # Find closing bracket
            while j < len(path) and path[j] != ']':
                j += 1
            if j >= len(path):
                raise ValueError("Unclosed bracket")

            # Extract index content
            index_str = path[i + 1:j]

            # Validate index is all digits
            if not index_str or not index_str.isdigit():
                raise ValueError("Invalid bracket index")

            # Check for negative indices (leading '-' would fail isdigit())
            # But we already validated isdigit(), so this is safe

            tokens.append(('index', int(index_str)))
            i = j + 1

            # After bracket, must have dot, another bracket, or end
            if i < len(path) and path[i] not in '.[]':
                raise ValueError("Invalid character after bracket")
            if i < len(path) and path[i] == '[':
                # Multiple brackets in a row is okay
                continue
            if i < len(path) and path[i] == '.':
                # Dot after bracket is okay
                i += 1
                if i >= len(path):
                    raise ValueError("Trailing dot")
        elif path[i].isalpha() or path[i] == '_':
            # Identifier
            j = i
            while j < len(path) and (path[j].isalnum() or path[j] == '_'):
                j += 1

            identifier = path[i:j]
            tokens.append(('key', identifier))
            i = j

            # After identifier, must have dot, bracket, or end
            if i < len(path) and path[i] not in '.[':
                raise ValueError("Invalid character after identifier")
            if i < len(path) and path[i] == '.':
                i += 1
                if i >= len(path):
                    raise ValueError("Trailing dot")
        else:
            raise ValueError(f"Invalid character: {path[i]}")

    # Navigate through data using tokens
    current = data
    for token_type, token_value in tokens:
        if token_type == 'key':
            # Must be a dict
            if not isinstance(current, dict):
                return default
            if token_value not in current:
                return default
            current = current[token_value]
        else:  # token_type == 'index'
            # Must be a list
            if not isinstance(current, list):
                return default
            if token_value < 0 or token_value >= len(current):
                return default
            current = current[token_value]

    return current
