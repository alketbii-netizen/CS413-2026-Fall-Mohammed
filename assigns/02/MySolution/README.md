# Assignment 2: Pairs, Projections, and Eight-Queens as a LAMBDA0 Term

Python 3.12 or later is required (the starter code uses the `type` alias syntax).

## What is in this directory

| File | Purpose |
| --- | --- |
| `lambda0.py` | Extended copy of the starter interpreter (pairs and projections) |
| `TEST/test01_lambda0.py` | The instructor's starter tests, unchanged, run against my copy |
| `TEST/test02_lambda0.py` | My tests for pairs and projections (42 tests) |
| `eight_queens.dats` | The original ATS2 eight-queens program that I translated |
| `queens_lambda0.py` | The translated LAMBDA0 term and its evaluation driver |
| `TEST/test03_queens.py` | Tests for the translation (18 tests) |
| `TEST/ats_expected_output.txt` | Output of the original ATS2 program (compiled with `patscc`) |
| `AI-TRANSCRIPT.md` | How AI was used and how its output was checked |

## Commands

```bash
# all tests (about 30 seconds; the full 8x8 search is part of test03)
python3 -m unittest discover -s TEST -p 'test0*.py'      # or: make -C TEST
python3 TEST/test02_lambda0.py                           # pairs/projections only
python3 TEST/test03_queens.py                            # queens only

# run the translation
python3 queens_lambda0.py            # all 92 solutions for 8 queens (about 20 s)
python3 queens_lambda0.py 6          # board size 6

# regenerate the original ATS2 output (needs the ATS2 compiler, e.g. apt install ats2-lang)
patscc -DATS_MEMALLOC_LIBC -o eight_queens eight_queens.dats && ./eight_queens > TEST/ats_expected_output.txt
python3 queens_lambda0.py | diff - TEST/ats_expected_output.txt && echo identical
```

## Tasks 1 and 2: pairs and projections in `lambda0.py`

I added cases for `T0Mpair`, `T0Mpfst` and `T0Mpsnd` to all four functions:

- `t0erm_size`: one node for the constructor plus the sizes of its subterms.
- `t0erm_fvset`: the union of both components' free variables, or the operand's. These constructors bind nothing.
- `t0erm_subst0`: recursion into both components or the operand, keeping the constructor. Binding behavior of `T0Mlam` and `T0Mfix` is untouched.
- `t0erm_cbv_evaluate0`: a pair evaluates its first component and then its second, and returns a `T0Mpair` of the two values. A projection evaluates its operand and returns the matching component, or raises `TypeError` if the operand is not a pair. Both components are always evaluated, so `T0Mpfst(T0Mpair(T0Mint(1), 1/0))` raises `ZeroDivisionError`.

### Changes to the interpreter beyond the assignment

I made three internal changes so the queens search finishes in seconds. None changes what any term evaluates to, the order of evaluation, or which errors are raised, and each has a test.

1. **Tail positions loop instead of recursing.** The body of an application and the selected branch of a conditional are evaluated in a `while` loop. The starter evaluator recursed on every tail call, so the queens search (about 16,000 tail calls) used several gigabytes of Python stack and was killed before finishing. `test_deep_tail_recursion_does_not_exhaust_the_python_stack` recurses 50,000 deep, and I confirmed it fails with `RecursionError` on the version without the loop.
2. **Cached free-variable sets, used to skip substitution.** `t0erm_subst0` returns a subterm unchanged when it does not contain the variable being replaced. The set is remembered on each node (not a dataclass field, so equality and `repr` are unaffected). `test_substitution_matches_naive_reference` compares the result with a plain reference implementation on 1,500 random terms.
3. **A pair that has been evaluated is remembered as a value**, so evaluating it again (for example after substitution) does not rebuild it. Without this, the growing list of found solutions was re-walked at every step and the 7x7 search took 20 s instead of 4 s.

No new primitive operations were needed: the starter already has `<`, `>=`, `==`, `!=`, `+`, `-` and unary `-`, and `abs` is written in the term (see below).

## Task 4: mapping from ATS2 to LAMBDA0

`eight_queens.dats` is my own earlier translation-exercise program from Assignment 1, based on the eight-queens example in Hongwei Xi's *Introduction to Programming in ATS*, chapter 3. It prints every solution as it finds it and then the total, so the term returns both the count and the list of solutions.

