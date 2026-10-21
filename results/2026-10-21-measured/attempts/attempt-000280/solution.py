import re


_NUMBER = r"(?:0|[1-9][0-9]*)"
_IDENTIFIERS = r"[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*"
_VERSION = re.compile(
    rf"({_NUMBER})\.({_NUMBER})\.({_NUMBER})"
    rf"(?:-({_IDENTIFIERS}))?"
    rf"(?:\+({_IDENTIFIERS}))?"
)


def _decimal_int(digits: str) -> int:
    """Convert without relying on Python's limit for long decimal strings."""
    result = 0
    for start in range(0, len(digits), 1000):
        chunk = digits[start:start + 1000]
        result = result * (10 ** len(chunk)) + int(chunk)
    return result


def parse(text: str) -> tuple:
    if not isinstance(text, str):
        raise ValueError("version must be a string")

    match = _VERSION.fullmatch(text)
    if match is None:
        raise ValueError("invalid semantic version")

    major, minor, patch, prerelease_text, build_text = match.groups()
    prerelease = []

    if prerelease_text is not None:
        for identifier in prerelease_text.split("."):
            if identifier.isdigit():
                if len(identifier) > 1 and identifier[0] == "0":
                    raise ValueError("numeric prerelease identifier has a leading zero")
                prerelease.append(_decimal_int(identifier))
            else:
                prerelease.append(identifier)

    build = tuple(build_text.split(".")) if build_text is not None else ()
    return (
        _decimal_int(major),
        _decimal_int(minor),
        _decimal_int(patch),
        tuple(prerelease),
        build,
    )


def compare(a: str, b: str) -> int:
    left = parse(a)
    right = parse(b)

    if left[:3] != right[:3]:
        return -1 if left[:3] < right[:3] else 1

    left_pre, right_pre = left[3], right[3]
    if not left_pre or not right_pre:
        if left_pre == right_pre:
            return 0
        return -1 if left_pre else 1

    for x, y in zip(left_pre, right_pre):
        x_numeric = isinstance(x, int)
        y_numeric = isinstance(y, int)
        if x_numeric != y_numeric:
            return -1 if x_numeric else 1
        if x != y:
            return -1 if x < y else 1

    if len(left_pre) == len(right_pre):
        return 0
    return -1 if len(left_pre) < len(right_pre) else 1
