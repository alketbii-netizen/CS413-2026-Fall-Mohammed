"""Tests for the eight-queens LAMBDA0 term (queens_lambda0.py).

Run with: python3 TEST/test03_queens.py   (or: make -C TEST TEST=test03_queens.py)
The full 8x8 search runs once (about a minute) and is shared by the tests.

TEST/ats_expected_output.txt is the output of the original ATS2 program
(../eight_queens.dats, compiled with patscc), which prints every solution
in discovery order and then the total count. See README.md to regenerate it.
"""

import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lambda0 import (
    T0Mint, T0Mbtf, T0Mpair, T0Mfix,
    t0erm_cbv_evaluate0, t0erm_fvset, t0erm_size,
)
import queens_lambda0 as q
from queens_lambda0 import I, app, run_queens, queens_term

# Known numbers of solutions of the n-queens problem (OEIS A000170).
KNOWN_COUNTS = {1: 1, 2: 0, 3: 0, 4: 2, 5: 10, 6: 4, 7: 40, 8: 92}


def read_ats_output():
    """Parse the original ATS2 program's output into (count, boards)."""
    text = (HERE / "ats_expected_output.txt").read_text()
    boards = []
    for block in re.split(r"Solution #\d+:\n", text)[1:]:
        rows = [line.split() for line in block.strip().split("\n")
                if line.strip() and not line.startswith("Total")]
        boards.append([row.index("Q") for row in rows])
    count = int(re.search(r"Total number of solutions = (\d+)", text).group(1))
    return count, boards


def is_valid_board(board, n):
    """n queens, one per row: no shared column and no shared diagonal."""
    if len(board) != n or any(not 0 <= c < n for c in board):
        return False
    for i in range(n):
        for k in range(i + 1, n):
            if board[i] == board[k] or abs(board[i] - board[k]) == k - i:
                return False
    return True


class TestAgainstOriginalATS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ats_count, cls.ats_boards = read_ats_output()
        cls.count, cls.boards = run_queens(8)

    def test_ats_reference_is_the_known_answer(self):
        self.assertEqual(self.ats_count, 92)
        self.assertEqual(len(self.ats_boards), 92)

    def test_same_number_of_solutions(self):
        self.assertEqual(self.count, self.ats_count)
        self.assertEqual(len(self.boards), self.ats_count)

    def test_same_solutions_in_the_same_order(self):
        # The ATS2 program enumerates solutions in discovery order; so must we.
        self.assertEqual(self.boards, self.ats_boards)

    def test_every_returned_board_is_valid(self):
        for board in self.boards:
            with self.subTest(board=board):
                self.assertTrue(is_valid_board(board, 8))

    def test_solutions_are_distinct(self):
        self.assertEqual(len({tuple(b) for b in self.boards}), 92)

    def test_first_and_last_solutions(self):
        self.assertEqual(self.boards[0], [0, 4, 7, 5, 2, 6, 1, 3])
        self.assertEqual(self.boards[-1], [7, 3, 0, 2, 5, 1, 6, 4])


class TestBoardSizes(unittest.TestCase):
    def test_counts_for_smaller_boards(self):
        for n in range(1, 8):
            with self.subTest(n=n):
                count, boards = run_queens(n)
                self.assertEqual(count, KNOWN_COUNTS[n])
                self.assertEqual(len(boards), KNOWN_COUNTS[n])
                for board in boards:
                    self.assertTrue(is_valid_board(board, n), board)

    def test_four_queens_exact_solutions(self):
        _, boards = run_queens(4)
        self.assertEqual(boards, [[1, 3, 0, 2], [2, 0, 3, 1]])


class TestConflictChecking(unittest.TestCase):
    """safety_test1/2 evaluated on their own by the interpreter."""

    def safe1(self, i0, j0, i, j):
        term = app(q.closed_safety_test1(), I(i0), I(j0), I(i), I(j))
        value = t0erm_cbv_evaluate0(term)
        self.assertIsInstance(value, T0Mbtf)
        return value.arg1

    def test_same_column_conflicts(self):
        self.assertFalse(self.safe1(0, 3, 5, 3))

    def test_diagonal_conflicts_both_directions(self):
        self.assertFalse(self.safe1(0, 0, 3, 3))   # down-right
        self.assertFalse(self.safe1(0, 5, 3, 2))   # down-left
        self.assertFalse(self.safe1(4, 4, 3, 3))   # up-left
        self.assertFalse(self.safe1(4, 4, 6, 6))

    def test_knight_move_and_distant_squares_are_safe(self):
        self.assertTrue(self.safe1(0, 0, 1, 2))
        self.assertTrue(self.safe1(0, 0, 2, 1))
        self.assertTrue(self.safe1(2, 7, 6, 1))

    def test_safe1_is_symmetric(self):
        for a in range(4):
            for b in range(4):
                for c in range(4):
                    for d in range(4):
                        if (a, b) != (c, d):
                            self.assertEqual(self.safe1(a, b, c, d), self.safe1(c, d, a, b))

    def test_safe1_agrees_with_python_formula(self):
        for i0 in range(5):
            for j0 in range(5):
                for i in range(5):
                    for j in range(5):
                        expected = j0 != j and abs(i0 - i) != abs(j0 - j)
                        self.assertEqual(self.safe1(i0, j0, i, j), expected)

    def safe2(self, i, j, columns_by_row):
        """Is (i, j) safe against queens on rows 0..i-1 given by
        columns_by_row? The term's board is a stack (newest row first)."""
        stack = I(0)
        for col in columns_by_row:
            stack = T0Mpair(I(col), stack)
        term = app(q.closed_safety_test2(), I(i), I(j), T0Mpair(I(i - 1), stack))
        return t0erm_cbv_evaluate0(term).arg1

    def test_safe2_on_the_empty_board(self):
        for j in range(8):
            self.assertTrue(self.safe2(0, j, []))

    def test_safe2_checks_every_earlier_row(self):
        placed = [0, 4, 7]               # first three rows of solution #1
        self.assertTrue(self.safe2(3, 5, placed))
        self.assertFalse(self.safe2(3, 0, placed))   # column of row 0
        self.assertFalse(self.safe2(3, 7, placed))   # column of row 2
        self.assertFalse(self.safe2(3, 6, placed))   # diagonal of row 2 (7,2)
        self.assertFalse(self.safe2(3, 3, placed))   # diagonal of row 0 (0,0)

    def test_safe2_agrees_with_python_formula(self):
        placed = [1, 3]
        for j in range(5):
            expected = all(
                placed[r] != j and abs(placed[r] - j) != 2 - r for r in range(2))
            self.assertEqual(self.safe2(2, j, placed), expected)


class TestTranslationIsAClosedTerm(unittest.TestCase):
    def test_term_is_closed_and_uses_recursion(self):
        term = queens_term(8)
        self.assertEqual(t0erm_fvset(term), frozenset())

        def contains_fix(t):
            if isinstance(t, T0Mfix):
                return True
            return any(contains_fix(getattr(t, f)) for f in ("arg1", "arg2", "arg3")
                       if hasattr(t, f) and hasattr(getattr(t, f), "ctag"))
        self.assertTrue(contains_fix(term))
        self.assertGreater(t0erm_size(term), 100)  # a real program, not a stub

    def test_term_evaluates_to_a_pair_of_count_and_solutions(self):
        value = t0erm_cbv_evaluate0(queens_term(4))
        self.assertIsInstance(value, T0Mpair)
        self.assertEqual(value.arg1, T0Mint(2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
