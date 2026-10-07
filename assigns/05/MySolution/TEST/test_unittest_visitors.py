"""unittest suite for lambda1_visitors.py (pretty printing and substitution).

Run from assigns/05:
    python3.12 -m unittest discover -s MySolution/TEST -p 'test_unittest_*.py' -v
"""

import copy
import unittest
from pathlib import Path
from unittest import mock

from shared_cases import (
    B, I, V, add, app, fix, fst, if0, lam, let, mul, pair, snd,
    FV_EXAMPLES, PRETTY_CASES, SUBST_CASES,
    check_fv_property, check_substitution_lemma, semantic_cases, structural_cases,
    all_names, free_variables,
)
import lambda1_vp as base
from lambda1_visitors import (
    PrettyPrintVisitor, SubstitutionVisitor, d0exp_alpha_equal, d0exp_pretty,
    d0exp_substitute,
)

ALL_CLASSES = [base.D0Eint, base.D0Ebtf, base.D0Evar, base.D0Eop1, base.D0Eop2,
               base.D0Elam, base.D0Efix, base.D0Eapp, base.D0Eif0, base.D0Elet,
               base.D0Epair, base.D0Epfst, base.D0Epsnd]

# One expression using every constructor.
EVERYTHING = let("p", pair(I(1), B(True)),
                 if0(base.D0Eop2("<", fst(V("p")), base.D0Eop1("+1", I(2))),
                     app(lam("a", V("a")), snd(V("p"))),
                     app(fix("f", "n", app(V("f"), V("n"))), V("x"))))

# Expressions that must never be evaluated by printing or substitution.
DANGEROUS = [
    base.D0Eop2("/", I(1), I(0)),
    V("unbound"),
    app(I(1), I(2)),
    fst(I(3)),
    app(fix("loop", "n", app(V("loop"), V("n"))), I(0)),
    if0(I(0), V("x"), V("x")),
    base.D0Eop1("nonsense", B(True)),
]


class PrettyPrintTests(unittest.TestCase):
    def test_expected_output(self):
        for name, expression, expected in PRETTY_CASES:
            with self.subTest(name):
                self.assertEqual(d0exp_pretty(expression), expected)

    def test_single_line_without_surrounding_whitespace(self):
        for name, expression, _ in PRETTY_CASES:
            with self.subTest(name):
                text = d0exp_pretty(expression)
                self.assertEqual(text, text.strip())
                self.assertNotIn("\n", text)

    def test_assignment_examples(self):
        self.assertEqual(d0exp_pretty(app(lam("x", add(V("x"), I(1))), I(4))),
                         "((lam x. (x + 1)) 4)")
        self.assertEqual(d0exp_pretty(base.D0Eop2("/", I(1), I(0))), "(1 / 0)")

    def test_both_booleans_and_signs(self):
        self.assertEqual(d0exp_pretty(B(True)), "true")
        self.assertEqual(d0exp_pretty(B(False)), "false")
        self.assertEqual(d0exp_pretty(I(-123456789012345678901234567890)),
                         "-123456789012345678901234567890")

    def test_visitor_can_be_used_directly_and_reused(self):
        visitor = PrettyPrintVisitor()
        self.assertEqual(add(I(1), I(2)).accept(visitor), "(1 + 2)")
        self.assertEqual(lam("x", V("x")).accept(visitor), "(lam x. x)")
        self.assertEqual(add(I(1), I(2)).accept(visitor), "(1 + 2)")

    def test_result_type_is_str(self):
        self.assertIsInstance(d0exp_pretty(EVERYTHING), str)

    def test_does_not_evaluate(self):
        with mock.patch.object(base.EvaluateVisitor, "__init__",
                               side_effect=AssertionError("evaluated")):
            for expression in DANGEROUS:
                with self.subTest(d0exp_pretty(expression)):
                    d0exp_pretty(expression)

    def test_input_is_preserved_and_output_is_deterministic(self):
        before = copy.deepcopy(EVERYTHING)
        first = d0exp_pretty(EVERYTHING)
        self.assertEqual(EVERYTHING, before)
        self.assertEqual(d0exp_pretty(EVERYTHING), first)


