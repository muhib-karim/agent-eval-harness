def tokenize(text: str) -> list[str]:
    tokens = []
    i = 0
    n = len(text)
    operators = "+-*/()"

    while i < n:
        char = text[i]

        if char.isspace():
            i += 1
        elif char in operators:
            tokens.append(char)
            i += 1
        elif "0" <= char <= "9":
            start = i
            while i < n and "0" <= text[i] <= "9":
                i += 1

            if i < n and text[i] == ".":
                i += 1
                if i == n or not ("0" <= text[i] <= "9"):
                    raise ValueError("Malformed number")
                while i < n and "0" <= text[i] <= "9":
                    i += 1

            tokens.append(text[start:i])
        else:
            raise ValueError(f"Invalid character: {char!r}")

    return tokens


def evaluate(text: str) -> float:
    tokens = tokenize(text)
    pos = 0

    def expression() -> float:
        nonlocal pos
        value = term()
        while pos < len(tokens) and tokens[pos] in ("+", "-"):
            operator = tokens[pos]
            pos += 1
            right = term()
            value = value + right if operator == "+" else value - right
        return value

    def term() -> float:
        nonlocal pos
        value = factor()
        while pos < len(tokens) and tokens[pos] in ("*", "/"):
            operator = tokens[pos]
            pos += 1
            right = factor()
            value = value * right if operator == "*" else value / right
        return value

    def factor() -> float:
        nonlocal pos
        sign = 1
        while pos < len(tokens) and tokens[pos] in ("+", "-"):
            if tokens[pos] == "-":
                sign = -sign
            pos += 1

        if pos >= len(tokens):
            raise ValueError("Expected an operand")

        token = tokens[pos]
        pos += 1

        if token == "(":
            value = expression()
            if pos >= len(tokens) or tokens[pos] != ")":
                raise ValueError("Unbalanced parentheses")
            pos += 1
        elif "0" <= token[0] <= "9":
            value = float(token)
        else:
            raise ValueError("Expected an operand")

        return sign * value

    if not tokens:
        raise ValueError("Empty expression")

    result = expression()
    if pos != len(tokens):
        raise ValueError("Unexpected trailing token")
    return result
