"""Pretty printing and capture-avoiding substitution for the LAMBDA AST.

Both operations are visitors over the supplied ``lambda1_vp.py``: each
expression dispatches to the right method through ``accept``, and neither
operation evaluates anything. Requires Python 3.12 or later.

Entry points
    d0exp_pretty(expression) -> str
    d0exp_substitute(expression, variable, replacement) -> expression
    d0exp_alpha_equal(expression1, expression2) -> bool   (helper, used by tests)

Fresh-name policy (used when a binder must be renamed)
    The new name for binder ``b`` is ``b_1``, or ``b_2``, ``b_3``, ... : the
    first of these that is not already in the "used" set. The used set starts
    as every variable occurrence and every binder name of the expression and
    of the replacement, plus the substitution target. Each generated name is
    added to it, so no name is generated twice in one call. The set is built
    again for every call, so results are deterministic.
"""

from __future__ import annotations

import sys
from pathlib import Path

# The supplied implementation lives one directory above MySolution/.
_ASSIGN_DIR = str(Path(__file__).resolve().parent.parent)
if _ASSIGN_DIR not in sys.path:
    sys.path.insert(0, _ASSIGN_DIR)

from lambda1_vp import (  # noqa: E402
    D0Eapp, D0Ebtf, D0Efix, D0Eif0, D0Eint, D0Elam, D0Elet, D0Eop1, D0Eop2,
    D0Epair, D0Epfst, D0Epsnd, D0Evar,
    D0ExpVisitor, d0exp, d0exp_fvset, dvar,
)


########################################################################
# Task 1: pretty printing (result type: str)
########################################################################

class PrettyPrintVisitor(D0ExpVisitor[str]):
    """Render an expression in the single-line format of the assignment."""

    def visit_int(self, dexp: D0Eint) -> str:
        return str(dexp.arg1)

    def visit_btf(self, dexp: D0Ebtf) -> str:
        return "true" if dexp.arg1 else "false"

    def visit_var(self, dexp: D0Evar) -> str:
        return dexp.arg1

    def visit_op1(self, dexp: D0Eop1) -> str:
        return f"({dexp.name} {dexp.arg1.accept(self)})"

    def visit_op2(self, dexp: D0Eop2) -> str:
        return f"({dexp.arg1.accept(self)} {dexp.name} {dexp.arg2.accept(self)})"

    def visit_lam(self, dexp: D0Elam) -> str:
        return f"(lam {dexp.arg1}. {dexp.arg2.accept(self)})"

    def visit_fix(self, dexp: D0Efix) -> str:
        return f"(fix {dexp.arg1}({dexp.arg2}). {dexp.arg3.accept(self)})"

    def visit_app(self, dexp: D0Eapp) -> str:
        return f"({dexp.arg1.accept(self)} {dexp.arg2.accept(self)})"

    def visit_if0(self, dexp: D0Eif0) -> str:
        return (f"(if {dexp.arg1.accept(self)} then {dexp.arg2.accept(self)}"
                f" else {dexp.arg3.accept(self)})")

    def visit_let(self, dexp: D0Elet) -> str:
        return (f"(let {dexp.arg1} = {dexp.arg2.accept(self)}"
                f" in {dexp.arg3.accept(self)})")

    def visit_pair(self, dexp: D0Epair) -> str:
        return f"(pair {dexp.arg1.accept(self)} {dexp.arg2.accept(self)})"

    def visit_pfst(self, dexp: D0Epfst) -> str:
        return f"(fst {dexp.arg1.accept(self)})"

    def visit_psnd(self, dexp: D0Epsnd) -> str:
        return f"(snd {dexp.arg1.accept(self)})"


def d0exp_pretty(dexp: d0exp) -> str:
    """Return the pretty-printed form of an expression (never evaluates it)."""
    return dexp.accept(PrettyPrintVisitor())


########################################################################
# Helper visitor: every variable occurrence and binder name (result: set)
########################################################################

