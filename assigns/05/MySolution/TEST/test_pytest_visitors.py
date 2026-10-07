"""pytest suite for lambda1_visitors.py (pretty printing and substitution).

Run from assigns/05 (pytest must be installed: python3.12 -m pip install pytest):
    python3.12 -m pytest MySolution/TEST/test_pytest_visitors.py -v
"""

import copy
from pathlib import Path
from unittest import mock

import pytest

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

EVERYTHING = let("p", pair(I(1), B(True)),
                 if0(base.D0Eop2("<", fst(V("p")), base.D0Eop1("+1", I(2))),
                     app(lam("a", V("a")), snd(V("p"))),
                     app(fix("f", "n", app(V("f"), V("n"))), V("x"))))

DANGEROUS = [
    base.D0Eop2("/", I(1), I(0)),
    V("unbound"),
    app(I(1), I(2)),
    fst(I(3)),
    app(fix("loop", "n", app(V("loop"), V("n"))), I(0)),
    if0(I(0), V("x"), V("x")),
    base.D0Eop1("nonsense", B(True)),
]

pretty_params = [pytest.param(e, s, id=n) for n, e, s in PRETTY_CASES]
subst_params = [pytest.param(e, x, r, out, id=n) for n, e, x, r, out in SUBST_CASES]


########################################################################
# Task 1: pretty printing
########################################################################

@pytest.mark.parametrize("expression, expected", pretty_params)
def test_pretty_exact_output(expression, expected):
    assert d0exp_pretty(expression) == expected


@pytest.mark.parametrize("expression, expected", pretty_params)
def test_pretty_is_single_line_without_extra_whitespace(expression, expected):
    text = d0exp_pretty(expression)
    assert text == text.strip()
    assert "\n" not in text


def test_pretty_assignment_examples():
    assert d0exp_pretty(app(lam("x", add(V("x"), I(1))), I(4))) == "((lam x. (x + 1)) 4)"
    assert d0exp_pretty(base.D0Eop2("/", I(1), I(0))) == "(1 / 0)"


def test_pretty_booleans_and_large_negative_integer():
    assert d0exp_pretty(B(True)) == "true"
    assert d0exp_pretty(B(False)) == "false"
    assert d0exp_pretty(I(-123456789012345678901234567890)) == "-123456789012345678901234567890"


def test_pretty_visitor_can_be_used_directly_and_reused():
    visitor = PrettyPrintVisitor()
    assert add(I(1), I(2)).accept(visitor) == "(1 + 2)"
    assert lam("x", V("x")).accept(visitor) == "(lam x. x)"
    assert add(I(1), I(2)).accept(visitor) == "(1 + 2)"


@pytest.mark.parametrize("expression", DANGEROUS)
def test_pretty_does_not_evaluate(expression):
    with mock.patch.object(base.EvaluateVisitor, "__init__",
                           side_effect=AssertionError("evaluated")):
        assert isinstance(d0exp_pretty(expression), str)


def test_pretty_preserves_input_and_is_deterministic():
    before = copy.deepcopy(EVERYTHING)
    first = d0exp_pretty(EVERYTHING)
    assert EVERYTHING == before
    assert d0exp_pretty(EVERYTHING) == first


########################################################################
# Task 2: substitution
########################################################################

@pytest.mark.parametrize("expression, variable, replacement, expected", subst_params)
def test_substitute_expected_result(expression, variable, replacement, expected):
    result = d0exp_substitute(expression, variable, replacement)
    assert result == expected, f"{d0exp_pretty(result)} != {d0exp_pretty(expected)}"


@pytest.mark.parametrize("expression, variable, replacement, expected", subst_params)
def test_substitute_free_variables_of_result(expression, variable, replacement, expected):
    result = d0exp_substitute(expression, variable, replacement)
    assert free_variables(result) == free_variables(expected)


@pytest.mark.parametrize("expression, variable, replacement, expected", subst_params)
def test_substitute_preserves_both_inputs(expression, variable, replacement, expected):
    e_before, r_before = copy.deepcopy(expression), copy.deepcopy(replacement)
    d0exp_substitute(expression, variable, replacement)
    assert expression == e_before
    assert replacement == r_before


@pytest.mark.parametrize("expression, variable, replacement, expected", subst_params)
def test_substitute_is_deterministic(expression, variable, replacement, expected):
    results = [d0exp_substitute(expression, variable, replacement) for _ in range(3)]
    assert results[0] == results[1] == results[2]


