import re

def get_path(data, path: str, default=None):
    if not path or path == '$':
        return data
    if not isinstance(path, str):
        return default

    # Reject whitespace
    if re.search(r'\s', path):
        raise ValueError("Malformed path")

    pos = 0
    n = len(path)
    current = data

    # Optional leading $
    if pos < n and path[pos] == '$':
        pos += 1

    while pos < n:
        if path[pos] == '.':
            # No repeated or trailing dots
            if pos + 1 >= n or path[pos + 1] == '.':
                raise ValueError("Malformed path")
            pos += 1
            # Parse identifier
            match = re.match(r'[A-Za-z_][A-Za-z0-9_]*', path[pos:])
            if not match:
                raise ValueError("Malformed path")
            key = match.group(0)
            pos += len(key)
            if isinstance(current, dict):
                if key in current:
                    current = current[key]
                else:
                    return default
            else:
                return default
        elif path[pos] == '[':
            pos += 1
            # Parse nonnegative index (leading zeros allowed)
            match = re.match(r'0|[1-9][0-9]*', path[pos:])
            if not match:
                raise ValueError("Malformed path")
            idx_str = match.group(0)
            pos += len(idx_str)
            if pos >= n or path[pos] != ']':
                raise ValueError("Malformed path")
            pos += 1
            try:
                idx = int(idx_str)
            except ValueError:
                return default
            if isinstance(current, list):
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return default
            else:
                return default
        else:
            raise ValueError("Malformed path")

    return current
