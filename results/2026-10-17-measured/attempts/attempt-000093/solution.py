import re
from typing import List

def tokenize(text: str) -> List[str]:
    if not text:
        return []
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        if text[i].isspace():
            i += 1
            continue
        if text[i] in '+-*/()':
            tokens.append(text[i])
            i += 1
            continue
        if text[i].isdigit():
            start = i
            while i < n and text[i].isdigit():
                i += 1
            if i < n and text[i] == '.':
                i += 1
                if i >= n or not text[i].isdigit():
                    raise ValueError("malformed number")
                while i < n and text[i].isdigit():
                    i += 1
            tokens.append(text[start:i])
            continue
        raise ValueError("invalid character")
    return tokens

def evaluate(text: str) -> float:
    tokens = tokenize(text)
    if not tokens:
        raise ValueError("empty expression")

    def parse_expr(idx):
        val, idx = parse_term(idx)
        while idx < len(tokens) and tokens[idx] in ('+', '-'):
            op = tokens[idx]
            idx += 1
            rval, idx = parse_term(idx)
            if op == '+':
                val += rval
            else:
                val -= rval
        return val, idx

    def parse_term(idx):
        val, idx = parse_factor(idx)
        while idx < len(tokens) and tokens[idx] in ('*', '/'):
            op = tokens[idx]
            idx += 1
            rval, idx = parse_factor(idx)
            if op == '*':
                val *= rval
            else:
                if rval == 0:
                    raise ZeroDivisionError
                val /= rval
        return val, idx

    def parse_factor(idx):
        if idx >= len(tokens):
            raise ValueError("trailing tokens or empty")
        tok = tokens[idx]
        if tok == '(':
            idx += 1
            val, idx = parse_expr(idx)
            if idx >= len(tokens) or tokens[idx] != ')':
                raise ValueError("unbalanced parentheses")
            idx += 1
            return val, idx
        if tok in ('+', '-'):
            idx += 1
            rval, idx = parse_factor(idx)
            return (+rval if tok == '+' else -rval), idx
        if re.fullmatch(r'\d+(\.\d+)?', tok):
            idx += 1
            return float(tok), idx
        raise ValueError("invalid token")

    result, idx = parse_expr(0)
    if idx != len(tokens):
        raise ValueError("trailing tokens or adjacent operands")
    return result
