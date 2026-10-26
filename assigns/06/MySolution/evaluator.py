"""The shared evaluator: one evaluator for source ASTs and target terms.

Entry points
    evaluate(e, budget=None)  -> EvalResult
        e may be a source AST (D0E...) or a target Term.

    Target terms: weak, left-to-right call-by-value beta-value reduction.
        Values are lambda abstractions.  (lam x. b) v --> b[x := v] counts as
        one step; alpha-renaming inside substitution does not.  No reduction
        under lambdas, no eta.  ``budget`` (required, >= 0) bounds the number
        of beta-value steps.  Execution is restricted to CLOSED target terms:
        an open term raises OpenTermError before any step is taken.

    Source ASTs: the same var / lam / app cases plus the source-only
        constructors, with left-to-right call-by-value source rules
        (natural numbers, truncated subtraction, short-circuit and/or,
        boolean if).  Environment based; not step-bounded (only required
        for terminating examples).  Errors raise SourceError.

Result
    EvalResult(status, value, steps)
        status "value"     -> value is a target Lam or a source D0V value
        status "exhausted" -> another step was needed but the budget was spent

This module never imports the compiler and never applies a source operation
to a target term; the target path only knows Var / Lam / App.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from source_ast import (
    D0E000, D0Eapp, D0Ebtf, D0Efix, D0Eif0, D0Eint, D0Elam, D0Elet, D0Eop1,
    D0Eop2, D0Epair, D0Epfst, D0Epsnd, D0Evar, D0ExpVisitor,
    D0V000, D0Vbtf, D0Vfix, D0Vint, D0Vlam, D0Vpair, ENVcns, ENVnil,
)
from target import App, Lam, Term, Var, subst

sys.setrecursionlimit(max(sys.getrecursionlimit(), 200_000))


@dataclass(frozen=True)
class EvalResult:
    status: str          # "value" or "exhausted"
    value: object        # Lam / D0V value, or None when exhausted
    steps: int           # beta-value steps performed (0 for source path)

    @property
    def ok(self) -> bool:
        return self.status == "value"


class OpenTermError(ValueError):
    """Target execution is restricted to closed terms."""


class SourceError(RuntimeError):
    """Runtime error in the source language (unbound variable, bad operand...)."""


class _Exhausted(Exception):
    pass


class Evaluator(D0ExpVisitor[object]):
    """One evaluator, two syntaxes.

    ``run_target`` handles Var / Lam / App terms with a step counter;
    the visit_* methods handle source ASTs in an environment ``env``.
    """

    def __init__(self, budget: int | None = None, env=ENVnil()) -> None:
        self.budget = budget
        self.steps = 0
        self.env = env

    # ------------------------------------------------------------------
    # Target path: weak left-to-right call-by-value over Var / Lam / App
    # ------------------------------------------------------------------
    def run_target(self, t: Term) -> Term:
        while True:
            if isinstance(t, Lam):          # a value: done, no step
                return t
            if isinstance(t, Var):          # cannot happen for closed terms
                raise OpenTermError(f"free variable {t.name!r} reached")
            assert isinstance(t, App)
            fn = self.run_target(t.fn)      # 1. function first
            arg = self.run_target(t.arg)    # 2. then argument
            if self.budget is not None and self.steps >= self.budget:
                raise _Exhausted()          # 3. a beta step is needed
            self.steps += 1
            t = subst(fn.body, fn.param, arg)   # (lam x. b) v --> b[x:=v]

    # ------------------------------------------------------------------
    # Source path: same var / lam / app cases + source-only constructors
    # ------------------------------------------------------------------
    def _with(self, env) -> "Evaluator":
        child = Evaluator(self.budget, env)
        return child

    def visit_var(self, e: D0Evar):
        env = self.env
        while isinstance(env, ENVcns):
            if env.arg1 == e.arg1:
                return env.arg2
            env = env.arg3
        raise SourceError(f"unbound variable {e.arg1!r}")

    def visit_lam(self, e: D0Elam):
        return D0Vlam(self.env, e)

    def visit_fix(self, e: D0Efix):
        return D0Vfix(self.env, e)

    def visit_app(self, e: D0Eapp):
        f = e.arg1.accept(self)
        a = e.arg2.accept(self)
        if isinstance(f, D0Vlam):
            return f.arg2.arg2.accept(self._with(ENVcns(f.arg2.arg1, a, f.arg1)))
        if isinstance(f, D0Vfix):
            fx = f.arg2
            env = ENVcns(fx.arg1, f, f.arg1)       # function name ...
            env = ENVcns(fx.arg2, a, env)          # ... shadowed by parameter
            return fx.arg3.accept(self._with(env))
        raise SourceError(f"application of a non-function: {f}")

    def visit_int(self, e: D0Eint):
        if e.arg1 < 0:
            raise SourceError(f"negative literal {e.arg1}")
        return D0Vint(e.arg1)

    def visit_btf(self, e: D0Ebtf):
        return D0Vbtf(bool(e.arg1))

    def visit_let(self, e: D0Elet):
        v = e.arg2.accept(self)                     # initializer first
        return e.arg3.accept(self._with(ENVcns(e.arg1, v, self.env)))

    def visit_if0(self, e: D0Eif0):
        c = self._bool(e.arg1.accept(self))
        return (e.arg2 if c else e.arg3).accept(self)

    def visit_pair(self, e: D0Epair):
        a = e.arg1.accept(self)
        b = e.arg2.accept(self)
        return D0Vpair(a, b)

    def visit_pfst(self, e: D0Epfst):
        p = e.arg1.accept(self)
        if not isinstance(p, D0Vpair):
            raise SourceError(f"fst of a non-pair: {p}")
        return p.arg1

    def visit_psnd(self, e: D0Epsnd):
        p = e.arg1.accept(self)
        if not isinstance(p, D0Vpair):
            raise SourceError(f"snd of a non-pair: {p}")
        return p.arg2

    def visit_op1(self, e: D0Eop1):
        if e.name != "not":
            raise SourceError(f"unsupported unary operator {e.name!r}")
        return D0Vbtf(not self._bool(e.arg1.accept(self)))

    def visit_op2(self, e: D0Eop2):
        op = e.name
        if op == "and":
            return D0Vbtf(self._bool(e.arg1.accept(self)) and self._bool(e.arg2.accept(self)))
        if op == "or":
            return D0Vbtf(self._bool(e.arg1.accept(self)) or self._bool(e.arg2.accept(self)))
        m = self._nat(e.arg1.accept(self))
        n = self._nat(e.arg2.accept(self))
        match op:
            case "+": return D0Vint(m + n)
            case "-": return D0Vint(max(m - n, 0))
            case "*": return D0Vint(m * n)
            case "<": return D0Vbtf(m < n)
            case "<=": return D0Vbtf(m <= n)
            case ">": return D0Vbtf(m > n)
            case ">=": return D0Vbtf(m >= n)
            case "==": return D0Vbtf(m == n)
            case "!=": return D0Vbtf(m != n)
        raise SourceError(f"unsupported binary operator {op!r}")

    @staticmethod
    def _bool(v) -> bool:
        if not isinstance(v, D0Vbtf):
            raise SourceError(f"boolean expected: {v}")
        return v.arg1

    @staticmethod
    def _nat(v) -> int:
        if not isinstance(v, D0Vint):
            raise SourceError(f"natural number expected: {v}")
        return v.arg1


def evaluate(e, budget: int | None = None) -> EvalResult:
    """Evaluate a target term (bounded) or a source AST (unbounded)."""
    if isinstance(e, Term):
        if budget is None or budget < 0:
            raise ValueError("target evaluation needs a nonnegative step budget")
        if e.fv:
            raise OpenTermError(f"target execution requires a closed term; free: {sorted(e.fv)}")
        ev = Evaluator(budget)
        try:
            v = ev.run_target(e)
        except _Exhausted:
            return EvalResult("exhausted", None, ev.steps)
        return EvalResult("value", v, ev.steps)
    if isinstance(e, D0E000):
        return EvalResult("value", e.accept(Evaluator()), 0)
    raise TypeError(f"neither a source AST nor a target term: {e!r}")


def source_value_to_python(v):
    """D0Vint -> int, D0Vbtf -> bool, D0Vpair -> tuple (for comparisons)."""
    if isinstance(v, D0Vbtf):
        return v.arg1
    if isinstance(v, D0Vint):
        return v.arg1
    if isinstance(v, D0Vpair):
        return (source_value_to_python(v.arg1), source_value_to_python(v.arg2))
    return v
