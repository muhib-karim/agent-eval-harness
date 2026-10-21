def tokenize(text: str) -> list[str]:
    tokens = []
    i = 0

    while i < len(text):
        char = text[i]

        if char.isspace():
            i += 1
        elif char in "+-*/()":
            tokens.append(char)
            i += 1
        elif "0" <= char <= "9":
            start = i
            while i < len(text) and "0" <= text[i] <= "9":
                i += 1

            if i < len(text) and text[i] == ".":
                i += 1
                if i >= len(text) or not ("0" <= text[i] <= "9"):
                    raise ValueError("malformed number")
                while i < len(text) and "0" <= text[i] <= "9":
                    i += 1

            tokens.append(text[start:i])
        else:
            raise ValueError(f"invalid character: {char!r}")

    return tokens


def evaluate(text: str) -> float:
    tokens = tokenize(text)
    position = 0

    def expression() -> float:
        nonlocal position
        value = term()

        while position < len(tokens) and tokens[position] in ("+", "-"):
            operator = tokens[position]
            position += 1
            right = term()
            value = value + right if operator == "+" else value - right

        return value

    def term() -> float:
        nonlocal position
        value = factor()

        while position < len(tokens) and tokens[position] in ("*", "/"):
            operator = tokens[position]
            position += 1
            right = factor()
            value = value * right if operator == "*" else value / right

        return value

    def factor() -> float:
        nonlocal position
        sign = 1

        while position < len(tokens) and tokens[position] in ("+", "-"):
            if tokens[position] == "-":
                sign = -sign
            position += 1

        if position >= len(tokens):
            raise ValueError("expected an operand")

        token = tokens[position]
        position += 1

        if token == "(":
            value = expression()
            if position >= len(tokens) or tokens[position] != ")":
                raise ValueError("unbalanced parentheses")
            position += 1
        elif token[0] in "0123456789":
            value = float(token)
        else:
            raise ValueError("expected an operand")

        return sign * value

    if not tokens:
        raise ValueError("empty expression")

    result = expression()
    if position != len(tokens):
        raise ValueError("unexpected trailing token")
    return result
