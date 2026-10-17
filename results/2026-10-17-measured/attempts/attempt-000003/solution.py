"""Tokenizer and evaluator for simple arithmetic expressions (no eval/exec)."""

_OPERATORS = set("+-*/()")
_WHITESPACE = set(" \t\n\r\f\v")


def _is_digit(c: str) -> bool:
    return "0" <= c <= "9"


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in _WHITESPACE:
            i += 1
            continue
        if c in _OPERATORS:
            tokens.append(c)
            i += 1
            continue
        if _is_digit(c):
            start = i
            while i < n and _is_digit(text[i]):
                i += 1
            if i < n and text[i] == ".":
                i += 1
                if i >= n or not _is_digit(text[i]):
                    raise ValueError("malformed number at position %d" % start)
                while i < n and _is_digit(text[i]):
                    i += 1
                if i < n and text[i] == ".":
                    raise ValueError("malformed number at position %d" % start)
            tokens.append(text[start:i])
            continue
        raise ValueError("invalid character %r at position %d" % (c, i))
    return tokens


def evaluate(text: str) -> float:
    tokens = tokenize(text)
    if not tokens:
        raise ValueError("empty expression")
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def parse_expr() -> float:
        nonlocal pos
        value = parse_term()
        while peek() in ("+", "-"):
            op = tokens[pos]
            pos += 1
            rhs = parse_term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def parse_term() -> float:
        nonlocal pos
        value = parse_unary()
        while peek() in ("*", "/"):
            op = tokens[pos]
            pos += 1
            rhs = parse_unary()
            if op == "*":
                value = value * rhs
            else:
                if rhs == 0:
                    raise ZeroDivisionError("division by zero")
                value = value / rhs
        return value

    def parse_unary() -> float:
        nonlocal pos
        sign = 1
        while peek() in ("+", "-"):
            if tokens[pos] == "-":
                sign = -sign
            pos += 1
        value = parse_primary()
        return -value if sign < 0 else value

    def parse_primary() -> float:
        nonlocal pos
        tok = peek()
        if tok is None:
            raise ValueError("unexpected end of expression")
        if tok == "(":
            pos += 1
            value = parse_expr()
            if peek() != ")":
                raise ValueError("unbalanced parentheses")
            pos += 1
            return value
        if tok in _OPERATORS:
            raise ValueError("unexpected token %r" % tok)
        pos += 1
        return float(tok)

    result = parse_expr()
    if pos != len(tokens):
        raise ValueError("unexpected token %r" % tokens[pos])
    return float(result)
