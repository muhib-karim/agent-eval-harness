import re

def parse(text: str) -> tuple:
    """
    Parse a semantic version string according to SemVer 2.0.0.

    Returns: (major, minor, patch, prerelease, build)
    - major, minor, patch: int
    - prerelease: tuple of identifiers (int for numeric, str for alphanumeric)
    - build: tuple of str identifiers
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")

    # SemVer 2.0.0 pattern
    # MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
    pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([a-zA-Z0-9\-]+(?:\.[a-zA-Z0-9\-]+)*))?(?:\+([a-zA-Z0-9\-]+(?:\.[a-zA-Z0-9\-]+)*))?$'

    match = re.match(pattern, text)
    if not match:
        raise ValueError(f"Invalid semantic version: {text}")

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))
    prerelease_str = match.group(4)
    build_str = match.group(5)

    # Parse prerelease identifiers
    prerelease = ()
    if prerelease_str:
        prerelease_identifiers = prerelease_str.split('.')
        parsed_prerelease = []
        for identifier in prerelease_identifiers:
            # Check if identifier is numeric (no leading zeros allowed)
            if identifier.isdigit():
                if len(identifier) > 1 and identifier[0] == '0':
                    raise ValueError(f"Numeric prerelease identifier has leading zero: {identifier}")
                parsed_prerelease.append(int(identifier))
            else:
                # Alphanumeric identifier
                parsed_prerelease.append(identifier)
        prerelease = tuple(parsed_prerelease)

    # Parse build metadata identifiers
    build = ()
    if build_str:
        build = tuple(build_str.split('.'))

    return (major, minor, patch, prerelease, build)


def compare(a: str, b: str) -> int:
    """
    Compare two semantic versions according to SemVer 2.0.0 precedence rules.

    Returns:
    - -1 if a < b
    - 0 if a == b (ignoring build metadata)
    - 1 if a > b
    """
    parsed_a = parse(a)
    parsed_b = parse(b)

    major_a, minor_a, patch_a, prerelease_a, _ = parsed_a
    major_b, minor_b, patch_b, prerelease_b, _ = parsed_b

    # Compare major, minor, patch
    if major_a != major_b:
        return -1 if major_a < major_b else 1
    if minor_a != minor_b:
        return -1 if minor_a < minor_b else 1
    if patch_a != patch_b:
        return -1 if patch_a < patch_b else 1

    # Compare prerelease versions
    # A version without prerelease has higher precedence than with prerelease
    if not prerelease_a and not prerelease_b:
        return 0
    if not prerelease_a:  # a has no prerelease, b does
        return 1
    if not prerelease_b:  # b has no prerelease, a does
        return -1

    # Both have prerelease, compare identifiers
    for i in range(min(len(prerelease_a), len(prerelease_b))):
        id_a = prerelease_a[i]
        id_b = prerelease_b[i]

        is_a_numeric = isinstance(id_a, int)
        is_b_numeric = isinstance(id_b, int)

        # Numeric identifiers have lower precedence than alphanumeric
        if is_a_numeric and not is_b_numeric:
            return -1
        if not is_a_numeric and is_b_numeric:
            return 1

        # Both numeric or both alphanumeric
        if id_a != id_b:
            return -1 if id_a < id_b else 1

    # All preceding identifiers are equal, shorter is lower
    if len(prerelease_a) != len(prerelease_b):
        return -1 if len(prerelease_a) < len(prerelease_b) else 1

    return 0
