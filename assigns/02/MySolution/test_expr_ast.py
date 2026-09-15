"""
Test cases for expr_ast.py.

Run with:  python3 test_expr_ast.py
"""

import expr_ast as ast


def test_normal_case_operator_precedence():
    """Normal input case: standard operator precedence (* before +)."""
    result = ast.evaluate(ast.parse("1 + 2 * 3"))
    assert result == 7.0, f"expected 7.0, got {result}"
    print("test_normal_case_operator_precedence: PASS")


def test_boundary_left_associativity():
    """Boundary/unusual case: chained same-precedence operators must be
    left-associative, not right-associative. This is the exact bug found
    and fixed during development: '10 - 3 - 2' must be (10-3)-2 = 5,
    not 10-(3-2) = 9. Also checks chained division for the same reason."""
    result = ast.evaluate(ast.parse("10 - 3 - 2"))
    assert result == 5.0, f"expected 5.0 (left-associative), got {result}"

    result2 = ast.evaluate(ast.parse("100 / 10 / 5"))
    assert result2 == 2.0, f"expected 2.0 (left-associative), got {result2}"

    print("test_boundary_left_associativity: PASS")


def test_custom_parentheses_and_unary_minus():
    """Additional test of our own design: parentheses overriding default
    precedence, combined with a leading unary minus."""
    result = ast.evaluate(ast.parse("-(2 + 3) * 4"))
    assert result == -20.0, f"expected -20.0, got {result}"

    # Also check the AST shape directly, not just the numeric result,
    # since a wrong tree could coincidentally evaluate to the right
    # number for simple cases.
    tree = ast.parse("(1 + 2) * 3")
    assert isinstance(tree, ast.BinOp) and tree.op == '*'
    assert isinstance(tree.left, ast.BinOp) and tree.left.op == '+'
    assert isinstance(tree.right, ast.Num) and tree.right.value == 3.0

    print("test_custom_parentheses_and_unary_minus: PASS")


if __name__ == "__main__":
    test_normal_case_operator_precedence()
    test_boundary_left_associativity()
    test_custom_parentheses_and_unary_minus()
    print("\nAll tests passed.")
