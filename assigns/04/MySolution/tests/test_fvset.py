"""Free-variable analysis: every expression constructor, duplicate
occurrences, nested bindings, recursive functions (fix), and let
initializer scope (Assign04.md, Task 4)."""

from lambdaweb.fvset import d0exp_fvset
from lambdaweb.lambda1 import (
    D0Eint, D0Ebtf, D0Eop1, D0Eop2, D0Evar,
    D0Elam, D0Efix, D0Eapp, D0Eif0, D0Elet,
    D0Epair, D0Epfst, D0Epsnd,
)


def test_return_type_is_frozenset():
    result = d0exp_fvset(D0Evar("x"))
    assert isinstance(result, frozenset)


def test_int_and_bool_literals_have_no_free_vars():
    assert d0exp_fvset(D0Eint(5)) == frozenset()
    assert d0exp_fvset(D0Ebtf(True)) == frozenset()


def test_var_is_its_own_free_variable():
    assert d0exp_fvset(D0Evar("x")) == frozenset({"x"})


def test_op1():
    assert d0exp_fvset(D0Eop1("-1", D0Evar("x"))) == frozenset({"x"})


def test_op2_unions_both_sides():
    assert d0exp_fvset(D0Eop2("+", D0Evar("x"), D0Evar("y"))) == frozenset({"x", "y"})


def test_duplicate_variable_occurrences_are_deduplicated():
    assert d0exp_fvset(D0Eop2("+", D0Evar("x"), D0Evar("x"))) == frozenset({"x"})


def test_lam_binds_its_parameter():
    assert d0exp_fvset(D0Elam("x", D0Evar("x"))) == frozenset()


def test_lam_unused_parameter_is_not_an_error_and_body_free_vars_remain():
    # An unused binding is not an error under this assignment's lint rule;
    # it just means the bound name does not appear in the free-variable set.
    assert d0exp_fvset(D0Elam("x", D0Evar("y"))) == frozenset({"y"})


def test_nested_lam_bindings():
    dexp = D0Elam("x", D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y"))))
    assert d0exp_fvset(dexp) == frozenset()


def test_fix_binds_both_function_name_and_parameter():
    # fix f(x). f(x)  -- both f and x are bound in the body.
    dexp = D0Efix("f", "x", D0Eapp(D0Evar("f"), D0Evar("x")))
    assert d0exp_fvset(dexp) == frozenset()


def test_fix_body_can_still_have_other_free_vars():
    dexp = D0Efix("f", "x", D0Evar("y"))
    assert d0exp_fvset(dexp) == frozenset({"y"})


def test_recursive_factorial_is_closed():
    # The Assignment-4 canned factorial example, built directly here.
    fact = D0Efix(
        "fact", "n",
        D0Eif0(
            D0Eop2("==", D0Evar("n"), D0Eint(0)),
            D0Eint(1),
            D0Eop2("*", D0Evar("n"), D0Eapp(D0Evar("fact"), D0Eop2("-", D0Evar("n"), D0Eint(1)))),
        ),
    )
    assert d0exp_fvset(fact) == frozenset()
    assert d0exp_fvset(D0Eapp(fact, D0Eint(5))) == frozenset()


def test_app_unions_function_and_argument():
    assert d0exp_fvset(D0Eapp(D0Evar("f"), D0Evar("x"))) == frozenset({"f", "x"})


def test_if0_traverses_all_three_branches():
    dexp = D0Eif0(D0Evar("a"), D0Evar("b"), D0Evar("c"))
    assert d0exp_fvset(dexp) == frozenset({"a", "b", "c"})


def test_let_binds_name_in_body_only_not_in_initializer():
    # let x = x in x  --  the *initializer*'s x is free (x is not yet
    # bound while the initializer is evaluated); the *body*'s x is bound.
    dexp = D0Elet("x", D0Evar("x"), D0Evar("x"))
    assert d0exp_fvset(dexp) == frozenset({"x"})


def test_let_with_closed_initializer_and_bound_body():
    dexp = D0Elet("x", D0Eint(1), D0Evar("x"))
    assert d0exp_fvset(dexp) == frozenset()


def test_let_body_can_have_other_free_vars():
    dexp = D0Elet("x", D0Eint(1), D0Evar("y"))
    assert d0exp_fvset(dexp) == frozenset({"y"})


def test_pair_and_projections():
    pair = D0Epair(D0Evar("a"), D0Evar("b"))
    assert d0exp_fvset(pair) == frozenset({"a", "b"})
    assert d0exp_fvset(D0Epfst(D0Evar("p"))) == frozenset({"p"})
    assert d0exp_fvset(D0Epsnd(D0Evar("p"))) == frozenset({"p"})
