"""
d0exp_fvset — free-variable analysis for the LAMBDA language.

Not defined in the supplied lambda1.py, so it is implemented here as its
own module and imported by the backend adapter for the Lint operation
(Assign04, Task 2: "Parse the input into a d0exp and compute its free
variables using d0exp_fvset").

Scoping rules (from Assign04.md):
  - D0Elam(param, body):        binds `param` in `body`.
  - D0Efix(fname, param, body): binds both `fname` and `param` in `body`
                                 (the function may call itself by name).
  - D0Elet(name, init, body):   binds `name` only in `body`, NOT in
                                 `init` (the initializer is evaluated
                                 before the binding exists — this matches
                                 lambda1.py's f0_D0Elet, which evaluates
                                 dexp.arg2 in the *old* environment before
                                 extending it for dexp.arg3).
  - Every other form has no variable of its own; it simply unions the
    free variables of its subexpressions.
  - An unused binding is not an error under this assignment's lint rule
    (d0exp_fvset only ever *removes* a bound name from the free set; it
    never flags a binder whose name does not occur free in its scope).

d0exp_fvset does not evaluate the expression; it only inspects its shape.
"""

from __future__ import annotations

from lambdaweb.lambda1 import (
    d0exp,
    D0Eint, D0Ebtf, D0Eop1, D0Eop2, D0Evar,
    D0Elam, D0Efix, D0Eapp, D0Eif0, D0Elet,
    D0Epair, D0Epfst, D0Epsnd,
)


def d0exp_fvset(dexp: d0exp) -> frozenset[str]:
    """Return the set of free (unbound) variable names occurring in dexp."""
    if isinstance(dexp, D0Eint):
        return frozenset()
    elif isinstance(dexp, D0Ebtf):
        return frozenset()
    elif isinstance(dexp, D0Evar):
        return frozenset({dexp.arg1})
    elif isinstance(dexp, D0Eop1):
        return d0exp_fvset(dexp.arg1)
    elif isinstance(dexp, D0Eop2):
        return d0exp_fvset(dexp.arg1) | d0exp_fvset(dexp.arg2)
    elif isinstance(dexp, D0Elam):
        # lam x. body(x): x is bound in body.
        return d0exp_fvset(dexp.arg2) - {dexp.arg1}
    elif isinstance(dexp, D0Efix):
        # fix f(x). body(f, x): both f and x are bound in body.
        return d0exp_fvset(dexp.arg3) - {dexp.arg1, dexp.arg2}
    elif isinstance(dexp, D0Eapp):
        return d0exp_fvset(dexp.arg1) | d0exp_fvset(dexp.arg2)
    elif isinstance(dexp, D0Eif0):
        return (
            d0exp_fvset(dexp.arg1)
            | d0exp_fvset(dexp.arg2)
            | d0exp_fvset(dexp.arg3)
        )
    elif isinstance(dexp, D0Elet):
        # let x = init in body: x is bound in body only, NOT in init.
        return d0exp_fvset(dexp.arg2) | (d0exp_fvset(dexp.arg3) - {dexp.arg1})
    elif isinstance(dexp, D0Epair):
        return d0exp_fvset(dexp.arg1) | d0exp_fvset(dexp.arg2)
    elif isinstance(dexp, D0Epfst):
        return d0exp_fvset(dexp.arg1)
    elif isinstance(dexp, D0Epsnd):
        return d0exp_fvset(dexp.arg1)
    else:
        raise TypeError(f"d0exp_fvset({dexp!r}): unrecognized d0exp form")
