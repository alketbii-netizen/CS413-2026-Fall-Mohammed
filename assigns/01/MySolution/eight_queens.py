"""
The Eight-Queens Puzzle
Translated from ATS to Python 3.

Original source: "Introduction to Programming in ATS" by Hongwei Xi,
Chapter 3 (Functions), "Example: The Eight-Queens Puzzle"
https://ats-lang.github.io/FROZEN000/DOCUMENT/INT2PROGINATS/HTML/INT2PROGINATS-BOOK-onechunk.html

A board configuration is represented as a tuple of 8 integers
(board[i] gives the column position of the queen placed on row i),
mirroring the ATS program's "int8" tuple representation.
"""

N = 8


def print_dots(i: int) -> None:
    if i > 0:
        print(". ", end="")
        print_dots(i - 1)


def print_row(i: int) -> None:
    print_dots(i)
    print("Q ", end="")
    print_dots(N - i - 1)
    print()


def print_board(bd) -> None:
    for i in range(N):
        print_row(bd[i])
    print()


def board_get(bd, i: int) -> int:
    if 0 <= i < N:
        return bd[i]
    return -1


def board_set(bd, i: int, j: int):
    if 0 <= i < N:
        new_bd = list(bd)
        new_bd[i] = j
        return tuple(new_bd)
    return bd


def safety_test1(i0: int, j0: int, i: int, j: int) -> bool:
    """Queens at (i0, j0) and (i, j) do not attack each other:
    they must not share a column, and they must not share a diagonal."""
    return j0 != j and abs(i0 - i) != abs(j0 - j)


def safety_test2(i: int, j: int, bd, i0: int) -> bool:
    """Position (i, j) is safe with respect to all queens already
    placed on rows 0 through i0 of board bd."""
    if i0 >= 0:
        return (
            safety_test1(i0, board_get(bd, i0), i, j)
            and safety_test2(i, j, bd, i0 - 1)
        )
    return True


def search(bd, i: int, j: int, nsol: int) -> int:
    """Backtracking search for queen placements on rows 0 through N-1.
    Returns the total number of solutions found.

    NOTE on translation: the original ATS function is written as a
    tail-recursive function, and the ATS compiler turns tail calls into
    a loop that uses no extra stack space. Python does not perform this
    optimization, so a *direct*, call-for-call translation of the ATS
    code (each ATS tail call turned into "return search(...)") overflows
    Python's recursion limit well before all 92 solutions are found: the
    call chain for the full search involves far more than N=8 nested
    calls, since every recursive step -- not just each row of the board
    -- adds a Python stack frame that is never popped until the whole
    search finishes. This function is therefore written as an explicit
    while-loop that mirrors the state transitions of the ATS version
    (the same bd/i/j/nsol updates, in the same order) without recursion.
    """
    while True:
        if j < N:
            if safety_test2(i, j, bd, i - 1):
                bd1 = board_set(bd, i, j)
                if i + 1 == N:
                    print(f"Solution #{nsol + 1}:\n")
                    print_board(bd1)
                    nsol += 1
                    j += 1  # bd, i unchanged; try next column in this row
                else:
                    bd, i, j = bd1, i + 1, 0  # positioning next piece
            else:
                j += 1
        else:
            if i > 0:
                i, j = i - 1, board_get(bd, i - 1) + 1
            else:
                return nsol


def solve() -> int:
    """Run the search from an empty board and return the solution count."""
    bd0 = (0, 0, 0, 0, 0, 0, 0, 0)
    return search(bd0, 0, 0, 0)


def main() -> None:
    nsol = solve()
    print(f"Total number of solutions = {nsol}")


if __name__ == "__main__":
    import sys
    sys.setrecursionlimit(10000)
    main()
