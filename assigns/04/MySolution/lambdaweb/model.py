"""
Model (MVC): owns the applied source, its revision, action results, and
any generated-code artifact. Enforces state rules (F2, F3, F8, F10)
entirely on its own — no HTML, no HTTP request objects, no browser
concepts appear anywhere in this file, so it can be constructed and
tested with plain Python (see tests/test_model.py, which runs with no
Flask app and no browser).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lambdaweb.limits import MAX_SOURCE_BYTES
from lambdaweb.results import ActionResult, ActionStatus


class PendingEditError(Exception):
    """Raised when a tool action or source replacement is attempted while
    unapplied edits are present (F2)."""


class InvalidSourceError(Exception):
    """Raised when source text fails validation (F3): empty/whitespace-only,
    or larger than the documented size limit. `preserved` is always True
    to signal to the controller that the model's applied state was left
    untouched."""


class NoAppliedSourceError(Exception):
    """Raised when a tool action is requested before any source has been
    applied (F4: "Require applied source before invoking
    source-processing operations")."""


@dataclass
class SourceModel:
    source_name: str = "(none)"
    applied_source: str = ""
    pending_source: str | None = None
    revision: int = 0
    results: dict[str, ActionResult] = field(default_factory=dict)
    artifact: object | None = None       # revision-tagged compiled artifact (always
    artifact_revision: int | None = None  # None: Compile is a placeholder)
    busy: bool = False

    # ---- queries -----------------------------------------------------

    @property
    def has_pending_edit(self) -> bool:
        return self.pending_source is not None

    @property
    def has_applied_source(self) -> bool:
        return bool(self.applied_source.strip())

    @property
    def execute_available(self) -> bool:
        # Execute is only ever enabled once a real artifact exists for the
        # CURRENT revision (F4: "Execute remains disabled while generated
        # code is unavailable"; source changes invalidate a stale artifact).
        return self.artifact is not None and self.artifact_revision == self.revision

    # ---- validation ----------------------------------------------------

    @staticmethod
    def validate_text(text: str) -> None:
        if not text.strip():
            raise InvalidSourceError("source is empty or whitespace-only")
        size = len(text.encode("utf-8", errors="strict"))
        if size > MAX_SOURCE_BYTES:
            raise InvalidSourceError(
                f"source is {size} bytes, exceeding the "
                f"{MAX_SOURCE_BYTES}-byte limit"
            )

    # ---- mutations -----------------------------------------------------

    def load_source(self, name: str, text: str) -> None:
        """Replace the applied source outright (upload / canned example /
        fresh manual-input slate). F8: creates a new revision and clears
        prior results/artifact. Blocked while a pending edit exists (F2)."""
        if self.has_pending_edit:
            raise PendingEditError(
                "apply or discard the current edit before loading a new source"
            )
        SourceModel.validate_text(text)
        self.source_name = name
        self.applied_source = text
        self.pending_source = None
        self.revision += 1
        self.results = {}
        self.artifact = None
        self.artifact_revision = None

    def start_manual_input(self) -> None:
        """F1: 'Manual input opens a blank editor.' This opens a *pending*
        blank editor; nothing is applied (and no revision is created)
        until the user applies non-empty text."""
        if self.has_pending_edit:
            raise PendingEditError(
                "apply or discard the current edit before starting manual input"
            )
        self.pending_source = ""

    def edit(self, text: str) -> None:
        """F2: 'Allow typing initial code without an upload and editing
        loaded source.' Called on every editor change; tracks the
        in-progress edit without touching applied_source."""
        self.pending_source = None if text == self.applied_source else text

    def apply_edit(self) -> None:
        """F2 'Apply changes'. On success: commits pending_source as the
        new applied_source, bumps the revision, clears results/artifact
        (F8). On failure (F3): applied_source is left untouched, and
        pending_source is deliberately NOT cleared, so the rejected text
        stays in the editor for the user to fix."""
        if not self.has_pending_edit:
            return  # nothing to apply
        SourceModel.validate_text(self.pending_source)  # may raise InvalidSourceError
        self.applied_source = self.pending_source
        self.pending_source = None
        self.revision += 1
        self.results = {}
        self.artifact = None
        self.artifact_revision = None

    def discard_edit(self) -> None:
        """F2 'Discard changes'. Reverts to applied_source; no revision
        change, no effect on results."""
        self.pending_source = None

    def require_actionable(self) -> None:
        """Guard used by the Controller before dispatching ANY
        source-processing operation (Lint/Interpret/Type-check/Compile).
        Raised errors carry the specific reason so the View can explain
        why the action was refused."""
        if self.has_pending_edit:
            raise PendingEditError(
                "apply or discard the current edit before running an action"
            )
        if not self.has_applied_source:
            raise NoAppliedSourceError("no source has been applied yet")

    def record_result(self, result: ActionResult) -> None:
        self.results[result.action] = result
        if result.action == "compile":
            if result.status == ActionStatus.SUCCESS:
                self.artifact = result.message  # placeholder hook; never SUCCESS today
                self.artifact_revision = result.revision
            else:
                self.artifact = None
                self.artifact_revision = None
