import re

def get_path(data, path: str, default=None):
    if path == '' or path == '$':
        return data

    # Reject whitespace anywhere
    if re.search(r'\s', path):
        raise ValueError("Malformed path")

    # Pattern for valid path components
    # Starts optionally with $., then segments
    original_path = path
    if path.startswith('$'):
        path = path[1:]
        if path.startswith('.'):
            path = path[1:]
        elif path and not path.startswith('['):
            raise ValueError("Malformed path")

    if not path:
        return data

    # Reject trailing dot
    if path.endswith('.'):
        raise ValueError("Malformed path")

    # Split into segments, handling dots and brackets
    segments = []
    i = 0
    n = len(path)
    expect_dot = False

    while i < n:
        if expect_dot:
            if path[i] != '.':
                raise ValueError("Malformed path")
            i += 1
            if i >= n or path[i] in '.[':
                raise ValueError("Malformed path")  # repeated or trailing dot handled
            expect_dot = False

        if path[i] == '[':
            # parse index
            j = i + 1
            if j >= n or not path[j].isdigit():
                raise ValueError("Malformed path")
            while j < n and path[j].isdigit():
                j += 1
            if j >= n or path[j] != ']':
                raise ValueError("Malformed path")
            index_str = path[i+1:j]
            # negative check (already ensured digits only)
            segments.append(('index', int(index_str)))
            i = j + 1
            expect_dot = True
        elif re.match(r'[A-Za-z_]', path[i]):
            # parse identifier
            j = i + 1
            while j < n and re.match(r'[A-Za-z0-9_]', path[j]):
                j += 1
            ident = path[i:j]
            segments.append(('key', ident))
            i = j
            expect_dot = True
        else:
            raise ValueError("Malformed path")

        # After bracket, must have dot or end before next key
        if i < n and path[i] not in '.[' and not expect_dot:
            pass  # handled by loop

    # Now traverse
    current = data
    for typ, val in segments:
        if typ == 'key':
            if isinstance(current, dict):
                if val in current:
                    current = current[val]
                else:
                    return default
            else:
                return default
        elif typ == 'index':
            if isinstance(current, list):
                if 0 <= val < len(current):
                    current = current[val]
                else:
                    return default
            else:
                return default
    return current