class NameCollectorVisitor(D0ExpVisitor[frozenset[dvar]]):
    """All names in an expression: free and bound occurrences and binders."""

    def visit_int(self, dexp: D0Eint) -> frozenset[dvar]:
        return frozenset()

    def visit_btf(self, dexp: D0Ebtf) -> frozenset[dvar]:
        return frozenset()

    def visit_var(self, dexp: D0Evar) -> frozenset[dvar]:
        return frozenset({dexp.arg1})

    def visit_op1(self, dexp: D0Eop1) -> frozenset[dvar]:
        return dexp.arg1.accept(self)

    def visit_op2(self, dexp: D0Eop2) -> frozenset[dvar]:
        return dexp.arg1.accept(self) | dexp.arg2.accept(self)

    def visit_lam(self, dexp: D0Elam) -> frozenset[dvar]:
        return frozenset({dexp.arg1}) | dexp.arg2.accept(self)

    def visit_fix(self, dexp: D0Efix) -> frozenset[dvar]:
        return frozenset({dexp.arg1, dexp.arg2}) | dexp.arg3.accept(self)

    def visit_app(self, dexp: D0Eapp) -> frozenset[dvar]:
        return dexp.arg1.accept(self) | dexp.arg2.accept(self)

    def visit_if0(self, dexp: D0Eif0) -> frozenset[dvar]:
        return (dexp.arg1.accept(self) | dexp.arg2.accept(self)
                | dexp.arg3.accept(self))

    def visit_let(self, dexp: D0Elet) -> frozenset[dvar]:
        return (frozenset({dexp.arg1}) | dexp.arg2.accept(self)
                | dexp.arg3.accept(self))

    def visit_pair(self, dexp: D0Epair) -> frozenset[dvar]:
        return dexp.arg1.accept(self) | dexp.arg2.accept(self)

    def visit_pfst(self, dexp: D0Epfst) -> frozenset[dvar]:
        return dexp.arg1.accept(self)

    def visit_psnd(self, dexp: D0Epsnd) -> frozenset[dvar]:
        return dexp.arg1.accept(self)


########################################################################
# Task 2: capture-avoiding substitution (result type: an expression)
########################################################################

