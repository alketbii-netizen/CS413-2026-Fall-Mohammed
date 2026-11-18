"""Solver and lazy-stream tests: every success path runs the LAMBDA3 program."""
import time
import unittest
from collections import Counter
from contextlib import contextmanager
from unittest import mock

from solver import queens as Q

L = Q.L
FIRST_8 = (0, 4, 7, 5, 2, 6, 1, 3)
LAST_8 = (7, 3, 0, 2, 5, 1, 6, 4)


@contextmanager
def count_applications():
    """Count LAMBDA3 applications of the solver's recursive functions.

    Wraps lambda3._d0val_apply (called by the interpreter for every function
    application) and tallies calls of the fix-bound functions `tc`
    (try_column) and `chk` (check_safe).  This is an observable trace hook:
    if a tail had been forced, these counters would move.
    """
    real = L._d0val_apply
    counts = Counter()

    def counting(fn, arg):
        if isinstance(fn, L.D0Vfix):
            counts[fn.arg2.arg1] += 1
        return real(fn, arg)

    with mock.patch.object(L, "_d0val_apply", counting):
        yield counts


def take(stream, k):
    out = []
    for _ in range(k):
        ev, stream = Q.next_event(stream)
        if ev is None:
            break
        out.append(ev)
    return out, stream


def valid(board):
    return all(board[i] != board[j] and abs(board[i] - board[j]) != j - i
               for i in range(len(board)) for j in range(i + 1, len(board)))


class TestSafety(unittest.TestCase):
    """Required test 1, via the LAMBDA3 CPS checker (one queen per row, so
    'same row' for the stored column list means two queens in one column)."""

    def test_same_column(self):
        self.assertFalse(Q.safe(3, [3]))
        self.assertFalse(Q.safe(0, [0, 2, 4]))

    def test_diagonal_down_right(self):
        self.assertFalse(Q.safe(4, [3]))          # col - distance
        self.assertFalse(Q.safe(5, [3, 0]))       # two rows back

    def test_diagonal_down_left(self):
        self.assertFalse(Q.safe(2, [3]))          # col + distance
        self.assertFalse(Q.safe(1, [3, 6]))

    def test_safe_placements(self):
        self.assertTrue(Q.safe(0, []))
        self.assertTrue(Q.safe(1, [3]))
        self.assertTrue(Q.safe(6, [0, 4, 7, 5, 2]))


class TestCPSPaths(unittest.TestCase):
    """Required test 2: success, failure, and resumption at the next candidate."""

    def test_4x4_trace_prefix(self):
        evs = list(Q.iterate(4))
        head = [(e["event"], e.get("column"), e.get("row"), e.get("board")) for e in evs[:16]]
        self.assertEqual(head, [
            ("try", 0, 0, []), ("place", 0, 0, [0]),
            ("try", 0, 1, [0]), ("reject", 0, 1, [0]),       # conflict -> next column
            ("try", 1, 1, [0]), ("reject", 1, 1, [0]),
            ("try", 2, 1, [0]), ("place", 2, 1, [0, 2]),     # safe -> deeper search
            ("try", 0, 2, [0, 2]), ("reject", 0, 2, [0, 2]),
            ("try", 1, 2, [0, 2]), ("reject", 1, 2, [0, 2]),
            ("try", 2, 2, [0, 2]), ("reject", 2, 2, [0, 2]),
            ("try", 3, 2, [0, 2]), ("reject", 3, 2, [0, 2]),
        ])
        # row 2 exhausted -> failure continuation backtracks row 1 and
        # resumes at the NEXT candidate column 3 of row 1
        self.assertEqual(evs[16], {"event": "backtrack", "column": 2, "row": 1, "board": [0]})
        self.assertEqual(evs[17], {"event": "try", "column": 3, "row": 1, "board": [0]})

    def test_success_continuation_resumes_after_solution(self):
        evs = list(Q.iterate(4))
        i = next(k for k, e in enumerate(evs) if e["event"] == "solution")
        self.assertEqual(evs[i]["board"], [1, 3, 0, 2])
        self.assertEqual(evs[i - 1]["event"], "place")
        # after the solution the search resumes by backtracking the last queen
        self.assertEqual(evs[i + 1], {"event": "backtrack", "column": 2, "row": 3, "board": [1, 3, 0]})
        self.assertEqual([tuple(e["board"]) for e in evs if e["event"] == "solution"],
                         [(1, 3, 0, 2), (2, 0, 3, 1)])