def test_substitute_table_in_pretty_notation():
    e = lam("y", add(V("x"), V("y")))
    assert d0exp_pretty(d0exp_substitute(e, "x", V("y"))) == "(lam y_1. (y + y_1))"
    e = fix("f", "n", add(V("x"), app(V("f"), V("n"))))
    assert d0exp_pretty(d0exp_substitute(e, "x", V("f"))) == "(fix f_1(n). (f + (f_1 n)))"
    e = let("y", V("x"), add(V("x"), V("y")))
    assert d0exp_pretty(d0exp_substitute(e, "x", V("y"))) == "(let y_1 = y in (y + y_1))"


def test_substitute_does_not_capture():
    result = d0exp_substitute(lam("y", add(V("x"), V("y"))), "x", V("y"))
    assert result != lam("y", add(V("y"), V("y")))
    assert free_variables(result) == {"y"}


def test_let_initializer_versus_body():
    assert d0exp_substitute(let("x", V("x"), V("x")), "x", I(3)) == let("x", I(3), V("x"))
    assert d0exp_substitute(let("y", V("x"), V("x")), "x", I(3)) == let("y", I(3), I(3))
    e = let("y", V("y"), add(V("x"), V("y")))
    assert d0exp_substitute(e, "x", V("y")) == let("y_1", V("y"), add(V("y"), V("y_1")))


def test_both_fix_binders_shadow():
    e = fix("f", "n", add(V("f"), V("n")))
    assert d0exp_substitute(e, "f", I(1)) == e
    assert d0exp_substitute(e, "n", I(1)) == e


def test_fix_with_equal_names_follows_the_evaluator():
    e = fix("f", "f", V("f"))
    applied = app(d0exp_substitute(e, "x", I(0)), I(41))
    assert base.d0exp_evaluate(applied) == base.D0Vint(41)
    renamed = d0exp_substitute(fix("g", "g", add(V("g"), V("x"))), "x", V("g"))
    env = base.ENVcns("g", base.D0Vint(100), base.ENVnil())
    assert base.d0exp_evaluate(app(renamed, I(1)), env) == base.D0Vint(101)


def test_replacement_is_inserted_as_is_and_not_substituted_again():
    r = add(V("x"), I(1))
    assert d0exp_substitute(pair(V("x"), V("x")), "x", r) == pair(r, r)


def test_fresh_names_are_not_reused_across_calls():
    e = lam("y", add(V("x"), V("y")))
    first = d0exp_substitute(e, "x", V("y"))
    assert first == lam("y_1", add(V("y"), V("y_1")))
    assert d0exp_substitute(e, "x", V("y")) == first


def test_three_nested_renamings_use_three_distinct_fresh_names():
    e = lam("a", lam("b", lam("a", add(V("x"), add(V("a"), V("b"))))))
    result = d0exp_substitute(e, "x", add(V("a"), V("b")))
    binders, node = [], result
    while isinstance(node, base.D0Elam):
        binders.append(node.arg1)
        node = node.arg2
    assert len(set(binders)) == 3
    expected = lam("p", lam("q", lam("r", add(add(V("a"), V("b")), add(V("r"), V("q"))))))
    assert d0exp_alpha_equal(result, expected)


@pytest.mark.parametrize("expression", DANGEROUS)
def test_substitute_does_not_evaluate(expression):
    with mock.patch.object(base.EvaluateVisitor, "__init__",
                           side_effect=AssertionError("evaluated")):
        d0exp_substitute(expression, "x", V("x"))
        d0exp_substitute(lam("x", expression), "x", I(0))
        d0exp_substitute(expression, "unbound", I(1))


def test_division_by_zero_survives_substitution():
    e = base.D0Eop2("/", V("x"), I(0))
    assert d0exp_substitute(e, "x", I(1)) == base.D0Eop2("/", I(1), I(0))


def test_substitution_visitor_can_be_used_directly():
    e = lam("y", add(V("x"), V("y")))
    visitor = SubstitutionVisitor.for_expression(e, "x", V("y"))
    assert e.accept(visitor) == lam("y_1", add(V("y"), V("y_1")))


########################################################################
# Free-variable property and semantic oracle
########################################################################

@pytest.mark.parametrize("expression, variable, replacement", FV_EXAMPLES)
def test_free_variable_property_on_examples(expression, variable, replacement):
    check_fv_property(expression, variable, replacement)


def test_exact_free_variables_of_examples():
    e = fix("f", "n", add(V("x"), app(V("f"), V("n"))))
    assert free_variables(d0exp_substitute(e, "x", add(V("f"), V("n")))) == {"f", "n"}
    e = lam("y", add(V("x"), V("y")))
    assert free_variables(d0exp_substitute(e, "x", V("y"))) == {"y"}


