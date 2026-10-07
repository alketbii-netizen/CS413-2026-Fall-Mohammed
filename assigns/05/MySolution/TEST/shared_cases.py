"""Example inputs, expected results and checks shared by both test suites.

Expected results were worked out by hand from the assignment text and the
fresh-name policy in lambda1_visitors.py (b -> b_1, b_2, ...), not copied from
program output. The checks here only raise AssertionError, so the unittest
suite and the pytest suite can both call them.
"""

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))        # MySolution/ (lambda1_visitors.py)
sys.path.insert(0, str(HERE.parent.parent))  # assigns/05 (the supplied lambda1_vp.py)

from lambda1_vp import (                    # noqa: E402
    D0Eapp, D0Ebtf, D0Efix, D0Eif0, D0Eint, D0Elam, D0Elet, D0Eop1, D0Eop2,
    D0Epair, D0Epfst, D0Epsnd, D0Evar,
    D0Vbtf, D0Vint, D0Vpair, D0Vfix, D0Vlam, ENVcns, ENVnil,
    d0exp_evaluate, d0exp_fvset,
)
from lambda1_visitors import (              # noqa: E402
    NameCollectorVisitor, d0exp_alpha_equal, d0exp_pretty, d0exp_substitute,
)

########################################################################
# Short constructors
########################################################################

def V(name): return D0Evar(name)
def I(n): return D0Eint(n)
def B(b): return D0Ebtf(b)
def add(a, b): return D0Eop2("+", a, b)
def mul(a, b): return D0Eop2("*", a, b)
def lam(x, body): return D0Elam(x, body)
def fix(f, x, body): return D0Efix(f, x, body)
def app(a, b): return D0Eapp(a, b)
def let(x, init, body): return D0Elet(x, init, body)
def pair(a, b): return D0Epair(a, b)
def fst(a): return D0Epfst(a)
def snd(a): return D0Epsnd(a)
def if0(c, t, f): return D0Eif0(c, t, f)

########################################################################
# Task 1: (expression, exact output)
########################################################################

PRETTY_CASES = [
    ("int", I(42), "42"),
    ("zero", I(0), "0"),
    ("negative int", I(-7), "-7"),
    ("large int", I(10**30), "1000000000000000000000000000000"),
    ("large negative int", I(-(10**30)), "-1000000000000000000000000000000"),
    ("true", B(True), "true"),
    ("false", B(False), "false"),
    ("variable", V("x"), "x"),
    ("variable with underscore and digits", V("_a_1B2"), "_a_1B2"),
    ("op1 +1", D0Eop1("+1", V("x")), "(+1 x)"),
    ("op1 -1", D0Eop1("-1", I(5)), "(-1 5)"),
    ("op2 +", add(I(1), I(2)), "(1 + 2)"),
    ("op2 -", D0Eop2("-", I(1), I(-2)), "(1 - -2)"),
    ("op2 *", mul(V("a"), V("b")), "(a * b)"),
    ("op2 /", D0Eop2("/", I(1), I(0)), "(1 / 0)"),
    ("op2 <", D0Eop2("<", I(1), I(2)), "(1 < 2)"),
    ("op2 >=", D0Eop2(">=", I(1), I(2)), "(1 >= 2)"),
    ("op2 ==", D0Eop2("==", I(1), I(2)), "(1 == 2)"),
    ("op2 !=", D0Eop2("!=", I(1), I(2)), "(1 != 2)"),
    ("lam", lam("x", V("x")), "(lam x. x)"),
    ("fix", fix("f", "n", app(V("f"), V("n"))), "(fix f(n). (f n))"),
    ("app", app(V("f"), I(3)), "(f 3)"),
    ("if0", if0(B(True), I(1), I(2)), "(if true then 1 else 2)"),
    ("let", let("x", I(1), add(V("x"), V("y"))), "(let x = 1 in (x + y))"),
    ("pair", pair(I(1), B(False)), "(pair 1 false)"),
    ("pfst", fst(pair(I(1), I(2))), "(fst (pair 1 2))"),
    ("psnd", snd(pair(I(1), I(2))), "(snd (pair 1 2))"),
    ("assignment example",
     app(lam("x", add(V("x"), I(1))), I(4)), "((lam x. (x + 1)) 4)"),
    ("nested",
     let("p", pair(I(1), lam("z", D0Eop1("-1", V("z")))),
         if0(D0Eop2("<", fst(V("p")), I(0)), B(False),
             app(snd(V("p")), I(10)))),
     "(let p = (pair 1 (lam z. (-1 z))) in "
     "(if ((fst p) < 0) then false else ((snd p) 10)))"),
    ("fix with nested lam",
     fix("go", "i", if0(D0Eop2("==", V("i"), I(0)), I(0),
                        app(V("go"), D0Eop1("-1", V("i"))))),
     "(fix go(i). (if (i == 0) then 0 else (go (-1 i))))"),
]

