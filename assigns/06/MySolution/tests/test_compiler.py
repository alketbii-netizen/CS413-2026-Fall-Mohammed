"""Obligations 3-7: source coverage, scope, divergence, rejection, purity."""
import copy
import itertools
import unittest
from unittest import mock

from tests.helpers import DIVERGE_BUDGET, run
import compiler
import evaluator
from compiler import CompileError, compile_expr
from evaluator import evaluate, source_value_to_python
from examples import DEMOS, EX, fact_program, fib_program
from source_ast import (LOOP, app, boo, d0exp_fvset, fix, fst, if_, lam, let,
                        num, op1, op2, pair, snd, var)
from target import free_vars, is_pure, show

EX_ = "EXHAUSTED"


def src_eval(e):
    return source_value_to_python(evaluate(e).value)


def check(test, e, kind, expected):
    """Compiled result and source evaluator must both give ``expected``."""
    test.assertEqual(run(e, kind), expected, msg=f"compiled: {e}")
    test.assertEqual(src_eval(e), expected, msg=f"source: {e}")


class TestConstructorsAndOperators(unittest.TestCase):
    def test_literals(self):
        check(self, num(0), "nat", 0)
        check(self, num(5), "nat", 5)
        check(self, boo(True), "bool", True)
        check(self, boo(False), "bool", False)

    def test_var_lam_app(self):
        check(self, app(lam("x", var("x")), num(3)), "nat", 3)

    def test_arithmetic(self):
        for m, n in itertools.product(range(4), range(4)):
            check(self, op2("+", num(m), num(n)), "nat", m + n)
            check(self, op2("-", num(m), num(n)), "nat", max(m - n, 0))
            check(self, op2("*", num(m), num(n)), "nat", m * n)
        # predecessor of zero via subtraction
        check(self, op2("-", num(0), num(1)), "nat", 0)

    def test_every_comparison_both_outcomes(self):
        cases = {"<": (1, 2, 2, 1), "<=": (2, 2, 3, 2), ">": (3, 1, 1, 3),
                 ">=": (2, 2, 1, 2), "==": (2, 2, 2, 3), "!=": (1, 2, 2, 2)}
        for op, (a, b, c, d) in cases.items():
            check(self, op2(op, num(a), num(b)), "bool", True)
            check(self, op2(op, num(c), num(d)), "bool", False)
        check(self, op2("==", num(0), num(0)), "bool", True)

    def test_boolean_truth_tables(self):
        for a, b in itertools.product((True, False), repeat=2):
            check(self, op2("and", boo(a), boo(b)), "bool", a and b)
            check(self, op2("or", boo(a), boo(b)), "bool", a or b)
        check(self, op1("not", boo(True)), "bool", False)
        check(self, op1("not", boo(False)), "bool", True)

    def test_if_both_branches(self):
        check(self, if_(boo(True), num(1), num(2)), "nat", 1)
        check(self, if_(boo(False), num(1), num(2)), "nat", 2)
        check(self, if_(op2("<", num(3), num(2)), boo(True), boo(False)), "bool", False)

    def test_let_pair_projections(self):
        check(self, let("x", num(2), op2("*", var("x"), var("x"))), "nat", 4)
        check(self, fst(pair(num(2), boo(True))), "nat", 2)
        check(self, snd(pair(num(2), boo(True))), "bool", True)
        check(self, pair(pair(num(2), boo(True)), num(3)),
              ("pair", ("pair", "nat", "bool"), "nat"), ((2, True), 3))

    def test_fix(self):
        check(self, fact_program(0), "nat", 1)
        check(self, fact_program(4), "nat", 24)
        check(self, fib_program(0), "nat", 0)
        check(self, fib_program(5), "nat", 5)


class TestScope(unittest.TestCase):
    def test_nested_lets_and_shadowing(self):
        e = let("x", num(1), let("x", op2("+", var("x"), num(1)),
                                 app(lam("x", op2("*", var("x"), num(10))), var("x"))))
        check(self, e, "nat", 20)

    def test_let_initializer_scope(self):
        # let x = 2 in let x = x + 1 in x   -> init sees the OUTER x
        check(self, let("x", num(2), let("x", op2("+", var("x"), num(1)), var("x"))), "nat", 3)
        # let x = x in x is open: x free in the initializer
        e = let("x", var("x"), var("x"))
        self.assertEqual(free_vars(compile_expr(e)), {"x"})

    def test_both_fix_binders(self):
        # fix f(n). if n == 0 then 0 else f (n - 1) + 2   (uses f and n)
        body = if_(op2("==", var("n"), num(0)), num(0),
                   op2("+", app(var("f"), op2("-", var("n"), num(1))), num(2)))
        check(self, app(fix("f", "n", body), num(3)), "nat", 6)

    def test_coincident_fix_binders(self):
        # (fix f(f). f) 3 -> parameter shadows function name -> 3
        check(self, app(fix("f", "f", var("f")), num(3)), "nat", 3)
        self.assertEqual(free_vars(compile_expr(fix("f", "f", var("g")))), {"g"})

    def test_encoding_names_as_source_names(self):
        # Source variables named like encoding/fresh variables.
        for x in ("s", "z", "t", "f", "x", "w", "g", "v", "p", "a", "b",
                  "n", "m", "_k_1", "tail", "c"):
            e = let(x, num(2), if_(op2("<", var(x), num(3)),
                                   op2("+", var(x), num(1)), var(x)))
            check(self, e, "nat", 3)
            fn = "g" if x == "f" else "f"
            e2 = app(fix(fn, x, if_(op2("==", var(x), num(0)), num(7),
                                    app(var(fn), op2("-", var(x), num(1))))), num(2))
            check(self, e2, "nat", 7)

    def test_open_expressions_preserve_free_variables(self):
        cases = [
            op2("+", var("s"), var("z")),
            if_(var("t"), var("f"), var("x")),
            op2("and", var("_k_1"), var("_k_2")),
            op2("or", var("s"), lam("s", var("z"))),
            let("x", var("x"), var("y")),
            fix("f", "x", app(var("f"), app(var("x"), var("g")))),
            fix("f", "f", app(var("f"), var("h"))),
            pair(fst(var("p")), snd(var("q"))),
            op1("not", var("b")),
            lam("y", if_(var("c"), var("y"), var("u"))),
        ]
        for e in cases:
            self.assertEqual(free_vars(compile_expr(e)), d0exp_fvset(e), e)

    def test_thunk_names_avoid_capture(self):
        # A source variable called _k_1 inside a branch must stay free.
        e = if_(var("c"), var("_k_1"), var("_k_2"))
        t = compile_expr(e)
        self.assertEqual(free_vars(t), {"c", "_k_1", "_k_2"})

    def test_deterministic_names(self):
        e = if_(boo(True), var("_k_1"), num(1))
        self.assertEqual(show(compile_expr(e)), show(compile_expr(e)))

    def test_input_not_mutated(self):
        for _, _, e, _, _ in DEMOS:
            snap = copy.deepcopy(e)
            compile_expr(e)
            self.assertEqual(e, snap)


