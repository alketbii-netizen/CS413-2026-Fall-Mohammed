########################################################################
########################################################################
# playing with lambda calculus
########################################################################
########################################################################
#
type nint = int
type sint = int
type strn = str
type tvar = strn
#
########################################################################
from abc import ABC
from enum import Enum
from dataclasses import dataclass
from typing import \
    Generic, TypeVar, Callable
########################################################################
@dataclass
class T0M000(ABC):
    ctag = "T0M000"
    pass
type t0erm = T0M000
########################################################################
@dataclass
class T0Mvar(T0M000):
    arg1: tvar
    ctag = "T0Mvar"
########################################################################
@dataclass
class T0Mlam(T0M000):
    arg1: tvar
    arg2: t0erm
    ctag = "T0Mlam"
@dataclass
class T0Mfix(T0M000):
    arg1: tvar
    arg2: tvar
    arg3: t0erm
    ctag = "T0Mfix"
########################################################################
@dataclass
class T0Mapp(T0M000):
    arg1: t0erm
    arg2: t0erm
    ctag = "T0Mapp"
########################################################################
@dataclass
class T0Mint(T0M000):
    arg1: sint
    ctag = "T0Mint"
@dataclass
class T0Mbtf(T0M000):
    arg1: bool
    ctag = "T0Mbtf"
@dataclass
class T0Mstr(T0M000):
    arg1: strn
    ctag = "T0Mstr"
########################################################################
@dataclass
class T0Mop1(T0M000):
    arg1: strn
    arg2: t0erm
    ctag = "T0Mop1"
@dataclass
class T0Mop2(T0M000):
    arg1: strn
    arg2: t0erm
    arg3: t0erm
    ctag = "T0Mop2"
########################################################################
@dataclass
class T0Mif0(T0M000):
    arg1: t0erm
    arg2: t0erm
    arg3: t0erm
    ctag = "T0Mif0"
########################################################################
########################################################################
@dataclass
class T0Mpair(T0M000): # pair
    arg1: t0erm
    arg2: t0erm
    ctag = "T0Mpair"
@dataclass
class T0Mpfst(T0M000): # fst projection
    arg1: t0erm
    ctag = "T0Mpfst"
@dataclass
class T0Mpsnd(T0M000): # 2nd projection
    arg1: t0erm
    ctag = "T0Mpsnd"
########################################################################
########################################################################
def t0erm_size(term: t0erm) -> sint:
    if False:
        return 0
    elif isinstance(term, T0Mint):
        return 1
    elif isinstance(term, T0Mbtf):
        return 1
    elif isinstance(term, T0Mstr):
        return 1
    elif isinstance(term, T0Mvar):
        return 1
    elif isinstance(term, T0Mlam):
        return 1 + t0erm_size(term.arg2)
    elif isinstance(term, T0Mfix):
        return 1 + t0erm_size(term.arg3)
    elif isinstance(term, T0Mapp):
        return 1 + t0erm_size(term.arg1) + t0erm_size(term.arg2)
    elif isinstance(term, T0Mop1):
        return 1 + t0erm_size(term.arg2)
    elif isinstance(term, T0Mop2):
        return 1 + t0erm_size(term.arg2) + t0erm_size(term.arg3)
    elif isinstance(term, T0Mif0):
        return 1 + t0erm_size(term.arg1) + t0erm_size(term.arg2) + t0erm_size(term.arg3)
    elif isinstance(term, T0Mpair):
        return 1 + t0erm_size(term.arg1) + t0erm_size(term.arg2)
    elif isinstance(term, (T0Mpfst, T0Mpsnd)):
        return 1 + t0erm_size(term.arg1)
    else:
        raise TypeError(f"t0erm_size({term})")
########################################################################
X = TypeVar("X")
type fvset = frozenset[strn]
########################################################################
def t0erm_fvset(term: t0erm) -> fvset:
    # Terms are never mutated, so the free-variable set of each node is
    # computed once and remembered on the node (not a dataclass field, so
    # equality and repr are unaffected). t0erm_subst0 uses it to skip
    # subterms that do not mention the variable being replaced.
    cached = term.__dict__.get("_fv")
    if cached is None:
        cached = _t0erm_fvset_compute(term)
        term.__dict__["_fv"] = cached
    return cached
