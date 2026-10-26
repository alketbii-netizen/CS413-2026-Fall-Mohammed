"""Compiler: extended LAMBDA source AST  ->  pure lambda term.

Entry point
    compile_expr(e: source AST) -> target Term     (raises CompileError)

Compilation is a D0ExpVisitor: each visit method translates the
subexpressions and combines their translations; nothing is evaluated and
this module does not import the evaluator.  The source AST is only read.

Fresh-name policy
    The only binders the compiler places around translated code are the
    thunk parameters of delayed branches (if / and / or).  For a thunk
    around translated term T the parameter is fresh("_k", all_names(T)),
    i.e. the first of _k_1, _k_2, ... that does not occur anywhere in T
    (free, bound or as a binder).  It therefore cannot capture any source
    variable, and the choice is deterministic.  Library combinators are
    closed and never surround translated code, so their internal names
    (s, z, t, f, ...) do not restrict source programs.
"""

from __future__ import annotations

from source_ast import (
    D0Eapp, D0Ebtf, D0Efix, D0Eif0, D0Eint, D0Elam, D0Elet, D0Eop1, D0Eop2,
    D0Epair, D0Epfst, D0Epsnd, D0Evar, D0ExpVisitor,
)
from target import App, Lam, Term, Var, all_names, fresh
import church as enc


class CompileError(ValueError):
    """Unsupported literal or operator in the source program."""


def thunk(body: Term) -> Term:
    """lam k. body, with k fresh for body."""
    return Lam(fresh("_k", all_names(body)), body)


def delayed_choice(sel: Term, on_true: Term, on_false: Term) -> Term:
    """(sel (lam u. on_true) (lam v. on_false)) I"""
    return App(App(App(sel, thunk(on_true)), thunk(on_false)), enc.I())


class CompileVisitor(D0ExpVisitor[Term]):

    def visit_int(self, e: D0Eint) -> Term:
        n = e.arg1
        if type(n) is not int or n < 0:
            raise CompileError(f"unsupported literal {n!r}: only natural numbers (n >= 0) are allowed")
        return enc.NUM(n)

    def visit_btf(self, e: D0Ebtf) -> Term:
        return enc.BOOL(bool(e.arg1))

    def visit_var(self, e: D0Evar) -> Term:
        return Var(e.arg1)

    def visit_lam(self, e: D0Elam) -> Term:
        return Lam(e.arg1, e.arg2.accept(self))

    def visit_app(self, e: D0Eapp) -> Term:
        return App(e.arg1.accept(self), e.arg2.accept(self))

    def visit_let(self, e: D0Elet) -> Term:
        # (lam x. C[body]) C[init]   -- x is not in scope in init
        init = e.arg2.accept(self)
        body = e.arg3.accept(self)
        return App(Lam(e.arg1, body), init)

    def visit_if0(self, e: D0Eif0) -> Term:
        c = e.arg1.accept(self)
        t = e.arg2.accept(self)
        f = e.arg3.accept(self)
        return delayed_choice(c, t, f)

    def visit_fix(self, e: D0Efix) -> Term:
        # Z (lam f. lam x. C[body]); if f == x the inner binder shadows.
        return App(enc.Z(), Lam(e.arg1, Lam(e.arg2, e.arg3.accept(self))))

    def visit_pair(self, e: D0Epair) -> Term:
        return App(App(enc.PAIR(), e.arg1.accept(self)), e.arg2.accept(self))

    def visit_pfst(self, e: D0Epfst) -> Term:
        return App(enc.FST(), e.arg1.accept(self))

    def visit_psnd(self, e: D0Epsnd) -> Term:
        return App(enc.SND(), e.arg1.accept(self))

    def visit_op1(self, e: D0Eop1) -> Term:
        if e.name != "not":
            raise CompileError(f"unsupported unary operator {e.name!r} (only 'not')")
        return App(enc.NOT(), e.arg1.accept(self))

    def visit_op2(self, e: D0Eop2) -> Term:
        op = e.name
        if op not in enc.STRICT_OP2 and op not in ("and", "or"):
            raise CompileError(f"unsupported binary operator {op!r}")
        left = e.arg1.accept(self)
        right = e.arg2.accept(self)
        if op == "and":   # if left then right else false
            return delayed_choice(left, right, enc.FALSE())
        if op == "or":    # if left then true else right
            return delayed_choice(left, enc.TRUE(), right)
        return App(App(enc.STRICT_OP2[op](), left), right)


def compile_expr(e) -> Term:
    """Translate a source AST to a pure target term (does not evaluate)."""
    return e.accept(CompileVisitor())
