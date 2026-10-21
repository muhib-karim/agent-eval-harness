def tokenize(text: str) -> list[str]:
    tokens = []
    i = 0
    n = len(text)
    ws = " \t\n\r\f\v"
    while i < n:
        c = text[i]
        if c in ws:
            i += 1
        elif c in "+-*/()":
            tokens.append(c)
            i += 1
        elif "0" <= c <= "9":
            j = i
            while j < n and "0" <= text[j] <= "9":
                j += 1
            if j < n and text[j] == ".":
                k = j + 1
                while k < n and "0" <= text[k] <= "9":
                    k += 1
                if k == j + 1:
                    raise ValueError("malformed number")
                j = k
            if j < n and text[j] == ".":
                raise ValueError("malformed number")
            tokens.append(text[i:j])
            i = j
        else:
            raise ValueError(f"invalid character {c!r}")
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
        while peek() in ("+", "-"):
            op = tokens[pos]
            pos += 1
            right = term()
            value = value + right if op == "+" else value - right
        return value

    def term():
        nonlocal pos
        value = unary()
        while peek() in ("*", "/"):
            op = tokens[pos]
            pos += 1
            right = unary()
            if op == "*":
                value = value * right
            else:
                if right == 0:
                    raise ZeroDivisionError("division by zero")
                value = value / right
        return value

    def unary():
        nonlocal pos
        sign = 1
        while peek() in ("+", "-"):
            if tokens[pos] == "-":
                sign = -sign
            pos += 1
        return sign * primary()

    def primary():
        nonlocal pos
        t = peek()
        if t is None:
            raise ValueError("unexpected end of expression")
        if t == "(":
            pos += 1
            value = expr()
            if peek() != ")":
                raise ValueError("unbalanced parentheses")
            pos += 1
            return value
        if t[0].isdigit():
            pos += 1
            return float(t)
        raise ValueError(f"unexpected token {t!r}")

    result = expr()
    if pos != len(tokens):
        raise ValueError("unexpected trailing tokens")
    return float(result)