########################################################################
def _t0erm_fvset_compute(term: t0erm) -> fvset:
    if False:
        return frozenset()
    elif isinstance(term, T0Mint):
        return frozenset()
    elif isinstance(term, T0Mbtf):
        return frozenset()
    elif isinstance(term, T0Mstr):
        return frozenset()
    elif isinstance(term, T0Mvar):
        return frozenset([term.arg1])
    elif isinstance(term, T0Mlam):
        return t0erm_fvset(term.arg2) - {term.arg1}
    elif isinstance(term, T0Mfix):
        return t0erm_fvset(term.arg3) - {term.arg1, term.arg2}
    elif isinstance(term, T0Mapp):
        return (t0erm_fvset(term.arg1) | t0erm_fvset(term.arg2))
    elif isinstance(term, T0Mop1):
        return t0erm_fvset(term.arg2)
    elif isinstance(term, T0Mop2):
        return (t0erm_fvset(term.arg2) | t0erm_fvset(term.arg3))
    elif isinstance(term, T0Mif0):
        return (t0erm_fvset(term.arg1) | t0erm_fvset(term.arg2) | t0erm_fvset(term.arg3))
    elif isinstance(term, T0Mpair):
        # A pair binds nothing: free variables of both components.
        return (t0erm_fvset(term.arg1) | t0erm_fvset(term.arg2))
    elif isinstance(term, (T0Mpfst, T0Mpsnd)):
        # A projection binds nothing: free variables of its operand.
        return t0erm_fvset(term.arg1)
    else:
        raise TypeError(f"t0erm_fvset({term})")
########################################################################
#
# HX-2026-08-25:
# [tsub] is assumed to be closed;
# therefore, no capturing is possible!
#
def t0erm_subst0\
(term: t0erm, x0: tvar, tsub: t0erm) -> t0erm:
    def subst0(term: t0erm) -> t0erm:
        if False:
            return None
        elif x0 not in t0erm_fvset(term):
            # Nothing to replace in this subterm (the result would be an
            # equal term), so reuse it as is.
            return term
        elif isinstance(term, T0Mint):
            return term
        elif isinstance(term, T0Mbtf):
            return term
        elif isinstance(term, T0Mstr):
            return term
        elif isinstance(term, T0Mvar):
            return tsub if x0 == term.arg1 else term
        elif isinstance(term, T0Mlam):
            x1 = term.arg1
            if x0 == x1:
                return term
            else:
                return T0Mlam(x1, subst0(term.arg2))
        elif isinstance(term, T0Mfix):
            f0 = term.arg1
            x1 = term.arg2
            if x0 == f0:
                return term
            elif x0 == x1:
                return term
            else:
                return T0Mfix(f0, x1, subst0(term.arg3))
        elif isinstance(term, T0Mapp):
            return T0Mapp(subst0(term.arg1), subst0(term.arg2))
        elif isinstance(term, T0Mop1):
            return T0Mop1(term.arg1, subst0(term.arg2))
        elif isinstance(term, T0Mop2):
            return T0Mop2(term.arg1, subst0(term.arg2), subst0(term.arg3))
        elif isinstance(term, T0Mif0):
            return T0Mif0(subst0(term.arg1), subst0(term.arg2), subst0(term.arg3))
        elif isinstance(term, T0Mpair):
            return T0Mpair(subst0(term.arg1), subst0(term.arg2))
        elif isinstance(term, T0Mpfst):
            return T0Mpfst(subst0(term.arg1))
        elif isinstance(term, T0Mpsnd):
            return T0Mpsnd(subst0(term.arg1))
        else:
            raise TypeError(f"subst0({term})")
    return subst0(term)
