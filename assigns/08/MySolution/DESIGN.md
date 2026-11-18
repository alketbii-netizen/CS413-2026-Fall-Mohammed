# Design — Animated N-Queens with CPS and Lazy Streams

## Architecture

```text
 Browser (static/)                         Python process (server/, solver/)
 ┌──────────────────────────┐   POST /rpc  ┌────────────┐   ┌──────────────┐
 │ main.js   wiring/buttons │  JSON-RPC    │ app.py     │──▶│ rpc.py       │
 │ player.js pull & buffer  │─────────────▶│ HTTP, 415, │   │ envelope,    │
 │ board-view.js render     │◀─────────────│ static     │   │ validation,  │
 │ rpc-client.js transport  │  200 / 204   └────────────┘   │ dispatch     │
 └──────────────────────────┘                               └──────┬───────┘
                                                                   ▼
                                    ┌──────────────────────────────────────┐
                                    │ streams.py  StreamTable              │
                                    │ uuid → {unforced Strm, size, lock,   │
                                    │         last_used}  TTL, max open    │
                                    └──────────────┬───────────────────────┘
                                                   ▼ force one cell (lazy_eval)
                                    ┌──────────────────────────────────────┐
                                    │ solver/queens.py  adapter            │
                                    │   event tuple → JSON dict            │
                                    └──────────────┬───────────────────────┘
                                                   ▼
                                    ┌──────────────────────────────────────┐
                                    │ solver/queens_cps.lam  (LAMBDA3)     │
                                    │ CPS search ─▶ Lazy[Stcn[Event]]      │
                                    │   cell = event + unforced tail thunk │
                                    └──────────────────────────────────────┘
```

Search logic exists only in `queens_cps.lam`. The adapter never inspects closures. The browser never sees LAMBDA3 values.

## Solver state and invariant

A partial board is `List[sint]` of queen columns, **newest row first**: for a board of length `r`, the head is the column in row `r-1`.

**Invariant:** rows `0..r-1` each hold one queen, and no two queens share a column or a diagonal. The search places row `r` next, trying columns `0..n-1` left to right. The adapter reverses the list so JSON boards are in row order.

## Continuations

All continuations have the answer type `Strm[Event]` (= `Lazy[Stcn[Event]]`).

| Continuation | Type | Role |
| --- | --- | --- |
| success `sk` | `(List[sint], unit -> Strm[Event]) -> Strm[Event]` | gets a complete board and the failure continuation that resumes the search after it |
| failure `fk` | `unit -> Strm[Event]` | resumes the next candidate of the enclosing row (emitting `backtrack`), or at the root emits `done` |
| `on_safe`, `on_conflict` | `unit -> Strm[Event]` | the CPS safety checker calls exactly one of them |

```text
try_column(row, col, board, sk, fk):
  if col == n: fk()                                  # row exhausted -> enclosing failure
  else emit_lazy(try(col,row,board), λ.
    check_safe(col, 1, board,
      on_safe     = λ. let nb = place(col, board) in
                       emit_lazy(place(col,row,nb), λ.
                         search(row+1, nb, sk,
                                λ. emit_lazy(backtrack(col,row,board),
                                             λ. try_column(row, col+1, board, sk, fk)))),
      on_conflict = λ. emit_lazy(reject(col,row,board),
                                 λ. try_column(row, col+1, board, sk, fk))))

search(row, board, sk, fk) = if row == n then sk(board, fk) else try_column(row, 0, board, sk, fk)
on_solution(board, resume) = emit_lazy(solution(board), resume)
root_exhausted()           = emit_lazy(done, λ. empty_stream)
stream(n) = lazy( lazy_eval(try_column(0, 0, [], on_solution, root_exhausted)) )
```

**Search order.** The failure continuation built for a placed queen is "record backtrack, then try the next column in this row". It is the `fk` handed to the deeper search, so the deeper row returns control to it when it runs out of columns. That gives depth-first, left-to-right order. Solutions come out in lexicographic order, without duplicates, because each board prefix is extended exactly once per column.

