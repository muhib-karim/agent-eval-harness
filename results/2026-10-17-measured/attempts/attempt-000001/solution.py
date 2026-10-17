def _is_digit(c: str) -> bool:
    return '0' <= c <= '9'


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
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
        if _is_digit(c):
            start = i
            while i < n and _is_digit(text[i]):
                i += 1
            if i < n and text[i] == '.':
                i += 1
                if i >= n or not _is_digit(text[i]):
                    raise ValueError("malformed number at position %d" % start)
                while i < n and _is_digit(text[i]):
                    i += 1
                if i < n and (text[i] == '.' or _is_digit(text[i])):
                    raise ValueError("malformed number at position %d" % start)
            tokens.append(text[start:i])
            continue
        if c == '.':
            raise ValueError("malformed number at position %d" % i)
        raise ValueError("invalid character %r at position %d" % (c, i))
    return tokens


class _Parser:
    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self):
        tok = self.peek()
        if tok is None:
            raise ValueError("unexpected end of expression")
        self.pos += 1
        return tok

    def parse(self) -> float:
        if not self.tokens:
            raise ValueError("empty expression")
        value = self.expr()
        if self.pos != len(self.tokens):
            raise ValueError("unexpected token %r" % self.tokens[self.pos])
        return value

    def expr(self) -> float:
        value = self.term()
        while self.peek() in ('+', '-'):
            op = self.advance()
            rhs = self.term()
            if op == '+':
                value = value + rhs
            else:
                value = value - rhs
        return value

    def term(self) -> float:
        value = self.unary()
        while self.peek() in ('*', '/'):
            op = self.advance()
            rhs = self.unary()
            if op == '*':
                value = value * rhs
            else:
                if rhs == 0:
                    raise ZeroDivisionError("division by zero")
                value = value / rhs
        return value

    def unary(self) -> float:
        negative = False
        while self.peek() in ('+', '-'):
            if self.advance() == '-':
                negative = not negative
        value = self.primary()
        return -value if negative else value

    def primary(self) -> float:
        tok = self.peek()
        if tok is None:
            raise ValueError("unexpected end of expression")
        if tok == '(':
            self.advance()
            value = self.expr()
            if self.peek() != ')':
                raise ValueError("unbalanced parentheses")
            self.advance()
            return value
        if _is_digit(tok[0]):
            self.advance()
            return float(tok)
        raise ValueError("unexpected token %r" % tok)


def evaluate(text: str) -> float:
    tokens = tokenize(text)
    return float(_Parser(tokens).parse())
