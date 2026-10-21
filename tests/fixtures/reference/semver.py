import re

_NUM = r"0|[1-9][0-9]*"
_IDENT = r"[0-9A-Za-z-]+"
_PATTERN = re.compile(
    rf"({_NUM})\.({_NUM})\.({_NUM})"
    rf"(?:-({_IDENT}(?:\.{_IDENT})*))?"
    rf"(?:\+({_IDENT}(?:\.{_IDENT})*))?"
)


def parse(text):
    if not isinstance(text, str):
        raise ValueError("version must be a string")
    match = _PATTERN.fullmatch(text)
    if not match:
        raise ValueError(f"invalid version: {text!r}")
    major, minor, patch, pre, build = match.groups()
    prerelease = []
    for ident in pre.split(".") if pre else []:
        if ident.isdigit():
            if len(ident) > 1 and ident[0] == "0":
                raise ValueError("numeric prerelease identifier has a leading zero")
            prerelease.append(int(ident))
        else:
            prerelease.append(ident)
    return (
        int(major),
        int(minor),
        int(patch),
        tuple(prerelease),
        tuple(build.split(".")) if build else (),
    )


def _ident_key(ident):
    return (0, ident, "") if isinstance(ident, int) else (1, 0, ident)


def _key(text):
    major, minor, patch, pre, _ = parse(text)
    release = 1 if not pre else 0
    return (major, minor, patch, release, [_ident_key(i) for i in pre])


def compare(a, b):
    ka, kb = _key(a), _key(b)
    return (ka > kb) - (ka < kb)
