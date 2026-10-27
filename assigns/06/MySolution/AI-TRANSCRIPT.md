# AI Transcript — Midterm 1 (Assignment 6)

## Tools used

- **Claude (Anthropic), claude.ai** — help syncing the class repository and
  generating the implementation, tests, documentation drafts and slide deck.

## Important prompts and suggestions

1. *"How can I pull from the professor's GitHub repository?"* — Claude
   suggested adding the class repo as the `upstream` remote and running
   `git fetch upstream` / `git merge upstream/main main` / `git push origin main`.
2. *"Look at the whole thing, we are working on assign 6"* — Claude read
   `Assign06.md`, `REQUIREMENTS.md` and `assigns/05/lambda1_vp.py`, then
   proposed and wrote this design:
   - a separate immutable target AST (`Var`/`Lam`/`App`) with cached free
     variables and capture-avoiding substitution (adapting my Assignment 5
     fresh-name scheme `b_1, b_2, ...`);
   - a closed Church-encoding library, with a pair-shifting predecessor and
     comparisons derived from truncated subtraction;
   - a `D0ExpVisitor` compiler using delayed thunks for `if`/`and`/`or`, `Z`
     for `fix`, and fresh thunk parameters `_k_i` chosen against all names
     in the thunk body;
   - one shared evaluator (bounded weak call-by-value for target terms,
     environment-based call-by-value for source ASTs);
   - STEP/BASE spine and two-marker boolean observers;
   - a `unittest` suite and `demo.py`.
3. Claude suggested renaming the encoding module from `encodings.py` to
   `church.py`, because `encodings` shadows a Python standard-library package.

## Problems found during review/testing

- A first version of one scope test used `x = "f"` together with a function
  also named `f`, which accidentally created a coincident `fix f(f)` and
  failed. The compiler was right and the test was wrong. The test was fixed
  to use a different function name in that case.

## How the results were reviewed and tested

- Ran `python3 -m unittest discover -s MySolution -t MySolution` (53 tests,
  all passing) and `python3 MySolution/demo.py` (15/15 demonstrations match).
- Each demo's compiled answer is compared with an explicit expected value
  *and* with the shared evaluator's source-side answer.
- Tests check purity of all output, closedness of every combinator,
  `FV(C[e]) = FV(e)` on open programs, input immutability, and that compilation
  never calls the evaluator (the evaluator entry points are patched to fail).
- My own review: I ran the tests and demo on my machine (Python 3.13), confirmed the results, and presented the demo output on camera. Claude also drafted the slides and speaking script and joined my two Zoom recordings into one video.
