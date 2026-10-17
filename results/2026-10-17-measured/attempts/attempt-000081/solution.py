def get_path(data, path: str, default=None):
    if not isinstance(path, str):
        raise ValueError("path must be a string")

    if path == '' or path == '$':
        return data

    # Parse the path into components, validating syntax
    components = []  # list of ('key', str) or ('index', int)
    i = 0
    n = len(path)

    # Optional leading '$'
    if i < n and path[i] == '$':
        i += 1
        if i == n:
            return data
        if path[i] != '.' and path[i] != '[':
            raise ValueError("Invalid path")

    # First component: identifier or bracket index
    def parse_identifier(start):
        j = start
        if j >= n or not (path[j].isalpha() and path[j].isascii() and (path[j] == '_' or path[j].isalpha())) and path[j] != '_':
            # need to check properly
            pass
        # Do it carefully
        if j >= n:
            return None
        c = path[j]
        if not (c == '_' or ('a' <= c <= 'z') or ('A' <= c <= 'Z')):
            return None
        j += 1
        while j < n:
            c = path[j]
            if c == '_' or ('a' <= c <= 'z') or ('A' <= c <= 'Z') or ('0' <= c <= '9'):
                j += 1
            else:
                break
        return j

    def parse_index_bracket(start):
        # start points at '['
        j = start + 1
        if j >= n or not path[j].isdigit():
            raise ValueError("Malformed index")
        while j < n and path[j].isdigit():
            j += 1
        if j >= n or path[j] != ']':
            raise ValueError("Malformed index")
        idx = int(path[start+1:j])
        return idx, j + 1  # position after ']'

    first = True
    while i < n:
        if first:
            if path[i] == '[':
                idx, ni = parse_index_bracket(i)
                components.append(('index', idx))
                i = ni
            else:
                ni = parse_identifier(i)
                if ni is None:
                    raise ValueError("Invalid path")
                components.append(('key', path[i:ni]))
                i = ni
            first = False
        else:
            if i >= n:
                break
            if path[i] == '.':
                i += 1
                if i >= n:
                    raise ValueError("Trailing dot")
                ni = parse_identifier(i)
                if ni is None:
                    raise ValueError("Invalid identifier after dot")
                components.append(('key', path[i:ni]))
                i = ni
            elif path[i] == '[':
                idx, ni = parse_index_bracket(i)
                components.append(('index', idx))
                i = ni
            else:
                raise ValueError("Invalid path syntax")

        # After a component, next must be '.' or '[' or end
        if i < n and path[i] not in '.[':
            raise ValueError("Invalid path syntax")

    # Now walk the data
    current = data
    for kind, val in components:
        if kind == 'key':
            if not isinstance(current, dict):
                return default
            if val not in current:
                return default
            current = current[val]
        else:
            if not isinstance(current, list):
                return default
            if val >= len(current):
                return default
            current = current[val]

    return current
