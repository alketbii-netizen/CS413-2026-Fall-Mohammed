"""Church-encoding library: closed target terms built from Var/Lam/App only.

Every builder returns a fresh, closed pure term.  The upper-case names are
Python builder names / documentation abbreviations, never target primitives:
compiler output contains only their expansions.

Representations (as required):
    TRUE   = lam t. lam f. t
    FALSE  = lam t. lam f. f
    NUM(n) = lam s. lam z. s (s ... (s z))          (n applications)
    PAIR   = lam a. lam b. lam p. p a b
    Z      = lam g. (lam x. g (lam v. x x v)) (lam x. g (lam v. x x v))

References: A. Church (1936/1941) for numerals and booleans; the
pair-based predecessor follows Kleene's construction as presented in
Pierce, *Types and Programming Languages*, §5.2; Z is the standard
call-by-value fixed-point combinator (Pierce §5.2, "fix").
"""

from __future__ import annotations

from target import App, Lam, Term, Var


# ---- small construction helpers ---------------------------------------

def lams(params: str, body: Term) -> Term:
    """lams("a b c", e) = lam a. lam b. lam c. e"""
    for p in reversed(params.split()):
        body = Lam(p, body)
    return body


def apps(f: Term, *args: Term) -> Term:
    """apps(f, a, b) = ((f a) b)"""
    for a in args:
        f = App(f, a)
    return f


V = Var  # brevity


# ---- identity / dummy value -------------------------------------------

def I() -> Term:
    return Lam("w", V("w"))


# ---- booleans ----------------------------------------------------------

def TRUE() -> Term:
    return lams("t f", V("t"))


def FALSE() -> Term:
    return lams("t f", V("f"))


def BOOL(b: bool) -> Term:
    return TRUE() if b else FALSE()


def NOT() -> Term:
    # lam b. lam t. lam f. b f t
    return lams("b t f", apps(V("b"), V("f"), V("t")))


def AND_STRICT() -> Term:
    # lam p. lam q. p q p  -- both operands already values (used by EQ)
    return lams("p q", apps(V("p"), V("q"), V("p")))


# ---- natural numbers ---------------------------------------------------

def NUM(n: int) -> Term:
    if n < 0:
        raise ValueError("Church numerals are natural numbers")
    body: Term = V("z")
    for _ in range(n):
        body = App(V("s"), body)
    return lams("s z", body)


def SUCC() -> Term:
    # lam n. lam s. lam z. s (n s z)
    return lams("n s z", App(V("s"), apps(V("n"), V("s"), V("z"))))


def ADD() -> Term:
    # lam m. lam n. lam s. lam z. m s (n s z)
    return lams("m n s z", apps(V("m"), V("s"), apps(V("n"), V("s"), V("z"))))


def MUL() -> Term:
    # lam m. lam n. lam s. m (n s)
    return lams("m n s", App(V("m"), App(V("n"), V("s"))))


def ISZERO() -> Term:
    # lam n. n (lam x. FALSE) TRUE
    return Lam("n", apps(V("n"), Lam("x", FALSE()), TRUE()))


# ---- pairs -------------------------------------------------------------

def PAIR() -> Term:
    return lams("a b p", apps(V("p"), V("a"), V("b")))


def FST() -> Term:
    # lam p. p (lam a. lam b. a)
    return Lam("p", App(V("p"), lams("a b", V("a"))))


def SND() -> Term:
    # lam p. p (lam a. lam b. b)
    return Lam("p", App(V("p"), lams("a b", V("b"))))


def PRED() -> Term:
    """Pair-shifting predecessor.

    PRED = lam n. FST (n SHIFT (PAIR 0 0))
    SHIFT = lam q. PAIR (SND q) (SUCC (SND q))

    Starting from (0, 0), each SHIFT maps (a, b) to (b, b+1).  After n
    shifts the pair is (n-1, n) for n >= 1 and (0, 0) for n = 0, so FST
    yields n-1, and PRED 0 = 0.  Under call-by-value every intermediate pair
    is a value, so the cost is linear in n.
    """
    shift = Lam("q", apps(PAIR(), App(SND(), V("q")),
                          App(SUCC(), App(SND(), V("q")))))
    return Lam("n", App(FST(), apps(V("n"), shift, apps(PAIR(), NUM(0), NUM(0)))))


def SUB() -> Term:
    # truncated: lam m. lam n. n PRED m   (apply PRED n times to m)
    return lams("m n", apps(V("n"), PRED(), V("m")))


# ---- comparisons (all on naturals) --------------------------------------

def LEQ() -> Term:
    # m <= n  iff  m - n = 0
    return lams("m n", App(ISZERO(), apps(SUB(), V("m"), V("n"))))


def LT() -> Term:
    # m < n  iff  (m + 1) - n = 0
    return lams("m n", App(ISZERO(), apps(SUB(), App(SUCC(), V("m")), V("n"))))


def GEQ() -> Term:
    return lams("m n", apps(LEQ(), V("n"), V("m")))


def GT() -> Term:
    return lams("m n", apps(LT(), V("n"), V("m")))


def EQ() -> Term:
    return lams("m n", apps(AND_STRICT(), apps(LEQ(), V("m"), V("n")),
                            apps(LEQ(), V("n"), V("m"))))


def NEQ() -> Term:
    return lams("m n", App(NOT(), apps(EQ(), V("m"), V("n"))))


# ---- recursion ---------------------------------------------------------

def Z() -> Term:
    half = Lam("x", App(V("g"), Lam("v", apps(V("x"), V("x"), V("v")))))
    return Lam("g", App(half, half))


# Binary operators whose operands are both evaluated (strict).
STRICT_OP2 = {
    "+": ADD, "-": SUB, "*": MUL,
    "<": LT, "<=": LEQ, ">": GT, ">=": GEQ, "==": EQ, "!=": NEQ,
}

# Every library combinator, for closedness tests.
LIBRARY = {
    "I": I, "TRUE": TRUE, "FALSE": FALSE, "NOT": NOT, "AND_STRICT": AND_STRICT,
    "SUCC": SUCC, "PRED": PRED, "ISZERO": ISZERO, "ADD": ADD, "SUB": SUB,
    "MUL": MUL, "LT": LT, "LEQ": LEQ, "GT": GT, "GEQ": GEQ, "EQ": EQ,
    "NEQ": NEQ, "PAIR": PAIR, "FST": FST, "SND": SND, "Z": Z,
    "NUM(0)": lambda: NUM(0), "NUM(3)": lambda: NUM(3),
}
