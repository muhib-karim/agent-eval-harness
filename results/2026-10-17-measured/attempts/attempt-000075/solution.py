import re


_TOKEN_RE = re.compile(r"""
    (?P<num>\d+(?:\.\d+)?)|(?P<op>[+\-*/()])
""", re.VERBOSE)


def tokenize(text: str) -> list[str]:
    tokens = []
    pos = 0
    n = len(text)
    while pos < n:
        ch = text[pos]
        if ch.isspace():
            pos += 1
            continue
        m = _TOKEN_RE.match(text, pos)
        if not m:
            raise ValueError(f"Invalid character at position {pos}: {ch!r}")
        tokens.append(m.group(0))
        pos = m.end()
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.n = len(tokens)

    def peek(self):
        if self.pos < self.n:
            return self.tokens[self.pos]
        return None

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self):
        if self.n == 0:
            raise ValueError("Empty expression")
        value = self.parse_expr()
        if self.pos != self.n:
            raise ValueError(f"Unexpected token: {self.tokens[self.pos]!r}")
        return value

    def parse_expr(self):
        left = self.parse_term()
        while True:
            tok = self.peek()
            if tok in ('+', '-'):
                self.advance()
                right = self.parse_term()
                if tok == '+':
                    left = left + right
                else:
                    left = left - right
            else:
                return left

    def parse_term(self):
        left = self.parse_unary()
        while True:
            tok = self.peek()
            if tok in ('*', '/'):
                self.advance()
                right = self.parse_unary()
                if tok == '*':
                    left = left * right
                else:
                    if right == 0:
                        raise ZeroDivisionError("Division by zero")
                    left = left / right
            else:
                return left

    def parse_unary(self):
        tok = self.peek()
        if tok == '+':
            self.advance()
            return self.parse_unary()
        if tok == '-':
            self.advance()
            return -self.parse_unary()
        return self.parse_atom()

    def parse_atom(self):
        tok = self.peek()
        if tok is None:
            raise ValueError("Unexpected end of expression")
        if tok == '(':
            self.advance()
            value = self.parse_expr()
            if self.peek() != ')':
                raise ValueError("Unbalanced parentheses")
            self.advance()
            return value
        if tok == ')':
            raise ValueError("Unexpected ')'")
        # must be number
        self.advance()
        if '.' in tok:
            return float(tok)
        return float(int(tok))


def evaluate(text: str) -> float:
    return _Parser(tokenize(text)).parse()