#
########################################################################
########################################################################
#
def t0erm_cbv_evaluate0(term: t0erm) -> t0erm:
    # Tail calls (the body of an application and the selected branch of an
    # [if0]) are evaluated by looping rather than by Python recursion, so
    # a long tail-recursive LAMBDA0 program does not need a Python stack
    # frame per call. Values, evaluation order, and errors are unchanged.
    while True:
        if False:
            return None
        elif isinstance(term, T0Mint): return term
        elif isinstance(term, T0Mbtf): return term
        elif isinstance(term, T0Mstr): return term
        elif isinstance(term, T0Mlam): return term
        elif isinstance(term, T0Mfix): return term
        elif isinstance(term, T0Mapp):
            t1 = t0erm_cbv_evaluate0(term.arg1)
            t2 = t0erm_cbv_evaluate0(term.arg2)
            if isinstance(t1, T0Mlam):
                term = t0erm_subst0(t1.arg2, t1.arg1, t2)
                continue  # tail position: loop instead of recursing
            elif isinstance(t1, T0Mfix):
                # Substitute the argument, then bind the recursive name to t1.
                term = t0erm_subst0(t0erm_subst0(t1.arg3, t1.arg2, t2), t1.arg1, t1)
                continue  # tail position
            else:
                raise TypeError(f"t0erm_cbv_evaluate0: application expects a lam/fix ({t1})")
        elif isinstance(term, T0Mif0):
            t1 = t0erm_cbv_evaluate0(term.arg1)
            if isinstance(t1, T0Mbtf):
                if t1.arg1:
                    term = term.arg2
                else:
                    term = term.arg3
                continue  # tail position: the selected branch
            else:
                raise TypeError(f"t0erm_cbv_evaluate0: condition expects a boolean ({t1})")
        elif isinstance(term, T0Mop1):
            if term.arg1 in ("+", "-"):
                t1 = t0erm_cbv_evaluate0(term.arg2)
                if isinstance(t1, T0Mint):
                    if term.arg1 == "+":
                        return T0Mint(t1.arg1)
                    else:
                        return T0Mint(-(t1.arg1))
                else:
                    raise TypeError(f"t0erm_cbv_evaluate0: {term.arg1} expects integers ({t1})")
            else:
                raise TypeError(f"t0erm_cbv_evaluate0({term})")
        elif isinstance(term, T0Mop2):
            if term.arg1 in ("+", "-", "*", "/", "%"):
                t1 = t0erm_cbv_evaluate0(term.arg2)
                t2 = t0erm_cbv_evaluate0(term.arg3)
                if isinstance(t1, T0Mint) and isinstance(t2, T0Mint):
                    if term.arg1 == "+":
                        return T0Mint(t1.arg1 + t2.arg1)
                    elif term.arg1 == "-":
                        return T0Mint(t1.arg1 - t2.arg1)
                    elif term.arg1 == "*":
                        return T0Mint(t1.arg1 * t2.arg1)
                    elif term.arg1 == "%":
                        return T0Mint(t1.arg1 % t2.arg1)
                    else: # term.arg1 == "/"
                        # Integer division rounds down, as in Python.
                        return T0Mint(t1.arg1 // t2.arg1)
                else:
                    raise TypeError(f"t0erm_cbv_evaluate0: {term.arg1} expects integers ({t1}, {t2})")
            elif term.arg1 in ("<", ">", "<=", ">=", "==", "!="):
                t1 = t0erm_cbv_evaluate0(term.arg2)
                t2 = t0erm_cbv_evaluate0(term.arg3)
                if isinstance(t1, T0Mint) and isinstance(t2, T0Mint):
                    if term.arg1 == "<":
                        return T0Mbtf(t1.arg1 < t2.arg1)
                    elif term.arg1 == ">":
                        return T0Mbtf(t1.arg1 > t2.arg1)
                    elif term.arg1 == "<=":
                        return T0Mbtf(t1.arg1 <= t2.arg1)
                    elif term.arg1 == ">=":
                        return T0Mbtf(t1.arg1 >= t2.arg1)
                    elif term.arg1 == "==":
                        return T0Mbtf(t1.arg1 == t2.arg1)
                    else: # term.arg1 == "!="
                        return T0Mbtf(t1.arg1 != t2.arg1)
                else:
                    raise TypeError(f"t0erm_cbv_evaluate0: {term.arg1} expects integers ({t1}, {t2})")
            else:
                raise TypeError(f"t0erm_cbv_evaluate0({term})")
        elif isinstance(term, T0Mpair):
            # Left to right: t1 first, then t2. A pair is a value only when
            # both components are values. Both are always evaluated, even if a
            # surrounding projection selects just one of them.
            if term.__dict__.get("_isval"):
                return term    # already known to be a pair of values
            t1 = t0erm_cbv_evaluate0(term.arg1)
            t2 = t0erm_cbv_evaluate0(term.arg2)
            result = T0Mpair(t1, t2)
            # Remember that this pair is a value, so evaluating it again
            # (for example after it is substituted somewhere) does not walk
            # its components again. Not a dataclass field: equality and
            # repr are unaffected.
            result.__dict__["_isval"] = True
            return result
        elif isinstance(term, T0Mpfst):
            t1 = t0erm_cbv_evaluate0(term.arg1)
            if isinstance(t1, T0Mpair):
                return t1.arg1
            else:
                raise TypeError(f"t0erm_cbv_evaluate0: fst expects a pair ({t1})")
        elif isinstance(term, T0Mpsnd):
            t1 = t0erm_cbv_evaluate0(term.arg1)
            if isinstance(t1, T0Mpair):
                return t1.arg2
            else:
                raise TypeError(f"t0erm_cbv_evaluate0: snd expects a pair ({t1})")
        else:
            raise TypeError(f"t0erm_cbv_evaluate0({term})")
#
########################################################################
########################################################################
# end of [CS413-2026-Fall/assigns/02/lambda0.py]
########################################################################
########################################################################
