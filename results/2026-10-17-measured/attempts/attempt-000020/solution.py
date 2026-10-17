"""
solution.py

Implements a small arithmetic tokenizer and evaluator using only the
Python standard library (no eval/exec).

Supported tokens:
    - Unsigned integers:            123
    - Unsigned decimals (digits on BOTH sides of the dot): 12.34
    - Operators / punctuation:      + - * / ( )

Whitespace is ignored. Any other character, or a malformed number
(e.g. "1.", ".5", "1..2"), raises ValueError.

evaluate() supports:
    - parentheses
    - unary + and - (including repeated/stacked signs)
    - standard precedence (unary > * / > + -)
    - left-associative binary operators
    - raises ValueError for empty expressions, missing operators between
      operands, trailing tokens, or unbalanced parentheses
    - raises ZeroDivisionError for division by zero
"""

from typing import List, Optional

_OPERATOR_CHARS = "+-*/()"


def tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    i = 0
    n = len(text)

    while i < n:
        c = text[i]

        if c.isspace():
            i += 1
            continue

        if c in _OPERATOR_CHARS:
            tokens.append(c)
            i += 1
            continue

        if c.isdigit():
            start = i
            while i < n and text[i].isdigit():
                i += 1

            if i < n and text[i] == '.':
                j = i + 1
                if j < n and text[j].isdigit():
                    i = j
                    while i < n and text[i].isdigit():
                        i += 1
                else:
                    raise ValueError(
                        f"Malformed number starting at position {start}: "
                        f"{text[start:i+1]!r}"
                    )

            tokens.append(text[start:i])
            continue

        # Any other character (including a lone '.') is invalid.
        raise ValueError(f"Unexpected character {c!r} at position {i}")

    return tokens


def evaluate(text: str) -> float:
    tokens = tokenize(text)

    if not tokens:
        raise ValueError("Empty expression")

    pos = [0]  # mutable index box so nested functions can advance it

    def peek() -> Optional[str]:
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def advance() -> Optional[str]:
        tok = peek()
        pos[0] += 1
        return tok

    def parse_primary() -> float:
        tok = peek()
        if tok is None:
            raise ValueError("Unexpected end of expression")

        if tok == '(':
            advance()
            value = parse_expr()
            if peek() != ')':
                raise ValueError("Unbalanced parentheses: expected ')'")
            advance()
            return value

        if tok in _OPERATOR_CHARS:
            raise ValueError(f"Unexpected token {tok!r}")

        # Must be a number token.
        advance()
        return float(tok)

    def parse_factor() -> float:
        sign = 1
        while peek() in ('+', '-'):
            if advance() == '-':
                sign = -sign
        value = parse_primary()
        return sign * value

    def parse_term() -> float:
        value = parse_factor()
        while peek() in ('*', '/'):
            op = advance()
            rhs = parse_factor()
            if op == '*':
                value *= rhs
            else:
                if rhs == 0:
                    raise ZeroDivisionError("Division by zero")
                value /= rhs
        return value

    def parse_expr() -> float:
        value = parse_term()
        while peek() in ('+', '-'):
            op = advance()
            rhs = parse_term()
            if op == '+':
                value += rhs
            else:
                value -= rhs
        return value

    result = parse_expr()

    if pos[0] != len(tokens):
        raise ValueError(
            f"Unexpected trailing tokens starting at {tokens[pos[0]:]!r}"
        )

    return result


if __name__ == "__main__":
    # Simple manual smoke tests.
    examples = [
        "1 + 2 * 3",
        "(1 + 2) * 3",
        "-3 + 4",
        "--3 + 4",
        "3.14 * 2",
        "10 / 4",
    ]
    for ex in examples:
        print(ex, "=>", evaluate(ex))