class SubstitutionTests(unittest.TestCase):
    def test_expected_results(self):
        for name, expression, variable, replacement, expected in SUBST_CASES:
            with self.subTest(name):
                result = d0exp_substitute(expression, variable, replacement)
                self.assertEqual(result, expected,
                                 f"got {d0exp_pretty(result)}, "
                                 f"expected {d0exp_pretty(expected)}")

    def test_results_have_the_expected_free_variables(self):
        for name, expression, variable, replacement, expected in SUBST_CASES:
            with self.subTest(name):
                result = d0exp_substitute(expression, variable, replacement)
                self.assertEqual(free_variables(result), free_variables(expected))

    def test_assignment_example_table_in_pretty_notation(self):
        # Spot-check the table of the assignment through the printer as well.
        e = lam("y", add(V("x"), V("y")))
        self.assertEqual(d0exp_pretty(d0exp_substitute(e, "x", V("y"))),
                         "(lam y_1. (y + y_1))")
        e = fix("f", "n", add(V("x"), app(V("f"), V("n"))))
        self.assertEqual(d0exp_pretty(d0exp_substitute(e, "x", V("f"))),
                         "(fix f_1(n). (f + (f_1 n)))")

    def test_naive_capture_is_not_produced(self):
        result = d0exp_substitute(lam("y", add(V("x"), V("y"))), "x", V("y"))
        self.assertNotEqual(result, lam("y", add(V("y"), V("y"))))
        self.assertEqual(free_variables(result), {"y"})

    def test_let_initializer_versus_body(self):
        # initializer is always substituted, body only if the let name differs
        e = let("x", V("x"), V("x"))
        self.assertEqual(d0exp_substitute(e, "x", I(3)), let("x", I(3), V("x")))
        e = let("y", V("x"), V("x"))
        self.assertEqual(d0exp_substitute(e, "x", I(3)), let("y", I(3), I(3)))
        # renaming the let name does not touch the initializer
        e = let("y", V("y"), add(V("x"), V("y")))
        self.assertEqual(d0exp_substitute(e, "x", V("y")),
                         let("y_1", V("y"), add(V("y"), V("y_1"))))

    def test_both_fix_binders_shadow(self):
        e = fix("f", "n", add(V("f"), V("n")))
        self.assertEqual(d0exp_substitute(e, "f", I(1)), e)
        self.assertEqual(d0exp_substitute(e, "n", I(1)), e)

    def test_fix_with_equal_names_follows_the_evaluator(self):
        # In fix f(f). body the parameter wins: applying it binds f to the argument.
        e = fix("f", "f", V("f"))
        applied = app(d0exp_substitute(e, "x", I(0)), I(41))
        self.assertEqual(base.d0exp_evaluate(applied), base.D0Vint(41))
        e = fix("g", "g", add(V("g"), V("x")))
        renamed = d0exp_substitute(e, "x", V("g"))
        env = base.ENVcns("g", base.D0Vint(100), base.ENVnil())
        self.assertEqual(base.d0exp_evaluate(app(renamed, I(1)), env),
                         base.D0Vint(101))

    def test_replacement_is_inserted_once(self):
        r = add(V("x"), I(1))
        result = d0exp_substitute(pair(V("x"), V("x")), "x", r)
        self.assertEqual(result, pair(r, r))

    def test_inputs_are_preserved(self):
        for name, expression, variable, replacement, expected in SUBST_CASES:
            with self.subTest(name):
                e_before, r_before = copy.deepcopy(expression), copy.deepcopy(replacement)
                d0exp_substitute(expression, variable, replacement)
                self.assertEqual(expression, e_before)
                self.assertEqual(replacement, r_before)

    def test_repeated_calls_give_equal_results(self):
        for name, expression, variable, replacement, expected in SUBST_CASES:
            with self.subTest(name):
                results = [d0exp_substitute(expression, variable, replacement)
                           for _ in range(3)]
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[1], results[2])

    def test_fresh_names_do_not_leak_between_calls(self):
        e = lam("y", add(V("x"), V("y")))
        first = d0exp_substitute(e, "x", V("y"))
        second = d0exp_substitute(e, "x", V("y"))
        self.assertEqual(first, lam("y_1", add(V("y"), V("y_1"))))
        self.assertEqual(second, first)

    def test_fresh_names_are_distinct_and_new(self):
        e = lam("a", lam("b", lam("a", add(V("x"), add(V("a"), V("b"))))))
        r = add(V("a"), V("b"))
        result = d0exp_substitute(e, "x", r)
        binders = []
        node = result
        while isinstance(node, base.D0Elam):
            binders.append(node.arg1)
            node = node.arg2
        self.assertEqual(len(set(binders)), 3)
        for b in binders:
            self.assertNotIn(b, {"x"})
        self.assertTrue(d0exp_alpha_equal(
            result, lam("p", lam("q", lam("r", add(add(V("a"), V("b")),
                                                   add(V("r"), V("q"))))))))

    def test_does_not_evaluate(self):
        with mock.patch.object(base.EvaluateVisitor, "__init__",
                               side_effect=AssertionError("evaluated")):
            for expression in DANGEROUS:
                with self.subTest(d0exp_pretty(expression)):
                    d0exp_substitute(expression, "x", V("x"))
                    d0exp_substitute(lam("x", expression), "x", I(0))
                    d0exp_substitute(expression, "unbound", I(1))

    def test_division_by_zero_survives_substitution(self):
        e = base.D0Eop2("/", V("x"), I(0))
        self.assertEqual(d0exp_substitute(e, "x", I(1)), base.D0Eop2("/", I(1), I(0)))

    def test_visitor_class_can_be_used_directly(self):
        e = lam("y", add(V("x"), V("y")))
        visitor = SubstitutionVisitor.for_expression(e, "x", V("y"))
        self.assertEqual(e.accept(visitor), lam("y_1", add(V("y"), V("y_1"))))

    def test_result_is_an_expression(self):
        self.assertIsInstance(d0exp_substitute(EVERYTHING, "x", I(1)), base.D0E000)


