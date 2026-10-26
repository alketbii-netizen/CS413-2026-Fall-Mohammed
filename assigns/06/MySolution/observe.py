"""Bounded observers (decoders) for compiled results.

All observation work is pure target reduction by the shared evaluator; Python
only inspects the FINAL shape of the observation output.

Natural numbers
    context:  v STEP BASE
        STEP = lam tail. lam c. lam z. c tail
        BASE = lam c. lam z. z
    Under call-by-value every STEP receives an already-evaluated tail, so a
    Church numeral n yields the finite spine
        lam c. lam z. c (lam c. lam z. c ( ... (lam c. lam z. z)))
    with n nodes of the form  lam c. lam z. c TAIL  (c != z, c bound by
    the outer binder) ending in  lam c. lam z. z.  The host counts the nodes,
    up to alpha-renaming.  Any other shape is "malformed".

Booleans
    context:  v MT MF  with markers MT = lam m1. lam m2. m1 and
    MF = lam m1. lam m2. lam m3. m3 (distinct closed values).
    The output must be alpha-equal to MT (-> True) or MF (-> False).

Pairs
    evaluate the pair to a value p, then evaluate (FST p) and (SND p) under
    the observation budget and observe each component with its expected
    kind, recursively.

Kinds:  "nat" | "bool" | ("pair", kind1, kind2)

Every observer returns ObsResult(status, value, steps) with status
"ok" | "exhausted" | "malformed"; steps counts only observation steps.
"""

from __future__ import annotations

from dataclasses import dataclass

from church import FST, SND, apps, lams
from evaluator import evaluate
from target import App, Lam, Term, Var, alpha_equal


def STEP() -> Term:
    return lams("tail c z", App(Var("c"), Var("tail")))


def BASE() -> Term:
    return lams("c z", Var("z"))


def MARK_T() -> Term:
    return lams("m1 m2", Var("m1"))


def MARK_F() -> Term:
    return lams("m1 m2 m3", Var("m3"))


@dataclass(frozen=True)
class ObsResult:
    status: str                 # "ok" | "exhausted" | "malformed"
    value: object               # int / bool / tuple, or None
    steps: int                  # observation beta-value steps
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def count_spine(t: Term) -> int | None:
    """Count STEP nodes in a final observation spine; None if malformed."""
    n = 0
    while True:
        if not (isinstance(t, Lam) and isinstance(t.body, Lam)):
            return None
        c, z, body = t.param, t.body.param, t.body.body
        if c == z:
            return None
        if isinstance(body, Var) and body.name == z:
            return n
        if (isinstance(body, App) and isinstance(body.fn, Var)
                and body.fn.name == c and isinstance(body.arg, Lam)):
            n += 1
            t = body.arg
            continue
        return None


def observe_nat(v: Term, budget: int) -> ObsResult:
    r = evaluate(apps(v, STEP(), BASE()), budget)
    if not r.ok:
        return ObsResult("exhausted", None, r.steps, "observation budget exhausted")
    n = count_spine(r.value)
    if n is None:
        return ObsResult("malformed", None, r.steps, "output is not a STEP/BASE spine")
    return ObsResult("ok", n, r.steps)


def observe_bool(v: Term, budget: int) -> ObsResult:
    r = evaluate(apps(v, MARK_T(), MARK_F()), budget)
    if not r.ok:
        return ObsResult("exhausted", None, r.steps, "observation budget exhausted")
    if alpha_equal(r.value, MARK_T()):
        return ObsResult("ok", True, r.steps)
    if alpha_equal(r.value, MARK_F()):
        return ObsResult("ok", False, r.steps)
    return ObsResult("malformed", None, r.steps, "output is neither boolean marker")


def observe(v: Term, kind, budget: int) -> ObsResult:
    """Observe an already-evaluated value v with the expected kind.

    ``budget`` bounds the TOTAL observation steps (projections included).
    """
    if kind == "nat":
        return observe_nat(v, budget)
    if kind == "bool":
        return observe_bool(v, budget)
    if isinstance(kind, tuple) and kind[0] == "pair":
        used = 0
        parts = []
        for proj, k in ((FST, kind[1]), (SND, kind[2])):
            r = evaluate(App(proj(), v), budget - used)
            used += r.steps
            if not r.ok:
                return ObsResult("exhausted", None, used, "projection exhausted the budget")
            o = observe(r.value, k, budget - used)
            used += o.steps
            if not o.ok:
                return ObsResult(o.status, None, used, o.detail)
            parts.append(o.value)
        return ObsResult("ok", tuple(parts), used)
    raise ValueError(f"unknown result kind {kind!r}")


@dataclass(frozen=True)
class RunResult:
    exec_status: str            # "value" | "exhausted"
    exec_steps: int
    obs: ObsResult | None       # None when execution exhausted
    term: Term                  # compiled term


def run_compiled(term: Term, kind, exec_budget: int, obs_budget: int) -> RunResult:
    """Execute a compiled term, then observe it (separate budgets/counts)."""
    r = evaluate(term, exec_budget)
    if not r.ok:
        return RunResult("exhausted", r.steps, None, term)
    return RunResult("value", r.steps, observe(r.value, kind, obs_budget), term)
