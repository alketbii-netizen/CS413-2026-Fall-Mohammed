"""Service layer: thin wrapper over the provided LAMBDA3 implementation.

No parsing, checking, evaluation or compilation logic lives here; every
operation calls lambda3.  Interpretation runs in a separate worker process
with a hard deadline so a runaway program can be terminated.
"""
from __future__ import annotations

import multiprocessing as mp
import sys
from pathlib import Path

LAMBDA3_DIR = Path(__file__).resolve().parent.parent / "LAMBDA3"
if str(LAMBDA3_DIR) not in sys.path:
    sys.path.insert(0, str(LAMBDA3_DIR))

import lambda3 as L  # noqa: E402

MAX_SOURCE_CHARS = 20_000      # characters of LAMBDA3 source per request
INTERPRET_TIMEOUT = 5.0        # seconds of wall-clock time per interpretation
VERSION = "1.0"


class ServiceTimeout(Exception):
    """Interpretation did not finish before the deadline."""


def health() -> dict:
    return {"status": "ok", "version": VERSION}


def typecheck(source: str) -> dict:
    _expr, typ = L.d0exp_parse_and_typecheck(source)
    return {"type": L.format_type(typ)}


def _interpret_worker(source: str, queue) -> None:
    try:
        sys.setrecursionlimit(100_000)
        expr, typ = L.d0exp_parse_and_typecheck(source)
        value = L.d0exp_evaluate(expr)
        queue.put(("ok", {"type": L.format_type(typ), "value": L.d0val_format(value)}))
    except BaseException as exc:  # reported to the parent, never re-raised here
        queue.put(("error", type(exc).__name__))


def interpret(source: str, timeout: float | None = None) -> dict:
    # Parse and type-check first in-process so syntax/type errors map exactly.
    L.d0exp_parse_and_typecheck(source)
    limit = INTERPRET_TIMEOUT if timeout is None else timeout
    queue = mp.Queue()
    proc = mp.Process(target=_interpret_worker, args=(source, queue), daemon=True)
    proc.start()
    try:
        status, payload = queue.get(timeout=limit)
    except Exception:
        proc.terminate()
        proc.join(1)
        raise ServiceTimeout(f"interpretation exceeded {limit} seconds")
    proc.join(1)
    if status == "ok":
        return payload
    raise RuntimeError(f"interpreter failed: {payload}")


def compile_source(source: str, target: str) -> dict:
    expr, _typ = L.d0exp_parse_and_typecheck(source)
    code = L.d0exp_compile(expr) if target == "python" else L.d0exp_compile_js(expr)
    return {"target": target, "code": code}
