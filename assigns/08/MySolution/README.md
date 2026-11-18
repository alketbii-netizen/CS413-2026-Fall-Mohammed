# Assign08 — Animated N-Queens with CPS and Lazy Streams

Mohammed Alketbi. Python 3.12+ (tested with 3.13), Flask 3.1. The optional browser tests use Playwright.

## Setup

```sh
cd assigns/08
python -m pip install -r MySolution/requirements.txt
# optional, for the automated browser tests:
python -m pip install playwright && python -m playwright install chromium
```

## Run

```sh
python MySolution/server/app.py          # open http://127.0.0.1:8000/
```

## Test (from `assigns/08/`)

```sh
python -m unittest discover -s MySolution/tests -t MySolution -v
```

This runs 39 tests and takes about 45 s, because it runs the full 8×8 search twice in the solver tests and once over HTTP. Browser tests skip themselves if Playwright isn't installed.

## Controls

| Control | Action |
| --- | --- |
| Size | board size 4–10 (default 8) |
| Start / Restart | opens a new stream (no search work is done yet) |
| Step | shows the next event |
| Play / Pause | animates at the chosen speed (10–800 ms per event) |
| Next solution | plays until the next `solution`, or `done` |
| Reset | closes the stream and clears the board |

Colors: yellow = try, blue = place, red ✕ = reject (the attacking queen is outlined red), orange = backtrack, green board = solution. The status line distinguishes a solution from "Search complete". RPC or network failures show a red error banner.

The client requests 8 events at a time, only when its buffer is empty. It never downloads the full trace.

## RPC examples

```sh
curl -s -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"service.health","params":{},"id":1}'
curl -s -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"queens.open","params":{"size":8},"id":2}'
#  -> {"jsonrpc":"2.0","result":{"stream_id":"<uuid>","size":8},"id":2}
curl -s -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"queens.next","params":{"stream_id":"<uuid>","limit":4},"id":3}'
curl -s -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"queens.close","params":{"stream_id":"<uuid>"},"id":4}'
```

In PowerShell, use `curl.exe` and escape the inner quotes, or use `Invoke-RestMethod`.

## Layout

```text
MySolution/
  solver/queens_cps.lam   CPS search + lazy event stream (LAMBDA3)
  solver/queens.py        adapter: open, force one cell, event -> JSON
  server/streams.py       stream table (TTL, cleanup, limits, locking)
  server/rpc.py           JSON-RPC envelope, validation, dispatch
  server/app.py           Flask: POST /rpc and the static client
  static/                 index.html, style.css, rpc-client.js, player.js, board-view.js, main.js
  tests/                  solver, stream table, RPC/HTTP, browser
  DESIGN.md  TESTING.md  AI-TRANSCRIPT.md
```

## Reused code

The safety rule (same column, or diagonal at distance `d`) follows `safe` in `LAMBDA3/mytest/eight_queens_stream.lam`, rewritten in CPS for a row-major board. The search, the continuations and the stream construction are new. The reference file builds solutions with `stream_append` and is not used.

## Limitations

- Single-process development server; stream state is lost on restart.
- JSON-RPC batches are rejected with `-32600`, because stream calls are order-dependent.
- The LAMBDA3 interpreter is slow: the full 8×8 trace (33,589 events) takes about 10 s to force end to end, and 10×10 takes minutes. Opening a stream or reading a prefix is instant.
- No authentication; for local use only.
