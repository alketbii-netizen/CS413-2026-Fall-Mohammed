# ARCHITECTURE

## Component diagram

```
                         Browser
              +---------------------------+
              |  templates/index.html     |
              |  static/app.js (View)     |
              +-------------+-------------+
                            | fetch() -- JSON over HTTP
                            v
              +---------------------------+
              |  lambdaweb/routes.py      |   Controller
              |  (Flask Blueprint)        |
              +------+-------------+------+
                     |             |
                     v             v
      +-----------------+   +--------------------------+
      | lambdaweb/       |   | LanguageBackend (ABC)    |
      | model.py         |   | lambdaweb/backend.py     |
      | SourceModel      |   |  RealLambdaBackend       |
      +-----------------+   +------+------+------+------+
                                    |      |      |
                                    v      v      v
                      constructor_reader.py  fvset.py
                                    |
                                    v
                        lambdaweb/lambda1.py (vendored,
                        unmodified; d0exp_evaluate)
```

- `routes.py` is the only module that imports Flask. It never imports
  `lambda1`, `fvset`, or `constructor_reader` directly.
- `model.py` imports nothing from Flask and nothing from `backend.py`.
- `backend.py` is the only module that imports `lambda1.py`,
  `fvset.py`, and `constructor_reader.py`.
- `app.js` only calls the five `/api/...` endpoints and renders the JSON
  it gets back; it has no notion of "free variable" or "d0exp" at all.

## Responsibility table

| Responsibility | Files / classes / functions |
|---|---|
| **Model** | `lambdaweb/model.py` — `SourceModel` (applied source, revision, pending edit, results, artifact), `PendingEditError`, `InvalidSourceError`, `NoAppliedSourceError` |
| **View** | `lambdaweb/templates/index.html` (structure), `lambdaweb/static/app.js` (renders JSON state, forwards DOM events to Controller endpoints), `lambdaweb/static/style.css` |
| **Controller** | `lambdaweb/routes.py` — Flask Blueprint `bp`; one view function per endpoint (`api_load_upload`, `api_load_manual`, `api_load_example`, `api_edit`, `api_apply`, `api_discard`, `api_action`); `_state_dict()` shapes Model state into the JSON the View expects |
| **Backend adapter (interface)** | `lambdaweb/backend.py` — `LanguageBackend` (ABC: `lint`, `interpret`, `typecheck`, `compile`, `execute`) |
| **Backend adapter (real implementation)** | `lambdaweb/backend.py` — `RealLambdaBackend`, using `lambdaweb/constructor_reader.py` (`read_d0exp`) and `lambdaweb/fvset.py` (`d0exp_fvset`) |
| **Vendored language tool** | `lambdaweb/lambda1.py` — supplied verbatim; `d0exp_evaluate` |
| **App wiring** | `lambdaweb/__init__.py` — `create_app(backend=None, model=None)` factory; `run.py` — entry point |

The **Controller coordinates** calls to the backend interface (it decides
*when* to call `lint`/`interpret`/etc., based on Model state such as
"is there a pending edit"), while the **Model owns the data** those calls
read (`applied_source`) and the results they produce
(`model.record_result(...)`). Splitting it this way means the Model
never needs to know the backend exists at all — `test_model.py` proves
this by testing `SourceModel` with zero backend or Flask involvement.

## Sequence: Load source → Lint → Interpret (including an undeclared variable)

1. Browser: user clicks **Factorial (canned)**.
2. `app.js` → `POST /api/load/example {"name": "factorial"}`.
3. Controller (`api_load_example`) reads `CANNED_EXAMPLES["factorial"]`
   and calls `model.load_source("factorial", text)`.
4. Model validates the text, sets `applied_source`, bumps `revision` to
   1, clears `results` and `artifact`.
5. Controller returns the new state as JSON; View re-renders the editor,
   source name, and revision.
6. Browser: user clicks **Lint**.
7. `app.js` → `POST /api/action/lint`.
8. Controller calls `model.require_actionable()` (passes: no pending
   edit, source is applied), then `backend.lint(model.applied_source)`.
9. `RealLambdaBackend.lint` calls `read_d0exp(source)` (constructor
   reader) to get a `d0exp`, then `d0exp_fvset(dexp)`. The factorial
   example is closed, so the free-variable set is empty →
   `BackendResult(SUCCESS, "no free (undeclared) variables found")`.
