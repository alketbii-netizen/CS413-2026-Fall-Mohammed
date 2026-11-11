# RPC Contract — LAMBDA3 JSON-RPC Service

## Transport

One endpoint: `POST /rpc`, request and response media type `application/json`.

- **HTTP 200**: any JSON-RPC response object or array, including parse errors and invalid requests. The RPC outcome is in the body (`result` or `error`).
- **HTTP 204**, empty body: a single valid notification, or a batch of only valid notifications.
- **HTTP 415**: request media type is not `application/json` (a transport failure; no JSON-RPC body).
- HTTP 405/404 from the framework for other methods/paths.

## Envelope

Request: `{"jsonrpc":"2.0","method":<string>,"params":<object>,"id":<string|number|null>}`. Omitting `id` makes it a notification (no response). Response: `{"jsonrpc":"2.0","result":…,"id":…}` or `{"jsonrpc":"2.0","error":{"code":int,"message":str,"data"?:…},"id":…}` — never both. The response `id` equals the request `id`; when the request is invalid or its id is unusable, `id` is `null`.

**Batches**: a nonempty JSON array returns an array with one response per call and per invalid item; valid notifications are omitted. Clients match responses by `id`, not position. Empty array → one Invalid Request object, `id: null`. All-notification batch → 204, empty body.

## Methods

| Method | Params | Result |
| --- | --- | --- |
| `service.health` | `{}` | `{"status":"ok","version":"1.0"}` |
| `lambda.typecheck` | `{"source": str}` | `{"type": str}` |
| `lambda.interpret` | `{"source": str}` | `{"type": str, "value": str}` |
| `lambda.compile` | `{"source": str, "target": "python"\|"javascript"}` | `{"target": str, "code": str}` |

All source methods parse and type-check with `d0exp_parse_and_typecheck` first. Types use `format_type`, values `d0val_format` (functions print as `<lam>` / `<fix>`). Compile returns code text unchanged and does not run it.

## Errors

| Code | Meaning | `data` |
| --- | --- | --- |
| -32700 | Parse error (body is not JSON) | — |
| -32600 | Invalid Request (bad envelope, empty batch, bad id) | — |
| -32601 | Method not found | `{"method"}` |
| -32602 | Invalid params (params not an object, missing/blank/non-string/oversized source, bad target, nonempty health params) | `{"field","reason"}` |
| -32603 | Internal error (logged server-side; no details returned) | — |
| -32010 | LAMBDA syntax error | `{"message","line","column"}` |
| -32011 | LAMBDA type error (incl. unbound variables) | `{"message"}` |
| -32012 | Execution timeout | `{"seconds","note"}` |

No tracebacks or filesystem paths are returned.

## Limits

Source ≤ 20,000 characters. Interpretation runs in a child process with a 5 s deadline; on expiry the process is terminated and `-32012` returned. A timeout does not prove nontermination.

## Examples

```json
→ {"jsonrpc":"2.0","method":"service.health","params":{},"id":1}
← {"jsonrpc":"2.0","result":{"status":"ok","version":"1.0"},"id":1}

→ {"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"1 + 2"},"id":2}
← {"jsonrpc":"2.0","result":{"type":"sint"},"id":2}

→ {"jsonrpc":"2.0","method":"lambda.interpret","params":{"source":"let fact : sint -> sint = fix fact(n: sint): sint => if n <= 1 then 1 else n * fact(n - 1) in fact(6) end"},"id":3}
← {"jsonrpc":"2.0","result":{"type":"sint","value":"720"},"id":3}

→ {"jsonrpc":"2.0","method":"lambda.compile","params":{"source":"1 + 2","target":"python"},"id":4}
← {"jsonrpc":"2.0","result":{"target":"python","code":"…generated Python…"},"id":4}

→ {"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"1 +"},"id":5}
← {"jsonrpc":"2.0","error":{"code":-32010,"message":"LAMBDA syntax error","data":{"message":"…","line":1,"column":4}},"id":5}

→ {"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"1 + true"},"id":6}
← {"jsonrpc":"2.0","error":{"code":-32011,"message":"LAMBDA type error","data":{"message":"…"}},"id":6}

→ [{"jsonrpc":"2.0","method":"service.health","params":{},"id":"a"},
   {"jsonrpc":"2.0","method":"service.health","params":{}},
   {"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"1"},"id":2}]
← [{"jsonrpc":"2.0","result":{"status":"ok","version":"1.0"},"id":"a"},
   {"jsonrpc":"2.0","result":{"type":"sint"},"id":2}]

→ [{"jsonrpc":"2.0","method":"service.health","params":{}}]
← HTTP 204, empty body
```

## Schema

JSON Schema for request and response envelopes: [`schema.json`](schema.json).
