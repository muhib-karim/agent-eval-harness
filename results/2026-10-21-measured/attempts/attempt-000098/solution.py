import string

_WS = set(string.whitespace)
_DIGITS = set("0123456789")
_OPS = set("+-*/()")


def tokenize(text: str) -> list[str]:
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in _WS:
            i += 1
        elif c in _OPS:
            tokens.append(c)
            i += 1
        elif c in _DIGITS:
            j = i
            while j < n and text[j] in _DIGITS:
                j += 1
            if j < n and text[j] == '.':
                k = j + 1
                if k >= n or text[k] not in _DIGITS:
                    raise ValueError("malformed number")
                while k < n and text[k] in _DIGITS:
                    k += 1
                j = k
            tokens.append(text[i:j])
            i = j
        else:
            raise ValueError("invalid character %r" % c)
    return tokens


def evaluate(text: str) -> float:
    tokens = tokenize(text)
    if not tokens:
        raise ValueError("empty expression")
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def expr():
        nonlocal pos
        value = term()
        while peek() in ('+', '-'):
            op = tokens[pos]
            pos += 1
            rhs = term()
            value = value + rhs if op == '+' else value - rhs
        return value

    def term():
        nonlocal pos
        value = unary()
        while peek() in ('*', '/'):
            op = tokens[pos]
            pos += 1
            rhs = unary()
            if op == '*':
                value = value * rhs
            else:
                if rhs == 0:
                    raise ZeroDivisionError("division by zero")
                value = value / rhs
        return value

    def unary():
        nonlocal pos
        sign = 1
        while peek() in ('+', '-'):
            if tokens[pos] == '-':
                sign = -sign
            pos += 1
        return sign * primary()

    def primary():
        nonlocal pos
        t = peek()
        if t is None:
            raise ValueError("unexpected end of expression")
        if t == '(':
            pos += 1
            value = expr()
            if peek() != ')':
                raise ValueError("unbalanced parentheses")
            pos += 1
            return value
        if t[0] in _DIGITS:
            pos += 1
            return float(t)
        raise ValueError("unexpected token %r" % t)

    result = expr()
    if pos != len(tokens):
        raise ValueError("unexpected trailing token %r" % tokens[pos])
    return float(result)