########################################################################
# Task 2: (name, expression, variable, replacement, expected result)
########################################################################

SUBST_CASES = [
    # --- the assignment's examples --------------------------------------
    ("example 1: plain", add(V("x"), V("z")), "x", I(3),
     add(I(3), V("z"))),
    ("example 2: lambda shadows", lam("x", add(V("x"), V("y"))), "x", I(3),
     lam("x", add(V("x"), V("y")))),
    ("example 3: lambda capture", lam("y", add(V("x"), V("y"))), "x", V("y"),
     lam("y_1", add(V("y"), V("y_1")))),
    ("example 4: let initializer", let("x", V("x"), add(V("x"), V("y"))), "x", I(3),
     let("x", I(3), add(V("x"), V("y")))),
    ("example 5: let capture", let("y", V("x"), add(V("x"), V("y"))), "x", V("y"),
     let("y_1", V("y"), add(V("y"), V("y_1")))),
    ("example 6: fix capture",
     fix("f", "n", add(V("x"), app(V("f"), V("n")))), "x", V("f"),
     fix("f_1", "n", add(V("f"), app(V("f_1"), V("n"))))),
    ("example 7: replacement contains the target", V("x"), "x", add(V("x"), I(1)),
     add(V("x"), I(1))),

    # --- every constructor ------------------------------------------------
    ("through every constructor",
     pair(D0Eop1("+1", V("x")),
          if0(V("x"), app(V("x"), V("x")), fst(snd(V("x"))))),
     "x", V("y"),
     pair(D0Eop1("+1", V("y")),
          if0(V("y"), app(V("y"), V("y")), fst(snd(V("y")))))),
    ("literals are kept", pair(I(5), B(True)), "x", I(9), pair(I(5), B(True))),
    ("through lam fix let without conflicts",
     lam("a", fix("g", "b", let("c", V("x"), add(V("c"), add(V("a"), V("b")))))),
     "x", I(7),
     lam("a", fix("g", "b", let("c", I(7), add(V("c"), add(V("a"), V("b"))))))),
    ("non-matching variable", add(V("a"), V("b")), "x", I(3),
     add(V("a"), V("b"))),
    ("matching variable in several places", add(V("x"), mul(V("x"), V("y"))),
     "x", I(2), add(I(2), mul(I(2), V("y")))),
    ("replacement contains the target (binary)", add(V("x"), V("y")), "x",
     mul(V("x"), V("x")), add(mul(V("x"), V("x")), V("y"))),
    ("replacement contains the target (under a binder)", lam("z", V("x")), "x",
     add(V("x"), I(1)), lam("z", add(V("x"), I(1)))),
    ("replacement is not substituted again", pair(V("x"), V("x")), "x",
     pair(V("x"), V("y")), pair(pair(V("x"), V("y")), pair(V("x"), V("y")))),

    # --- shadowing --------------------------------------------------------
    ("lambda shadows in nested position",
     add(V("x"), lam("x", V("x"))), "x", I(1), add(I(1), lam("x", V("x")))),
    ("fix function name shadows", fix("f", "n", app(V("f"), V("n"))), "f", I(3),
     fix("f", "n", app(V("f"), V("n")))),
    ("fix parameter shadows", fix("f", "n", add(V("n"), V("x"))), "n", I(3),
     fix("f", "n", add(V("n"), V("x")))),
    ("fix with equal function name and parameter, target is that name",
     fix("f", "f", add(V("f"), V("x"))), "f", I(3),
     fix("f", "f", add(V("f"), V("x")))),
    ("fix with equal function name and parameter, other target",
     fix("f", "f", add(V("f"), V("x"))), "x", I(1),
     fix("f", "f", add(V("f"), I(1)))),
    ("let shadows in its body", let("x", I(1), add(V("x"), V("y"))), "x", I(3),
     let("x", I(1), add(V("x"), V("y")))),
    ("let initializer sees the target, body does not",
     let("x", add(V("x"), I(1)), mul(V("x"), V("x"))), "x", I(5),
     let("x", add(I(5), I(1)), mul(V("x"), V("x")))),
    ("let initializer and body both use the target",
     let("y", V("x"), add(V("x"), V("y"))), "x", I(5),
     let("y", I(5), add(I(5), V("y")))),

    # --- capture avoidance -----------------------------------------------
    ("fix parameter conflict",
     fix("f", "n", add(V("x"), app(V("f"), V("n")))), "x", V("n"),
     fix("f", "n_1", add(V("n"), app(V("f"), V("n_1"))))),
    ("fix conflicts with both binders",
     fix("f", "n", add(V("x"), app(V("f"), V("n")))), "x", add(V("f"), V("n")),
     fix("f_1", "n_1", add(add(V("f"), V("n")), app(V("f_1"), V("n_1"))))),
    ("fix with equal function name and parameter, conflict",
     fix("g", "g", add(V("g"), V("x"))), "x", V("g"),
     fix("g_2", "g_1", add(V("g_1"), V("g")))),
    ("lambda capture inside a larger term",
     app(lam("y", mul(V("x"), V("y"))), V("x")), "x", V("y"),
     app(lam("y_1", mul(V("y"), V("y_1"))), V("y"))),
    ("let body capture, initializer is not renamed",
     let("y", add(V("y"), V("x")), mul(V("y"), V("x"))), "x", V("y"),
     let("y_1", add(V("y"), V("y")), mul(V("y_1"), V("y")))),
    ("lambda and let both capture",
     lam("a", let("b", V("a"), add(V("x"), V("b")))), "x", add(V("a"), V("b")),
     lam("a_1", let("b_1", V("a_1"), add(add(V("a"), V("b")), V("b_1"))))),

    # --- nested shadowing during alpha-renaming ----------------------------
    ("renaming stops at an inner binder of the same name",
     lam("y", lam("y", add(V("x"), V("y")))), "x", V("y"),
     lam("y_1", lam("y_2", add(V("y"), V("y_2"))))),
    ("renaming reaches occurrences under inner binders of other names",
     lam("y", lam("z", add(V("y"), add(V("z"), V("x"))))), "x", V("y"),
     lam("y_1", lam("z", add(V("y_1"), add(V("z"), V("y")))))),

    # --- fresh-name collisions ---------------------------------------------
    ("fresh name avoids a name in the expression",
     lam("y", add(add(V("x"), V("y")), V("y_1"))), "x", V("y"),
     lam("y_2", add(add(V("y"), V("y_2")), V("y_1")))),
    ("fresh name avoids a name generated earlier in the same call",
     app(lam("y", add(V("x"), V("y"))), lam("y", add(V("x"), V("y")))), "x", V("y"),
     app(lam("y_1", add(V("y"), V("y_1"))), lam("y_2", add(V("y"), V("y_2"))))),
    ("fresh name avoids a bound name of the replacement",
     lam("y", add(V("x"), V("y"))), "x", app(lam("y_1", V("y_1")), V("y")),
     lam("y_2", add(app(lam("y_1", V("y_1")), V("y")), V("y_2")))),
    ("fresh name avoids the substitution target",
     lam("y", add(V("y_1"), V("y"))), "y_1", V("y"),
     lam("y_2", add(V("y"), V("y_2")))),
    ("fresh name avoids a binder that is not used",
     lam("y", lam("y_1", add(V("x"), V("y")))), "x", V("y"),
     lam("y_2", lam("y_1", add(V("y"), V("y_2"))))),

    # --- no unnecessary renaming -------------------------------------------
    ("no renaming when the target does not occur in the body",
     lam("y", V("z")), "x", V("y"), lam("y", V("z"))),
    ("no renaming in let when the target does not occur in the body",
     let("y", I(1), V("z")), "x", V("y"), let("y", I(1), V("z"))),
    ("no renaming in fix when the target does not occur in the body",
     fix("f", "n", V("z")), "x", add(V("f"), V("n")), fix("f", "n", V("z"))),
    ("no renaming when the binder is not in the replacement",
     lam("y", add(V("x"), V("y"))), "x", V("z"), lam("y", add(V("z"), V("y")))),
]