class FreeVariablePropertyTests(unittest.TestCase):
    def test_examples(self):
        for k, (expression, variable, replacement) in enumerate(FV_EXAMPLES):
            with self.subTest(k):
                check_fv_property(expression, variable, replacement)

    def test_exact_free_variables_of_examples(self):
        e = fix("f", "n", add(V("x"), app(V("f"), V("n"))))
        r = add(V("f"), V("n"))
        self.assertEqual(free_variables(d0exp_substitute(e, "x", r)), {"f", "n"})
        e = lam("y", add(V("x"), V("y")))
        self.assertEqual(free_variables(d0exp_substitute(e, "x", V("y"))), {"y"})

    def test_target_not_free_gives_the_same_expression(self):
        e = lam("x", add(V("x"), V("y")))
        result = d0exp_substitute(e, "x", V("y"))
        self.assertEqual(result, e)
        self.assertEqual(free_variables(result), {"y"})

    def test_random_terms(self):
        for expression, variable, replacement in structural_cases():
            check_fv_property(expression, variable, replacement)

    def test_fresh_names_never_collide_on_random_terms(self):
        for expression, variable, replacement in structural_cases(500, seed=7):
            result = d0exp_substitute(expression, variable, replacement)
            # every name of the result is old, or is a generated "<old>_<k>" name
            old = all_names(expression) | all_names(replacement)
            for name in all_names(result) - old:
                stem, _, number = name.rpartition("_")
                self.assertTrue(number.isdigit() and stem in old, name)


class SemanticTests(unittest.TestCase):
    """Substitution lemma: evaluating e[x := r] equals evaluating e with x bound
    to the value of r. The evaluator is used only here, as an independent oracle."""

    def test_random_terms(self):
        meaningful = 0
        cases = semantic_cases()
        for expression, variable, replacement in cases:
            outcome = check_substitution_lemma(expression, variable, replacement)
            if outcome[0] in ("int", "pair"):
                meaningful += 1
        self.assertGreater(meaningful, len(cases) * 0.9)


