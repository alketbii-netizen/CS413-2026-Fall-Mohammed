"""
Language-tool interface (adapter). Assign04, Task 2: "Place language-tool
integration behind a separate backend interface or adapter." Neither the
View nor the Model imports lambda1.py, fvset.py, or constructor_reader.py
directly — only this module does. The Controller talks to a
`LanguageBackend` only through the five conceptual operations below, so a
future real compiler/type-checker can be dropped in by implementing this
same interface (see ARCHITECTURE.md, "how real type-checking and
compilation could replace the placeholders").
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Any

from lambdaweb.constructor_reader import ConstructorReadError, read_d0exp
from lambdaweb.fvset import d0exp_fvset
from lambdaweb.lambda1 import D0V000, D0Vpair, d0exp_evaluate
from lambdaweb.limits import INTERPRET_TIMEOUT_SECONDS
from lambdaweb.results import ActionStatus, BackendResult


class LanguageBackend(ABC):
    """lint(source) -> result
    interpret(source) -> result
    typecheck(source) -> not-implemented result
    compile(source) -> not-implemented result
    execute(artifact) -> result, when generated code is available

    These are conceptual signatures (per Assign04.md), not prescribed
    function names or HTTP routes; routes.py is the only place that turns
    them into HTTP endpoints.
    """

    @abstractmethod
    def lint(self, source: str) -> BackendResult: ...

    @abstractmethod
    def interpret(self, source: str) -> BackendResult: ...

    @abstractmethod
    def typecheck(self, source: str) -> BackendResult: ...

    @abstractmethod
    def compile(self, source: str) -> BackendResult: ...

    @abstractmethod
    def execute(self, artifact: Any) -> BackendResult: ...


class RealLambdaBackend(LanguageBackend):
    """The one real implementation for this assignment: Lint and Interpret
    are real (backed by lambda1.py + fvset.py + constructor_reader.py);
    Type-check and Compile are documented placeholders; Execute is
    reserved for generated code and is always DISABLED here because
    Compile never produces an artifact."""

    def __init__(self, interpret_timeout: float = INTERPRET_TIMEOUT_SECONDS) -> None:
        self._interpret_timeout = interpret_timeout

    # ---- Lint: real free-variable checking ------------------------------

    def lint(self, source: str) -> BackendResult:
        try:
            dexp = read_d0exp(source)
        except ConstructorReadError as exc:
            return BackendResult(ActionStatus.ERROR, f"invalid input: {exc}")

        # Lint must not evaluate the expression (Assign04.md).
        free_vars = d0exp_fvset(dexp)
        if free_vars:
            names = ", ".join(sorted(free_vars))  # deterministic order
            return BackendResult(
                ActionStatus.ERROR,
                f"undeclared variable(s): {names}",
            )
        return BackendResult(ActionStatus.SUCCESS, "no free (undeclared) variables found")

    # ---- Interpret: real evaluation --------------------------------------

    def interpret(self, source: str) -> BackendResult:
        try:
            dexp = read_d0exp(source)
        except ConstructorReadError as exc:
            return BackendResult(ActionStatus.ERROR, f"invalid input: {exc}")

        # Run the evaluation on a DAEMON thread with a hard join timeout
        # (F10 / Assign04.md: "a documented timeout or other bounded
        # execution mechanism so a nonterminating program cannot leave
        # the application permanently busy"). The thread is daemonic so
        # that an abandoned, still-running computation (after a timeout)
        # can never block the application's own process from exiting or
        # from handling the next request.
        outcome: dict[str, Any] = {}

        def _worker() -> None:
            try:
                outcome["value"] = d0exp_evaluate(dexp)
            except BaseException as exc:  # noqa: BLE001 - captured, not swallowed
                outcome["exc"] = exc

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join(self._interpret_timeout)

        if thread.is_alive():
            return BackendResult(
                ActionStatus.BACKEND_FAILURE,
                f"interpretation timed out after {self._interpret_timeout}s "
                f"(possible non-terminating program)",
            )

        if "exc" in outcome:
            exc = outcome["exc"]
            if isinstance(exc, RecursionError):
                return BackendResult(
                    ActionStatus.ERROR,
                    "runtime failure: maximum recursion depth exceeded "
                    "(the program is likely non-terminating or too deeply recursive)",
                )
            if isinstance(exc, (ZeroDivisionError, TypeError)):
                return BackendResult(ActionStatus.ERROR, f"runtime failure: {exc}")
            return BackendResult(ActionStatus.BACKEND_FAILURE, f"backend failure: {exc}")

        value = outcome["value"]
        if _contains_error_sentinel(value):
            return BackendResult(
                ActionStatus.ERROR,
                "runtime failure: evaluation produced an error sentinel "
                "(likely an unbound variable lookup at run time)",
            )
        return BackendResult(ActionStatus.SUCCESS, repr(value))

    # ---- Type-check / Compile: documented placeholders -------------------

    def typecheck(self, source: str) -> BackendResult:
        try:
            read_d0exp(source)
        except ConstructorReadError as exc:
            return BackendResult(ActionStatus.ERROR, f"invalid input: {exc}")
        return BackendResult(ActionStatus.NOT_IMPLEMENTED, "type checking is not yet implemented")

    def compile(self, source: str) -> BackendResult:
        try:
            read_d0exp(source)
        except ConstructorReadError as exc:
            return BackendResult(ActionStatus.ERROR, f"invalid input: {exc}")
        return BackendResult(ActionStatus.NOT_IMPLEMENTED, "compilation is not yet implemented")

    # ---- Execute: reserved for generated code -----------------------------

    def execute(self, artifact: Any) -> BackendResult:
        if artifact is None:
            return BackendResult(
                ActionStatus.DISABLED,
                "Execute runs generated code from Compile. Compilation is not "
                "yet implemented, so no artifact exists and Execute is disabled.",
            )
        # Reserved for a future real compiler extension (see ARCHITECTURE.md):
        # would run the artifact and never re-derive it from `source`.
        return BackendResult(
            ActionStatus.NOT_IMPLEMENTED,
            "executing generated code is not yet implemented",
        )


def _contains_error_sentinel(value: Any) -> bool:
    """True if `value` is the bare D0V000() error sentinel, or a pair
    containing one directly (Assign04.md: 'Treat an error sentinel
    D0V000() returned directly or inside a pair as an error rather than
    successful output'). Uses `type(x) is D0V000` rather than isinstance,
    since D0Vint/D0Vbtf/etc. are themselves subclasses of D0V000 and are
    valid successful results, not errors.
    """
    if type(value) is D0V000:
        return True
    if isinstance(value, D0Vpair):
        return type(value.arg1) is D0V000 or type(value.arg2) is D0V000
    return False
