"""
solution.py

Implements get_path(data, path, default=None) which extracts a value from
nested dict/list structures using a small path language:

    - ''  or '$'                 -> returns data itself
    - dot-separated identifiers: [A-Za-z_][A-Za-z0-9_]*
    - zero-based bracket indices: [digits]  (digits may have leading zeros)
    - an optional leading '$' may be used to explicitly anchor the path,
      e.g. "$.users[0].name" or "$[0]"
    - without a leading '$', the path may start directly with an identifier
      (e.g. "users[0].name") or with a bracketed index (e.g. "[0][1].x")

Rules:
    - Keys only apply to dict values; indices only apply to list values.
    - Missing keys, out-of-range indices, or type mismatches return `default`.
    - A present value of None is returned as None (not treated as missing).
    - Malformed syntax always raises ValueError, regardless of whether an
      earlier component would already be missing in `data`.
    - No whitespace, negative indices, quoted keys, or wildcards are allowed.
    - Repeated or trailing dots are invalid.
    - An identifier may not appear immediately after a ']' without an
      intervening '.'.
    - `data` is never mutated.
"""

import re

_IDENT_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
_DIGITS_RE = re.compile(r'[0-9]+')

_SENTINEL = object()


def get_path(data, path: str, default=None):
    if path == '' or path == '$':
        return data

    tokens = []  # list of ('key', name) or ('index', int)
    n = len(path)
    pos = 0

    has_dollar = path.startswith('$')
    if has_dollar:
        pos = 1

    while pos < n:
        c = path[pos]

        if c == '.':
            pos += 1
            if pos >= n:
                raise ValueError(f"Malformed path: trailing '.' in {path!r}")
            m = _IDENT_RE.match(path, pos)
            if not m:
                raise ValueError(
                    f"Malformed path: expected identifier after '.' at position {pos} in {path!r}"
                )
            name = m.group(0)
            tokens.append(('key', name))
            pos = m.end()

        elif c == '[':
            pos += 1
            m = _DIGITS_RE.match(path, pos)
            if not m:
                raise ValueError(
                    f"Malformed path: expected digits after '[' at position {pos} in {path!r}"
                )
            digits = m.group(0)
            pos = m.end()
            if pos >= n or path[pos] != ']':
                raise ValueError(
                    f"Malformed path: expected ']' at position {pos} in {path!r}"
                )
            pos += 1
            idx = int(digits)
            tokens.append(('index', idx))

        elif c.isalpha() or c == '_':
            # A bare identifier (no leading '.') is only permitted as the
            # very first token, and only when the path did not start with
            # an explicit '$'.
            if len(tokens) == 0 and not has_dollar:
                m = _IDENT_RE.match(path, pos)
                if not m:
                    raise ValueError(
                        f"Malformed path: invalid identifier at position {pos} in {path!r}"
                    )
                name = m.group(0)
                tokens.append(('key', name))
                pos = m.end()
            else:
                raise ValueError(
                    f"Malformed path: unexpected identifier at position {pos} in {path!r} "
                    f"(missing '.' before identifier)"
                )

        else:
            raise ValueError(
                f"Malformed path: unexpected character {c!r} at position {pos} in {path!r}"
            )

    if not tokens:
        # Something like "$" handled earlier; this covers degenerate cases
        # such as a lone '$' already returned above. If we got here with
        # has_dollar True and no tokens, it's just "$", but that's already
        # handled by the early return. Defensive fallback:
        return data

    current = data
    for ttype, val in tokens:
        if ttype == 'key':
            if isinstance(current, dict) and val in current:
                current = current[val]
            else:
                return default
        else:  # 'index'
            if isinstance(current, list) and 0 <= val < len(current):
                current = current[val]
            else:
                return default

    return current
