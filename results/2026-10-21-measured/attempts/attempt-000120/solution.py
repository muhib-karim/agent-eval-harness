import re

_IDENT = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
_INDEX = re.compile(r'\[([0-9]+)\]')


def _parse(path):
    n = len(path)
    tokens = []  # ('k', name) or ('i', digits)
    pos = 0

    def parse_ident(p):
        m = _IDENT.match(path, p)
        if not m:
            raise ValueError("Malformed path: expected identifier at position %d" % p)
        tokens.append(('k', m.group(0)))
        return m.end()

    def parse_bracket(p):
        m = _INDEX.match(path, p)
        if not m:
            raise ValueError("Malformed path: bad index at position %d" % p)
        tokens.append(('i', m.group(1)))
        return m.end()

    if path.startswith('$'):
        pos = 1
        if pos == n:
            return tokens
        c = path[pos]
        if c == '.':
            pos = parse_ident(pos + 1)
        elif c == '[':
            pos = parse_bracket(pos)
        else:
            raise ValueError("Malformed path at position %d" % pos)
    else:
        if path[0] == '[':
            pos = parse_bracket(0)
        else:
            pos = parse_ident(0)

    while pos < n:
        c = path[pos]
        if c == '.':
            pos = parse_ident(pos + 1)
        elif c == '[':
            pos = parse_bracket(pos)
        else:
            raise ValueError("Malformed path at position %d" % pos)
    return tokens


def get_path(data, path: str, default=None):
    if not isinstance(path, str):
        raise ValueError("path must be a string")
    if path == "" or path == "$":
        return data
    tokens = _parse(path)  # validate fully before traversing
    cur = data
    for kind, val in tokens:
        if kind == 'k':
            if isinstance(cur, dict) and val in cur:
                cur = cur[val]
            else:
                return default
        else:
            if not isinstance(cur, list):
                return default
            s = val.lstrip('0') or '0'
            if len(s) > 18:
                return default
            idx = int(s)
            if idx >= len(cur):
                return default
            cur = cur[idx]
    return cur
