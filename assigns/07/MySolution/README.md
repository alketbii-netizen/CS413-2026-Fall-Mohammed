# Assign07 — JSON-RPC Service for LAMBDA3

Mohammed Alketbi. Python 3.12+ (tested 3.13), Flask 3.1.

## Setup, start, test (run from `assigns/07/`)

```sh
python -m pip install -r MySolution/requirements.txt
python MySolution/app.py                                   # serves http://127.0.0.1:8000/rpc
python -m unittest discover -s MySolution/tests -t MySolution/tests -v   # own HTTP tests (Flask test client)
python -m unittest discover -s TEST -v                     # instructor black-box tests (server running)
```

Endpoint: `POST http://127.0.0.1:8000/rpc`, `Content-Type: application/json`.

## Modules

- `app.py` — HTTP transport (Flask). Rejects non-JSON media types with HTTP 415.
- `rpc.py` — JSON-RPC 2.0 envelope validation, batches, notifications, dispatch, error mapping. Framework-free.
- `service.py` — thin adapter over `../LAMBDA3/lambda3.py`; interpretation in a terminable worker process.
- `RPC.md` — contract, examples, error codes, limits; `schema.json` — JSON Schema for envelopes.

## Limits

- Max source: 20,000 characters (`-32602` if exceeded).
- Interpretation deadline: 5 seconds wall clock; the worker process is terminated and `-32012` returned. A timeout does not prove nontermination.

## curl examples

```sh
curl -s -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"service.health","params":{},"id":1}'
curl -s -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"1 + 2"},"id":2}'
curl -s -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"lambda.interpret","params":{"source":"let fact : sint -> sint = fix fact(n: sint): sint => if n <= 1 then 1 else n * fact(n - 1) in fact(6) end"},"id":3}'
#  -> {"jsonrpc":"2.0","result":{"type":"sint","value":"720"},"id":3}
curl -s -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"lambda.interpret","params":{"source":"x + 1"},"id":4}'
#  -> error -32011 (unbound variable x rejected by the LAMBDA3 type checker)
curl -s -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"lambda.compile","params":{"source":"1 + 2","target":"javascript"},"id":5}'
```

`lambda.compile` returns generated Python/JavaScript as text; the service never runs generated code.

## Limitations

Single local development server; no auth; no streaming (Assign08).
