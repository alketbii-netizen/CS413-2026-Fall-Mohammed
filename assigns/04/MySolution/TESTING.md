# TESTING

## Automated tests

Run with:

```bash
python -m pytest -q
```

76 tests, ~5 seconds, no browser required for any of them; specifically:

- `tests/test_model.py` — runs **without a browser or web server**: it
  only imports `lambdaweb.model` and `lambdaweb.results`, never
  `lambdaweb.routes` or Flask.
- `tests/test_controller.py` — substitutes a **fake `LanguageBackend`**
  (`FakeBackend`) via `create_app(backend=FakeBackend())`, exercising the
  real routes and the real `templates/index.html` unchanged.
- `tests/test_fvset.py`, `tests/test_constructor_reader.py`,
  `tests/test_backend.py` — the real language-tool logic (free-variable
  analysis, the restricted reader, and real Lint/Interpret via
  `lambda1.d0exp_evaluate`).

### Traceability: automated tests → F1–F10

| Req | Covered by |
|---|---|
| F1 (load menu: upload/manual/canned) | `test_controller.py::test_load_example_then_lint_dispatches_to_backend`, `::test_manual_input_then_apply`; browser check #1 below |
| F2 (edit / Apply / Discard / blocked while pending) | `test_model.py::test_edit_tracks_pending_text_and_clears_when_matching_applied`, `::test_apply_edit_commits_and_bumps_revision_and_clears_results`, `::test_discard_edit_reverts_without_changing_revision`, `::test_require_actionable_blocks_on_pending_edit`; `test_controller.py::test_action_blocked_while_pending_edit_present` |
| F3 (reject empty/invalid-UTF-8/oversized; preserve applied; keep rejected edit) | `test_model.py::test_load_source_rejects_empty_text_and_preserves_previous_applied_source`, `::test_apply_edit_rejects_invalid_text_and_preserves_pending_for_correction`; `test_constructor_reader.py::test_rejects_empty_source`, `::test_rejects_oversized_source`; `test_controller.py::test_upload_rejects_invalid_utf8`, `::test_apply_rejects_empty_edit_and_preserves_previous_applied_source` |
| F4 (button order; require applied source; Execute disabled) | `test_controller.py::test_action_blocked_when_no_source_applied_yet`, `::test_execute_remains_unavailable_without_a_real_compiler`; button order verified by inspection of `templates/index.html` and browser check #3 below |
| F5 (real Lint) | `test_backend.py::test_lint_success_for_closed_program`, `::test_lint_reports_undeclared_variable`, `::test_lint_does_not_evaluate_a_closed_program_that_would_fail_at_runtime` |
| F6 (real Interpret; distinguish input vs runtime errors) | `test_backend.py::test_interpret_arithmetic`, `::test_interpret_factorial_example`, `::test_interpret_fibonacci_example`, `::test_interpret_reports_malformed_input`, `::test_interpret_reports_runtime_failure_division_by_zero` |
| F7 (Type-check/Compile placeholders; Execute explanation) | `test_backend.py::test_typecheck_is_not_implemented_for_valid_source`, `::test_compile_is_not_implemented_for_valid_source`, `::test_execute_is_disabled_without_an_artifact`; `test_controller.py::test_placeholder_typecheck_and_compile_never_report_success` |
| F8 (new revision per accepted change; clears results/artifact) | `test_model.py::test_load_source_sets_fields_and_bumps_revision`, `::test_artifact_invalidated_by_new_revision`; `test_controller.py::test_every_accepted_load_creates_a_new_revision_and_clears_results` |
| F9 (results carry action/revision/outcome; literal text rendering) | `test_model.py::test_record_result_overwrites_previous_result_for_same_action`; literal-text rendering verified by browser check #4 below (JS uses `.textContent` only — see `static/app.js`) |
| F10 (busy status; controls restored; backend failure + retry; timeout) | `test_controller.py::test_backend_failure_is_reported_and_model_recovers_for_retry`; `test_backend.py::test_interpret_times_out_on_an_expensive_computation` |

## Browser smoke test