| ATS2 | LAMBDA0 term in `queens_lambda0.py` |
| --- | --- |
| `abs` | `ABS` = `lam v. if v < 0 then -v else v` |
| `safety_test1(i0, j0, i, j)` | `SAFETY_TEST1`, a curried `lam`; `andalso` is a `T0Mif0` with `false` in the else branch, so it short-circuits as in ATS |
| `safety_test2(i, j, bd, i0)` | `SAFETY_TEST2` = `lam i. lam j. fix go(p). ...` where `p = (i0, bd)`; recursion with `T0Mfix` |
| `search(bd, i, j, nsol)` | `search_term(n)` = `fix search(st). ...`, where `st = (bd, (i, (j, (nsol, sols))))` |
| `board_get`, `board_set` | `fst bd` and `pair(j, bd)` on the stack representation below |
| `N` | `T0Mint(n)` built into the term, so the board size is a parameter of the Python builder |
| `print_board` and the printing in `search` | the extra accumulator `sols`, a list of the boards found; Python only formats it afterwards |
| `main0` | the final application of `search` to the initial state |

**Data representations.**

- *Board.* The ATS2 board is an 8-tuple indexed by row. I use a stack instead: a right-nested list of pairs, `(col_of_latest_row, (col_of_previous_row, ... NIL))`, where `NIL` is `T0Mint(0)`. Placing a queen is `pair(j, bd)`, reading the latest row is `fst bd`, and backtracking is `snd bd`. This avoids the 8-way `if` chains of `board_get`/`board_set` and keeps the same search order, so the solutions come out in the same order.
- *State of the search.* `fix` has one parameter, so the four ATS arguments plus the solution accumulator are packed into a nested tuple and unpacked with projections inside the body.
- *Solutions.* A list of boards (each a stack), newest first. `decode_result` reverses it and each board for display.
- *Closed term.* Helper functions are bound with `let x = value in body`, which is `(lam x. body) value`, so each definition is a closed value when it is substituted. `queens_term` asserts that `t0erm_fvset` of the whole term is empty.

**What Python does.** It builds the term, runs `t0erm_cbv_evaluate0`, decodes the resulting pair, and prints it. The search, the conflict checks and the backtracking all happen inside the evaluation of the term.

**Changes needed for call-by-value.**

- `andalso` must be an `if`, not a function call, or the right operand would always be evaluated (and `safety_test2` would run past row 0 into an empty board).
- The conditional's branches are evaluated lazily by the interpreter, which is what makes the base case of the recursion work.
- Every `let` initializer is evaluated before the body, which is the order ATS2 uses.
- Tail calls need the evaluator change described above.

## Results

- `python3 TEST/test02_lambda0.py`: 42 tests pass. `test01_lambda0.py` (27 starter tests) also passes on my copy.
- `python3 TEST/test03_queens.py`: 18 tests pass in about 27 s.
- **Comparison with the original ATS2 program.** The ATS2 program enumerates solutions and prints the total. The LAMBDA0 term finds the same 92 solutions in the same order (compared board by board in `test_same_solutions_in_the_same_order`), and `python3 queens_lambda0.py | diff - TEST/ats_expected_output.txt` reports no differences across all 1013 lines.
- Every returned board is checked independently for no shared row, column or diagonal. Smaller boards give the known counts (n=1..7: 1, 0, 0, 2, 10, 4, 40) and every board is valid.
- `safety_test1` and `safety_test2` are evaluated on their own by the interpreter: same column, diagonals in all four directions, safe squares, symmetry, and an exhaustive comparison with the Python formula on a 5x5 grid.

## Limitations

- The interpreter is substitution-based, so the 8x8 search takes about 20 seconds, compared with milliseconds for compiled ATS2.
- Non-tail recursion is still bounded by Python's recursion limit. `safety_test2` is not a tail call (it is wrapped in `andalso`) but only goes 8 deep. `queens_lambda0.py` raises the limit and runs the evaluation in a thread with a large stack for safety.
- The term returns the list of solutions instead of printing them, because LAMBDA0 has no output.

## How I reviewed and verified AI-generated code

I used Claude to draft the interpreter extension, the queens term and the tests. See `AI-TRANSCRIPT.md` for details. In short:

- I ran everything rather than trusting it. The first full 8x8 run used about 1 GB of memory per minute and had to be stopped; that led to the tail-call change.
- I compared the term's results with the compiled ATS2 program's real output, not with numbers I remembered.
- I wrote tests that would catch the failure modes I was worried about: the unselected pair component must still be evaluated, evaluation order must be left to right, and each optimization must agree with a plain reference.
- One of my own tests was wrong (it took one projection too many); I fixed the test, not the implementation, after tracing it by hand.
