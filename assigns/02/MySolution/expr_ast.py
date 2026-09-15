"""
expr_ast.py — a small arithmetic expression language: tokenizer, parser
(producing an Abstract Syntax Tree), AST pretty-printer, and an
AST-walking evaluator.

Grammar (standard arithmetic precedence, left-associative +,-,*,/):

    expr   := term (('+' | '-') term)*
    term   := factor (('*' | '/') factor)*
    factor := NUMBER | '(' expr ')' | ('-' | '+') factor
"""

from dataclasses import dataclass
from typing import Union


# ---------- Tokenizer ----------

class Token:
    def __init__(self, kind, value=None):
        self.kind = kind    # 'NUM', 'PLUS', 'MINUS', 'STAR', 'SLASH', 'LPAREN', 'RPAREN', 'EOF'
        self.value = value

    def __repr__(self):
        return f"Token({self.kind!r}, {self.value!r})"


def tokenize(text: str):
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        if c.isdigit() or c == '.':
            j = i
            while j < n and (text[j].isdigit() or text[j] == '.'):
                j += 1
            tokens.append(Token('NUM', float(text[i:j])))
            i = j
            continue
        if c == '+':
            tokens.append(Token('PLUS')); i += 1; continue
        if c == '-':
            tokens.append(Token('MINUS')); i += 1; continue
        if c == '*':
            tokens.append(Token('STAR')); i += 1; continue
        if c == '/':
            tokens.append(Token('SLASH')); i += 1; continue
        if c == '(':
            tokens.append(Token('LPAREN')); i += 1; continue
        if c == ')':
            tokens.append(Token('RPAREN')); i += 1; continue
        raise SyntaxError(f"Unexpected character {c!r} at position {i}")
    tokens.append(Token('EOF'))
    return tokens


# ---------- AST node types ----------

@dataclass
class Num:
    value: float


@dataclass
class BinOp:
    op: str    # '+', '-', '*', '/'
    left: "Node"
    right: "Node"


@dataclass
class UnaryOp:
    op: str    # '+', '-'
    operand: "Node"


Node = Union[Num, BinOp, UnaryOp]


# ---------- Parser ----------

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind):
        tok = self.advance()
        if tok.kind != kind:
            raise SyntaxError(f"Expected {kind}, got {tok.kind}")
        return tok

    def parse(self) -> Node:
        node = self.parse_expr()
        self.expect('EOF')
        return node

    # expr := term (('+' | '-') term)*
    #
    # NOTE ON A BUG FOUND DURING REVIEW: the first version of this parser
    # recursed on the right-hand side here (`right = self.parse_expr()`),
    # which builds a right-associative tree for +/- even though they are
    # left-associative operators. That made "10 - 3 - 2" parse as
    # 10 - (3 - 2) = 9 instead of the correct (10 - 3) - 2 = 5. The fix is
    # to use an explicit loop that keeps folding new terms onto the left
    # side, which is the standard way to make a recursive-descent parser
    # produce a left-associative tree.
    def parse_expr(self) -> Node:
        left = self.parse_term()
        while self.peek().kind in ('PLUS', 'MINUS'):
            op = '+' if self.advance().kind == 'PLUS' else '-'
            right = self.parse_term()
            left = BinOp(op, left, right)
        return left

    # term := factor (('*' | '/') factor)*
    # Same left-associativity fix as parse_expr, for the same reason.
    def parse_term(self) -> Node:
        left = self.parse_factor()
        while self.peek().kind in ('STAR', 'SLASH'):
            op = '*' if self.advance().kind == 'STAR' else '/'
            right = self.parse_factor()
            left = BinOp(op, left, right)
        return left

    # factor := NUMBER | '(' expr ')' | ('-' | '+') factor
    def parse_factor(self) -> Node:
        tok = self.peek()
        if tok.kind == 'NUM':
            self.advance()
            return Num(tok.value)
        if tok.kind == 'LPAREN':
            self.advance()
            node = self.parse_expr()
            self.expect('RPAREN')
            return node
        if tok.kind in ('PLUS', 'MINUS'):
            self.advance()
            operand = self.parse_factor()
            return UnaryOp('-' if tok.kind == 'MINUS' else '+', operand)
        raise SyntaxError(f"Unexpected token {tok}")


def parse(text: str) -> Node:
    return Parser(tokenize(text)).parse()


# ---------- Evaluator ----------

def evaluate(node: Node) -> float:
    if isinstance(node, Num):
        return node.value
    if isinstance(node, UnaryOp):
        val = evaluate(node.operand)
        return -val if node.op == '-' else val
    if isinstance(node, BinOp):
        lval = evaluate(node.left)
        rval = evaluate(node.right)
        if node.op == '+':
            return lval + rval
        if node.op == '-':
            return lval - rval
        if node.op == '*':
            return lval * rval
        if node.op == '/':
            return lval / rval
    raise TypeError(f"Unknown node type: {node}")


# ---------- Pretty printer ----------

def pretty(node: Node, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(node, Num):
        return f"{pad}Num({node.value})"
    if isinstance(node, UnaryOp):
        return f"{pad}UnaryOp({node.op})\n{pretty(node.operand, indent+1)}"
    if isinstance(node, BinOp):
        return (
            f"{pad}BinOp({node.op})\n"
            f"{pretty(node.left, indent+1)}\n"
            f"{pretty(node.right, indent+1)}"
        )
    return f"{pad}<unknown>"


if __name__ == "__main__":
    examples = ["1 + 2 * 3", "10 - 3 - 2", "(1 + 2) * 3", "-5 + 3"]
    for expr in examples:
        tree = parse(expr)
        print(f"expr:   {expr}")
        print(f"ast:\n{pretty(tree)}")
        print(f"result: {evaluate(tree)}")
        print()