Performed with an **actual Chromium browser** (via Playwright, driving the
real DOM — not a simulation) against a live `python run.py` server at
`http://127.0.0.1:5000/`. A `dialog` listener was attached to catch any
`alert()`/`confirm()` popup, to make the "no HTML/JS execution" check in
row 6 a real, falsifiable check rather than a visual guess.

| # | Steps | Expected | Observed |
|---|---|---|---|
| 1 | Load the page. Click **Factorial (canned)**. | `#source-name` shows "factorial", `#source-revision` shows "1". | Observed exactly: `source-name: factorial`, `revision: 1`. |
| 2 | Click **Manual input**. | Editor becomes blank and editable. | Observed: editor value was `''`. |
| 3 | Type `<script>alert(1)</script>` into the editor (debounced `/api/edit` fires), then check the Lint button **before** applying. | Lint button must be `disabled` while the edit is unapplied. | Observed: `lint btn disabled while pending: True`. |
| 4 | Click **Apply changes**. | Edit is committed as the new applied source (revision bumps); status shows a busy message while the request is in flight. | Observed: status text was `Busy: applying changes...` (captured mid-flight), and revision advanced to 2 in the next check. |
| 5 | Click **Lint**. Check: (a) no JS `dialog` fired: the script tag must never execute; (b) the editor still shows the literal source text; (c) the results table shows Lint's outcome as plain text. | No alert; editor shows the raw string `<script>alert(1)</script>`; results table shows a Lint row with a real error message (since `<script>...</script>` is not a valid constructor expression, this is also a legitimate F6-style "malformed input" case). | Observed: `dialogs fired: []` (none); `editor textContent literal: '<script>alert(1)</script>'` (exact match, confirming `.textContent`/`.value`-only rendering, never interpreted as markup); results table's Lint row read `Lint  2  error  invalid input: syntax error: invalid syntax (<unknown>, line 1)` — a plain-text outcome, not a color swatch. |
| 6 | Click **Manual input** again, type `D0Eint(1)`, apply, then press **Tab** with focus in the editor. | Focus moves to the next control in the visual layout (native tab order — no custom/broken tabindex). | Observed: `document.activeElement.id == "btn-apply"`, i.e. focus moved from the editor to the next button in DOM order, confirming the controls are ordinary keyboard-reachable elements. |
| 7 | (Covered automatically, not re-run manually here — see traceability table) Upload a file with invalid UTF-8 bytes. | Rejected with an "invalid UTF-8" message; previous applied source untouched. | Verified via `tests/test_controller.py::test_upload_rejects_invalid_utf8`, and independently via a raw HTTP request during development (`curl -F "file=@badbytes;type=text/plain"` style check) before the automated test was written. |
| 8 | Interpret a computation engineered to exceed a very small timeout. | Reports a timeout (backend failure) and the app is immediately usable again — not stuck "Busy". | Verified via `tests/test_backend.py::test_interpret_times_out_on_an_expensive_computation` (a real 4-million-call Fibonacci run against a 0.01s timeout, asserting the request returns promptly with a `backend_failure` status rather than blocking). |
| 9 | Retry an action after a simulated backend failure. | The next call to the same action succeeds normally. | Verified via `tests/test_controller.py::test_backend_failure_is_reported_and_model_recovers_for_retry`, using a `FakeBackend` that raises on the first call and returns success on the second. |
| 10 | Check that outcome text never relies on color alone. | Every outcome (`success` / `error` / `not_implemented` / `backend_failure` / `disabled` / `pending_edit` / ...) reads as a plain-text word in the results table and status line. | Observed directly in row 5's results-table text dump above — the outcome is the literal word `error`, with no color-only signal anywhere in the markup (`static/style.css` never uses color as the sole differentiator; see `static/app.js`, which writes plain text via `textContent`, and `templates/index.html`, which has no color-coded elements at all). |

Rows 1–6 and 10 were executed live in Chromium during development of this
submission; rows 7–9 are exercised by the automated suite (and were also
spot-checked by hand against a running server before the corresponding
test was written), so they are listed here for F1–F10 traceability rather
than re-run as separate manual steps.