########################################################################
# Checks shared by both suites
########################################################################

def free_variables(dexp):
    return d0exp_fvset(dexp)


def check_fv_property(dexp, variable, replacement):
    """FV(e[x := r]) = (FV(e) - {x}) | FV(r) if x is free in e; otherwise the
    result equals e (so it is alpha-equivalent and has the same free variables)."""
    result = d0exp_substitute(dexp, variable, replacement)
    if variable in free_variables(dexp):
        expected = (free_variables(dexp) - {variable}) | free_variables(replacement)
        assert free_variables(result) == expected, (dexp, variable, replacement, result)
    else:
        assert d0exp_alpha_equal(result, dexp), (dexp, variable, replacement, result)
        assert free_variables(result) == free_variables(dexp)
        assert result == dexp


# Examples for the free-variable property: (expression, variable, replacement)
FV_EXAMPLES = [
    (add(V("x"), V("z")), "x", add(V("y"), V("w"))),
    (lam("y", add(V("x"), V("y"))), "x", V("y")),
    (let("y", V("x"), add(V("x"), V("y"))), "x", V("y")),
    (fix("f", "n", add(V("x"), app(V("f"), V("n")))), "x", add(V("f"), V("n"))),
    (fix("g", "g", add(V("g"), V("x"))), "x", V("g")),
    (lam("y", lam("y", add(V("x"), V("y")))), "x", V("y")),
    (lam("y", V("z")), "x", V("y")),
    (add(V("a"), V("b")), "x", V("c")),
    (V("x"), "x", add(V("x"), I(1))),
    (let("x", V("x"), V("x")), "x", V("q")),
]

