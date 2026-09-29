# LAMBDA Web Front-End (MVC)

A small local, single-user web front-end for the LAMBDA language system:
load a program (upload / manual / canned example), edit it, and run
**Lint** (real undeclared-variable checking) and **Interpret** (real
evaluation via the supplied `lambda1.py`). **Type-check** and **Compile**
are documented placeholders; **Execute** is reserved for a future
compiler and stays disabled until one exists. See `ARCHITECTURE.md` for
the MVC design and the backend contract.

## Runtime versions

- Python **3.12** or later (required — `lambda1.py` uses the Python 3.12
  `type` statement).
- Flask 3.x (installed via `requirements.txt`).
- Tested with Python 3.12.3 and Flask 3.1.3 on Linux.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```bash
python run.py
```

Then open **http://127.0.0.1:5000/** in a browser. The server binds only
to the loopback interface (127.0.0.1); it is not exposed on the network.

## Running the tests

```bash
python -m pytest
```

All 76 automated tests (model, free-variable analysis, constructor
reader, backend, and controller-with-a-fake-backend) should pass in a
few seconds, with no browser and no running server required for most of
them (see `TESTING.md`).

## Supported input format

Source is a single Python **constructor expression** of type `d0exp`
(not a LAMBDA parser, and not arbitrary Python) — e.g.:

```
D0Eop2("+", D0Eint(20), D0Eint(22))
```

Constructor names (`D0Eint`, `D0Ebtf`, `D0Eop1`, `D0Eop2`, `D0Evar`,
`D0Elam`, `D0Efix`, `D0Eapp`, `D0Eif0`, `D0Elet`, `D0Epair`, `D0Epfst`,
`D0Epsnd`) are available without any import. Nested constructors, `#`
comments, and multi-line expressions are all accepted. The reader
(`lambdaweb/constructor_reader.py`) parses this text with Python's `ast`
module and only ever builds objects from this fixed whitelist — it never
calls `eval()`/`exec()` on uploaded text, so arbitrary Python or shell
code cannot run through it (see `tests/test_constructor_reader.py` for
the specific attack-style inputs it rejects).

## Execution bounds

- Maximum source size: **64 KiB** (`lambdaweb/limits.py:MAX_SOURCE_BYTES`).
  Larger uploads/edits are rejected with the previously applied source
  preserved.
- **Interpret** timeout: **5 seconds** (`INTERPRET_TIMEOUT_SECONDS`). A
  computation still running after 5 seconds is reported as a backend
  failure ("interpretation timed out"), and the application immediately
  becomes usable again — the abandoned computation runs on a background
  daemon thread that can never block the app (see `ARCHITECTURE.md`,
  Design decision 2).

## Demonstration

With the server running, in the browser:

1. **Factorial / Fibonacci.** Click **Factorial (canned)**, then
   **Interpret** → `D0Vint(arg1=120)` (5! = 120). Click
   **Fibonacci (canned)**, then **Interpret** → `D0Vint(arg1=55)`
   (fib(10) = 55).
2. **Undeclared variable.** Click **Manual input**, type
   `D0Evar("x")`, click **Apply changes**, then **Lint** → reports
   `undeclared variable(s): x`. Edit it to `D0Eint(1)`, **Apply
   changes** again, then **Lint** → `no free (undeclared) variables
   found`.
3. **Runtime failure after a successful Lint.** Type
   `D0Eop2("/", D0Eint(1), D0Eint(0))`, **Apply changes**. **Lint**
   succeeds (the expression is closed — Lint never evaluates it).
   **Interpret** then reports a runtime failure (division by zero). This
   is the concrete case that shows why Lint success does **not** imply
   Interpret will succeed.
4. **Placeholders and Execute.** Click **Type-check** → "type checking
   is not yet implemented". Click **Compile** → "compilation is not yet
   implemented". **Execute** is disabled and explains why (no compiled
   artifact exists, since Compile is a placeholder).

Sample files for the same scenarios are in `sample_inputs/` (`factorial.txt`,
`fibonacci.txt`, `error_undeclared_variable.txt`,
`error_runtime_division_by_zero.txt`) and can be loaded with **Choose File**.

## Known limitations

- Single-user, in-memory state: nothing persists across a server
  restart, and there is no concept of accounts or multiple concurrent
  users editing the same source (out of scope per Assign04.md).
- Type-checking and Compile are placeholders; Execute is therefore
  always disabled in this submission — there is no generated code to
  run.
- A LAMBDA program is entered only as a `d0exp` constructor expression;
  there is no concrete LAMBDA syntax or parser here.
- The Interpret timeout bounds *how long the application waits*, not the
  underlying computation itself — Python cannot forcibly kill a thread,
  so a truly runaway computation keeps using CPU in the background even
  after the request has returned (see `ARCHITECTURE.md`).

## Reflection (AI-assisted MVC design)

MVC helped most at the Model/Backend boundary: once `SourceModel` was
defined to know nothing about HTTP, Flask, or `lambda1.py`, its state
rules (pending edits block actions, a rejected edit preserves the
previous applied source, a new revision clears stale results) could be
written and unit-tested as plain Python with zero setup, which made the
trickier rules — like "Lint must never evaluate, but Interpret must
independently re-parse the same source" — easy to get right and easy to
regress-test in isolation. It also made the "test backend without
changing view code" requirement almost free: because the Controller only
ever talks to the `LanguageBackend` interface, `tests/test_controller.py`
could substitute a `FakeBackend` and still exercise the real routes and
templates.

Separation was hardest at the View/Controller boundary for anything
involving *busy state*. A synchronous Flask request-response cycle has
no natural notion of "in progress" once you're back in JavaScript, so
`app.js` ended up owning a small piece of client-side state
(`requestInFlight`) purely to disable/re-enable controls around each
`fetch()` call — that isn't really "view rendering" in the pure MVC
sense, but there was no clean way to push it server-side without either
polling or a persistent connection (websockets), which felt
disproportionate for a local single-user tool. The interpret-timeout
mechanism was the second-hardest part, mainly because Python threads
cannot be cancelled; the daemon-thread approach guarantees the
*application* stays responsive, but doesn't guarantee the underlying
computation actually stops, which is a limitation worth flagging rather
than hiding.

A future change this architecture makes easier: because `LanguageBackend`
is an abstract interface and `SourceModel.record_result` already has the
artifact-tracking hook wired in, adding a real compiler only requires a
new `LanguageBackend` implementation (or extending `RealLambdaBackend`)
— no changes to `routes.py`, `model.py`, or any template would be
needed, as sketched in `ARCHITECTURE.md`'s "Replacing the placeholders"
section.
