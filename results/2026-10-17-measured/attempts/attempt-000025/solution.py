import re

_IDENT_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*', re.ASCII)
_INDEX_RE = re.compile(r'[0-9]+', re.ASCII)


def get_path(data, path: str, default=None):
    """
    Navigate `data` using a restricted JSONPath-like `path` string.

    Supports:
      - '' or '$' -> returns data itself
      - dot-separated ASCII identifiers: .name
      - bracket indices into lists: [0], [01], etc. (leading zeros allowed)
      - a leading identifier without a dot, only as the very first segment
        when the path does not start with '$' (e.g. "users[0].name")
      - '$' may be followed directly by '.' or '[' or be the whole path

    Missing dict keys, out-of-range/invalid list indices, or type mismatches
    (key into non-dict, index into non-list) cause `default` to be returned,
    but syntax is still fully validated and malformed paths raise ValueError
    even if an earlier component would already be "missing".

    Never mutates `data`.
    """
    if not isinstance(path, str):
        raise ValueError("path must be a string")

    n = len(path)
    if n == 0:
        return data

    pos = 0
    has_dollar = False
    if path[0] == '$':
        has_dollar = True
        pos = 1

    if pos == n:
        return data

    current = data
    missing = False
    # A bare identifier (without a preceding dot) is only allowed as the
    # very first segment, and only if the path did not start with '$'.
    leading = not has_dollar

    while pos < n:
        c = path[pos]

        if c == '.':
            pos += 1
            m = _IDENT_RE.match(path, pos)
            if not m:
                raise ValueError(f"Malformed path at position {pos}: expected identifier")
            key = m.group(0)
            pos = m.end()

            if not missing:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    missing = True

            leading = False

        elif c == '[':
            pos += 1
            m = _INDEX_RE.match(path, pos)
            if not m:
                raise ValueError(f"Malformed path at position {pos}: expected digits")
            idx_str = m.group(0)
            pos = m.end()

            if pos >= n or path[pos] != ']':
                raise ValueError(f"Malformed path at position {pos}: expected ']'")
            pos += 1

            idx = int(idx_str)

            if not missing:
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    missing = True

            leading = False

        elif leading:
            m = _IDENT_RE.match(path, pos)
            if not m:
                raise ValueError(f"Malformed path at position {pos}: expected identifier")
            key = m.group(0)
            pos = m.end()

            if not missing:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    missing = True

            leading = False

        else:
            # e.g. identifier right after a ']' without a dot, whitespace,
            # quotes, wildcards, stray characters, etc.
            raise ValueError(f"Malformed path at position {pos}: unexpected character {c!r}")

    if missing:
        return default
    return current
