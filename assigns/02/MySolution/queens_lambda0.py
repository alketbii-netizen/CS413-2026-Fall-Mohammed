"""Eight-queens, translated from ATS2 (eight_queens.dats) into a LAMBDA0 term.

The search algorithm and the queen-conflict checks are ordinary t0erm
structure (T0Mlam / T0Mapp / T0Mfix / T0Mif0 / T0Mpair / projections) and
are executed by t0erm_cbv_evaluate0 from lambda0.py. The Python in this
file only (1) builds the AST, (2) runs the interpreter, and (3) decodes and
displays the resulting value. It never searches for queens itself.

Run:  python3 queens_lambda0.py          (all solutions for N = 8)
      python3 queens_lambda0.py 6        (board size 6)

See README.md for how each ATS2 function maps to a term below.
"""

import sys
import threading

from lambda0 import (
    T0Mint, T0Mbtf, T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mif0,
    T0Mop1, T0Mop2, T0Mpair, T0Mpfst, T0Mpsnd,
    t0erm_cbv_evaluate0, t0erm_fvset,
)

########################################################################
# Small AST-building helpers (they only construct t0erm values).
########################################################################

def V(x): return T0Mvar(x)
def I(n): return T0Mint(n)
def lam(x, body): return T0Mlam(x, body)
def fix(f, x, body): return T0Mfix(f, x, body)
def pair(a, b): return T0Mpair(a, b)
def fst(t): return T0Mpfst(t)
def snd(t): return T0Mpsnd(t)
def neg(t): return T0Mop1("-", t)
def op2(op, a, b): return T0Mop2(op, a, b)
def if_(c, t, e): return T0Mif0(c, t, e)

def app(f, *args):
    """Curried application: app(f, a, b) = ((f a) b)."""
    for a in args:
        f = T0Mapp(f, a)
    return f

def let(x, value, body):
    """let x = value in body  ==  (lam x. body) value   (call-by-value)."""
    return T0Mapp(T0Mlam(x, body), value)

def and_(a, b):
    """a andalso b: short-circuit, as in ATS2."""
    return if_(a, b, T0Mbtf(False))

def tuple_(*items):
    """Right-nested pairs: tuple_(a, b, c) = (a, (b, c))."""
    result = items[-1]
    for item in reversed(items[:-1]):
        result = pair(item, result)
    return result

NIL = I(0)   # end-of-list marker; lists are right-nested pairs ending in NIL

########################################################################
# The translated program.
########################################################################

# abs(v) = if v < 0 then -v else v      (ATS2 builtin [abs])
ABS = lam("v", if_(op2("<", V("v"), I(0)), neg(V("v")), V("v")))

# safety_test1(i0, j0, i, j) = j0 != j andalso abs(i0-i) != abs(j0-j)
SAFETY_TEST1 = lam("i0", lam("j0", lam("i", lam("j",
    and_(
        op2("!=", V("j0"), V("j")),
        op2("!=",
            app(V("abs"), op2("-", V("i0"), V("i"))),
            app(V("abs"), op2("-", V("j0"), V("j"))))
    )))))

# safety_test2(i, j, bd, i0): is a queen at (i, j) safe w.r.t. rows i0..0?
#   if i0 >= 0 then safety_test1(i0, board_get(bd, i0), i, j)
#                   andalso safety_test2(i, j, bd, i0-1)
#   else true
# The board is a stack (see README): the head of [bd] is row i0's column,
# so board_get(bd, i0) is [fst bd] and the board for row i0-1 is [snd bd].
# The recursion carries (i0, bd) as one pair; i and j are closed over.
SAFETY_TEST2 = lam("i", lam("j",
    fix("go", "p",
        let("i0", fst(V("p")),
        let("bd", snd(V("p")),
            if_(op2(">=", V("i0"), I(0)),
                and_(
                    app(V("safety_test1"), V("i0"), fst(V("bd")), V("i"), V("j")),
                    app(V("go"), pair(op2("-", V("i0"), I(1)), snd(V("bd"))))),
                T0Mbtf(True)))))))