class SubstitutionVisitor(D0ExpVisitor[d0exp]):
    """Compute ``e[variable := replacement]`` without evaluating ``e``.

    The context carried down the traversal is: the target ``variable``, the
    ``replacement`` with its free variables, and ``used``, one set of names
    shared by every visitor of the same call (it grows as fresh names are
    generated). Use ``SubstitutionVisitor.for_expression`` to build the
    initial ``used`` set from the whole expression.
    """

    def __init__(self, variable: dvar, replacement: d0exp,
                 used: set[dvar]) -> None:
        self.variable = variable
        self.replacement = replacement
        self.replacement_fvs = d0exp_fvset(replacement)
        self.used = used

    @classmethod
    def for_expression(cls, dexp: d0exp, variable: dvar,
                       replacement: d0exp) -> SubstitutionVisitor:
        used = set(dexp.accept(NameCollectorVisitor()))
        used |= replacement.accept(NameCollectorVisitor())
        used.add(variable)
        return cls(variable, replacement, used)

    # -- helpers ------------------------------------------------------

    def _fresh(self, base: dvar) -> dvar:
        k = 1
        while f"{base}_{k}" in self.used:
            k += 1
        name = f"{base}_{k}"
        self.used.add(name)
        return name

    def _occurs_free(self, dexp: d0exp) -> bool:
        """Can the target be replaced somewhere in this expression?"""
        return self.variable in d0exp_fvset(dexp)

    def _rename(self, body: d0exp, old: dvar, new: dvar) -> d0exp:
        """Alpha-renaming: ``body[old := new]`` for a fresh ``new``.

        ``new`` occurs nowhere in the input, so no binder can capture it and
        no further renaming happens. A binder named ``old`` inside ``body``
        shadows it, so only the occurrences bound by the outer binder change.
        """
        return body.accept(SubstitutionVisitor(old, D0Evar(new), self.used))

    # -- leaves -------------------------------------------------------

    def visit_int(self, dexp: D0Eint) -> d0exp:
        return D0Eint(dexp.arg1)

    def visit_btf(self, dexp: D0Ebtf) -> d0exp:
        return D0Ebtf(dexp.arg1)

    def visit_var(self, dexp: D0Evar) -> d0exp:
        if dexp.arg1 == self.variable:
            return self.replacement   # inserted as is, never visited again
        return dexp

    # -- forms without binders ----------------------------------------

    def visit_op1(self, dexp: D0Eop1) -> d0exp:
        return D0Eop1(dexp.name, dexp.arg1.accept(self))

    def visit_op2(self, dexp: D0Eop2) -> d0exp:
        return D0Eop2(dexp.name, dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_app(self, dexp: D0Eapp) -> d0exp:
        return D0Eapp(dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_if0(self, dexp: D0Eif0) -> d0exp:
        return D0Eif0(dexp.arg1.accept(self), dexp.arg2.accept(self),
                      dexp.arg3.accept(self))

    def visit_pair(self, dexp: D0Epair) -> d0exp:
        return D0Epair(dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_pfst(self, dexp: D0Epfst) -> d0exp:
        return D0Epfst(dexp.arg1.accept(self))

    def visit_psnd(self, dexp: D0Epsnd) -> d0exp:
        return D0Epsnd(dexp.arg1.accept(self))

    # -- binders ------------------------------------------------------

    def visit_lam(self, dexp: D0Elam) -> d0exp:
        x, body = dexp.arg1, dexp.arg2
        if x == self.variable or not self._occurs_free(body):
            return dexp                  # target is bound, or nothing to replace
        if x in self.replacement_fvs:    # the binder would capture the replacement
            new = self._fresh(x)
            body, x = self._rename(body, x, new), new
        return D0Elam(x, body.accept(self))

    def visit_fix(self, dexp: D0Efix) -> d0exp:
        f, x, body = dexp.arg1, dexp.arg2, dexp.arg3
        if self.variable in (f, x) or not self._occurs_free(body):
            return dexp
        # The parameter is renamed first: when f == x the parameter shadows the
        # function name, so every occurrence in the body belongs to the
        # parameter, and f is renamed afterwards without touching the body.
        if x in self.replacement_fvs:
            new = self._fresh(x)
            body, x = self._rename(body, x, new), new
        if f in self.replacement_fvs:
            new = self._fresh(f)
            body, f = self._rename(body, f, new), new
        return D0Efix(f, x, body.accept(self))

    def visit_let(self, dexp: D0Elet) -> d0exp:
        x, init, body = dexp.arg1, dexp.arg2, dexp.arg3
        new_init = init.accept(self)     # x is not bound in its own initializer
        if x == self.variable or not self._occurs_free(body):
            return D0Elet(x, new_init, body)
        if x in self.replacement_fvs:
            new = self._fresh(x)
            body, x = self._rename(body, x, new), new
        return D0Elet(x, new_init, body.accept(self))


def d0exp_substitute(dexp: d0exp, variable: dvar, replacement: d0exp) -> d0exp:
    """Return ``dexp[variable := replacement]``; neither input is modified."""
    return dexp.accept(
        SubstitutionVisitor.for_expression(dexp, variable, replacement))


########################################################################
# Helper: alpha-equivalence through a canonical form (result type: str)
########################################################################

class CanonicalFormVisitor(D0ExpVisitor[str]):
    """Print an expression with bound names replaced by binder depths.

    Two expressions are alpha-equivalent exactly when their canonical forms
    are equal. Free variables keep their names. A ``fix`` whose function name
    equals its parameter binds the name to the parameter, as the evaluator does.
    """

    def __init__(self, scope: dict[dvar, int] | None = None,
                 depth: int = 0) -> None:
        self.scope = scope or {}
        self.depth = depth

    def _extend(self, names_and_depths: list[tuple[dvar, int]],
                added: int) -> CanonicalFormVisitor:
        scope = dict(self.scope)
        for name, depth in names_and_depths:    # later entries shadow earlier
            scope[name] = depth
        return CanonicalFormVisitor(scope, self.depth + added)

    def visit_int(self, dexp: D0Eint) -> str:
        return str(dexp.arg1)

    def visit_btf(self, dexp: D0Ebtf) -> str:
        return "true" if dexp.arg1 else "false"

    def visit_var(self, dexp: D0Evar) -> str:
        if dexp.arg1 in self.scope:
            return f"#{self.scope[dexp.arg1]}"
        return dexp.arg1

    def visit_op1(self, dexp: D0Eop1) -> str:
        return f"({dexp.name} {dexp.arg1.accept(self)})"

    def visit_op2(self, dexp: D0Eop2) -> str:
        return f"({dexp.arg1.accept(self)} {dexp.name} {dexp.arg2.accept(self)})"

    def visit_lam(self, dexp: D0Elam) -> str:
        inner = self._extend([(dexp.arg1, self.depth)], 1)
        return f"(lam {dexp.arg2.accept(inner)})"

    def visit_fix(self, dexp: D0Efix) -> str:
        inner = self._extend([(dexp.arg1, self.depth),
                              (dexp.arg2, self.depth + 1)], 2)
        return f"(fix {dexp.arg3.accept(inner)})"

    def visit_app(self, dexp: D0Eapp) -> str:
        return f"({dexp.arg1.accept(self)} {dexp.arg2.accept(self)})"

    def visit_if0(self, dexp: D0Eif0) -> str:
        return (f"(if {dexp.arg1.accept(self)} then {dexp.arg2.accept(self)}"
                f" else {dexp.arg3.accept(self)})")

    def visit_let(self, dexp: D0Elet) -> str:
        inner = self._extend([(dexp.arg1, self.depth)], 1)
        return f"(let {dexp.arg2.accept(self)} in {dexp.arg3.accept(inner)})"

    def visit_pair(self, dexp: D0Epair) -> str:
        return f"(pair {dexp.arg1.accept(self)} {dexp.arg2.accept(self)})"

    def visit_pfst(self, dexp: D0Epfst) -> str:
        return f"(fst {dexp.arg1.accept(self)})"

    def visit_psnd(self, dexp: D0Epsnd) -> str:
        return f"(snd {dexp.arg1.accept(self)})"


def d0exp_alpha_equal(dexp1: d0exp, dexp2: d0exp) -> bool:
    """True when the two expressions differ only in the names of bound variables."""
    return (dexp1.accept(CanonicalFormVisitor())
            == dexp2.accept(CanonicalFormVisitor()))
