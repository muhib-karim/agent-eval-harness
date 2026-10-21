def tokenize(text: str) -> list[str]:
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in ' \t\n\r\f\v':
            i += 1
            continue
        if c in '+-*/()':
            tokens.append(c)
            i += 1
            continue
        if '0' <= c <= '9':
            j = i
            while j < n and '0' <= text[j] <= '9':
                j += 1
            if j < n and text[j] == '.':
                k = j + 1
                while k < n and '0' <= text[k] <= '9':
                    k += 1
                if k == j + 1:
                    raise ValueError("malformed number: missing digits after decimal point")
                j = k
                if j < n and (text[j] == '.' or '0' <= text[j] <= '9'):
                    raise ValueError("malformed number")
            tokens.append(text[i:j])
            i = j
            continue
        if c == '.':
            raise ValueError("malformed number: missing digits before decimal point")
        raise ValueError(f"invalid character: {c!r}")
    return tokens


def _is_number(tok: str) -> bool:
    return bool(tok) and '0' <= tok[0] <= '9'


def evaluate(text: str) -> float:
    tokens = tokenize(text)
    if not tokens:
        raise ValueError("empty expression")
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def parse_expr():
        nonlocal pos
        value = parse_term()
        while peek() in ('+', '-'):
            op = tokens[pos]
            pos += 1
            rhs = parse_term()
            value = value + rhs if op == '+' else value - rhs
        return value

    def parse_term():
        nonlocal pos
        value = parse_unary()
        while peek() in ('*', '/'):
            op = tokens[pos]
            pos += 1
            rhs = parse_unary()
            if op == '*':
                value = value * rhs
            else:
                if rhs == 0:
                    raise ZeroDivisionError("division by zero")
                value = value / rhs
        return value

    def parse_unary():
        nonlocal pos
        negative = False
        while peek() in ('+', '-'):
            if tokens[pos] == '-':
                negative = not negative
            pos += 1
        value = parse_primary()
        return -value if negative else value

    def parse_primary():
        nonlocal pos
        tok = peek()
        if tok is None:
            raise ValueError("unexpected end of expression")
        if tok == '(':
            pos += 1
            value = parse_expr()
            if peek() != ')':
                raise ValueError("unbalanced parentheses")
            pos += 1
            return value
        if _is_number(tok):
            pos += 1
            return float(tok)
        raise ValueError(f"unexpected token: {tok!r}")

    result = parse_expr()
    if pos != len(tokens):
        raise ValueError(f"unexpected token: {tokens[pos]!r}")
    return float(result)