def search_term(n):
    """search(bd, i, j, nsol) of the ATS2 program, with the extra
    accumulator [sols] replacing the program's printing of each solution.
    The single parameter [st] is the 5-tuple (bd, (i, (j, (nsol, sols)))).
    """
    def next_state(bd, i, j, nsol, sols):
        return app(V("search"), tuple_(bd, i, j, nsol, sols))

    return fix("search", "st",
        let("bd",   fst(V("st")),
        let("r1",   snd(V("st")),
        let("i",    fst(V("r1")),
        let("r2",   snd(V("r1")),
        let("j",    fst(V("r2")),
        let("r3",   snd(V("r2")),
        let("nsol", fst(V("r3")),
        let("sols", snd(V("r3")),
            if_(op2("<", V("j"), I(n)),                       # j < N
                if_(app(V("safety_test2"), V("i"), V("j"),     # safe?
                        pair(op2("-", V("i"), I(1)), V("bd"))),
                    let("bd1", pair(V("j"), V("bd")),          # board_set
                        if_(op2("==", op2("+", V("i"), I(1)), I(n)),
                            # a full board: record it, keep searching row i
                            next_state(V("bd"), V("i"),
                                       op2("+", V("j"), I(1)),
                                       op2("+", V("nsol"), I(1)),
                                       pair(V("bd1"), V("sols"))),
                            # place the next queen on row i+1
                            next_state(V("bd1"),
                                       op2("+", V("i"), I(1)), I(0),
                                       V("nsol"), V("sols")))),
                    # not safe: try the next column
                    next_state(V("bd"), V("i"), op2("+", V("j"), I(1)),
                               V("nsol"), V("sols"))),
                # j >= N: backtrack, or finish
                if_(op2(">", V("i"), I(0)),
                    next_state(snd(V("bd")),
                               op2("-", V("i"), I(1)),
                               op2("+", fst(V("bd")), I(1)),
                               V("nsol"), V("sols")),
                    pair(V("nsol"), V("sols")))))))))))))


def closed_safety_test1():
    """A closed term for safety_test1, for testing it on its own."""
    return let("abs", ABS, SAFETY_TEST1)


def closed_safety_test2():
    """A closed term for safety_test2, for testing it on its own."""
    return let("abs", ABS, let("safety_test1", SAFETY_TEST1, SAFETY_TEST2))


def queens_term(n=8):
    """The closed t0erm that searches all placements of n queens and
    evaluates to  pair(count, solutions)."""
    program = \
        let("abs", ABS,
        let("safety_test1", SAFETY_TEST1,
        let("safety_test2", SAFETY_TEST2,
        let("search", search_term(n),
            app(V("search"), tuple_(NIL, I(0), I(0), I(0), NIL))))))
    assert t0erm_fvset(program) == frozenset(), "the queens term must be closed"
    return program

########################################################################
# Running the term and decoding its value (display/checking only).
########################################################################

def list_to_python(value):
    """Decode a right-nested pair list ending in NIL into a Python list."""
    items = []
    while isinstance(value, T0Mpair):
        items.append(value.arg1)
        value = value.arg2
    assert value == NIL, f"malformed list ending in {value}"
    return items


def decode_result(value):
    """pair(count, sols) -> (count, [board rows ...] in discovery order).
    Each board is a list of columns by row, row 0 first, like the ATS2
    program's int8 tuple."""
    count = value.arg1.arg1
    stacks = list_to_python(value.arg2)          # newest solution first
    boards = [[c.arg1 for c in reversed(list_to_python(s))] for s in stacks]
    return count, list(reversed(boards))          # oldest (discovery order) first


def run_queens(n=8):
    """Evaluate the translated term with the interpreter; return (count, boards).
    The interpreter is recursive (no tail-call optimization), so the search
    needs a deep Python stack; run it in a thread with a big one."""
    result = {}

    def work():
        sys.setrecursionlimit(50_000_000)
        result["value"] = t0erm_cbv_evaluate0(queens_term(n))

    threading.stack_size(512 * 1024 * 1024)
    thread = threading.Thread(target=work)
    thread.start()
    thread.join()
    return decode_result(result["value"])


def format_board(board):
    n = len(board)
    return "".join(
        " ".join("Q" if c == col else "." for c in range(n)) + " \n"
        for col in board)


def main(argv):
    n = int(argv[1]) if len(argv) > 1 else 8
    count, boards = run_queens(n)
    for k, board in enumerate(boards, start=1):
        print(f"Solution #{k}:\n")
        print(format_board(board))
    print(f"Total number of solutions = {count}")


if __name__ == "__main__":
    main(sys.argv)
