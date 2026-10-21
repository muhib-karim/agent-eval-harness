"""
solution.py

Implements get_path(data, path, default=None): a small, strict path lookup
helper for nested dict/list structures.

Grammar (informal):
    path      := '' | '$' | ['$'] first rest*
    first     := identifier | index            (when no leading '$')
    first     := '.' identifier | index        (when leading '$' is present)
    rest      := '.' identifier | index
    identifier:= [A-Za-z_][A-Za-z0-9_]*
    index     := '[' [0-9]+ ']'

Anything else (whitespace, negative indices, quoted keys, wildcards,
repeated/trailing dots, identifier directly after a bracket, etc.) is a
syntax error and raises ValueError. Syntax is validated fully before any
traversal, so malformed paths always raise regardless of the data.
"""

import re

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_INDEX_RE = re.compile(r"\[([0-9]+)\]")


def _parse(path):
    """Parse a path string into a list of ('key', str) / ('idx', int) components.

    Raises ValueError on malformed syntax.
    """
    if not isinstance(path, str):
        raise ValueError("path must be a string")

    if path == "" or path == "$":
        return []

    n = len(path)
    i = 0
    comps = []

    if path[0] == "$":
        i = 1
        # After '$' the next thing must be '.identifier' or '[index]'.
        if i >= n or path[i] not in ".[":
            raise ValueError("malformed path: %r" % (path,))
    else:
        if path[0] == ".":
            raise ValueError("malformed path: leading dot in %r" % (path,))

    first = True
    while i < n:
        c = path[i]
        if c == ".":
            i += 1
            m = _IDENT_RE.match(path, i)
            if m is None:
                raise ValueError("malformed path: expected identifier at %d in %r"
                                 % (i, path))
            comps.append(("key", m.group(0)))
            i = m.end()
        elif c == "[":
            m = _INDEX_RE.match(path, i)
            if m is None:
                raise ValueError("malformed path: bad index at %d in %r"
                                 % (i, path))
            comps.append(("idx", int(m.group(1))))
            i = m.end()
        else:
            if not first:
                # Identifier (or garbage) not introduced by a dot after
                # a previous component -> error.
                raise ValueError("malformed path: unexpected %r at %d in %r"
                                 % (c, i, path))
            m = _IDENT_RE.match(path, i)
            if m is None:
                raise ValueError("malformed path: unexpected %r at %d in %r"
                                 % (c, i, path))
            comps.append(("key", m.group(0)))
            i = m.end()
        first = False

    return comps


def get_path(data, path, default=None):
    """Look up a value inside nested dicts/lists using a dotted/bracketed path.

    - '' or '$' returns data unchanged.
    - Dot-separated identifiers index into dicts; [n] indexes into lists.
    - Missing keys, out-of-range indices, or type mismatches return `default`
      (the very same object that was passed in).
    - A present value of None is returned as None.
    - Malformed syntax raises ValueError (checked before any traversal).
    - `data` is never mutated.
    """
    comps = _parse(path)

    cur = data
    for kind, val in comps:
        if kind == "key":
            if not isinstance(cur, dict):
                return default
            if val not in cur:
                return default
            cur = cur[val]
        else:  # 'idx'
            if not isinstance(cur, list):
                return default
            if val >= len(cur):
                return default
            cur = cur[val]
    return cur


if __name__ == "__main__":
    sample = {
        "users": [
            {"name": "ann", "tags": [["a", "b"], ["c"]]},
            {"name": None},
        ],
        "x": [[{"x": 5}]],
    }
    assert get_path(sample, "") is sample
    assert get_path(sample, "$") is sample
    assert get_path(sample, "users[0].name") == "ann"
    assert get_path(sample, "$.users[01].name") is None
    assert get_path(sample, "x[0][0].x") == 5
    assert get_path(sample["x"], "[0][0].x") == 5
    assert get_path(sample["users"], "$[0]") is sample["users"][0]
    sentinel = object()
    assert get_path(sample, "users[5].name", sentinel) is sentinel
    assert get_path(sample, "users.name", sentinel) is sentinel
    assert get_path(sample, "nope", sentinel) is sentinel
    for bad in ["users[-1]", "users[ 0]", "users..name", "users.", ".users",
                "users[0]name", "users['a']", "users.*", "$users", "$.",
                "users [0]", "users[]", "users[0", "1abc", "a.1"]:
        try:
            get_path(sample, bad)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for %r" % bad)
    print("ok")
