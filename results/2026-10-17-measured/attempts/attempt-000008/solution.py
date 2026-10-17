_ID_START = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_")
_ID_CHARS = _ID_START | set("0123456789")
_DIGITS = set("0123456789")


def _parse(path):
    if not isinstance(path, str):
        raise ValueError("path must be a string")
    tokens = []
    n = len(path)
    i = 0

    def parse_ident(i):
        if i >= n or path[i] not in _ID_START:
            raise ValueError("expected identifier at position %d" % i)
        j = i + 1
        while j < n and path[j] in _ID_CHARS:
            j += 1
        return ("key", path[i:j]), j

    def parse_index(i):
        # path[i] == '['
        j = i + 1
        k = j
        while k < n and path[k] in _DIGITS:
            k += 1
        if k == j:
            raise ValueError("expected digits in index at position %d" % j)
        if k >= n or path[k] != "]":
            raise ValueError("expected ']' at position %d" % k)
        return ("idx", int(path[j:k])), k + 1

    if n == 0:
        return tokens
    if path[0] == "$":
        i = 1
        if i == n:
            return tokens
        if path[i] not in ".[":
            raise ValueError("unexpected character after '$'")
    else:
        if path[0] == "[":
            tok, i = parse_index(0)
        else:
            tok, i = parse_ident(0)
        tokens.append(tok)

    while i < n:
        c = path[i]
        if c == ".":
            tok, i = parse_ident(i + 1)
        elif c == "[":
            tok, i = parse_index(i)
        else:
            raise ValueError("unexpected character %r at position %d" % (c, i))
        tokens.append(tok)
    return tokens


def get_path(data, path: str, default=None):
    tokens = _parse(path)
    cur = data
    for kind, val in tokens:
        if kind == "key":
            if not isinstance(cur, dict):
                return default
            try:
                if val not in cur:
                    return default
                cur = cur[val]
            except Exception:
                return default
        else:
            if not isinstance(cur, list):
                return default
            if val >= len(cur):
                return default
            cur = cur[val]
    return cur