10. Controller wraps this in an `ActionResult(action="lint", revision=1,
    ...)` and calls `model.record_result(...)`.
11. View shows "Lint — success — no free (undeclared) variables found".
12. Browser: user clicks **Interpret**. Same path as steps 7–11, but the
    Controller calls `backend.interpret(...)`, which parses the source
    again and calls `d0exp_evaluate` (with a bounded-time daemon thread —
    see Design decision 2 below). Result: "Interpret — success —
    D0Vint(arg1=120)".

**Undeclared-variable variant:** if the user instead types
`D0Evar("x")` into the editor and applies it, then clicks **Lint**, step
9 finds `d0exp_fvset(D0Evar("x")) == frozenset({"x"})`, which is
non-empty, so the backend returns
`BackendResult(ERROR, "undeclared variable(s): x")` instead. The View
renders this in the same results table as an `error` outcome, visibly
distinct from a `success` or `not_implemented` outcome — no evaluation
is attempted by Lint either way.

## Design decisions and tradeoffs

**1. The Controller coordinates the backend; the Model stays inert.**
`api_action()` in `routes.py` decides when to call the backend and
builds the `ActionResult`; `SourceModel` only stores what it is given.
*Tradeoff:* this keeps the Model trivially unit-testable without any
backend or network concerns (see `test_model.py`), at the cost of
putting a bit more logic in the Controller than a "fat model" design
would. Given that Assign04.md explicitly allows either the Model or the
Controller to coordinate backend calls, this was chosen to keep the
Model provably independent of "how the language tool is invoked" per
its own responsibility description.

**2. A daemon thread with a join-timeout bounds `interpret`, not a
process-level timeout or `signal.alarm`.** `RealLambdaBackend.interpret`
runs `d0exp_evaluate` on a `threading.Thread(daemon=True)` and calls
`thread.join(timeout)`; if the thread is still alive afterward, the
request returns `BACKEND_FAILURE` immediately, and the abandoned
computation is simply left to run in the background. *Tradeoff:* Python
cannot forcibly kill a running thread, so a genuinely stuck computation
keeps consuming CPU until it happens to finish (or forever, for a true
infinite loop) — but marking the thread **daemonic** guarantees it can
never block the application from exiting or from handling the next
request, which is the actual requirement ("cannot leave the application
permanently busy"). The alternative — a subprocess per Interpret call,
which genuinely can be killed — was rejected for this assignment as
disproportionate for a single-user local tool with no true `while`-loop
construct in the language (every non-terminating LAMBDA program is
recursive, so it already hits Python's recursion limit almost
immediately in practice; the timeout mainly bounds *slow-but-terminating*
programs, such as an exponential-time Fibonacci call with a large `n`).

## Replacing the placeholders

**Type-checking:** a real type-checker would be a new function,
`d0exp_typecheck(dexp) -> TypeCheckResult`, added alongside
`d0exp_fvset` and called from a new `RealLambdaBackend.typecheck`
implementation — the Controller and View require no changes at all,
since `typecheck(source) -> result` is already the contract every
caller uses. The only change needed elsewhere is that `TYPE_CHECKED`
would become a real possible outcome for Compile to depend on.

**Compilation and Execute:** a real `compile(source) -> result` would,
on success, produce a genuine artifact (e.g., generated code or bytecode)
and call `model.record_result(ActionResult("compile", revision,
SUCCESS, ...))` with that artifact attached — `SourceModel.record_result`
already contains the hook for this
(`self.artifact = result.message; self.artifact_revision =
result.revision` when `action == "compile"` and `status == SUCCESS`;
today this branch is simply never reached, since the placeholder never
returns `SUCCESS`). `SourceModel.execute_available` already checks that
the artifact's revision matches the *current* source revision, so a
source edit or a failed recompilation automatically invalidates a stale
artifact without any extra code. Execute would then call
`backend.execute(model.artifact)` — already wired in `routes.py` — which
would run the artifact directly rather than re-deriving it from
`source`, satisfying "Execute must consume that artifact without
silently recompiling."

No extension along these lines is implemented in this submission — Type-check
and Compile remain placeholders exactly as specified, and Execute remains
disabled — this section only describes the seam that is already in place
for that future work.
