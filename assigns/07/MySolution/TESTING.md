# Testing

Run from `assigns/07/`: `python -m unittest discover -s MySolution/tests -t MySolution/tests -v`
(Flask test client, no server needed). Observed: **10 tests, OK**.
Instructor black-box suite with `python MySolution/app.py` running:
`python -m unittest discover -s TEST -v`. Observed: **15 tests, OK**.

| Required behavior | Test |
| --- | --- |
| 1 health + id preserved | `test_health` |
| 2 typecheck types | `test_typecheck` |
| 3 arithmetic, factorial, tuple, collection | `test_interpret_arithmetic_factorial_tuple_collection` |
| 4 Python/JS compile | `test_compile_python_and_javascript` |
| 5 syntax vs type error codes | `test_syntax_and_type_errors_distinct` |
| 6 malformed JSON, envelopes, unknown method, params, blank/oversized source, 415 | `test_invalid_inputs` |
| 7 function value `<lam>` | `test_function_value_formatted` |
| 8 injected failure / timeout, no traceback | `test_injected_failure_and_timeout`, `test_real_timeout_terminates_worker` |
| 9 unbound variable rejected | `test_syntax_and_type_errors_distinct` (`x + 1` → -32011) |
| 10 batches, notifications, empty batch | `test_batches_and_notifications` |

Successful typecheck/interpret/compile tests call real LAMBDA3; mocks are used only for failure injection.

## Architecture

```text
HTTP client ──POST /rpc──▶ app.py (Flask transport, 415 check)
                              │ raw body
                              ▼
                           rpc.py (JSON-RPC envelope, batch, dispatch, error codes)
                              │ method(params)
                              ▼
                           service.py (adapter, limits, worker-process deadline)
                              │
                              ▼
                           LAMBDA3/lambda3.py (parse+typecheck, evaluate, format, compile)
```
