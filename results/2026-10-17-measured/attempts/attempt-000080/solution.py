def get_path(data, path: str, default=None):
    if path == "" or path == "$":
        return data

    # Validate and tokenize the path
    tokens = []
    i = 0
    n = len(path)

    # Handle leading $
    if i < n and path[i] == '$':
        i += 1
        if i < n and path[i] not in '.[':
            raise ValueError("Invalid path after $")

    expect_component = True  # whether we expect an identifier or bracket
    after_bracket = False

    while i < n:
        c = path[i]
        if c == '.':
            if expect_component:
                raise ValueError("Repeated or leading dot")
            if after_bracket:
                # after bracket, dot is allowed to separate next component
                pass
            i += 1
            expect_component = True
            after_bracket = False
            if i >= n:
                raise ValueError("Trailing dot")
        elif c == '[':
            # bracket index
            if after_bracket:
                # consecutive brackets allowed: [0][1]
                pass
            elif not expect_component and tokens:
                # e.g. after identifier without dot -> not allowed? 
                # "identifier immediately after a bracket without a dot" is disallowed,
                # but bracket after identifier without dot is also disallowed per spec?
                # Spec: "an identifier immediately after a bracket without a dot" is rejected.
                # It doesn't explicitly say bracket after identifier without dot is rejected,
                # but examples: users[0].name -> bracket follows identifier directly.
                # So bracket after identifier is allowed. Bracket after bracket allowed.
                pass
            i += 1
            start = i
            while i < n and path[i].isdigit():
                i += 1
            if start == i:
                raise ValueError("Empty or invalid index")
            if i >= n or path[i] != ']':
                raise ValueError("Unclosed bracket")
            tokens.append(('index', int(path[start:i])))
            i += 1
            expect_component = False
            after_bracket = True
        elif c.isalpha() or c == '_':
            if after_bracket:
                # identifier immediately after bracket without dot
                raise ValueError("Identifier after bracket without dot")
            if not expect_component:
                # identifier without dot separator
                raise ValueError("Missing dot before identifier")
            start = i
            if not (c.isalpha() or c == '_'):
                raise ValueError("Invalid identifier start")
            i += 1
            while i < n and (path[i].isalnum() or path[i] == '_'):
                i += 1
            tokens.append(('key', path[start:i]))
            expect_component = False
            after_bracket = False
        else:
            raise ValueError(f"Invalid character: {c}")

    if expect_component:
        raise ValueError("Path ends unexpectedly")

    # Traverse
    current = data
    for kind, val in tokens:
        if kind == 'key':
            if not isinstance(current, dict):
                return default
            if val not in current:
                return default
            current = current[val]
        else:  # index
            if not isinstance(current, list):
                return default
            if val >= len(current):
                return default
            current = current[val]

    return current