class AlphaEqualityTests(unittest.TestCase):
    def test_renamed_binders_are_equal(self):
        self.assertTrue(d0exp_alpha_equal(lam("a", V("a")), lam("b", V("b"))))
        self.assertTrue(d0exp_alpha_equal(
            let("a", V("y"), V("a")), let("b", V("y"), V("b"))))
        self.assertTrue(d0exp_alpha_equal(
            fix("f", "n", app(V("f"), V("n"))), fix("g", "m", app(V("g"), V("m")))))

    def test_different_structure_is_not_equal(self):
        self.assertFalse(d0exp_alpha_equal(lam("a", lam("b", V("a"))),
                                           lam("a", lam("b", V("b")))))
        self.assertFalse(d0exp_alpha_equal(lam("a", V("y")), lam("a", V("z"))))
        self.assertFalse(d0exp_alpha_equal(lam("a", V("a")), lam("a", V("y"))))

    def test_let_initializer_is_outside_the_binder(self):
        self.assertFalse(d0exp_alpha_equal(let("a", V("a"), V("a")),
                                           let("b", V("b"), V("b"))))
        self.assertTrue(d0exp_alpha_equal(let("a", V("a"), V("a")),
                                          let("b", V("a"), V("b"))))

    def test_fix_with_equal_names_binds_the_parameter(self):
        self.assertTrue(d0exp_alpha_equal(fix("f", "f", V("f")),
                                          fix("g", "h", V("h"))))
        self.assertFalse(d0exp_alpha_equal(fix("f", "f", V("f")),
                                           fix("g", "h", V("g"))))


class DesignTests(unittest.TestCase):
    def test_every_constructor_dispatches_through_accept(self):
        counts = {cls: 0 for cls in ALL_CLASSES}

        def spy(cls):
            original = cls.accept

            def accept(self, visitor):
                counts[cls] += 1
                return original(self, visitor)
            return accept

        patches = [mock.patch.object(cls, "accept", spy(cls)) for cls in ALL_CLASSES]
        for p in patches:
            p.start()
        try:
            for operation in (lambda: d0exp_pretty(EVERYTHING),
                              lambda: d0exp_substitute(EVERYTHING, "x", I(1))):
                for cls in counts:
                    counts[cls] = 0
                operation()
                for cls, n in counts.items():
                    self.assertGreaterEqual(n, 1, cls.__name__)
        finally:
            for p in patches:
                p.stop()

    def test_printing_visits_each_node_once(self):
        counts = {"n": 0}
        original = {cls: cls.accept for cls in ALL_CLASSES}

        def spy(cls):
            def accept(self, visitor):
                counts["n"] += 1
                return original[cls](self, visitor)
            return accept

        patches = [mock.patch.object(cls, "accept", spy(cls)) for cls in ALL_CLASSES]
        for p in patches:
            p.start()
        try:
            d0exp_pretty(add(I(1), mul(V("x"), I(2))))
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(counts["n"], 5)

    def test_no_central_type_test_in_the_source(self):
        source = (Path(__file__).resolve().parent.parent / "lambda1_visitors.py").read_text()
        for forbidden in ("isinstance(", ".ctag", "type(", "getattr(", "hasattr(",
                          "match "):
            self.assertNotIn(forbidden, source)

    def test_visitors_implement_the_supplied_interface(self):
        for cls in (PrettyPrintVisitor, SubstitutionVisitor):
            self.assertTrue(issubclass(cls, base.D0ExpVisitor))
            self.assertEqual(cls.__abstractmethods__, frozenset())

    def test_supplied_free_variable_visitor_is_reused(self):
        self.assertEqual(base.d0exp_fvset(lam("x", add(V("x"), V("y")))), {"y"})


if __name__ == "__main__":
    unittest.main()
