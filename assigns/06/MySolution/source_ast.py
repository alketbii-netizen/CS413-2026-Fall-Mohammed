"""Access to the supplied source AST (Assignment 5's lambda1_vp.py).

The supplied file lives in ``assigns/05/`` and is imported unchanged.  This
module only puts that directory on ``sys.path`` and re-exports the names the
rest of the project uses, plus a few small constructor helpers for writing
examples and tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ASSIGN05 = Path(__file__).resolve().parent.parent.parent / "05"
if str(_ASSIGN05) not in sys.path:
    sys.path.insert(0, str(_ASSIGN05))

from lambda1_vp import (  # noqa: E402,F401
    D0E000, D0Eapp, D0Ebtf, D0Efix, D0Eif0, D0Eint, D0Elam, D0Elet, D0Eop1,
    D0Eop2, D0Epair, D0Epfst, D0Epsnd, D0Evar, D0ExpVisitor,
    D0V000, D0Vbtf, D0Vfix, D0Vint, D0Vlam, D0Vpair,
    ENVcns, ENVnil, d0exp_fvset,
)

# Small helpers so examples read closer to the explanatory notation.
def num(n: int) -> D0Eint: return D0Eint(n)
def boo(b: bool) -> D0Ebtf: return D0Ebtf(b)
def var(x: str) -> D0Evar: return D0Evar(x)
def lam(x: str, body) -> D0Elam: return D0Elam(x, body)
def app(f, a) -> D0Eapp: return D0Eapp(f, a)
def op2(name: str, a, b) -> D0Eop2: return D0Eop2(name, a, b)
def op1(name: str, a) -> D0Eop1: return D0Eop1(name, a)
def if_(c, t, f) -> D0Eif0: return D0Eif0(c, t, f)
def let(x: str, init, body) -> D0Elet: return D0Elet(x, init, body)
def pair(a, b) -> D0Epair: return D0Epair(a, b)
def fst(e) -> D0Epfst: return D0Epfst(e)
def snd(e) -> D0Epsnd: return D0Epsnd(e)
def fix(f: str, x: str, body) -> D0Efix: return D0Efix(f, x, body)

# LOOP = (fix loop(x). loop x) 0
def LOOP():
    return app(fix("loop", "x", app(var("loop"), var("x"))), num(0))


def show_source(e) -> str:
    """Render a source AST in the explanatory notation (for the demo)."""
    match e:
        case D0Eint(arg1=n): return str(n)
        case D0Ebtf(arg1=b): return "true" if b else "false"
        case D0Evar(arg1=x): return x
        case D0Elam(arg1=x, arg2=b): return f"(lam {x}. {show_source(b)})"
        case D0Efix(arg1=f, arg2=x, arg3=b): return f"(fix {f}({x}). {show_source(b)})"
        case D0Eapp(arg1=a, arg2=b): return f"({show_source(a)} {show_source(b)})"
        case D0Eop1(name=o, arg1=a): return f"({o} {show_source(a)})"
        case D0Eop2(name=o, arg1=a, arg2=b): return f"({show_source(a)} {o} {show_source(b)})"
        case D0Eif0(arg1=c, arg2=t, arg3=f):
            return f"(if {show_source(c)} then {show_source(t)} else {show_source(f)})"
        case D0Elet(arg1=x, arg2=i, arg3=b):
            return f"(let {x} = {show_source(i)} in {show_source(b)})"
        case D0Epair(arg1=a, arg2=b): return f"(pair {show_source(a)} {show_source(b)})"
        case D0Epfst(arg1=a): return f"(fst {show_source(a)})"
        case D0Epsnd(arg1=a): return f"(snd {show_source(a)})"
    raise TypeError(f"not a source expression: {e!r}")
