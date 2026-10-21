import re

_SEMVER_RE = re.compile(r'''
    ^
    (?P<major>0|[1-9]\d*)
    \.
    (?P<minor>0|[1-9]\d*)
    \.
    (?P<patch>0|[1-9]\d*)
    (?:-(?P<prerelease>
        (?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)
        (?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*
    ))?
    (?:\+(?P<build>
        [0-9a-zA-Z-]+
        (?:\.[0-9a-zA-Z-]+)*
    ))?
    $
''', re.VERBOSE)

_NUMERIC_ID_RE = re.compile(r'^(0|[1-9]\d*)$')


def parse(text: str) -> tuple:
    if not isinstance(text, str):
        raise ValueError("Version must be a string")

    m = _SEMVER_RE.match(text)
    if m is None:
        raise ValueError(f"Invalid semantic version: {text!r}")

    major = int(m.group('major'))
    minor = int(m.group('minor'))
    patch = int(m.group('patch'))

    prerelease_str = m.group('prerelease')
    if prerelease_str:
        prerelease_ids = []
        for ident in prerelease_str.split('.'):
            if _NUMERIC_ID_RE.match(ident):
                prerelease_ids.append(int(ident))
            else:
                prerelease_ids.append(ident)
        prerelease = tuple(prerelease_ids)
    else:
        prerelease = ()

    build_str = m.group('build')
    if build_str:
        build = tuple(build_str.split('.'))
    else:
        build = ()

    return (major, minor, patch, prerelease, build)


def _compare_prerelease(pre_a: tuple, pre_b: tuple) -> int:
    if pre_a == () and pre_b == ():
        return 0
    if pre_a == ():
        # a has no prerelease -> a is higher
        return 1
    if pre_b == ():
        return -1

    for ia, ib in zip(pre_a, pre_b):
        if ia == ib:
            continue
        a_is_num = isinstance(ia, int)
        b_is_num = isinstance(ib, int)
        if a_is_num and b_is_num:
            return -1 if ia < ib else 1
        elif a_is_num and not b_is_num:
            return -1
        elif not a_is_num and b_is_num:
            return 1
        else:
            return -1 if ia < ib else 1

    if len(pre_a) != len(pre_b):
        return -1 if len(pre_a) < len(pre_b) else 1

    return 0


def compare(a: str, b: str) -> int:
    pa = parse(a)
    pb = parse(b)

    for i in range(3):
        if pa[i] != pb[i]:
            return -1 if pa[i] < pb[i] else 1

    return _compare_prerelease(pa[3], pb[3])