class TestDivergence(unittest.TestCase):
    B = DIVERGE_BUDGET

    def test_unselected_divergence_skipped(self):
        self.assertEqual(run(if_(boo(True), num(1), LOOP()), "nat", self.B), 1)
        self.assertEqual(run(if_(boo(False), LOOP(), num(2)), "nat", self.B), 2)
        self.assertEqual(run(op2("and", boo(False), LOOP()), "bool", self.B), False)
        self.assertEqual(run(op2("or", boo(True), LOOP()), "bool", self.B), True)

    def test_selected_divergence_exhausts(self):
        self.assertEqual(run(if_(boo(True), LOOP(), num(1)), "nat", self.B), EX_)
        self.assertEqual(run(if_(boo(False), num(1), LOOP()), "nat", self.B), EX_)
        self.assertEqual(run(op2("and", boo(True), LOOP()), "bool", self.B), EX_)
        self.assertEqual(run(op2("or", boo(False), LOOP()), "bool", self.B), EX_)

    def test_strict_positions_exhaust(self):
        cases = [
            app(lam("x", num(0)), LOOP()),            # unused argument
            let("x", LOOP(), num(2)),                  # unused let initializer
            fst(pair(num(2), LOOP())),                 # second pair component
            snd(pair(LOOP(), boo(True))),              # first pair component
            op2("+", LOOP(), num(1)),
            op2("*", num(0), LOOP()),
            LOOP(),
        ]
        for e in cases:
            self.assertEqual(run(e, "nat", self.B), EX_, e)


class TestRejection(unittest.TestCase):
    def assertRejected(self, e, needle):
        with self.assertRaises(CompileError) as cm:
            compile_expr(e)
        self.assertIn(needle, str(cm.exception))

    def test_negative_literal(self):
        self.assertRejected(num(-1), "-1")

    def test_unsupported_operators(self):
        self.assertRejected(op2("/", num(4), num(2)), "'/'")
        self.assertRejected(op2("%", num(4), num(2)), "'%'")
        self.assertRejected(op1("-1", num(4)), "'-1'")
        self.assertRejected(op1("+1", num(4)), "'+1'")

    def test_rejected_in_unselected_or_unapplied_code(self):
        self.assertRejected(if_(boo(True), num(1), num(-3)), "-3")
        self.assertRejected(op2("and", boo(False), op2("/", num(1), num(1))), "'/'")
        self.assertRejected(lam("x", op2("/", var("x"), num(2))), "'/'")
        self.assertRejected(fix("f", "x", op1("neg", var("x"))), "'neg'")
        self.assertRejected(let("y", num(1), pair(num(0), num(-7))), "-7")


class TestPurityAndIsolation(unittest.TestCase):
    def test_output_pure_for_demos_and_all_constructors(self):
        for _, _, e, _, _ in DEMOS:
            self.assertTrue(is_pure(compile_expr(e)))

    def test_compilation_never_calls_evaluator(self):
        boom = mock.Mock(side_effect=AssertionError("evaluator called"))
        with mock.patch.object(evaluator, "evaluate", boom), \
             mock.patch.object(evaluator.Evaluator, "run_target", boom), \
             mock.patch.object(evaluator.Evaluator, "visit_app", boom):
            for e in (op2("+", num(2), op2("*", num(3), num(4))), LOOP(),
                      fact_program(4)):
                snap = copy.deepcopy(e)
                t = compile_expr(e)
                self.assertTrue(is_pure(t))
                self.assertEqual(e, snap)
        boom.assert_not_called()
        self.assertFalse(hasattr(compiler, "evaluate"))
        self.assertNotIn("evaluator", compiler.__dict__)


class TestDemonstrations(unittest.TestCase):
    def test_all_demos(self):
        for id_, _, e, kind, expected in DEMOS:
            budget = DIVERGE_BUDGET if expected == EX else 100_000
            self.assertEqual(run(e, kind, budget), expected, id_)
            if expected != EX:
                self.assertEqual(src_eval(e), expected, id_)


if __name__ == "__main__":
    unittest.main()