`check_safe(col, d, board, ok, bad)` compares `col` with the head of `board` at distance `d`. Same column, `col - d` or `col + d` calls `bad()`; otherwise it recurses on the tail with `d + 1`; the empty board calls `ok()`. It never returns a Boolean. The test-only `safety_probe` wraps it to report which continuation ran. Every call to a continuation, to `check_safe` and to `try_column` is in tail position.

`try_column` and `search` are mutually recursive. LAMBDA3's `fix` is self-recursive, so `search` is a local `lam` inside the body of `fix tc`, where `tc` is in scope.

## From CPS to a lazy stream

```text
emit_lazy(e, k) = lazy_make(λ. stcn_cons(e, lazy_make(λ. lazy_eval(k(())))))
```

- **Opening** (`queens.open`) applies `queens_stream` to `n`. That only builds the outer `lazy_make`, so no `try_column` or `check_safe` runs. The tests count these applications through a trace hook and confirm both counts are 0.
- **Forcing one cell** runs the pending continuation until the next `emit_lazy`. That covers at most one `try_column` step and its safety check, or one continuation hop (`backtrack`, `solution`). It yields `stcn_cons(event, tail)`, where `tail` is a new unforced `lazy_make`. Nothing beyond the next event is computed.
- There is no list of solutions anywhere. Unrequested tails stay unforced, which the tests check through the `evaluated` flag and the counters.

## Event schema (JSON)

| `event` | Fields | Meaning |
| --- | --- | --- |
| `try` | `column`, `row`, `board` (current) | candidate considered |
| `place` | `column`, `row`, `board` (with the new queen) | candidate safe, added |
| `reject` | `column`, `row`, `board` (current) | candidate attacked |
| `backtrack` | `column`, `row`, `board` (restored, without that queen) | branch failed; next column follows |
| `solution` | `board` (all `n` columns) | complete arrangement |
| `done` | — | final event, exactly once |

LAMBDA3 has no strings or records, so an event is the tuple `(kind, column, row, board)` with kind `0..5`. The adapter maps it to the JSON above.

## JSON-RPC methods and examples

```json
→ {"jsonrpc":"2.0","method":"service.health","params":{},"id":1}
← {"jsonrpc":"2.0","result":{"status":"ok","version":"1.0"},"id":1}

→ {"jsonrpc":"2.0","method":"queens.open","params":{"size":8},"id":2}
← {"jsonrpc":"2.0","result":{"stream_id":"3f0c…-uuid","size":8},"id":2}

→ {"jsonrpc":"2.0","method":"queens.next","params":{"stream_id":"3f0c…","limit":3},"id":3}
← {"jsonrpc":"2.0","result":{"events":[
     {"event":"try","column":0,"row":0,"board":[]},
     {"event":"place","column":0,"row":0,"board":[0]},
     {"event":"try","column":0,"row":1,"board":[0]}],"done":false},"id":3}

→ {"jsonrpc":"2.0","method":"queens.close","params":{"stream_id":"3f0c…"},"id":4}
← {"jsonrpc":"2.0","result":{"closed":true},"id":4}
```

## Lifetime, limits, errors

- **Stream table:** process-local `uuid4 → entry`, with one lock per entry. A `next` call forces up to `limit` cells and stores the tail under that lock, so each request is atomic.
- **Inactivity lifetime:** 600 s since last use. Expired entries are swept on every request. Server restart invalidates all IDs.
- **Exhaustion:** when `done` is returned, the LAMBDA3 stream is dropped at once. A small tombstone answers later `next` calls with `{"events":[],"done":true}` until it expires or is closed.
- **Limits:** `size` is an integer from 4 to 10. `limit` is an integer from 1 to 32. At most 64 live streams. All input is validated before a stream is allocated.
- **Errors:** `-32700` parse error, `-32600` invalid request (including batches, which are not supported), `-32601` unknown method, `-32602` invalid params, `-32603` internal error (logged, no details returned), `-32020` unknown/closed/expired stream, `-32021` too many open streams.
- **HTTP status:** 200 for any JSON-RPC response, 204 (empty body) for notifications, 415 for a non-JSON media type.
- **No code execution:** only the four fixed methods exist. Request text is never evaluated, and responses never include tracebacks, paths or closures.
