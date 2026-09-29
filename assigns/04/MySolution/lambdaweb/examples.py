"""
Canned example sources (F1: "Factorial (canned), and Fibonacci (canned)").

Each is written as LAMBDA source text in the constructor-expression
format the restricted reader accepts (see constructor_reader.py) — the
same text a user could type or upload by hand. They are loaded as
*editable* starting points (F1), not baked into the code as d0exp
objects directly.
"""

FACTORIAL_SOURCE = """\
# factorial(5) via a self-referential `fix` (fact is bound to itself
# and to its own parameter `n` inside the body, so it can call itself).
D0Eapp(
    D0Efix("fact", "n",
        D0Eif0(
            D0Eop2("==", D0Evar("n"), D0Eint(0)),
            D0Eint(1),
            D0Eop2(
                "*",
                D0Evar("n"),
                D0Eapp(D0Evar("fact"), D0Eop2("-", D0Evar("n"), D0Eint(1)))
            )
        )
    ),
    D0Eint(5)
)
"""

FIBONACCI_SOURCE = """\
# fibonacci(10) via a self-referential `fix`.
D0Eapp(
    D0Efix("fib", "n",
        D0Eif0(
            D0Eop2("<", D0Evar("n"), D0Eint(2)),
            D0Evar("n"),
            D0Eop2(
                "+",
                D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(1))),
                D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(2)))
            )
        )
    ),
    D0Eint(10)
)
"""

CANNED_EXAMPLES = {
    "factorial": FACTORIAL_SOURCE,
    "fibonacci": FIBONACCI_SOURCE,
}
