# Eight Queens — AI-Assisted Translation

This folder contains the solution for CS413 Practice Assignment 01:
translating the eight-queens puzzle program from ATS to Python 3,
with AI assistance.

## Contents

- `eight_queens.dats` — the original ATS program.
- `eight_queens.py` — the Python 3 translation.
- `test_eight_queens.py` — automated test cases (normal, boundary, custom).
- `AI-TRANSCRIPT.md` — record of the AI-assisted development process.
- `ats_expected_output.txt` / `python_actual_output.txt` — full program
  outputs, verified identical.
- `diff_result.txt` — confirmation that the two outputs match exactly.

## How to run

Compile and run the original ATS program:

patscc -DATS_MEMALLOC_LIBC -o eight_queens eight_queens.dats
./eight_queens


Run the Python translation:

python3 eight_queens.py


Run the test suite:

python3 test_eight_queens.py


## AI Reflection

I used Claude to translate the ATS eight-queens program (from Xi's
*Introduction to Programming in ATS*) into Python 3. The AI did well
at reproducing the structure of the original faithfully — function
names, the tuple-based board representation, and the backtracking
logic all carried over cleanly. It also took the initiative to
actually install the ATS compiler and compile/run the original
program instead of only describing it, which meant the "original"
source I ended up with was verified rather than just plausible-looking.

The main weakness showed up immediately when the first version of the
Python translation was run: it crashed with a `RecursionError`. The
ATS `search` function is deliberately written in tail-recursive style,
and the book text itself notes this — because the ATS compiler
optimizes tail calls into a loop with constant stack space. Python has
no such optimization, so translating each ATS tail call directly into
`return search(...)` builds up one real stack frame per recursive step
across the entire search (not just one per board row), which blew past
Python's recursion limit long before all 92 solutions were found. This
is a genuine semantic gap between the two languages that a purely
syntactic translation cannot paper over.

To verify the fix (rewriting `search` as an explicit loop with the same
state transitions), I didn't just trust that it "looked right" — the
original ATS program was compiled and run, its full output was
captured, and it was diffed byte-for-byte against the Python program's
output. They matched exactly, including the order of all 92 solutions.
Understanding why the recursion blew up required knowing what
tail-call optimization is and that Python doesn't do it — not
something you'd catch by just reading the Python code in isolation.

I would not have trusted the AI-generated translation without testing
it. The first version looked completely reasonable and even matched
the ATS code almost one-to-one, but it simply didn't run to completion.
Using an AI here shifted the nature of the work: less time was spent
transcribing syntax by hand, and more time was spent verifying
behavior — compiling the original, diffing outputs, and reasoning
about why something failed rather than just that it failed. The AI was
a fast way to get a plausible first draft and to explain the bug once
found, but the actual correctness of the final program rests on the
compile-and-diff verification, not on the AI's assurance that the
translation was faithful.
