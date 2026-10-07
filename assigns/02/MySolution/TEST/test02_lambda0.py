"""Tests for pairs and projections in MySolution/lambda0.py.

Run with: python3 TEST/test02_lambda0.py   (or: make -C TEST)
Requires Python 3.12 or later, like lambda0.py.

The sys.path line below makes these tests import MySolution/lambda0.py
(the parent of this TEST directory), never the starter file in assigns/02.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lambda0
from lambda0 import (
    T0Mint, T0Mbtf, T0Mstr, T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mif0,
    T0Mop1, T0Mop2, T0Mpair, T0Mpfst, T0Mpsnd,
    t0erm_size, t0erm_fvset, t0erm_subst0, t0erm_cbv_evaluate0,
)

DIV0 = T0Mop2("/", T0Mint(1), T0Mint(0))


def pair(a, b):
    return T0Mpair(a, b)


class TestImportsMySolution(unittest.TestCase):
    def test_imports_the_extended_copy(self):
        expected = Path(__file__).resolve().parents[1] / "lambda0.py"
        self.assertEqual(Path(lambda0.__file__).resolve(), expected)


class TestSize(unittest.TestCase):
    def test_pair(self):
        self.assertEqual(t0erm_size(pair(T0Mint(1), T0Mint(2))), 3)

    def test_projections(self):
        self.assertEqual(t0erm_size(T0Mpfst(T0Mvar("x"))), 2)
        self.assertEqual(t0erm_size(T0Mpsnd(T0Mvar("x"))), 2)

    def test_nested(self):
        # fst(pair(pair(1, 2), snd(pair(3, 4)))):
        #   fst 1 + pair 1 + pair 3 + snd 1 + pair 3 = 9
        inner = pair(pair(T0Mint(1), T0Mint(2)), T0Mpsnd(pair(T0Mint(3), T0Mint(4))))
        self.assertEqual(t0erm_size(T0Mpfst(inner)), 1 + 1 + 3 + 1 + 3)

    def test_inside_other_constructs(self):
        term = T0Mlam("x", T0Mif0(T0Mbtf(True), pair(T0Mvar("x"), T0Mint(1)), T0Mpfst(T0Mvar("x"))))
        # lam 1 + if0 1 + btf 1 + pair 3 + fst 2 = 8
        self.assertEqual(t0erm_size(term), 8)


class TestFvset(unittest.TestCase):
    def test_example_from_assignment(self):
        term = T0Mpfst(pair(T0Mvar("x"), T0Mvar("y")))
        self.assertEqual(t0erm_fvset(term), frozenset({"x", "y"}))

    def test_closed_pair(self):
        self.assertEqual(t0erm_fvset(pair(T0Mint(1), T0Mbtf(False))), frozenset())

    def test_projection_operand(self):
        self.assertEqual(t0erm_fvset(T0Mpsnd(T0Mvar("p"))), frozenset({"p"}))

    def test_pairs_and_projections_bind_nothing(self):
        # x occurs free in both components and under both projections.
        term = pair(T0Mpfst(T0Mvar("x")), T0Mpsnd(T0Mvar("x")))
        self.assertEqual(t0erm_fvset(term), frozenset({"x"}))

    def test_under_lambda_and_fix_binders(self):
        term = T0Mlam("x", pair(T0Mvar("x"), T0Mvar("y")))
        self.assertEqual(t0erm_fvset(term), frozenset({"y"}))
        term = T0Mfix("f", "n", T0Mpfst(pair(T0Mapp(T0Mvar("f"), T0Mvar("n")), T0Mvar("z"))))
        self.assertEqual(t0erm_fvset(term), frozenset({"z"}))

    def test_nested(self):
        term = pair(pair(T0Mvar("a"), T0Mvar("b")), T0Mpfst(pair(T0Mvar("c"), T0Mvar("a"))))
        self.assertEqual(t0erm_fvset(term), frozenset({"a", "b", "c"}))


class TestSubst0(unittest.TestCase):
    def test_both_pair_components(self):
        term = pair(T0Mvar("x"), pair(T0Mvar("x"), T0Mvar("y")))
        expected = pair(T0Mint(7), pair(T0Mint(7), T0Mvar("y")))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)), expected)

    def test_projection_operands_preserve_constructor(self):
        self.assertEqual(
            t0erm_subst0(T0Mpfst(T0Mvar("x")), "x", T0Mint(7)), T0Mpfst(T0Mint(7)))
        self.assertEqual(
            t0erm_subst0(T0Mpsnd(T0Mvar("x")), "x", T0Mint(7)), T0Mpsnd(T0Mint(7)))

    def test_unrelated_variable_unchanged(self):
        term = pair(T0Mvar("y"), T0Mpfst(T0Mvar("z")))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)), term)

    def test_under_lambda_binder(self):
        # The inner lambda rebinds x, so nothing is replaced under it.
        term = pair(T0Mvar("x"), T0Mlam("x", pair(T0Mvar("x"), T0Mvar("y"))))
        expected = pair(T0Mint(7), T0Mlam("x", pair(T0Mvar("x"), T0Mvar("y"))))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)), expected)
        # A different binder does not block substitution.
        term = T0Mlam("z", T0Mpfst(pair(T0Mvar("x"), T0Mvar("z"))))
        expected = T0Mlam("z", T0Mpfst(pair(T0Mint(7), T0Mvar("z"))))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)), expected)

    def test_under_fix_binders(self):
        body = pair(T0Mvar("f"), pair(T0Mvar("n"), T0Mvar("x")))
        # x is free in the fix: replaced.
        self.assertEqual(
            t0erm_subst0(T0Mfix("f", "n", body), "x", T0Mint(7)),
            T0Mfix("f", "n", pair(T0Mvar("f"), pair(T0Mvar("n"), T0Mint(7)))))
        # Substituting the self name or the parameter is blocked.
        term = T0Mfix("f", "n", body)
        self.assertEqual(t0erm_subst0(term, "f", T0Mint(7)), term)
        self.assertEqual(t0erm_subst0(term, "n", T0Mint(7)), term)

    def test_nested_projection_and_pair(self):
        term = T0Mpfst(T0Mpsnd(pair(T0Mint(1), pair(T0Mvar("x"), T0Mint(3)))))
        expected = T0Mpfst(T0Mpsnd(pair(T0Mint(1), pair(T0Mint(7), T0Mint(3)))))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(7)), expected)

    def test_substituting_a_pair_value(self):
        sub = pair(T0Mint(1), T0Mint(2))
        self.assertEqual(
            t0erm_subst0(T0Mpsnd(T0Mvar("p")), "p", sub), T0Mpsnd(sub))


class TestEvaluation(unittest.TestCase):
    def test_example_from_assignment(self):
        term = T0Mpsnd(pair(T0Mint(1), T0Mop2("+", T0Mint(2), T0Mint(3))))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(5))

    def test_pair_components_are_evaluated(self):
        term = pair(T0Mop2("+", T0Mint(1), T0Mint(2)), T0Mop2("*", T0Mint(3), T0Mint(4)))
        self.assertEqual(t0erm_cbv_evaluate0(term), pair(T0Mint(3), T0Mint(12)))

    def test_both_projections(self):
        p = pair(T0Mop2("+", T0Mint(1), T0Mint(1)), T0Mop2("-", T0Mint(9), T0Mint(2)))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mpfst(p)), T0Mint(2))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mpsnd(p)), T0Mint(7))

    def test_nested_pairs(self):
        term = pair(pair(T0Mint(1), T0Mint(2)), pair(T0Mint(3), pair(T0Mint(4), T0Mint(5))))
        self.assertEqual(t0erm_cbv_evaluate0(term), term)
        self.assertEqual(t0erm_cbv_evaluate0(T0Mpfst(T0Mpfst(term))), T0Mint(1))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mpsnd(T0Mpfst(term))), T0Mint(2))
        self.assertEqual(
            t0erm_cbv_evaluate0(T0Mpfst(T0Mpsnd(T0Mpsnd(term)))), T0Mint(4))
        # One projection too many reaches the integer 5, not a pair.
        with self.assertRaises(TypeError):
            t0erm_cbv_evaluate0(T0Mpfst(T0Mpsnd(T0Mpsnd(T0Mpsnd(term)))))

    def test_pairs_of_different_kinds_of_values(self):
        identity = T0Mlam("x", T0Mvar("x"))
        term = pair(T0Mint(1), pair(T0Mbtf(True), pair(T0Mstr("s"), identity)))
        self.assertEqual(t0erm_cbv_evaluate0(term), term)  # all components are values
        # A function stored in a pair can be extracted and applied.
        call = T0Mapp(T0Mpsnd(T0Mpsnd(T0Mpsnd(term))), T0Mint(42))
        self.assertEqual(t0erm_cbv_evaluate0(call), T0Mint(42))

    def test_pair_of_functions(self):
        inc = T0Mlam("x", T0Mop2("+", T0Mvar("x"), T0Mint(1)))
        dbl = T0Mlam("x", T0Mop2("*", T0Mvar("x"), T0Mint(2)))
        fs = pair(inc, dbl)
        self.assertEqual(t0erm_cbv_evaluate0(T0Mapp(T0Mpfst(fs), T0Mint(10))), T0Mint(11))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mapp(T0Mpsnd(fs), T0Mint(10))), T0Mint(20))

    def test_function_accepting_a_pair(self):
        # (lam p. fst(p) + snd(p)) (pair(3, 4)) = 7
        add = T0Mlam("p", T0Mop2("+", T0Mpfst(T0Mvar("p")), T0Mpsnd(T0Mvar("p"))))
        term = T0Mapp(add, pair(T0Mint(3), T0Mint(4)))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(7))

    def test_function_returning_a_pair(self):
        swap = T0Mlam("p", pair(T0Mpsnd(T0Mvar("p")), T0Mpfst(T0Mvar("p"))))
        term = T0Mapp(swap, pair(T0Mint(1), T0Mint(2)))
        self.assertEqual(t0erm_cbv_evaluate0(term), pair(T0Mint(2), T0Mint(1)))

    def test_recursive_function_over_pairs(self):
        # sum-to-n with an accumulator carried in a pair: f(n, acc).
        f = T0Mfix("f", "st", T0Mif0(
            T0Mop2("<=", T0Mpfst(T0Mvar("st")), T0Mint(0)),
            T0Mpsnd(T0Mvar("st")),
            T0Mapp(T0Mvar("f"), pair(
                T0Mop2("-", T0Mpfst(T0Mvar("st")), T0Mint(1)),
                T0Mop2("+", T0Mpsnd(T0Mvar("st")), T0Mpfst(T0Mvar("st")))))))
        self.assertEqual(
            t0erm_cbv_evaluate0(T0Mapp(f, pair(T0Mint(10), T0Mint(0)))), T0Mint(55))

    def test_pair_is_a_value_only_when_components_are(self):
        # The first component is not a value until evaluated.
        term = pair(T0Mapp(T0Mlam("x", T0Mvar("x")), T0Mint(5)), T0Mint(6))
        self.assertEqual(t0erm_cbv_evaluate0(term), pair(T0Mint(5), T0Mint(6)))

    def test_projection_of_non_pair_raises_typeerror(self):
        for operand in (T0Mint(1), T0Mbtf(True), T0Mstr("s"), T0Mlam("x", T0Mvar("x"))):
            for proj in (T0Mpfst, T0Mpsnd):
                with self.subTest(proj=proj.__name__, operand=operand):
                    with self.assertRaises(TypeError):
                        t0erm_cbv_evaluate0(proj(operand))

    def test_projection_of_computed_non_pair_raises_typeerror(self):
        term = T0Mpfst(T0Mop2("+", T0Mint(1), T0Mint(2)))
        with self.assertRaises(TypeError):
            t0erm_cbv_evaluate0(term)

    def test_projection_of_unevaluated_variable_still_fails(self):
        # A free variable is not a value; evaluation reports a TypeError.
        with self.assertRaises(TypeError):
            t0erm_cbv_evaluate0(T0Mpfst(T0Mvar("x")))


class TestEvaluationOrder(unittest.TestCase):
    def test_unselected_second_component_is_still_evaluated(self):
        # Example from the assignment: must raise, not return T0Mint(1).
        term = T0Mpfst(pair(T0Mint(1), DIV0))
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)

    def test_unselected_first_component_is_still_evaluated(self):
        term = T0Mpsnd(pair(DIV0, T0Mint(2)))
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)

    def test_left_component_evaluated_before_right(self):
        # The left error (ZeroDivisionError) must win over the right one
        # (TypeError), and vice versa.
        bad_type = T0Mop1("-", T0Mstr("bad"))
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(pair(DIV0, bad_type))
        with self.assertRaises(TypeError):
            t0erm_cbv_evaluate0(pair(bad_type, DIV0))

    def test_evaluation_order_with_projections_around_pairs(self):
        bad_type = T0Mop1("-", T0Mstr("bad"))
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(T0Mpsnd(pair(DIV0, bad_type)))
        with self.assertRaises(TypeError):
            t0erm_cbv_evaluate0(T0Mpfst(pair(bad_type, DIV0)))

    def test_projection_operand_evaluated_before_selection(self):
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(T0Mpfst(T0Mpsnd(pair(T0Mint(0), pair(T0Mint(1), DIV0)))))

    def test_pair_argument_is_evaluated_even_if_unused(self):
        term = T0Mapp(T0Mlam("p", T0Mint(42)), pair(T0Mint(1), DIV0))
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)

    def test_unselected_conditional_branch_with_pair_is_not_evaluated(self):
        term = T0Mif0(T0Mbtf(True), T0Mint(1), pair(DIV0, DIV0))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(1))


def naive_subst0(term, x0, tsub):
    """Reference substitution: the starter's algorithm plus pairs, with no
    shortcuts. MySolution/lambda0.py skips subterms that do not mention x0;
    these tests check that this never changes the result."""
    def go(t):
        if isinstance(t, (T0Mint, T0Mbtf, T0Mstr)):
            return t
        if isinstance(t, T0Mvar):
            return tsub if t.arg1 == x0 else t
        if isinstance(t, T0Mlam):
            return t if t.arg1 == x0 else T0Mlam(t.arg1, go(t.arg2))
        if isinstance(t, T0Mfix):
            return t if x0 in (t.arg1, t.arg2) else T0Mfix(t.arg1, t.arg2, go(t.arg3))
        if isinstance(t, T0Mapp):
            return T0Mapp(go(t.arg1), go(t.arg2))
        if isinstance(t, T0Mop1):
            return T0Mop1(t.arg1, go(t.arg2))
        if isinstance(t, T0Mop2):
            return T0Mop2(t.arg1, go(t.arg2), go(t.arg3))
        if isinstance(t, T0Mif0):
            return T0Mif0(go(t.arg1), go(t.arg2), go(t.arg3))
        if isinstance(t, T0Mpair):
            return T0Mpair(go(t.arg1), go(t.arg2))
        if isinstance(t, (T0Mpfst, T0Mpsnd)):
            return type(t)(go(t.arg1))
        raise TypeError(t)
    return go(term)


def random_term(rng, depth):
    names = ["x", "y", "z"]
    if depth == 0:
        return rng.choice([T0Mint(rng.randint(0, 3)), T0Mbtf(rng.random() < 0.5),
                           T0Mvar(rng.choice(names))])
    k = rng.randrange(9)
    sub = lambda: random_term(rng, depth - 1)
    if k == 0: return T0Mlam(rng.choice(names), sub())
    if k == 1: return T0Mfix(rng.choice(names), rng.choice(names), sub())
    if k == 2: return T0Mapp(sub(), sub())
    if k == 3: return T0Mop1("-", sub())
    if k == 4: return T0Mop2("+", sub(), sub())
    if k == 5: return T0Mif0(sub(), sub(), sub())
    if k == 6: return T0Mpair(sub(), sub())
    if k == 7: return T0Mpfst(sub())
    return T0Mpsnd(sub())


class TestOptimizationsPreserveBehavior(unittest.TestCase):
    def test_substitution_matches_naive_reference(self):
        import random
        rng = random.Random(413)
        for _ in range(1500):
            term = random_term(rng, rng.randint(0, 5))
            x0 = rng.choice(["x", "y", "z"])
            tsub = random_term(rng, 1)
            with self.subTest(term=term, x0=x0):
                self.assertEqual(t0erm_subst0(term, x0, tsub),
                                 naive_subst0(term, x0, tsub))

    def test_cached_free_variables_match_a_fresh_computation(self):
        import random
        rng = random.Random(7)
        for _ in range(300):
            term = random_term(rng, rng.randint(0, 5))
            first = t0erm_fvset(term)
            self.assertEqual(first, t0erm_fvset(term))      # cached answer
            self.assertEqual(first, t0erm_fvset(naive_subst0(term, "no_such_var", T0Mint(0))))

    def test_deep_tail_recursion_does_not_exhaust_the_python_stack(self):
        # count(n) = if n == 0 then 0 else count(n - 1): the recursive call
        # is in tail position, 50000 deep (far beyond Python's default limit).
        count = T0Mfix("count", "n", T0Mif0(
            T0Mop2("==", T0Mvar("n"), T0Mint(0)),
            T0Mint(0),
            T0Mapp(T0Mvar("count"), T0Mop2("-", T0Mvar("n"), T0Mint(1)))))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mapp(count, T0Mint(50000))), T0Mint(0))

    def test_reevaluating_a_pair_value_is_stable(self):
        value = t0erm_cbv_evaluate0(pair(T0Mop2("+", T0Mint(1), T0Mint(2)), T0Mint(4)))
        again = t0erm_cbv_evaluate0(value)
        self.assertEqual(value, pair(T0Mint(3), T0Mint(4)))
        self.assertEqual(again, value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
