"""JSON-RPC 2.0 envelope handling and dispatch for the Queen service.

Framework-free: ``handle_payload(text, table) -> (http_status, body|None)``.
Only the four fixed methods below exist; no source text or function names
from requests are ever evaluated.
"""
from __future__ import annotations

import json
import logging
import uuid

from . import streams
from solver import queens

log = logging.getLogger("queens_rpc")

PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND = -32700, -32600, -32601
INVALID_PARAMS, INTERNAL_ERROR = -32602, -32603
UNKNOWN_STREAM = -32020      # unknown, closed or expired stream_id
TOO_MANY_STREAMS = -32021    # MAX_OPEN_STREAMS reached

VERSION = "1.0"
_ABSENT = object()


class RpcError(Exception):
    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code, self.message, self.data = code, message, data


def _err(id_, code, message, data=None):
    e = {"code": code, "message": message}
    if data is not None:
        e["data"] = data
    return {"jsonrpc": "2.0", "error": e, "id": id_}


def _bad(field, reason):
    return RpcError(INVALID_PARAMS, "Invalid params", {"field": field, "reason": reason})


def _only(params, allowed):
    extra = sorted(set(params) - set(allowed))
    if extra:
        raise _bad(extra[0], "unexpected parameter")


def _int_param(params, name, lo, hi):
    v = params.get(name, _ABSENT)
    if v is _ABSENT:
        raise _bad(name, "required")
    if type(v) is not int or not lo <= v <= hi:
        raise _bad(name, f"must be an integer from {lo} to {hi}")
    return v


def _stream_id(params):
    v = params.get("stream_id", _ABSENT)
    if v is _ABSENT:
        raise _bad("stream_id", "required")
    if not isinstance(v, str):
        raise _bad("stream_id", "must be a string")
    try:
        uuid.UUID(v)
    except ValueError:
        raise RpcError(UNKNOWN_STREAM, "Unknown or expired stream", {"stream_id": v[:64]})
    return v


def m_health(params, table):
    _only(params, ())
    return {"status": "ok", "version": VERSION}


def m_open(params, table):
    _only(params, ("size",))
    size = _int_param(params, "size", queens.MIN_SIZE, queens.MAX_SIZE)
    return {"stream_id": table.open(size), "size": size}


def m_next(params, table):
    _only(params, ("stream_id", "limit"))
    sid = _stream_id(params)
    limit = _int_param(params, "limit", streams.MIN_LIMIT, streams.MAX_LIMIT)
    events, done = table.next(sid, limit)
    return {"events": events, "done": done}


def m_close(params, table):
    _only(params, ("stream_id",))
    table.close(_stream_id(params))
    return {"closed": True}


METHODS = {"service.health": m_health, "queens.open": m_open,
           "queens.next": m_next, "queens.close": m_close}


def _id_ok(v):
    return v is None or isinstance(v, str) or (
        isinstance(v, (int, float)) and not isinstance(v, bool))


def handle_one(req, table):
    """Response dict, or None for a valid notification."""
    if (not isinstance(req, dict) or req.get("jsonrpc") != "2.0"
            or not isinstance(req.get("method"), str)
            or ("id" in req and not _id_ok(req["id"]))):
        return _err(None, INVALID_REQUEST, "Invalid Request")
    notification = "id" not in req
    rid = req.get("id")
    try:
        fn = METHODS.get(req["method"])
        if fn is None:
            raise RpcError(METHOD_NOT_FOUND, "Method not found", {"method": req["method"][:64]})
        params = req.get("params", {})
        if not isinstance(params, dict):
            raise RpcError(INVALID_PARAMS, "Invalid params", {"reason": "params must be an object"})
        resp = {"jsonrpc": "2.0", "result": fn(params, table), "id": rid}
    except RpcError as e:
        resp = _err(rid, e.code, e.message, e.data)
    except streams.UnknownStream:
        resp = _err(rid, UNKNOWN_STREAM, "Unknown or expired stream",
                    {"stream_id": str(req.get("params", {}).get("stream_id"))[:64]})
    except streams.TooManyStreams:
        resp = _err(rid, TOO_MANY_STREAMS, "Too many open streams",
                    {"max_open": streams.MAX_OPEN_STREAMS})
    except Exception:
        log.exception("internal error in %s", req.get("method"))
        resp = _err(rid, INTERNAL_ERROR, "Internal error")
    return None if notification else resp


def handle_payload(text, table):
    try:
        payload = json.loads(text)
    except ValueError:
        return 200, _err(None, PARSE_ERROR, "Parse error")
    if isinstance(payload, list):
        # Batches are not supported (optional in the spec): stream state is
        # order-dependent, so each call must be its own HTTP request.
        return 200, _err(None, INVALID_REQUEST, "Invalid Request",
                         {"reason": "batch requests are not supported"})
    resp = handle_one(payload, table)
    return (204, None) if resp is None else (200, resp)
