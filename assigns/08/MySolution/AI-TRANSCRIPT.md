# AI Transcript — Assign08

## Tools

Claude (Anthropic), claude.ai.

## Important prompts and suggestions

- "Assign 8 is up, what should I do to refresh the repo" → pull from the class `upstream` remote, then push.
- "Go check out assign 8 and ready me the file" → Claude read `Assign08.md`, `LAMBDA3/lambda3.py` (the lazy and stream value types and the `lazy_eval` primitive), `mylib/strm.lam` and `mytest/eight_queens_stream.lam`, then wrote the solution.
- Key design suggestions:
  - Write the search in LAMBDA3 in true CPS, with success `(board, resume) -> Strm` and failure `unit -> Strm` continuations and a CPS safety checker. Search is a local `lam` inside `fix try_column`, because `fix` is self-recursive only.
  - `emit_lazy(e, k) = lazy_make(λ. stcn_cons(e, lazy_make(λ. lazy_eval(k()))))`, so each cell holds one event and an unforced tail. The whole stream is wrapped in one more `lazy_make`, so opening does no work.
  - Encode events as `(kind, column, row, board)` tuples, since LAMBDA3 has no strings, and convert them to JSON in a small Python adapter.
  - Force cells from Python by evaluating LAMBDA3's own `lazy_eval` on the stored value, not by reimplementing it.
  - Prove laziness with a trace hook on `lambda3._d0val_apply` that counts `try_column`/`check_safe` calls, plus the tail's `evaluated` flag.
  - Keep a stream table with UUID ids, per-entry locks, a 600 s inactivity TTL, a 64-stream cap, and tombstones after `done`. Reject batches.
  - Split the browser client into transport, controller, renderer and wiring modules, fetching 8 events only when the buffer is empty.

## Problems found and fixed

- `create_app(table or StreamTable())` silently ignored an injected empty table, because `StreamTable` defines `__len__` and an empty one is falsy. The expiry test caught it; fixed with `is not None`.
- The first screenshot showed squashed board rows (no explicit grid rows) and a misleading log numbering after trimming. Both were fixed and checked with a second screenshot.

## Review and testing

- 39 automated tests pass (solver, laziness, stream table, JSON-RPC over HTTP, Playwright browser tests). See `TESTING.md`.
- The solver output was checked independently: 92 distinct valid boards, in lexicographic order, with known first and last solutions.
- The UI was checked visually from screenshots at desktop and phone widths.