class TestAllSolutions(unittest.TestCase):
    """Required tests 3 and 4."""

    @classmethod
    def setUpClass(cls):
        cls.events = list(Q.iterate(8))

    def test_92_distinct_valid_in_order(self):
        sols = [tuple(e["board"]) for e in self.events if e["event"] == "solution"]
        self.assertEqual(len(sols), 92)
        self.assertEqual(len(set(sols)), 92)
        self.assertTrue(all(len(s) == 8 and valid(s) for s in sols))
        self.assertEqual(sols, sorted(sols))           # lexicographic = DFS left-to-right
        self.assertEqual((sols[0], sols[-1]), (FIRST_8, LAST_8))

    def test_deterministic(self):
        again = [e for e in Q.iterate(8) if e["event"] == "solution"]
        self.assertEqual(again, [e for e in self.events if e["event"] == "solution"])

    def test_done_exactly_once_and_last(self):
        kinds = [e["event"] for e in self.events]
        self.assertEqual(kinds.count("done"), 1)
        self.assertEqual(self.events[-1], {"event": "done"})
        self.assertEqual(set(kinds), {"try", "place", "reject", "backtrack", "solution", "done"})

    def test_event_snapshots_and_coordinates(self):
        board = []           # replay the trace and check every snapshot
        for e in self.events:
            k = e["event"]
            if k == "try":
                self.assertEqual((e["row"], e["board"]), (len(board), board))
            elif k == "place":
                self.assertTrue(valid(e["board"]))
                self.assertEqual(e["board"], board + [e["column"]])
                self.assertEqual(e["row"], len(board))
                board = e["board"]
            elif k == "reject":
                self.assertEqual(e["board"], board)
                self.assertFalse(valid(board + [e["column"]]))
            elif k == "backtrack":
                self.assertEqual(board, e["board"] + [e["column"]])
                self.assertEqual(e["row"], len(e["board"]))
                board = e["board"]
            elif k == "solution":
                self.assertEqual(e["board"], board)
                self.assertEqual(len(board), 8)
            for v in e.get("board", []):
                self.assertTrue(0 <= v < 8)


class TestLaziness(unittest.TestCase):
    """Required test 5: proven with a trace counter and the tails' forced flags."""

    def test_open_performs_no_search(self):
        with count_applications() as n:
            s = Q.open_stream(8)
        self.assertEqual((n["tc"], n["chk"]), (0, 0))
        self.assertFalse(Q.is_forced(s))

    def test_forcing_one_cell_does_not_force_tail(self):
        s = Q.open_stream(8)
        with count_applications() as n:
            ev, tail = Q.next_event(s)
        self.assertEqual(ev["event"], "try")
        self.assertEqual((n["tc"], n["chk"]), (1, 0))   # safety not yet checked
        self.assertTrue(Q.is_forced(s))
        self.assertFalse(Q.is_forced(tail))

    def test_bounded_prefix_leaves_rest_unforced(self):
        s = Q.open_stream(8)
        with count_applications() as n:
            evs, tail = take(s, 10)
        self.assertEqual(len(evs), 10)
        self.assertFalse(Q.is_forced(tail))
        self.assertLess(n["tc"] + n["chk"], 30)
        with count_applications() as m:
            take(tail, 10)
        self.assertGreater(m["tc"] + m["chk"], 0)      # work happens only on demand

    def test_large_board_prefix_is_fast(self):
        t = time.perf_counter()
        s = Q.open_stream(10)
        evs, tail = take(s, 25)
        self.assertLess(time.perf_counter() - t, 2.0)   # full 10x10 takes minutes
        self.assertEqual(len(evs), 25)
        self.assertFalse(Q.is_forced(tail))

    def test_invalid_sizes(self):
        for bad in (3, 11, 8.0, "8", True, None):
            with self.assertRaises(ValueError):
                Q.open_stream(bad)


if __name__ == "__main__":
    unittest.main()
