"""
Test cases for the Python translation of the eight-queens program.

Run with:  python3 test_eight_queens.py

These tests compare the Python translation's behavior against known
correct results for the N=8 puzzle, and exercise the helper functions
directly (since N is hard-coded as 8 in this translation, "boundary"
here means testing the edges of the fixed 8x8 board / row indices,
rather than varying board size).
"""

import io
import contextlib

import eight_queens as eq


def run_solve_silently():
    """Run solve() while discarding the printed board output, returning
    just the solution count."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        nsol = eq.solve()
    return nsol


def test_normal_case_total_solutions():
    """Normal input case: solving the standard 8-queens puzzle should
    find exactly 92 solutions (the well-known answer)."""
    nsol = run_solve_silently()
    assert nsol == 92, f"expected 92 solutions, got {nsol}"
    print("test_normal_case_total_solutions: PASS")


def test_boundary_first_and_last_row_index():
    """Boundary/unusual case: board_get and board_set at the very first
    (0) and very last (7) row indices, and board_get with an
    out-of-range index (as in the original ATS program, which returns
    -1 for i outside 0..7)."""
    bd = (0, 0, 0, 0, 0, 0, 0, 0)

    bd1 = eq.board_set(bd, 0, 5)
    assert eq.board_get(bd1, 0) == 5, "row 0 (first row) was not set correctly"

    bd2 = eq.board_set(bd, 7, 3)
    assert eq.board_get(bd2, 7) == 3, "row 7 (last row) was not set correctly"

    assert eq.board_get(bd, 8) == -1, "out-of-range row should return -1"
    assert eq.board_get(bd, -1) == -1, "negative row should return -1"

    print("test_boundary_first_and_last_row_index: PASS")


def test_custom_known_solution_is_valid():
    """Additional test of our own design: check that a specific,
    independently-known valid 8-queens solution is correctly judged
    safe by safety_test1/safety_test2, and that a board with two
    queens on the same diagonal is correctly judged unsafe.

    (0-indexed columns per row.) This is one of the 92 solutions:
    row 0 -> col 0, row 1 -> col 4, row 2 -> col 7, row 3 -> col 5,
    row 4 -> col 2, row 5 -> col 6, row 6 -> col 1, row 7 -> col 3
    """
    bd = (0, 0, 0, 0, 0, 0, 0, 0)
    solution = [0, 4, 7, 5, 2, 6, 1, 3]
    for row, col in enumerate(solution):
        bd = eq.board_set(bd, row, col)

    # Every queen must be safe with respect to all queens placed before it.
    for row in range(8):
        col = eq.board_get(bd, row)
        assert eq.safety_test2(row, col, bd, row - 1), (
            f"queen at row {row}, col {col} should be safe in this solution"
        )

    # Now corrupt the solution: put two queens on the same diagonal
    # (row 0 col 0, row 1 col 1 attack each other diagonally).
    bad_bd = eq.board_set(bd, 1, 1)
    assert not eq.safety_test2(1, 1, bad_bd, 0), (
        "queens on the same diagonal should be detected as unsafe"
    )

    print("test_custom_known_solution_is_valid: PASS")


if __name__ == "__main__":
    test_normal_case_total_solutions()
    test_boundary_first_and_last_row_index()
    test_custom_known_solution_is_valid()
    print("\nAll tests passed.")
