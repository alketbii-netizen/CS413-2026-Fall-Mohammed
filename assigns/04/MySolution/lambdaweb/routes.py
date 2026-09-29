"""
Controller (MVC): the only module that knows about HTTP. It translates
requests into Model method calls and Backend calls, and shapes the
result into JSON for the View's JavaScript to render. No language
analysis or interpretation logic lives here — that is entirely inside
backend.py, and this module never calls lambda1/fvset/constructor_reader
directly.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request, current_app

from lambdaweb.examples import CANNED_EXAMPLES
from lambdaweb.model import (
    InvalidSourceError,
    NoAppliedSourceError,
    PendingEditError,
    SourceModel,
)
from lambdaweb.results import ActionResult, ActionStatus, BackendResult

bp = Blueprint("lambdaweb", __name__)

ACTION_NAMES = ("lint", "interpret", "typecheck", "compile", "execute")


def _model() -> SourceModel:
    return current_app.config["MODEL"]


def _backend():
    return current_app.config["BACKEND"]


def _state_dict(model: SourceModel, error: dict | None = None) -> dict:
    return {
        "source_name": model.source_name,
        "revision": model.revision,
        "applied_source": model.applied_source,
        "pending_source": model.pending_source,
        "has_pending_edit": model.has_pending_edit,
        "has_applied_source": model.has_applied_source,
        "execute_available": model.execute_available,
        "results": {
            action: {
                "revision": r.revision,
                "status": r.status.value,
                "message": r.message,
            }
            for action, r in model.results.items()
        },
        "error": error,
    }


def _ok(model: SourceModel):
    return jsonify(_state_dict(model))


def _err(model: SourceModel, kind: str, message: str, http_status: int = 409):
    return jsonify(_state_dict(model, error={"type": kind, "message": message})), http_status


@bp.get("/")
def index():
    model = _model()
    return render_template("index.html", initial_state=_state_dict(model))


@bp.get("/api/state")
def api_state():
    return _ok(_model())


@bp.post("/api/load/upload")
def api_load_upload():
    model = _model()
    f = request.files.get("file")
    if f is None or f.filename == "":
        return _err(model, "invalid_source", "no file was selected", 400)
    raw = f.read()
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return _err(model, "invalid_source", "uploaded file is not valid UTF-8 text")
    try:
        model.load_source(f.filename, text)
    except PendingEditError as exc:
        return _err(model, "pending_edit", str(exc))
    except InvalidSourceError as exc:
        return _err(model, "invalid_source", str(exc))
    return _ok(model)


@bp.post("/api/load/manual")
def api_load_manual():
    model = _model()
    try:
        model.start_manual_input()
    except PendingEditError as exc:
        return _err(model, "pending_edit", str(exc))
    return _ok(model)


@bp.post("/api/load/example")
def api_load_example():
    model = _model()
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if name not in CANNED_EXAMPLES:
        return _err(model, "invalid_source", f"unknown example: {name!r}", 400)
    try:
        model.load_source(name, CANNED_EXAMPLES[name])
    except PendingEditError as exc:
        return _err(model, "pending_edit", str(exc))
    except InvalidSourceError as exc:  # pragma: no cover - canned examples are valid
        return _err(model, "invalid_source", str(exc))
    return _ok(model)


@bp.post("/api/edit")
def api_edit():
    model = _model()
    data = request.get_json(silent=True) or {}
    model.edit(data.get("text", ""))
    return _ok(model)


@bp.post("/api/apply")
def api_apply():
    model = _model()
    try:
        model.apply_edit()
    except InvalidSourceError as exc:
        # F3: applied_source stays untouched; pending_source (the rejected
        # text) is deliberately preserved by the model for correction.
        return _err(model, "invalid_source", str(exc))
    return _ok(model)


@bp.post("/api/discard")
def api_discard():
    model = _model()
    model.discard_edit()
    return _ok(model)


@bp.post("/api/action/<name>")
def api_action(name: str):
    model = _model()
    backend = _backend()

    if name not in ACTION_NAMES:
        return _err(model, "unknown_action", f"unknown action: {name}", 404)

    try:
        model.require_actionable()
    except PendingEditError as exc:
        return _err(model, "pending_edit", str(exc))
    except NoAppliedSourceError as exc:
        return _err(model, "no_applied_source", str(exc))

    model.busy = True
    try:
        if name == "execute":
            br = backend.execute(model.artifact if model.execute_available else None)
        else:
            br = getattr(backend, name)(model.applied_source)
    except Exception as exc:
        # A backend that raises instead of returning a BackendResult is
        # treated as a backend failure, never as a crash of the whole
        # application — this is what lets F10's "backend failure ... and
        # successful retry" be tested with a deliberately misbehaving
        # test backend (see tests/test_controller.py).
        br = BackendResult(ActionStatus.BACKEND_FAILURE, f"backend failure: {exc}")
    finally:
        model.busy = False

    result = ActionResult(action=name, revision=model.revision, status=br.status, message=br.message)
    model.record_result(result)
    return _ok(model)
