import re

_NUM = re.compile(r"0|[1-9][0-9]*")
_DIGITS = re.compile(r"[0-9]+")
_IDENT = re.compile(r"[0-9A-Za-z-]+")


def parse(text):
    if not isinstance(text, str):
        raise ValueError("version must be a str")
    s = text
    build = ()
    if "+" in s:
        s, build_part = s.split("+", 1)
        ids = build_part.split(".")
        for i in ids:
            if not _IDENT.fullmatch(i):
                raise ValueError("invalid build identifier: %r" % i)
        build = tuple(ids)
    prerelease = ()
    if "-" in s:
        s, pre_part = s.split("-", 1)
        ids = pre_part.split(".")
        out = []
        for i in ids:
            if not _IDENT.fullmatch(i):
                raise ValueError("invalid prerelease identifier: %r" % i)
            if _DIGITS.fullmatch(i):
                if not _NUM.fullmatch(i):
                    raise ValueError("numeric prerelease identifier has leading zero: %r" % i)
                out.append(int(i))
            else:
                out.append(i)
        prerelease = tuple(out)
    parts = s.split(".")
    if len(parts) != 3:
        raise ValueError("version core must be MAJOR.MINOR.PATCH")
    nums = []
    for p in parts:
        if not _NUM.fullmatch(p):
            raise ValueError("invalid numeric field: %r" % p)
        nums.append(int(p))
    return (nums[0], nums[1], nums[2], prerelease, build)


def _cmp(x, y):
    return (x > y) - (x < y)


def compare(a, b):
    pa = parse(a)
    pb = parse(b)
    for x, y in zip(pa[:3], pb[:3]):
        c = _cmp(x, y)
        if c:
            return c
    ra, rb = pa[3], pb[3]
    if not ra and not rb:
        return 0
    if not ra:
        return 1
    if not rb:
        return -1
    for x, y in zip(ra, rb):
        xi = isinstance(x, int)
        yi = isinstance(y, int)
        if xi and yi:
            c = _cmp(x, y)
        elif xi:
            c = -1
        elif yi:
            c = 1
        else:
            c = _cmp(x, y)
        if c:
            return c
    return _cmp(len(ra), len(rb))
