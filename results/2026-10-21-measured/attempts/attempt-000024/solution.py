"""Safe nested lookup using a small path syntax.

Supported syntax:
  ""  or "$"          -> returns data itself
  users[0].name       -> dot-separated identifiers and bracket indices
  $.users[01].name    -> optional leading "$" (must be followed by '.' or '[')
  [0][1].x , $[0]
"""

_IDENT_START = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_")
_IDENT_CHARS = _IDENT_START | frozenset("0123456789")
_DIGITS = frozenset("0123456789")


def _parse_ident(path, i):
    """Parse an identifier starting at i; return (name, new_index)."""
    n = len(path)
    if i >= n or path[i] not in _IDENT_START:
        raise ValueError("malformed path: expected identifier at position %d" % i)
    j = i + 1
    while j < n and path[j] in _IDENT_CHARS:
        j += 1
    return path[i:j], j


def _parse(path):
    """Parse the whole path into a list of ('key', str) / ('index', int)."""
    if not isinstance(path, str):
        raise ValueError("path must be a string")
    n = len(path)
    tokens = []
    i = 0
    allow_bare_ident = True
    if n and path[0] == "$":
        i = 1
        allow_bare_ident = False
        if i < n and path[i] not in ".[":
            raise ValueError("malformed path: '$' must be followed by '.' or '['")
    while i < n:
        c = path[i]
        if c == ".":
            name, i = _parse_ident(path, i + 1)
            tokens.append(("key", name))
        elif c == "[":
            j = i + 1
            while j < n and path[j] in _DIGITS:
                j += 1
            if j == i + 1 or j >= n or path[j] != "]":
                raise ValueError("malformed path: bad index at position %d" % i)
            tokens.append(("index", int(path[i + 1:j])))
            i = j + 1
        elif allow_bare_ident and i == 0 and c in _IDENT_START:
            name, i = _parse_ident(path, i)
            tokens.append(("key", name))
        else:
            raise ValueError("malformed path: unexpected %r at position %d" % (c, i))
    return tokens


def get_path(data, path, default=None):
    tokens = _parse(path)  # validate full syntax before any traversal
    current = data
    for kind, value in tokens:
        if kind == "key":
            if not isinstance(current, dict):
                return default
            try:
                current = current[value]
            except (KeyError, TypeError):
                return default
        else:
            if not isinstance(current, list):
                return default
            if value >= len(current):
                return default
            current = current[value]
    return current
