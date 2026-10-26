"""Obligation 3 (encodings level) and 7 (closed combinators)."""
import itertools
import unittest

from tests.helpers import OBS, SOL  # noqa: F401
import church as C
from church import apps
from evaluator import evaluate
from observe import observe_bool, observe_nat
from target import free_vars, is_pure


def nat(t):
    r = evaluate(t, 200_000); assert r.ok
    o = observe_nat(r.value, OBS); assert o.ok, o
    return o.value


def boolean(t):
    r = evaluate(t, 200_000); assert r.ok
    o = observe_bool(r.value, OBS); assert o.ok, o
    return o.value


NS = range(0, 5)


class TestEncodings(unittest.TestCase):
    def test_library_closed_and_pure(self):
        for name, mk in C.LIBRARY.items():
            t = mk()
            self.assertEqual(free_vars(t), frozenset(), name)
            self.assertTrue(is_pure(t), name)

    def test_numerals(self):
        for n in NS:
            self.assertEqual(nat(C.NUM(n)), n)

    def test_succ_pred_iszero(self):
        for n in NS:
            self.assertEqual(nat(apps(C.SUCC(), C.NUM(n))), n + 1)
            self.assertEqual(nat(apps(C.PRED(), C.NUM(n))), max(n - 1, 0))
            self.assertEqual(boolean(apps(C.ISZERO(), C.NUM(n))), n == 0)
        self.assertEqual(nat(apps(C.PRED(), C.NUM(0))), 0)   # pred 0 = 0

    def test_arithmetic(self):
        for m, n in itertools.product(NS, NS):
            self.assertEqual(nat(apps(C.ADD(), C.NUM(m), C.NUM(n))), m + n)
            self.assertEqual(nat(apps(C.SUB(), C.NUM(m), C.NUM(n))), max(m - n, 0))
            self.assertEqual(nat(apps(C.MUL(), C.NUM(m), C.NUM(n))), m * n)

    def test_comparisons_both_outcomes(self):
        ops = {"LT": lambda a, b: a < b, "LEQ": lambda a, b: a <= b,
               "GT": lambda a, b: a > b, "GEQ": lambda a, b: a >= b,
               "EQ": lambda a, b: a == b, "NEQ": lambda a, b: a != b}
        for name, py in ops.items():
            seen = set()
            for m, n in itertools.product(range(4), range(4)):
                got = boolean(apps(getattr(C, name)(), C.NUM(m), C.NUM(n)))
                self.assertEqual(got, py(m, n), (name, m, n))
                seen.add(got)
            self.assertEqual(seen, {True, False}, name)

    def test_booleans(self):
        self.assertIs(boolean(C.TRUE()), True)
        self.assertIs(boolean(C.FALSE()), False)
        self.assertIs(boolean(apps(C.NOT(), C.TRUE())), False)
        self.assertIs(boolean(apps(C.NOT(), C.FALSE())), True)

    def test_pairs(self):
        p = apps(C.PAIR(), C.NUM(2), C.TRUE())
        self.assertEqual(nat(apps(C.FST(), p)), 2)
        self.assertIs(boolean(apps(C.SND(), p)), True)


if __name__ == "__main__":
    unittest.main()
