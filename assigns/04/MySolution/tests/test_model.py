"""
Model tests. This file imports nothing from Flask, nothing from
lambdaweb.routes, and starts no server or browser — it exercises the
Model purely as plain Python objects (Assign04.md: "At least one model
test must run without a browser or web server").
"""

import pytest

from lambdaweb.model import (
    InvalidSourceError,
    NoAppliedSourceError,
    PendingEditError,
    SourceModel,
)
from lambdaweb.results import ActionResult, ActionStatus


def test_fresh_model_has_no_applied_source():
    m = SourceModel()
    assert not m.has_applied_source
    assert not m.has_pending_edit
    assert m.revision == 0


def test_load_source_sets_fields_and_bumps_revision():
    m = SourceModel()
    m.load_source("factorial", "D0Eint(1)")
    assert m.source_name == "factorial"
    assert m.applied_source == "D0Eint(1)"
    assert m.revision == 1
    assert m.results == {}


def test_load_source_rejects_empty_text_and_preserves_previous_applied_source():
    m = SourceModel()
    m.load_source("first", "D0Eint(1)")
    with pytest.raises(InvalidSourceError):
        m.load_source("second", "   ")
    # F3: previously applied source must be preserved after rejection.
    assert m.source_name == "first"
    assert m.applied_source == "D0Eint(1)"
    assert m.revision == 1


def test_load_source_blocked_while_pending_edit_present():
    m = SourceModel()
    m.load_source("first", "D0Eint(1)")
    m.edit("D0Eint(2)")
    assert m.has_pending_edit
    with pytest.raises(PendingEditError):
        m.load_source("second", "D0Eint(3)")


def test_edit_tracks_pending_text_and_clears_when_matching_applied():
    m = SourceModel()
    m.load_source("s", "D0Eint(1)")
    m.edit("D0Eint(2)")
    assert m.pending_source == "D0Eint(2)"
    assert m.has_pending_edit
    m.edit("D0Eint(1)")  # edited back to match applied source
    assert not m.has_pending_edit


def test_apply_edit_commits_and_bumps_revision_and_clears_results():
    m = SourceModel()
    m.load_source("s", "D0Eint(1)")
    m.record_result(ActionResult("lint", 1, ActionStatus.SUCCESS, "ok"))
    m.edit("D0Eint(2)")
    m.apply_edit()
    assert m.applied_source == "D0Eint(2)"
    assert m.revision == 2
    assert not m.has_pending_edit
    assert m.results == {}


def test_apply_edit_rejects_invalid_text_and_preserves_pending_for_correction():
    m = SourceModel()
    m.load_source("s", "D0Eint(1)")
    m.edit("   ")  # whitespace-only: invalid
    with pytest.raises(InvalidSourceError):
        m.apply_edit()
    # F3: applied_source untouched, rejected pending text kept for correction.
    assert m.applied_source == "D0Eint(1)"
    assert m.pending_source == "   "
    assert m.revision == 1


def test_discard_edit_reverts_without_changing_revision():
    m = SourceModel()
    m.load_source("s", "D0Eint(1)")
    m.edit("D0Eint(2)")
    m.discard_edit()
    assert not m.has_pending_edit
    assert m.applied_source == "D0Eint(1)"
    assert m.revision == 1


def test_require_actionable_blocks_on_pending_edit():
    m = SourceModel()
    m.load_source("s", "D0Eint(1)")
    m.edit("D0Eint(2)")
    with pytest.raises(PendingEditError):
        m.require_actionable()


def test_require_actionable_blocks_when_no_applied_source():
    m = SourceModel()
    with pytest.raises(NoAppliedSourceError):
        m.require_actionable()


def test_require_actionable_passes_with_applied_source_and_no_pending_edit():
    m = SourceModel()
    m.load_source("s", "D0Eint(1)")
    m.require_actionable()  # must not raise


def test_artifact_invalidated_by_new_revision():
    m = SourceModel()
    m.load_source("s", "D0Eint(1)")
    m.record_result(ActionResult("compile", 1, ActionStatus.SUCCESS, "fake-artifact"))
    assert m.execute_available
    m.load_source("s2", "D0Eint(2)")  # new revision
    assert not m.execute_available
    assert m.artifact is None


def test_record_result_overwrites_previous_result_for_same_action():
    m = SourceModel()
    m.load_source("s", "D0Eint(1)")
    m.record_result(ActionResult("lint", 1, ActionStatus.ERROR, "bad"))
    m.record_result(ActionResult("lint", 1, ActionStatus.SUCCESS, "ok"))
    assert m.results["lint"].status == ActionStatus.SUCCESS
