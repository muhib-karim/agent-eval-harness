import re

def parse(text: str) -> tuple:
    """
    Parse a semantic version string according to SemVer 2.0.0.

    Returns: (major, minor, patch, prerelease, build)
    - major, minor, patch: int
    - prerelease: tuple of identifiers (int for numeric, str for alphanumeric)
    - build: tuple of str identifiers

    Raises ValueError for invalid input.
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")

    # SemVer 2.0.0 regex pattern
    pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([a-zA-Z0-9\-\.]+))?(?:\+([a-zA-Z0-9\-\.]+))?$'
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
            if not identifier:
                raise ValueError(f"Empty prerelease identifier in: {text}")
            # Check if identifier is numeric (all digits, no leading zeros except "0")
            if identifier.isdigit():
                if len(identifier) > 1 and identifier[0] == '0':
                    raise ValueError(f"Numeric prerelease identifier with leading zero: {identifier}")
                parsed_prerelease.append(int(identifier))
            else:
                # Alphanumeric identifier - validate characters
                if not re.match(r'^[a-zA-Z0-9\-]+$', identifier):
                    raise ValueError(f"Invalid prerelease identifier: {identifier}")
                parsed_prerelease.append(identifier)
        prerelease = tuple(parsed_prerelease)

    # Parse build identifiers
    build = ()
    if build_str:
        build_identifiers = build_str.split('.')
        for identifier in build_identifiers:
            if not identifier:
                raise ValueError(f"Empty build identifier in: {text}")
            if not re.match(r'^[a-zA-Z0-9\-]+$', identifier):
                raise ValueError(f"Invalid build identifier: {identifier}")
        build = tuple(build_identifiers)

    return (major, minor, patch, prerelease, build)


def compare(a: str, b: str) -> int:
    """
    Compare two semantic version strings according to SemVer 2.0.0 precedence rules.

    Returns:
    - -1 if a < b
    - 0 if a == b (ignoring build metadata)
    - 1 if a > b

    Raises ValueError if either version string is invalid.
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

    # Version without prerelease > version with prerelease (when major.minor.patch equal)
    has_prerelease_a = len(prerelease_a) > 0
    has_prerelease_b = len(prerelease_b) > 0

    if not has_prerelease_a and has_prerelease_b:
        return 1
    if has_prerelease_a and not has_prerelease_b:
        return -1

    # Both have prerelease or both don't - compare prerelease identifiers
    if has_prerelease_a and has_prerelease_b:
        for i in range(max(len(prerelease_a), len(prerelease_b))):
            # Shorter prerelease has lower precedence
            if i >= len(prerelease_a):
                return -1
            if i >= len(prerelease_b):
                return 1

            id_a = prerelease_a[i]
            id_b = prerelease_b[i]

            is_num_a = isinstance(id_a, int)
            is_num_b = isinstance(id_b, int)

            # Numeric identifiers are always lower than alphanumeric
            if is_num_a and not is_num_b:
                return -1
            if not is_num_a and is_num_b:
                return 1

            # Both numeric or both alphanumeric
            if id_a != id_b:
                return -1 if id_a < id_b else 1

    # Versions are equal (ignoring build metadata)
    return 0
