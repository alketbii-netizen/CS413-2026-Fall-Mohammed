# Testing

Run from `assigns/08/`:

```sh
python -m unittest discover -s MySolution/tests -t MySolution -v
```

**Observed result:** 39 tests, all OK, in about 35 s (Python 3.13, Flask 3.1, Playwright Chromium). Without Playwright, the 5 browser tests are skipped and the other 34 still run.

Every successful solver test runs the LAMBDA3 program in `solver/queens_cps.lam`. Test doubles are used only for an injected internal failure, a fake clock, and an aborted network route in the browser.

## How laziness is proven

`tests/test_solver.py::count_applications` wraps `lambda3._d0val_apply`, which the interpreter calls for every function application, and counts calls of the solver's `fix` functions `tc` (try_column) and `chk` (check_safe). Each test then checks either those counters or the `evaluated` flag on the tail `Lazy` value. It never inspects formatted `<lazy>` text.

| Check | Observed |
| --- | --- |
| Opening an 8×8 stream | `tc = 0`, `chk = 0`; head unforced |
| Forcing one cell | `tc = 1`, `chk = 0` (a `try` event, not yet safety-checked); tail unforced |
| Taking 10 events | fewer than 30 solver applications; 11th cell unforced; work happens only when more is requested |
| Opening 10×10 and taking 25 events | under 2 s (the full 10×10 trace takes minutes); tail unforced |
| HTTP `next` with `limit = 32` | the stored tail after 33 events is unforced |

## Requirement → test

| # | Requirement | Tests |
| --- | --- | --- |
| 1 | Safety: same line, both diagonals, safe | `TestSafety.test_same_column`, `test_diagonal_down_right`, `test_diagonal_down_left`, `test_safe_placements` |
| 2 | CPS success/failure, resume at next candidate | `TestCPSPaths.test_4x4_trace_prefix`, `test_success_continuation_resumes_after_solution` |
| 3 | 92 solutions, order, determinism, no duplicates | `TestAllSolutions.test_92_distinct_valid_in_order`, `test_deterministic`, `test_done_exactly_once_and_last` |
| 4 | Each event kind, snapshots, coordinates | `TestAllSolutions.test_event_snapshots_and_coordinates` (replays all 33,589 events) |
| 5 | Lazy construction / bounded forcing | `TestLaziness.*`, `RpcTests.test_open_does_not_force`, `test_limits_1_and_32` |
| 6 | Exhaustion, repeat next, close, unknown, cleanup, expiry | `TestStreamTable.*`, `RpcTests.test_full_8x8_flow`, `test_unknown_and_closed_stream`, `test_expired_stream` |
| 7 | IDs, envelopes, unknown methods, params, notifications, app errors | `RpcTests.test_health_preserves_ids`, `test_malformed_and_invalid_envelopes`, `test_unknown_method_and_no_eval`, `test_invalid_params`, `test_notifications`, `test_injected_internal_failure` |
| 8 | Limits 1 and 32 | `RpcTests.test_limits_1_and_32`, `test_full_8x8_flow` (every batch ≤ 32) |
| 9 | HTTP flow through all 92 solutions to done | `RpcTests.test_full_8x8_flow` |
| 10 | Browser controls and failures | `BrowserTests.test_start_step_reset`, `test_play_pause_and_speed`, `test_next_solution_and_completion_on_4x4`, `test_rpc_failure_is_visible`, `test_expired_stream_error_shown` |

Observed 8×8 values: 92 distinct solutions, first `[0,4,7,5,2,6,1,3]`, last `[7,3,0,2,5,1,6,4]`, 33,589 events in total, and `done` exactly once at the end. The first solution appears at event 200.

## Manual UI checklist (if Playwright is not installed)

1. Run `python MySolution/server/app.py` and open http://127.0.0.1:8000/. Step, Play and Next solution are disabled.
2. **Start:** the status says "Opened a 8×8 search (nothing computed yet)".
3. **Step:** the log shows `1. try (row 0, col 0)` and a yellow-outlined cell. Step again: a blue-outlined queen.
4. **Play:** the button turns into Pause and events animate. Moving the speed slider changes the rate. **Pause** stops it.
5. **Next solution:** the board border turns green and the status says "Solution #1 found: [0,4,7,5,2,6,1,3]".
6. A reject shows a red ✕, with the attacking queen outlined in red. A backtrack shows an orange cell.
7. With size 4, press Next solution three times: "Search complete: 2 solutions", and the button changes to Restart.
8. Stop the server and press Step: a red "RPC failure" banner appears. Restart the server and press Start: the banner clears.
9. **Reset:** the board and counters clear.

## Architecture under test

```text
Browser (rpc-client / player / board-view) ─POST /rpc─▶ app.py ─▶ rpc.py ─▶ streams.StreamTable
                                                                              │ force 1 cell
                                                                              ▼
                                                    solver/queens.py ─▶ queens_cps.lam (LAMBDA3)
```
