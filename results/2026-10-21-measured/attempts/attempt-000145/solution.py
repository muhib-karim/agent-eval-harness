"""
solution.py

Implements:
    tokenize(text: str) -> list[str]
    evaluate(text: str) -> float

Only uses the Python standard library. No eval/exec is used.
"""

from typing import List, Optional


def tokenize(text: str) -> List[str]:
    """
    Tokenize an arithmetic expression string.

    Valid tokens:
      - unsigned integers:  digits+
      - decimals:           digits+ '.' digits+   (digits required on BOTH sides)
      - operators:          + - * / ( )

    Whitespace is ignored. Any other character, or a malformed number
    (e.g. "1." or ".5" or "1.2.3"), raises ValueError.
    """
    tokens: List[str] = []
    i = 0
    n = len(text)

    while i < n:
        c = text[i]

        if c.isspace():
            i += 1
            continue

        if c in '+-*/()':
            tokens.append(c)
            i += 1
            continue

        if c.isdigit():
            start = i
            while i < n and text[i].isdigit():
                i += 1

            if i < n and text[i] == '.':
                dot_pos = i
                i += 1
                if i >= n or not text[i].isdigit():
                    # malformed: dot not followed by at least one digit
                    bad = text[start:i] if i <= n else text[start:]
                    raise ValueError(
                        f"Malformed number near position {start}: {text[start:dot_pos+1]}"
                    )
                while i < n and text[i].isdigit():
                    i += 1

            tokens.append(text[start:i])
            continue

        if c == '.':
            # A decimal point with no leading digit is malformed/invalid.
            raise ValueError(f"Malformed number near position {i}: unexpected '.'")

        raise ValueError(f"Invalid character at position {i}: {c!r}")

    return tokens


def evaluate(text: str) -> float:
    """
    Evaluate an arithmetic expression supporting:
      - parentheses
      - unary + and - (including repeated signs)
      - binary + - * /  with usual precedence
      - left-associativity for binary operators

    Raises ValueError for empty expressions, adjacent operands,
    trailing tokens, unbalanced parentheses, or malformed tokens.
    Raises ZeroDivisionError for division by zero.
    """
    tokens = tokenize(text)

    if not tokens:
        raise ValueError("Empty expression")

    pos = 0
    length = len(tokens)

    def peek() -> Optional[str]:
        return tokens[pos] if pos < length else None

    def advance() -> str:
        nonlocal pos
        tok = tokens[pos]
        pos += 1
        return tok

    def parse_primary() -> float:
        nonlocal pos
        tok = peek()
        if tok is None:
            raise ValueError("Unexpected end of expression; expected a value")

        if tok == '(':
            advance()
            val = parse_expr()
            if peek() != ')':
                raise ValueError("Missing closing parenthesis")
            advance()
            return val

        if tok in '+-*/()':
            raise ValueError(f"Unexpected token where a value was expected: {tok!r}")

        # It's a number token
        advance()
        try:
            return float(tok)
        except ValueError:
            raise ValueError(f"Invalid number token: {tok!r}")

    def parse_factor() -> float:
        tok = peek()
        if tok in ('+', '-'):
            advance()
            val = parse_factor()
            return val if tok == '+' else -val
        return parse_primary()

    def parse_term() -> float:
        val = parse_factor()
        while True:
            tok = peek()
            if tok == '*' or tok == '/':
                advance()
                rhs = parse_factor()
                if tok == '*':
                    val = val * rhs
                else:
                    if rhs == 0:
                        raise ZeroDivisionError("Division by zero")
                    val = val / rhs
            else:
                break
        return val

    def parse_expr() -> float:
        val = parse_term()
        while True:
            tok = peek()
            if tok == '+' or tok == '-':
                advance()
                rhs = parse_term()
                if tok == '+':
                    val = val + rhs
                else:
                    val = val - rhs
            else:
                break
        return val

    result = parse_expr()

    if pos != length:
        raise ValueError(f"Trailing tokens after expression: {tokens[pos:]}")

    return result
