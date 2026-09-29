"""
Controller tests, using a fake LanguageBackend instead of the real one
(Assign04.md: "At least one controller test must substitute a test
backend without changing view code"). These exercise dispatch, source
loading/editing rules, busy-state cleanup, backend-failure handling, and
retry — all through Flask's test client, with NO change to routes.py or
the templates.
"""

import io

import pytest

from lambdaweb import create_app
from lambdaweb.backend import LanguageBackend
from lambdaweb.results import ActionStatus, BackendResult


class FakeBackend(LanguageBackend):
    """Deterministic stand-in for RealLambdaBackend. `interpret_result`
    and `raise_on_interpret` let individual tests control its behavior
    without touching lambda1.py or the real parser at all."""

    def __init__(self):
        self.interpret_result = BackendResult(ActionStatus.SUCCESS, "D0Vint(arg1=42)")
        self.raise_on_interpret = False
        self.calls = []

    def lint(self, source):
        self.calls.append(("lint", source))
        return BackendResult(ActionStatus.SUCCESS, "no free (undeclared) variables found")

    def interpret(self, source):
        self.calls.append(("interpret", source))
        if self.raise_on_interpret:
            raise RuntimeError("simulated backend crash")
        return self.interpret_result

    def typecheck(self, source):
        return BackendResult(ActionStatus.NOT_IMPLEMENTED, "type checking is not yet implemented")

    def compile(self, source):
        return BackendResult(ActionStatus.NOT_IMPLEMENTED, "compilation is not yet implemented")

    def execute(self, artifact):
        return BackendResult(ActionStatus.DISABLED, "no artifact available")


@pytest.fixture
def client():
    app = create_app(backend=FakeBackend())
    app.testing = True
    return app.test_client()


def _backend_of(client):
    return client.application.config["BACKEND"]


def test_index_page_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"LAMBDA Web Front-End" in resp.data


def test_load_example_then_lint_dispatches_to_backend(client):
    resp = client.post("/api/load/example", json={"name": "factorial"})
    assert resp.status_code == 200
    state = resp.get_json()
    assert state["source_name"] == "factorial"
    assert state["revision"] == 1

    resp = client.post("/api/action/lint")
    state = resp.get_json()
    assert state["results"]["lint"]["status"] == "success"
    assert _backend_of(client).calls[-1][0] == "lint"


def test_manual_input_then_apply(client):
    client.post("/api/load/manual")
    resp = client.post("/api/edit", json={"text": 'D0Eint(1)'})
    state = resp.get_json()
    assert state["has_pending_edit"] is True

    resp = client.post("/api/apply")
    state = resp.get_json()
    assert state["has_pending_edit"] is False
    assert state["applied_source"] == "D0Eint(1)"
    assert state["revision"] == 1


def test_action_blocked_while_pending_edit_present(client):
    client.post("/api/load/example", json={"name": "factorial"})
    client.post("/api/edit", json={"text": "changed but not applied"})
    resp = client.post("/api/action/lint")
    assert resp.status_code == 409
    state = resp.get_json()
    assert state["error"]["type"] == "pending_edit"


def test_action_blocked_when_no_source_applied_yet(client):
    resp = client.post("/api/action/lint")
    assert resp.status_code == 409
    assert resp.get_json()["error"]["type"] == "no_applied_source"


def test_apply_rejects_empty_edit_and_preserves_previous_applied_source(client):
    client.post("/api/load/example", json={"name": "factorial"})
    client.post("/api/edit", json={"text": "   "})
    resp = client.post("/api/apply")
    assert resp.status_code == 409
    state = resp.get_json()
    assert state["error"]["type"] == "invalid_source"
    assert state["applied_source"] != "   "  # previous applied source preserved
    assert state["pending_source"] == "   "  # rejected text kept for correction


def test_upload_rejects_invalid_utf8(client):
    bad_bytes = b"\xff\xfe\x00not-utf8"
    resp = client.post(
        "/api/load/upload",
        data={"file": (io.BytesIO(bad_bytes), "bad.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 409
    assert resp.get_json()["error"]["type"] == "invalid_source"


def test_placeholder_typecheck_and_compile_never_report_success(client):
    client.post("/api/load/example", json={"name": "factorial"})
    resp = client.post("/api/action/typecheck")
    assert resp.get_json()["results"]["typecheck"]["status"] == "not_implemented"
    resp = client.post("/api/action/compile")
    assert resp.get_json()["results"]["compile"]["status"] == "not_implemented"


def test_execute_remains_unavailable_without_a_real_compiler(client):
    client.post("/api/load/example", json={"name": "factorial"})
    state = client.get("/api/state").get_json()
    assert state["execute_available"] is False
    resp = client.post("/api/action/execute")
    assert resp.get_json()["results"]["execute"]["status"] == "disabled"


def test_backend_failure_is_reported_and_model_recovers_for_retry(client):
    client.post("/api/load/example", json={"name": "factorial"})
    backend = _backend_of(client)

    backend.raise_on_interpret = True
    resp = client.post("/api/action/interpret")
    state = resp.get_json()
    assert state["results"]["interpret"]["status"] == "backend_failure"

    # Busy must have been cleared even though the backend raised, and a
    # normal action must succeed right after (successful retry).
    backend.raise_on_interpret = False
    resp = client.post("/api/action/interpret")
    state = resp.get_json()
    assert state["results"]["interpret"]["status"] == "success"


def test_every_accepted_load_creates_a_new_revision_and_clears_results(client):
    client.post("/api/load/example", json={"name": "factorial"})
    client.post("/api/action/lint")
    state = client.get("/api/state").get_json()
    assert "lint" in state["results"]

    state = client.post("/api/load/example", json={"name": "fibonacci"}).get_json()
    assert state["revision"] == 2
    assert state["results"] == {}
