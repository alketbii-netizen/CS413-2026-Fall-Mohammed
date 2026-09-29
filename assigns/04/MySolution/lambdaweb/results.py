"""
Shared result vocabulary used by both the Model and the backend adapter,
so that neither has to import the other just to talk about outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ActionStatus(Enum):
    SUCCESS = "success"                  # operation ran and produced a real result
    ERROR = "error"                      # invalid input or a language-level error
                                          # (e.g. Lint found undeclared variables,
                                          # or Interpret hit a runtime failure)
    NOT_IMPLEMENTED = "not_implemented"  # Type-check / Compile placeholders
    BACKEND_FAILURE = "backend_failure"  # timeout, crash, or other tool failure
                                          # unrelated to the program's own validity
    DISABLED = "disabled"                # Execute, while no artifact exists


@dataclass(frozen=True)
class BackendResult:
    """What a LanguageBackend method returns: status + message only. The
    backend adapter has no notion of "source revision" — that belongs to
    the Model. The Controller pairs a BackendResult with the revision it
    was computed against to build an ActionResult."""
    status: ActionStatus
    message: str


@dataclass(frozen=True)
class ActionResult:
    """The outcome of one action (lint/interpret/typecheck/compile/execute)
    run against one source revision (F9: "results with their action,
    source revision, and outcome")."""
    action: str
    revision: int
    status: ActionStatus
    message: str