def test_target_not_free_gives_the_same_expression():
    e = lam("x", add(V("x"), V("y")))
    result = d0exp_substitute(e, "x", V("y"))
    assert result == e
    assert free_variables(result) == {"y"}


def test_free_variable_property_on_random_terms():
    for expression, variable, replacement in structural_cases():
        check_fv_property(expression, variable, replacement)


def test_fresh_names_are_generated_from_old_names_on_random_terms():
    for expression, variable, replacement in structural_cases(500, seed=7):
        result = d0exp_substitute(expression, variable, replacement)
        old = all_names(expression) | all_names(replacement)
        for name in all_names(result) - old:
            stem, _, number = name.rpartition("_")
            assert number.isdigit() and stem in old, name


def test_substitution_lemma_on_random_terms():
    """e[x := r] evaluates like e with x bound to the value of r (the evaluator
    is only an oracle here; a capture bug changes the result)."""
    cases = semantic_cases()
    meaningful = sum(
        check_substitution_lemma(e, x, r)[0] in ("int", "pair") for e, x, r in cases)
    assert meaningful > len(cases) * 0.9


########################################################################
# The alpha-equivalence helper
########################################################################

def test_alpha_equal_accepts_renamed_binders():
    assert d0exp_alpha_equal(lam("a", V("a")), lam("b", V("b")))
    assert d0exp_alpha_equal(let("a", V("y"), V("a")), let("b", V("y"), V("b")))
    assert d0exp_alpha_equal(fix("f", "n", app(V("f"), V("n"))),
                             fix("g", "m", app(V("g"), V("m"))))


def test_alpha_equal_rejects_different_structure():
    assert not d0exp_alpha_equal(lam("a", lam("b", V("a"))), lam("a", lam("b", V("b"))))
    assert not d0exp_alpha_equal(lam("a", V("y")), lam("a", V("z")))
    assert not d0exp_alpha_equal(lam("a", V("a")), lam("a", V("y")))


def test_alpha_equal_let_initializer_is_outside_the_binder():
    assert not d0exp_alpha_equal(let("a", V("a"), V("a")), let("b", V("b"), V("b")))
    assert d0exp_alpha_equal(let("a", V("a"), V("a")), let("b", V("a"), V("b")))


def test_alpha_equal_fix_with_equal_names_binds_the_parameter():
    assert d0exp_alpha_equal(fix("f", "f", V("f")), fix("g", "h", V("h")))
    assert not d0exp_alpha_equal(fix("f", "f", V("f")), fix("g", "h", V("g")))


########################################################################
# Visitor design
########################################################################

def _spy_on_accept(counts):
    patches = []
    for cls in ALL_CLASSES:
        original = cls.accept

        def accept(self, visitor, _cls=cls, _original=original):
            counts[_cls] = counts.get(_cls, 0) + 1
            return _original(self, visitor)

        patches.append(mock.patch.object(cls, "accept", accept))
    return patches


@pytest.mark.parametrize("operation", [
    lambda: d0exp_pretty(EVERYTHING),
    lambda: d0exp_substitute(EVERYTHING, "x", I(1)),
], ids=["pretty", "substitute"])
def test_every_constructor_dispatches_through_accept(operation):
    counts = {}
    patches = _spy_on_accept(counts)
    for p in patches:
        p.start()
    try:
        operation()
    finally:
        for p in patches:
            p.stop()
    for cls in ALL_CLASSES:
        assert counts.get(cls, 0) >= 1, cls.__name__


def test_printing_visits_each_node_once():
    counts = {}
    patches = _spy_on_accept(counts)
    for p in patches:
        p.start()
    try:
        d0exp_pretty(add(I(1), mul(V("x"), I(2))))
    finally:
        for p in patches:
            p.stop()
    assert sum(counts.values()) == 5


def test_no_central_type_test_in_the_source():
    source = (Path(__file__).resolve().parent.parent / "lambda1_visitors.py").read_text()
    for forbidden in ("isinstance(", ".ctag", "type(", "getattr(", "hasattr(", "match "):
        assert forbidden not in source


@pytest.mark.parametrize("cls", [PrettyPrintVisitor, SubstitutionVisitor])
def test_visitors_implement_the_supplied_interface(cls):
    assert issubclass(cls, base.D0ExpVisitor)
    assert cls.__abstractmethods__ == frozenset()


def test_supplied_free_variable_visitor_is_reused():
    assert base.d0exp_fvset(lam("x", add(V("x"), V("y")))) == {"y"}
