"""Obligation 6/ACC-11/12: observers, malformed outputs, budgets."""
import unittest

from tests.helpers import SOL  # noqa: F401
import church as C
from church import apps, lams
from compiler import compile_expr
from evaluator import evaluate
from observe import observe, observe_bool, observe_nat, run_compiled
from source_ast import boo, num, op2, pair
from target import App, Lam, Var


class TestObservers(unittest.TestCase):
    def test_alpha_renamed_literals(self):
        two = Lam("a", Lam("b", App(Var("a"), App(Var("a"), Var("b")))))
        self.assertEqual(observe_nat(two, 100).value, 2)
        tru = Lam("p", Lam("q", Var("p")))
        self.assertIs(observe_bool(tru, 100).value, True)

    def test_computed_values_with_redexes_inside(self):
        v = evaluate(apps(C.ADD(), C.NUM(2), C.NUM(3)), 1000).value
        # ADD's result still has unreduced applications under its binders
        self.assertEqual(observe_nat(v, 1000).value, 5)
        b = evaluate(apps(C.LT(), C.NUM(1), C.NUM(2)), 10_000).value
        self.assertIs(observe_bool(b, 1000).value, True)

    def test_church_zero_under_both_kinds(self):
        self.assertEqual(observe_nat(C.NUM(0), 100).value, 0)
        self.assertIs(observe_bool(C.NUM(0), 100).value, False)

    def test_malformed(self):
        self.assertEqual(observe_nat(C.TRUE(), 100).status, "malformed")
        self.assertEqual(observe_nat(lams("s z", Var("s")), 100).status, "malformed")
        self.assertEqual(observe_bool(C.NUM(2), 100).status, "malformed")
        self.assertEqual(observe_bool(C.I(), 100).status, "malformed")

    def test_observation_budget_exhaustion_is_distinct(self):
        o = observe_nat(C.NUM(5), 2)
        self.assertEqual(o.status, "exhausted")
        self.assertEqual(o.steps, 2)
        self.assertEqual(observe_nat(C.NUM(5), 1000).status, "ok")

    def test_separate_budgets_and_counts(self):
        t = compile_expr(op2("+", num(2), num(3)))
        r = run_compiled(t, "nat", 100, 100)
        self.assertEqual(r.exec_status, "value")
        self.assertTrue(r.obs.ok)
        self.assertGreater(r.exec_steps, 0)
        self.assertGreater(r.obs.steps, 0)
        r2 = run_compiled(t, "nat", 100, 1)
        self.assertEqual((r2.exec_status, r2.obs.status), ("value", "exhausted"))

    def test_nested_pair(self):
        t = compile_expr(pair(pair(num(2), boo(True)), num(3)))
        r = run_compiled(t, ("pair", ("pair", "nat", "bool"), "nat"), 100, 1000)
        self.assertEqual(r.obs.value, ((2, True), 3))


if __name__ == "__main__":
    unittest.main()