########################################################################
# Random terms
########################################################################

NAMES = ["x", "y", "z", "w"]


class Rand:
    """Seeded generator, so every run draws the same terms."""

    def __init__(self, seed):
        self.rng = random.Random(seed)

    def name(self):
        return self.rng.choice(NAMES)

    def any_term(self, depth):
        """Any constructor, any shape (never evaluated)."""
        r = self.rng
        if depth == 0:
            return r.choice([I(r.randint(-3, 3)), B(r.random() < 0.5), V(self.name())])
        sub = lambda: self.any_term(depth - 1)
        kind = r.randrange(11)
        if kind == 0: return D0Eop1("+1", sub())
        if kind == 1: return D0Eop2("+", sub(), sub())
        if kind == 2: return lam(self.name(), sub())
        if kind == 3: return fix(self.name(), self.name(), sub())
        if kind == 4: return app(sub(), sub())
        if kind == 5: return if0(sub(), sub(), sub())
        if kind == 6: return let(self.name(), sub(), sub())
        if kind == 7: return pair(sub(), sub())
        if kind == 8: return fst(sub())
        if kind == 9: return snd(sub())
        return V(self.name())

    def int_term(self, depth):
        """A well-typed term that always evaluates to an int when every name in
        NAMES is bound to an int: no fix, so evaluation always terminates."""
        r = self.rng
        if depth == 0:
            return r.choice([I(r.randint(-3, 3)), V(self.name())])
        sub = lambda: self.int_term(depth - 1)
        kind = r.randrange(8)
        if kind == 0: return add(sub(), sub())
        if kind == 1: return mul(sub(), sub())
        if kind == 2: return D0Eop2("-", sub(), sub())
        if kind == 3: return if0(D0Eop2("<", sub(), sub()), sub(), sub())
        if kind == 4: return let(self.name(), sub(), sub())
        if kind == 5: return app(lam(self.name(), sub()), sub())
        if kind == 6: return fst(pair(sub(), sub()))
        return snd(pair(sub(), sub()))

    def top_term(self, depth):
        if self.rng.random() < 0.25:
            return pair(self.int_term(depth), self.int_term(depth))
        return self.int_term(depth)

    def replacement(self):
        """A total integer expression over NAMES (so evaluating it cannot fail)."""
        r = self.rng
        kind = r.randrange(4)
        if kind == 0: return I(r.randint(-3, 3))
        if kind == 1: return V(self.name())
        if kind == 2: return add(V(self.name()), V(self.name()))
        return mul(V(self.name()), I(r.randint(-2, 3)))


def observe(value):
    """Comparable summary of a value; closures are opaque."""
    if isinstance(value, D0Vint):
        return ("int", value.arg1)
    if isinstance(value, D0Vbtf):
        return ("btf", value.arg1)
    if isinstance(value, D0Vpair):
        return ("pair", observe(value.arg1), observe(value.arg2))
    if isinstance(value, (D0Vlam, D0Vfix)):
        return ("closure",)
    return ("other", type(value).__name__)


def run(dexp, env):
    try:
        return observe(d0exp_evaluate(dexp, env))
    except Exception as exc:                     # compare error kinds as well
        return ("error", type(exc).__name__)


def base_env():
    env = ENVnil()
    for k, name in enumerate(NAMES):
        env = ENVcns(name, D0Vint(3 * k - 4), env)    # x=-4, y=-1, z=2, w=5
    return env


def check_substitution_lemma(dexp, variable, replacement):
    """Evaluating e[x := r] gives the same as evaluating e with x bound to the
    value of r, in an environment that binds every name. A capture bug changes
    which binding a free name of r sees, and so changes the result."""
    env = base_env()
    substituted = d0exp_substitute(dexp, variable, replacement)
    value_of_r = d0exp_evaluate(replacement, env)
    lhs = run(substituted, env)
    rhs = run(dexp, ENVcns(variable, value_of_r, env))
    assert lhs == rhs, (dexp, variable, replacement, substituted, lhs, rhs)
    return lhs


def semantic_cases(count=1500, seed=20261007):
    """(expression, variable, replacement) triples for the substitution lemma."""
    gen = Rand(seed)
    return [(gen.top_term(3), gen.name(), gen.replacement()) for _ in range(count)]


def structural_cases(count=1500, seed=20261008):
    gen = Rand(seed)
    return [(gen.any_term(4), gen.name(), gen.any_term(2)) for _ in range(count)]


def all_names(dexp):
    return dexp.accept(NameCollectorVisitor())
