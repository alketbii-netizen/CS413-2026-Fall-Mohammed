"""Target language: Church's pure lambda calculus.

    Term ::= Var(name) | Lam(name, Term) | App(Term, Term)

Terms are immutable (frozen dataclasses), so no operation here can mutate its
input.  Free-variable and all-name sets are computed once per node and cached.

Operations
    show(t)              printer: x, (lam x. body), (fn arg)
    free_vars(t)         set of free names
    all_names(t)         every name occurring in t (free, bound, or binder)
    fresh(base, avoid)   deterministic fresh name: base_1, base_2, ...
    subst(t, x, v)       capture-avoiding t[x := v]
    alpha_equal(a, b)    equality up to consistent renaming of bound names
    is_pure(t)           True iff t is built only from Var/Lam/App

Adapted from my Assignment 5 substitution visitor (fresh-name scheme b_1,
b_2, ...), rewritten for the three-constructor target AST.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


class Term:
    """Base class of the three target forms."""
    __slots__ = ()


@dataclass(frozen=True, eq=False)
class Var(Term):
    name: str

    @cached_property
    def fv(self) -> frozenset[str]:
        return frozenset((self.name,))

    @cached_property
    def names(self) -> frozenset[str]:
        return frozenset((self.name,))

    def __repr__(self) -> str:
        return f"Var({self.name!r})"


@dataclass(frozen=True, eq=False)
class Lam(Term):
    param: str
    body: Term

    @cached_property
    def fv(self) -> frozenset[str]:
        return self.body.fv - {self.param}

    @cached_property
    def names(self) -> frozenset[str]:
        return self.body.names | {self.param}

    def __repr__(self) -> str:
        return f"Lam({self.param!r}, {self.body!r})"


@dataclass(frozen=True, eq=False)
class App(Term):
    fn: Term
    arg: Term

    @cached_property
    def fv(self) -> frozenset[str]:
        return self.fn.fv | self.arg.fv

    @cached_property
    def names(self) -> frozenset[str]:
        return self.fn.names | self.arg.names

    def __repr__(self) -> str:
        return f"App({self.fn!r}, {self.arg!r})"


# ----------------------------------------------------------------------
# Printing
# ----------------------------------------------------------------------

def show(t: Term) -> str:
    """Render x, (lam x. body), (fn arg) — iteratively, so deep terms print."""
    out: list[str] = []
    stack: list[object] = [t]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, Var):
            out.append(item.name)
        elif isinstance(item, Lam):
            stack.extend((")", item.body, f"(lam {item.param}. "))
        elif isinstance(item, App):
            stack.extend((")", item.arg, " ", item.fn, "("))
        else:
            raise TypeError(f"not a target term: {item!r}")
    return "".join(out)


def size(t: Term) -> int:
    n, stack = 0, [t]
    while stack:
        x = stack.pop()
        n += 1
        if isinstance(x, Lam):
            stack.append(x.body)
        elif isinstance(x, App):
            stack.extend((x.fn, x.arg))
    return n


# ----------------------------------------------------------------------
# Names
# ----------------------------------------------------------------------

def free_vars(t: Term) -> frozenset[str]:
    return t.fv


def all_names(t: Term) -> frozenset[str]:
    return t.names


def fresh(base: str, avoid: frozenset[str] | set[str]) -> str:
    """First of base_1, base_2, ... not in ``avoid`` (deterministic)."""
    i = 1
    while f"{base}_{i}" in avoid:
        i += 1
    return f"{base}_{i}"


# ----------------------------------------------------------------------
# Capture-avoiding substitution
# ----------------------------------------------------------------------

def subst(t: Term, x: str, v: Term) -> Term:
    """Return t[x := v]; t and v are left unchanged.

    Subterms in which x is not free are shared, not copied.  A binder that
    would capture a free variable of v is renamed to fresh(binder, avoid)
    where avoid = names(body) | FV(v) | {x}.
    """
    if x not in t.fv:
        return t
    if isinstance(t, Var):
        return v  # t.name == x, because x is free in t
    if isinstance(t, App):
        return App(subst(t.fn, x, v), subst(t.arg, x, v))
    assert isinstance(t, Lam)
    y, body = t.param, t.body
    # y != x here, since x is free in t.
    if y in v.fv:
        y2 = fresh(y, body.names | v.fv | {x})
        body = subst(body, y, Var(y2))
        y = y2
    return Lam(y, subst(body, x, v))


# ----------------------------------------------------------------------
# Alpha-equivalence and purity
# ----------------------------------------------------------------------

def alpha_equal(a: Term, b: Term) -> bool:
    """Compare up to renaming of bound variables (de Bruijn-style levels)."""
    stack = [(a, b, {}, {}, 0)]
    while stack:
        s, t, ms, mt, depth = stack.pop()
        if isinstance(s, Var) and isinstance(t, Var):
            ls, lt = ms.get(s.name), mt.get(t.name)
            if ls != lt or (ls is None and s.name != t.name):
                return False
        elif isinstance(s, Lam) and isinstance(t, Lam):
            ms2 = dict(ms); ms2[s.param] = depth
            mt2 = dict(mt); mt2[t.param] = depth
            stack.append((s.body, t.body, ms2, mt2, depth + 1))
        elif isinstance(s, App) and isinstance(t, App):
            stack.append((s.fn, t.fn, ms, mt, depth))
            stack.append((s.arg, t.arg, ms, mt, depth))
        else:
            return False
    return True


def is_pure(t: object) -> bool:
    """True iff every node is exactly Var, Lam or App with valid names."""
    stack = [t]
    while stack:
        x = stack.pop()
        if type(x) is Var:
            if not IDENT.match(x.name):
                return False
        elif type(x) is Lam:
            if not IDENT.match(x.param):
                return False
            stack.append(x.body)
        elif type(x) is App:
            stack.extend((x.fn, x.arg))
        else:
            return False
    return True
