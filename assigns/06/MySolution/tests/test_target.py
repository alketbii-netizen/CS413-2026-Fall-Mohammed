"""Obligations 1-2: target AST, printer, substitution, call-by-value reducer."""
import unittest

from tests.helpers import SOL  # noqa: F401  (sets sys.path)
from evaluator import OpenTermError, evaluate
from target import App, Lam, Var, alpha_equal, free_vars, show, subst

I = Lam("x", Var("x"))
OMEGA = App(Lam("x", App(Var("x"), Var("x"))), Lam("x", App(Var("x"), Var("x"))))


class TestPrinter(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(show(Var("x")), "x")
        self.assertEqual(show(Lam("x", Var("x"))), "(lam x. x)")
        self.assertEqual(show(App(Var("f"), Var("a"))), "(f a)")
        self.assertEqual(show(Lam("f", App(App(Var("f"), Var("a")), Lam("y", Var("y"))))),
                         "(lam f. ((f a) (lam y. y)))")


class TestSubstitution(unittest.TestCase):
    def test_capture_avoided(self):
        # (lam y. x)[x := y]  ==alpha==  lam fresh. y, y still free
        t = Lam("y", Var("x"))
        r = subst(t, "x", Var("y"))
        self.assertIsInstance(r, Lam)
        self.assertNotEqual(r.param, "y")
        self.assertTrue(alpha_equal(r, Lam("q", Var("y"))))
        self.assertEqual(free_vars(r), {"y"})

    def test_shadowing_stops_substitution(self):
        t = Lam("x", Var("x"))
        self.assertIs(subst(t, "x", Var("y")), t)

    def test_nested_capture_and_fresh_name_collision(self):
        # lam y. lam y_1. x y y_1   [x := y]  must rename y to something
        # other than y_1 and keep the inner reference intact.
        t = Lam("y", Lam("y_1", App(App(Var("x"), Var("y")), Var("y_1"))))
        r = subst(t, "x", Var("y"))
        expect = Lam("a", Lam("b", App(App(Var("y"), Var("a")), Var("b"))))
        self.assertTrue(alpha_equal(r, expect))
        self.assertEqual(free_vars(r), {"y"})

    def test_inputs_preserved_and_replacement_shared(self):
        t = App(Var("x"), Lam("z", Var("x")))
        v = Lam("q", Var("q"))
        before_t, before_v = show(t), show(v)
        r = subst(t, "x", v)
        self.assertEqual(show(t), before_t)
        self.assertEqual(show(v), before_v)
        self.assertTrue(alpha_equal(r, App(v, Lam("z", v))))

    def test_open_terms(self):
        r = subst(App(Var("x"), Var("w")), "x", Var("u"))
        self.assertEqual(show(r), "(u w)")


class TestReducer(unittest.TestCase):
    def test_lambda_is_value_zero_steps_no_reduction_under_lambda(self):
        t = Lam("x", App(Lam("y", Var("y")), Var("x")))
        r = evaluate(t, 10)
        self.assertEqual((r.status, r.steps), ("value", 0))
        self.assertIs(r.value, t)

    def test_budget_boundaries(self):
        self.assertEqual((evaluate(I, 0).status, evaluate(I, 0).steps), ("value", 0))
        r = evaluate(App(I, I), 0)
        self.assertEqual((r.status, r.steps), ("exhausted", 0))
        r = evaluate(App(I, I), 1)
        self.assertEqual((r.status, r.steps), ("value", 1))
        self.assertTrue(alpha_equal(r.value, I))

    def test_left_to_right_order(self):
        # (I I) (I I): left child first, then right, then outer -> 3 steps.
        # With budget 1 only the left child was reduced; with budget 2 both
        # children, and the outer contraction still needs one more step.
        t = App(App(I, I), App(I, I))
        self.assertEqual(evaluate(t, 1).status, "exhausted")
        self.assertEqual(evaluate(t, 2).status, "exhausted")
        r = evaluate(t, 3)
        self.assertEqual((r.status, r.steps), ("value", 3))
        # Function position is evaluated before a diverging argument:
        # (OMEGA) (I I) exhausts without ever touching the argument.
        self.assertEqual(evaluate(App(OMEGA, App(I, I)), 50).status, "exhausted")

    def test_call_by_value_argument_evaluated(self):
        # (lam x. I) OMEGA diverges under call-by-value.
        r = evaluate(App(Lam("x", I), OMEGA), 1000)
        self.assertEqual((r.status, r.steps), ("exhausted", 1000))

    def test_deterministic_and_input_unchanged(self):
        t = App(App(I, I), App(I, I))
        snap = show(t)
        r1, r2 = evaluate(t, 10), evaluate(t, 10)
        self.assertEqual((r1.status, r1.steps), (r2.status, r2.steps))
        self.assertTrue(alpha_equal(r1.value, r2.value))
        self.assertEqual(show(t), snap)

    def test_open_term_rejected(self):
        with self.assertRaises(OpenTermError):
            evaluate(App(I, Var("free")), 10)

    def test_negative_budget_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(I, -1)


if __name__ == "__main__":
    unittest.main()
