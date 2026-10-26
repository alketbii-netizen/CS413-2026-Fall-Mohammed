"""The mandatory demonstration programs, built directly as source ASTs.

Each entry: (id, description, source AST, expected kind, expected answer)
where expected answer is a Python value or the string "EXHAUSTED".
"""

from source_ast import (LOOP, app, boo, fix, fst, if_, lam, let, num, op2,
                        pair, snd, var)


def fact_program(n: int):
    # (fix fact(n). if n == 0 then 1 else n * fact (n - 1)) n
    body = if_(op2("==", var("n"), num(0)),
               num(1),
               op2("*", var("n"), app(var("fact"), op2("-", var("n"), num(1)))))
    return app(fix("fact", "n", body), num(n))


def fib_program(n: int):
    # (fix fib(n). if n < 2 then n else fib (n - 1) + fib (n - 2)) n
    body = if_(op2("<", var("n"), num(2)),
               var("n"),
               op2("+", app(var("fib"), op2("-", var("n"), num(1))),
                        app(var("fib"), op2("-", var("n"), num(2)))))
    return app(fix("fib", "n", body), num(n))


EX = "EXHAUSTED"

DEMOS = [
    ("DEMO-01", "2 + 3 * 4", op2("+", num(2), op2("*", num(3), num(4))), "nat", 14),
    ("DEMO-02", "2 - 5", op2("-", num(2), num(5)), "nat", 0),
    ("DEMO-03", "if 2 <= 3 then 7 else 9",
     if_(op2("<=", num(2), num(3)), num(7), num(9)), "nat", 7),
    ("DEMO-04", "let x = 3 in (lam y. x + y) 4",
     let("x", num(3), app(lam("y", op2("+", var("x"), var("y"))), num(4))), "nat", 7),
    ("DEMO-05", "fst (pair 2 true)", fst(pair(num(2), boo(True))), "nat", 2),
    ("DEMO-06", "snd (pair 2 true)", snd(pair(num(2), boo(True))), "bool", True),
    ("DEMO-07", "(lam f. f 3) (lam x. x + 1)",
     app(lam("f", app(var("f"), num(3))), lam("x", op2("+", var("x"), num(1)))), "nat", 4),
    ("DEMO-08", "if true then 1 else LOOP", if_(boo(True), num(1), LOOP()), "nat", 1),
    ("DEMO-09", "(lam x. 0) LOOP", app(lam("x", num(0)), LOOP()), "nat", EX),
    ("DEMO-10", "fact 4", fact_program(4), "nat", 24),
    ("DEMO-11", "fib 5", fib_program(5), "nat", 5),
    ("DEMO-12", "LOOP = (fix loop(x). loop x) 0", LOOP(), "nat", EX),
    ("DEMO-13", "true and false", op2("and", boo(True), boo(False)), "bool", False),
    ("DEMO-14", "false or true", op2("or", boo(False), boo(True)), "bool", True),
    ("EXTRA-01", "pair (pair 2 true) 3", pair(pair(num(2), boo(True)), num(3)),
     ("pair", ("pair", "nat", "bool"), "nat"), ((2, True), 3)),
]
