import re

def tokenize(text: str) -> list[str]:
    """
    Tokenize a mathematical expression into a list of tokens.

    Tokens: ASCII unsigned integers or decimals with digits on BOTH sides of decimal point,
    and operators + - * / ( ).
    Whitespace is ignored. Any other character or malformed number raises ValueError.
    """
    if not text:
        return []

    tokens = []
    i = 0

    while i < len(text):
        # Skip whitespace
        if text[i].isspace():
            i += 1
            continue

        # Check for operators and parentheses
        if text[i] in '+-*/()':
            tokens.append(text[i])
            i += 1
            continue

        # Check for numbers (integers or decimals)
        if text[i].isdigit():
            j = i
            has_dot = False
            while j < len(text) and (text[j].isdigit() or text[j] == '.'):
                if text[j] == '.':
                    if has_dot:
                        raise ValueError(f"Multiple decimal points in number")
                    has_dot = True
                j += 1

            number_str = text[i:j]

            # Validate decimal format: must have digits on BOTH sides of decimal point
            if has_dot:
                parts = number_str.split('.')
                if len(parts) != 2 or not parts[0] or not parts[1]:
                    raise ValueError(f"Malformed decimal number: {number_str}")

            tokens.append(number_str)
            i = j
            continue

        # Any other character is invalid
        raise ValueError(f"Invalid character: {text[i]}")

    return tokens


def evaluate(text: str) -> float:
    """
    Evaluate a mathematical expression string and return the result as a float.

    Supports:
    - Parentheses
    - Unary + and - (including repeated signs)
    - Binary operators: + - * / with usual precedence and left-associativity

    Raises ValueError for:
    - Empty expressions
    - Adjacent operands
    - Trailing tokens
    - Unbalanced parentheses
    - Malformed input

    Raises ZeroDivisionError for division by zero.
    """
    tokens = tokenize(text)

    if not tokens:
        raise ValueError("Empty expression")

    pos = [0]  # Use list to allow modification in nested functions

    def parse_expression():
        """Parse addition and subtraction (lowest precedence)"""
        left = parse_term()

        while pos[0] < len(tokens) and tokens[pos[0]] in ['+', '-']:
            op = tokens[pos[0]]
            pos[0] += 1
            right = parse_term()
            if op == '+':
                left = left + right
            else:
                left = left - right

        return left

    def parse_term():
        """Parse multiplication and division (higher precedence)"""
        left = parse_unary()

        while pos[0] < len(tokens) and tokens[pos[0]] in ['*', '/']:
            op = tokens[pos[0]]
            pos[0] += 1
            right = parse_unary()
            if op == '*':
                left = left * right
            else:
                if right == 0:
                    raise ZeroDivisionError("Division by zero")
                left = left / right

        return left

    def parse_unary():
        """Parse unary operators and primary expressions"""
        # Handle unary + and -
        sign = 1
        while pos[0] < len(tokens) and tokens[pos[0]] in ['+', '-']:
            if tokens[pos[0]] == '-':
                sign *= -1
            pos[0] += 1

        value = parse_primary()
        return sign * value

    def parse_primary():
        """Parse numbers and parenthesized expressions"""
        if pos[0] >= len(tokens):
            raise ValueError("Unexpected end of expression")

        token = tokens[pos[0]]

        # Number
        if token[0].isdigit():
            pos[0] += 1
            return float(token)

        # Parenthesized expression
        if token == '(':
            pos[0] += 1
            value = parse_expression()
            if pos[0] >= len(tokens) or tokens[pos[0]] != ')':
                raise ValueError("Unbalanced parentheses: missing closing ')'")
            pos[0] += 1
            return value

        raise ValueError(f"Unexpected token: {token}")

    result = parse_expression()

    # Check if all tokens were consumed
    if pos[0] < len(tokens):
        raise ValueError(f"Trailing tokens: {tokens[pos[0]:]}")

    return result
