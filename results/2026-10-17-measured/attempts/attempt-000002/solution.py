def tokenize(text: str) -> list[str]:
    tokens = []
    i = 0
    n = len(text)

    def is_digit(ch):
        return '0' <= ch <= '9'

    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        if c in '+-*/()':
            tokens.append(c)
            i += 1
            continue
        if is_digit(c):
            j = i
            while j < n and is_digit(text[j]):
                j += 1
            if j < n and text[j] == '.':
                k = j + 1
                while k < n and is_digit(text[k]):
                    k += 1
                if k == j + 1:
                    raise ValueError("malformed number: missing digits after decimal point")
                j = k
                # A second decimal point directly after a decimal is malformed
                if j < n and text[j] == '.':
                    raise ValueError("malformed number: multiple decimal points")
            tokens.append(text[i:j])
            i = j
            continue
        if c == '.':
            raise ValueError("malformed number: missing digits before decimal point")
        raise ValueError(f"invalid character: {c!r}")
    return tokens


def evaluate(text: str) -> float:
    tokens = tokenize(text)
    if not tokens:
        raise ValueError("empty expression")
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def advance():
        nonlocal pos
        tok = tokens[pos]
        pos += 1
        return tok

    def parse_expr():
        value = parse_term()
        while peek() in ('+', '-'):
            op = advance()
            rhs = parse_term()
            if op == '+':
                value = value + rhs
            else:
                value = value - rhs
        return value

    def parse_term():
        value = parse_unary()
        while peek() in ('*', '/'):
            op = advance()
            rhs = parse_unary()
            if op == '*':
                value = value * rhs
            else:
                if rhs == 0:
                    raise ZeroDivisionError("division by zero")
                value = value / rhs
        return value

    def parse_unary():
        sign = 1
        while peek() in ('+', '-'):
            if advance() == '-':
                sign = -sign
        value = parse_primary()
        return -value if sign < 0 else value

    def parse_primary():
        tok = peek()
        if tok is None:
            raise ValueError("unexpected end of expression")
        if tok == '(':
            advance()
            value = parse_expr()
            if peek() != ')':
                raise ValueError("unbalanced parentheses")
            advance()
            return value
        if tok in '+-*/)':
            raise ValueError(f"unexpected token: {tok!r}")
        advance()
        return float(tok)

    result = parse_expr()
    if pos != len(tokens):
        raise ValueError(f"unexpected token: {tokens[pos]!r}")
    return float(result)
