"""Semantic Versioning 2.0.0 parsing and comparison (standard library only)."""

import re

_NUMERIC_RE = re.compile(r"^(0|[1-9][0-9]*)$")
_IDENT_RE = re.compile(r"^[0-9A-Za-z-]+$")
_DIGITS_RE = re.compile(r"^[0-9]+$")


def _parse_core(core):
    parts = core.split(".")
    if len(parts) != 3:
        raise ValueError("version core must be MAJOR.MINOR.PATCH")
    nums = []
    for p in parts:
        if not _NUMERIC_RE.match(p):
            raise ValueError("invalid numeric version component: %r" % (p,))
        nums.append(int(p))
    return nums[0], nums[1], nums[2]


def _parse_prerelease(s):
    idents = []
    for ident in s.split("."):
        if not ident or not _IDENT_RE.match(ident):
            raise ValueError("invalid prerelease identifier: %r" % (ident,))
        if _DIGITS_RE.match(ident):
            if not _NUMERIC_RE.match(ident):
                raise ValueError(
                    "numeric prerelease identifier has leading zeroes: %r" % (ident,)
                )
            idents.append(int(ident))
        else:
            idents.append(ident)
    return tuple(idents)


def _parse_build(s):
    idents = []
    for ident in s.split("."):
        if not ident or not _IDENT_RE.match(ident):
            raise ValueError("invalid build identifier: %r" % (ident,))
        idents.append(ident)
    return tuple(idents)


def parse(text):
    """Parse a SemVer 2.0.0 string into (major, minor, patch, prerelease, build)."""
    if not isinstance(text, str):
        raise ValueError("version must be a str")
    if not text:
        raise ValueError("empty version string")

    # Build metadata comes after the first '+'. Build identifiers may contain '-'.
    build = ()
    rest = text
    if "+" in rest:
        rest, build_str = rest.split("+", 1)
        build = _parse_build(build_str)

    # Prerelease comes after the first '-' in the remaining part. The version
    # core consists only of digits and dots, so the first '-' begins prerelease.
    prerelease = ()
    core = rest
    if "-" in rest:
        core, pre_str = rest.split("-", 1)
        prerelease = _parse_prerelease(pre_str)

    major, minor, patch = _parse_core(core)
    return (major, minor, patch, prerelease, build)


def _cmp(x, y):
    if x < y:
        return -1
    if x > y:
        return 1
    return 0


def _compare_prerelease(pa, pb):
    if not pa and not pb:
        return 0
    if not pa:
        return 1
    if not pb:
        return -1
    for ia, ib in zip(pa, pb):
        a_num = isinstance(ia, int)
        b_num = isinstance(ib, int)
        if a_num and b_num:
            c = _cmp(ia, ib)
        elif a_num:
            c = -1
        elif b_num:
            c = 1
        else:
            c = _cmp(ia, ib)
        if c != 0:
            return c
    return _cmp(len(pa), len(pb))


def compare(a, b):
    """Compare two SemVer strings by precedence; returns -1, 0 or 1."""
    ma, mi_a, pa_, pre_a, _ = parse(a)
    mb, mi_b, pb_, pre_b, _ = parse(b)
    c = _cmp((ma, mi_a, pa_), (mb, mi_b, pb_))
    if c != 0:
        return c
    return _compare_prerelease(pre_a, pre_b)
