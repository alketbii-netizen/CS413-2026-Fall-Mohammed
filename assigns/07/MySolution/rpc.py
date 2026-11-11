"""JSON-RPC 2.0 envelope handling and method dispatch (framework-free).

handle_payload(text) -> (http_status, response_obj_or_None)
"""
from __future__ import annotations

import json
import logging

import service

log = logging.getLogger("lambda_rpc")

PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND = -32700, -32600, -32601
INVALID_PARAMS, INTERNAL_ERROR = -32602, -32603
LAMBDA_SYNTAX_ERROR, LAMBDA_TYPE_ERROR, LAMBDA_TIMEOUT = -32010, -32011, -32012

_NO_ID = object()


class RpcError(Exception):
    def __init__(self, code: int, message: str, data=None):
        super().__init__(message)
        self.code, self.message, self.data = code, message, data


def _error(id_, code, message, data=None) -> dict:
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "error": err, "id": id_}


def _source(params: dict) -> str:
    src = params.get("source")
    if not isinstance(src, str) or not src.strip():
        raise RpcError(INVALID_PARAMS, "Invalid params",
                       {"field": "source", "reason": "must be a nonempty string"})
    if len(src) > service.MAX_SOURCE_CHARS:
        raise RpcError(INVALID_PARAMS, "Invalid params",
                       {"field": "source",
                        "reason": f"exceeds {service.MAX_SOURCE_CHARS} characters"})
    return src


def m_health(params):
    if params:
        raise RpcError(INVALID_PARAMS, "Invalid params", {"reason": "expects {}"})
    return service.health()


def m_typecheck(params):
    return service.typecheck(_source(params))


def m_interpret(params):
    return service.interpret(_source(params))


def m_compile(params):
    src = _source(params)
    target = params.get("target")
    if target not in ("python", "javascript"):
        raise RpcError(INVALID_PARAMS, "Invalid params",
                       {"field": "target", "reason": "must be 'python' or 'javascript'"})
    return service.compile_source(src, target)


METHODS = {
    "service.health": m_health,
    "lambda.typecheck": m_typecheck,
    "lambda.interpret": m_interpret,
    "lambda.compile": m_compile,
}


def _valid_id(req: dict):
    if "id" not in req:
        return _NO_ID
    i = req["id"]
    if i is None or isinstance(i, str) or (isinstance(i, (int, float)) and not isinstance(i, bool)):
        return i
    return None  # invalid id -> respond with null


def handle_one(req) -> dict | None:
    """Return a response object, or None for a valid notification."""
    if not isinstance(req, dict):
        return _error(None, INVALID_REQUEST, "Invalid Request")
    rid = _valid_id(req)
    bad_id = "id" in req and rid is None and req["id"] is not None
    if req.get("jsonrpc") != "2.0" or not isinstance(req.get("method"), str) or bad_id:
        return _error(None, INVALID_REQUEST, "Invalid Request")
    notification = rid is _NO_ID
    resp_id = None if notification else rid
    try:
        method = METHODS.get(req["method"])
        if method is None:
            raise RpcError(METHOD_NOT_FOUND, "Method not found", {"method": req["method"]})
        params = req.get("params", {})
        if not isinstance(params, dict):
            raise RpcError(INVALID_PARAMS, "Invalid params", {"reason": "params must be an object"})
        result = method(params)
        response = {"jsonrpc": "2.0", "result": result, "id": resp_id}
    except RpcError as e:
        response = _error(resp_id, e.code, e.message, e.data)
    except service.L.LambdaSyntaxError as e:
        response = _error(resp_id, LAMBDA_SYNTAX_ERROR, "LAMBDA syntax error",
                          {"message": e.msg, "line": e.lineno, "column": e.offset})
    except service.L.TypeCheckError as e:
        response = _error(resp_id, LAMBDA_TYPE_ERROR, "LAMBDA type error",
                          {"message": str(e)})
    except service.ServiceTimeout:
        response = _error(resp_id, LAMBDA_TIMEOUT, "Execution timeout",
                          {"seconds": service.INTERPRET_TIMEOUT,
                           "note": "a timeout does not prove nontermination"})
    except Exception:
        log.exception("internal error in %s", req.get("method"))
        response = _error(resp_id, INTERNAL_ERROR, "Internal error")
    return None if notification else response


def handle_payload(text: str):
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return 200, _error(None, PARSE_ERROR, "Parse error")
    if isinstance(payload, list):
        if not payload:
            return 200, _error(None, INVALID_REQUEST, "Invalid Request")
        out = [r for r in (handle_one(x) for x in payload) if r is not None]
        return (200, out) if out else (204, None)
    resp = handle_one(payload)
    return (204, None) if resp is None else (200, resp)
