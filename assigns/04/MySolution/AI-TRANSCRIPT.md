# AI-TRANSCRIPT

**AI tool used:** Claude (Anthropic), used interactively through the
Claude chat interface with a Linux sandbox (Python 3.12 venv, a real
Chromium browser via Playwright, and a shell) available for actually
running the code, not just generating it.

## Context

Assign04.md asked for a small MVC web front-end for LAMBDA, backed by
the supplied `lambda1.py`, with real Lint (free-variable checking via a
`d0exp_fvset` the file does *not* actually define) and real Interpret
(`d0exp_evaluate`), Type-check/Compile as placeholders, and Execute
disabled. The stakeholder brief (`README.00`) supplied the informal
motivation behind the same requirements.

## Important prompts and what the AI produced

1. **"Build the whole MVC app: design it, then implement it, run the
   tests, and only come back to me for the git/GitHub steps."** This was
   the governing instruction for the whole assignment (the user is
   unfamiliar with git but capable of directing scope); the AI planned
   the module layout up front (a `TaskCreate` list: structure → fvset →
   constructor reader → Model → backend → Controller/View → tests →
   docs → verify) before writing code, specifically so the Model,
   Backend, and Controller boundaries in `ARCHITECTURE.md` would match
   what was actually built rather than being written up after the fact.

2. **`d0exp_fvset` was not in the supplied `lambda1.py`.** The AI
   noticed this while reading the file (Assign04.md's Lint task assumes
   the function exists) and made an explicit choice, documented in both
   `lambda1.py`'s header comment and `ARCHITECTURE.md`: implement it as
   a separate `fvset.py` module rather than editing the vendored file,
   so `lambda1.py` stays an unmodified copy of what was supplied.

3. **"Load the expression through a restricted constructor reader ...
   do not execute arbitrary uploaded Python or shell code."** The AI's
   first instinct for a "Python constructor expression" reader would be
   `eval()` with a restricted globals dict — but a restricted-globals
   `eval` is a well-known incomplete sandbox (attribute access and
   dunder tricks can often escape it). Instead, the AI used `ast.parse`
   (parsing only, never executing) and hand-walked the resulting tree,
   accepting only literal values and calls to an explicit whitelist of
   constructor names. This was then actively tested, not just assumed
   safe: `tests/test_constructor_reader.py` includes
   `__import__('os').system(...)` and `open('/etc/passwd').read()` as
   literal test inputs, asserting they raise `ConstructorReadError`
   rather than running.

## Bugs found by actually running the code, not just reading it

- **Multiline/commented constructor expressions failed to parse.** The
  first version of `read_d0exp` called `ast.parse(source, mode="eval")`
  directly. Running `tests/test_constructor_reader.py` immediately
  surfaced `IndentationError: unexpected indent` for a test source
  copied from an indented Python triple-quoted string — a realistic
  case of pasted/copied source. Fixed by dedenting with `textwrap.dedent`
  before parsing.

- **The Interpret timeout test hung the whole test process — not just
  the one test.** The first version of the Interpret bounding used
  `concurrent.futures.ThreadPoolExecutor` with `future.result(timeout=
  ...)`. This looked correct (and the individual assertion did pass
  quickly), but running `pytest` on the full suite hung indefinitely.
  Diagnosis: `ThreadPoolExecutor` worker threads are **non-daemon** by
  default, so after a timeout fires and the request returns, the
  abandoned Fibonacci computation kept running in the background, and
  the Python process refused to exit while that thread was still alive
  — exactly the kind of bug that only shows up by actually running the
  test suite to completion (and specifically the *whole* suite, not a
  single file) rather than reading the code and trusting it. Fixed by
  replacing the executor with a plain `threading.Thread(daemon=True)`
  plus `thread.join(timeout=...)`, which guarantees the process (and,
  in the real app, the Flask server) can never be blocked by an
  abandoned computation, at the documented cost that the computation
  itself keeps using CPU until it happens to finish (see
  `ARCHITECTURE.md`, Design decision 2, and the "Known limitations"
  section of `README.md`).

- **The vendored `lambda1.py` requires Python 3.12** (it uses the
  `type X = ...` statement), but the sandbox's default `python3` was
  3.11. Running the tests immediately raised a `SyntaxError` at import
  time — a good example of a "test failure" that says nothing about the
  code's correctness and everything about the environment, caught only
  by trying to actually run it. Resolved by creating a Python 3.12
  virtual environment (`python3.12 -m venv .venv`) and documenting the
  3.12+ requirement explicitly in `README.md`'s "Runtime versions"
  section rather than silently working around it.

## Verification performed (not just "it compiles")

- **76 automated tests**, run to completion (`python -m pytest`),
  covering free-variable analysis for every `d0exp` constructor
  (including the specific let-initializer-scope and fix-self-reference
  rules from Assign04.md), the restricted reader's acceptance and
  rejection cases, real Lint/Interpret against `lambda1.d0exp_evaluate`
  (including factorial/Fibonacci base cases and a real timeout using an
  actual 4-million-call Fibonacci run, not a mock sleep), Model state
  rules with **zero** Flask/browser involvement, and Controller
  dispatch/error/retry behavior with a **fake** backend substituted in
  (`create_app(backend=FakeBackend())`) — reusing the real routes and
  templates unmodified.
- **A live server smoke test**, actually starting `python run.py` and
  hitting its endpoints with `curl` to confirm real end-to-end values
  (factorial → `D0Vint(arg1=120)`, fibonacci → `D0Vint(arg1=55)`,
  Type-check/Compile → "not yet implemented", Execute → disabled with
  an explanation), not just unit-level assertions.
- **A real Chromium browser session** (via Playwright, against the
  pre-installed browser binary, not a mock DOM), clicking through the
  actual page: confirmed the Lint button is genuinely `disabled` while
  an edit is unapplied, that a `<script>alert(1)</script>` payload
  typed into the editor never fires a JS dialog and is rendered back as
  literal text (asserted via a `dialog` event listener that must see
  zero dialogs, not by eyeballing the page), and that keyboard `Tab`
  moves focus through native, order-preserving controls. Details and
  the exact observed values are in `TESTING.md`'s browser smoke-test
  table.

## What was not just trusted

Every claim in `ARCHITECTURE.md` about module boundaries (e.g., "the
View never imports LAMBDA-specific logic") was checked directly against
the actual `import` statements in `lambdaweb/static/app.js` and
`lambdaweb/templates/index.html` (no imports at all — it is HTML/CSS/JS)
rather than asserted from the design intent alone. The reflection
section of `README.md` was written after the bugs above were found and
fixed, not before, so it reflects what actually went wrong rather than
an idealized account of the design process.
