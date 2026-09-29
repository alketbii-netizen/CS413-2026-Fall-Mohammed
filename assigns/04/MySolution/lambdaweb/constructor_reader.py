"""
Restricted reader for LAMBDA source in "Python constructor expression"
form, e.g.:

    D0Eop2("+", D0Eint(20), D0Eint(22))

Per Assign04.md: "Load the expression through a restricted constructor
reader that validates arguments; do not execute arbitrary uploaded
Python or shell code." This module NEVER calls eval()/exec() on
uploaded text. It parses the text with Python's `ast` module (which only
builds a syntax tree — it does not run anything), then walks that tree
by hand, only ever constructing objects from an explicit whitelist of
d0exp constructors with recursively-validated arguments. Any node kind
outside that whitelist (attribute access, subscripts, function/class
defs, imports, arbitrary names, comprehensions, f-strings with
expressions, etc.) is rejected before any object is built.
"""

from __future__ import annotations

import ast
import textwrap
from dataclasses import fields

from lambdaweb.lambda1 import (
    d0exp,
    D0Eint, D0Ebtf, D0Eop1, D0Eop2, D0Evar,
    D0Elam, D0Efix, D0Eapp, D0Eif0, D0Elet,
    D0Epair, D0Epfst, D0Epsnd,
)
from lambdaweb.limits import MAX_SOURCE_BYTES

# The only constructor names the reader will ever instantiate.
_CONSTRUCTORS: dict[str, type] = {
    "D0Eint": D0Eint,
    "D0Ebtf": D0Ebtf,
    "D0Eop1": D0Eop1,
    "D0Eop2": D0Eop2,
    "D0Evar": D0Evar,
    "D0Elam": D0Elam,
    "D0Efix": D0Efix,
    "D0Eapp": D0Eapp,
    "D0Eif0": D0Eif0,
    "D0Elet": D0Elet,
    "D0Epair": D0Epair,
    "D0Epfst": D0Epfst,
    "D0Epsnd": D0Epsnd,
}


class ConstructorReadError(Exception):
    """Raised for any malformed, oversized, or disallowed input."""


def read_d0exp(source: str) -> d0exp:
    """Parse `source` into a d0exp tree, or raise ConstructorReadError."""
    if source.encode("utf-8", errors="strict").__len__() > MAX_SOURCE_BYTES:
        raise ConstructorReadError(
            f"source exceeds the {MAX_SOURCE_BYTES}-byte size limit"
        )
    if not source.strip():
        raise ConstructorReadError("source is empty or whitespace-only")

    # Uploaded/pasted source is often copied from an indented context (a
    # function body, a quoted block); Python's grammar forbids a top-level
    # expression from starting with leading whitespace ("unexpected
    # indent"), so a common leading indentation is stripped before
    # parsing. This never changes the expression itself, only whether it
    # is accepted.
    try:
        tree = ast.parse(textwrap.dedent(source), mode="eval")
    except SyntaxError as exc:
        raise ConstructorReadError(f"syntax error: {exc}") from exc

    return _build(tree.body)


def _build(node: ast.AST):
    """Recursively translate a restricted AST node into a Python value:
    either a d0exp instance (from a whitelisted constructor call) or a
    plain literal (str, int, bool) used as a constructor argument.
    """
    # --- literals -------------------------------------------------
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (str, int, bool)):
            return node.value
        raise ConstructorReadError(
            f"unsupported literal type: {type(node.value).__name__}"
        )

    # --- negative integer literals, e.g. D0Eint(-1) ----------------
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = _build(node.operand)
        if isinstance(operand, bool) or not isinstance(operand, int):
            raise ConstructorReadError("unary '-' is only allowed on integers")
        return -operand

    # --- constructor calls ------------------------------------------
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ConstructorReadError(
                "only direct constructor calls are allowed, e.g. D0Eint(1)"
            )
        name = node.func.id
        if name not in _CONSTRUCTORS:
            raise ConstructorReadError(f"unknown or disallowed constructor: {name}")
        if node.keywords:
            raise ConstructorReadError(
                f"{name}(...): keyword arguments are not supported"
            )

        cls = _CONSTRUCTORS[name]
        expected = [f.name for f in fields(cls) if f.name != "ctag"]
        args = [_build(a) for a in node.args]
        if len(args) != len(expected):
            raise ConstructorReadError(
                f"{name}(...) expects {len(expected)} argument(s) "
                f"({', '.join(expected)}), got {len(args)}"
            )
        try:
            return cls(*args)
        except TypeError as exc:
            raise ConstructorReadError(f"{name}(...): invalid arguments: {exc}") from exc

    raise ConstructorReadError(
        f"disallowed expression element: {type(node).__name__}"
    )
