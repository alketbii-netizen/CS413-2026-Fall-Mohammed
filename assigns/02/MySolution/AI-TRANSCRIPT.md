# AI-TRANSCRIPT

**AI tool used:** Claude (Anthropic), working with a Linux shell where it could run Python 3.12 and the ATS2 compiler (`patscc`).

## Context

My first submission for Assignment 2 solved a different task (an arithmetic expression parser). The `Assign02.md` I had downloaded was cut off after its Objective, and the AI and I guessed a task instead of checking with the instructor. This directory is the corrected work for the real specification: extend `lambda0.py` with pairs and projections, test it, and translate the eight-queens ATS2 program into a LAMBDA0 term.

## What I asked the AI to do, and what it produced

1. **Read the real specification and starter files** from the class repository (`assigns/02/Assign02.md`, `assigns/02/lambda0.py`, `assigns/02/TEST/test01_lambda0.py`).
2. **Extend `lambda0.py`** with `T0Mpair`, `T0Mpfst`, `T0Mpsnd` in `t0erm_size`, `t0erm_fvset`, `t0erm_subst0` and `t0erm_cbv_evaluate0`. This was straightforward and correct on the first run of the tests.
3. **Write `TEST/test02_lambda0.py`** covering the cases listed in the assignment.
4. **Translate my own ATS2 program** (`eight_queens.dats`, from Assignment 1) into a LAMBDA0 term, `queens_lambda0.py`. I chose the data representations (see `README.md`) after reading the ATS2 source.
5. **Write `TEST/test03_queens.py`**, comparing against the output of the ATS2 program compiled with `patscc`.

## Problems found by running the code

- **A wrong test of mine.** In `test_nested_pairs` I took one `snd` too many, so the test raised `TypeError`. I traced the term by hand, saw that the implementation was right and the test was wrong, and fixed the test. I kept the over-long projection as an explicit `assertRaises(TypeError)` case.
- **A wrong size threshold.** `test03` first asserted the queens term had more than 300 nodes; it has 210. That was an arbitrary guess, not a bug, so I lowered it to "more than 100".
- **The full 8x8 search ran out of memory.** The first complete run was correct for small boards (N=4, 5, 6 gave 2, 10, 4 solutions) but for N=8 memory grew by about 1 GB per minute and would have exhausted the machine. The cause is that the starter evaluator uses a Python stack frame for every tail call, and the search makes about 16,000 of them. I made tail positions loop. The 8x8 run then used about 14 MB and finished with 92 solutions in 261 s.
- **Still too slow.** Two further behavior-preserving changes (cached free variables to skip substitution, and remembering that an evaluated pair is already a value) brought the 8x8 run to about 20 s. Profiling showed the second one was needed: 7x7 took 20 s with only the first change and 4 s with both, because the accumulated list of solutions was being re-walked at every step.

## How I verified the changes did not alter behavior

- All 27 instructor starter tests pass on my copy.
- `test_substitution_matches_naive_reference` compares the optimized `t0erm_subst0` with a plain reference on 1,500 random terms.
- `test_deep_tail_recursion_does_not_exhaust_the_python_stack` recurses 50,000 deep. I ran it on the version of `lambda0.py` before the tail change and confirmed it fails there, so the test does detect the problem it targets.
- The queens term returns the same 92 solutions in the same order as the ATS2 program (board-by-board test), and the printed output of `queens_lambda0.py` has no differences from the ATS2 output (`diff` over 1013 lines).
- Every board is also checked independently for no shared row, column, or diagonal, and smaller boards are compared with the known counts (1, 0, 0, 2, 10, 4, 40 for n = 1..7).

## What I did not rely on the AI for

- The expected results come from the compiled ATS2 program and from known counts, not from the AI's memory.
- The ATS2 source is my own file from Assignment 1; the AI did not write a new one for this task.
