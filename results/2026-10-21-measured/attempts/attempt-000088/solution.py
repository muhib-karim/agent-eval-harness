"""Semantic Versioning 2.0.0 parser and comparator (standard library only)."""

import re

_IDENT_RE = re.compile(r"^[0-9A-Za-z-]+$")
_NUMERIC_RE = re.compile(r"^(0|[1-9][0-9]*)$")
_DIGITS_RE = re.compile(r"^[0-9]+$")


def _parse_core_number(s: str) -> int:
    """Parse a MAJOR/MINOR/PATCH field: non-negative integer, no leading zeroes."""
    if not _NUMERIC_RE.match(s):
        raise ValueError("invalid numeric version field: %r" % (s,))
    return int(s)


def _parse_prerelease(s: str) -> tuple:
    """Parse the prerelease portion (text after '-', before '+')."""
    parts = s.split(".")
    result = []
    for ident in parts:
        if not ident or not _IDENT_RE.match(ident):
            raise ValueError("invalid prerelease identifier: %r" % (ident,))
        if _DIGITS_RE.match(ident):
            # Numeric identifier: no leading zeroes allowed.
            if not _NUMERIC_RE.match(ident):
                raise ValueError(
                    "numeric prerelease identifier has leading zeroes: %r" % (ident,)
                )
            result.append(int(ident))
        else:
            result.append(ident)
    return tuple(result)


def _parse_build(s: str) -> tuple:
    """Parse the build metadata portion (text after '+')."""
    parts = s.split(".")
    result = []
    for ident in parts:
        if not ident or not _IDENT_RE.match(ident):
            raise ValueError("invalid build identifier: %r" % (ident,))
        result.append(ident)
    return tuple(result)


def parse(text: str) -> tuple:
    """Parse a SemVer 2.0.0 string.

    Returns (major, minor, patch, prerelease, build) where prerelease is a
    tuple of identifiers (int for numeric, str otherwise) and build is a
    tuple of str. Raises ValueError on any invalid input.
    """
    if not isinstance(text, str):
        raise ValueError("version must be a str, got %s" % type(text).__name__)
    if not text:
        raise ValueError("empty version string")

    # Split off build metadata at the first '+'.
    build_str = None
    rest = text
    plus = rest.find("+")
    if plus != -1:
        build_str = rest[plus + 1:]
        rest = rest[:plus]

    # Split off prerelease at the first '-'.
    pre_str = None
    dash = rest.find("-")
    if dash != -1:
        pre_str = rest[dash + 1:]
        rest = rest[:dash]

    core = rest.split(".")
    if len(core) != 3:
        raise ValueError("version core must be MAJOR.MINOR.PATCH: %r" % (text,))
    major = _parse_core_number(core[0])
    minor = _parse_core_number(core[1])
    patch = _parse_core_number(core[2])

    prerelease = _parse_prerelease(pre_str) if pre_str is not None else ()
    build = _parse_build(build_str) if build_str is not None else ()

    return (major, minor, patch, prerelease, build)


def _cmp(x, y) -> int:
    if x < y:
        return -1
    if x > y:
        return 1
    return 0


def _compare_prerelease(pa: tuple, pb: tuple) -> int:
    if not pa and not pb:
        return 0
    if not pa:
        return 1   # release > prerelease
    if not pb:
        return -1  # prerelease < release
    for ia, ib in zip(pa, pb):
        a_num = isinstance(ia, int)
        b_num = isinstance(ib, int)
        if a_num and b_num:
            c = _cmp(ia, ib)
        elif a_num:
            c = -1  # numeric < alphanumeric
        elif b_num:
            c = 1
        else:
            c = _cmp(ia, ib)  # ASCII (code point) order for str
        if c != 0:
            return c
    return _cmp(len(pa), len(pb))


def compare(a: str, b: str) -> int:
    """Compare two SemVer strings by precedence. Returns -1, 0 or 1."""
    va = parse(a)
    vb = parse(b)
    c = _cmp(va[:3], vb[:3])
    if c != 0:
        return c
    return _compare_prerelease(va[3], vb[3])
