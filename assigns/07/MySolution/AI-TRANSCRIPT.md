# AI Transcript — Assign07

## Tools

Claude (Anthropic), claude.ai.

## Important prompts and suggestions

- "How can I update so it can appear in my repo" — pull from the class `upstream` remote and push.
- Claude read `Assign07.md`, the provided `LAMBDA3/lambda3.py` API and the instructor's `TEST/test_rpc_api.py`, then wrote:
  a Flask transport (`app.py`), a framework-free JSON-RPC dispatcher (`rpc.py`), a thin LAMBDA3 adapter
  (`service.py`) that runs interpretation in a terminable worker process, HTTP tests, and the documents.
- Design choices suggested: error codes -32010/-32011/-32012 as specified; 20,000-character source limit;
  5-second interpretation deadline; HTTP 415 for wrong media type; 204 for notification-only requests.

## Review and testing

- First test run had wrong expected ids in some test calls (test bug) and a timeout test that hit a
  recursion error instead of the deadline; both tests were corrected.
- Own suite: 10 tests pass. Instructor black-box suite (`TEST/`) against the running server: 15 tests pass.
- I ran the tests and the server on my machine before submitting.
