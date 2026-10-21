import re

_NUM = r"(0|[1-9][0-9]*)"
_CORE_RE = re.compile(r"\A" + _NUM + r"\." + _NUM + r"\." + _NUM + r"\Z")
_IDENT_RE = re.compile(r"\A[0-9A-Za-z-]+\Z")
_DIGITS_RE = re.compile(r"\A[0-9]+\Z")


def parse(text: str) -> tuple:
    if not isinstance(text, str):
        raise ValueError("version must be a string")

    rest = text
    build = ()
    if "+" in rest:
        rest, build_str = rest.split("+", 1)
        parts = build_str.split(".")
        for p in parts:
            if not _IDENT_RE.match(p):
                raise ValueError("invalid build metadata: %r" % text)
        build = tuple(parts)

    prerelease = ()
    if "-" in rest:
        rest, pre_str = rest.split("-", 1)
        ids = []
        for p in pre_str.split("."):
            if not _IDENT_RE.match(p):
                raise ValueError("invalid prerelease: %r" % text)
            if _DIGITS_RE.match(p):
                if len(p) > 1 and p[0] == "0":
                    raise ValueError("leading zero in prerelease: %r" % text)
                ids.append(int(p))
            else:
                ids.append(p)
        prerelease = tuple(ids)

    m = _CORE_RE.match(rest)
    if not m:
        raise ValueError("invalid version core: %r" % text)
    major, minor, patch = (int(g) for g in m.groups())
    return (major, minor, patch, prerelease, build)


def _cmp_ident(x, y) -> int:
    xi = isinstance(x, int)
    yi = isinstance(y, int)
    if xi and yi:
        return (x > y) - (x < y)
    if xi:
        return -1
    if yi:
        return 1
    return (x > y) - (x < y)


def compare(a: str, b: str) -> int:
    pa = parse(a)
    pb = parse(b)
    for i in range(3):
        if pa[i] != pb[i]:
            return -1 if pa[i] < pb[i] else 1
    ra, rb = pa[3], pb[3]
    if not ra and not rb:
        return 0
    if not ra:
        return 1
    if not rb:
        return -1
    for x, y in zip(ra, rb):
        c = _cmp_ident(x, y)
        if c:
            return c
    return (len(ra) > len(rb)) - (len(ra) < len(rb))
