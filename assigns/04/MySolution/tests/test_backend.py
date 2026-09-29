"""Real interpretation and linting through RealLambdaBackend, including
factorial/Fibonacci and their base cases, malformed input, runtime
failures, and the placeholder/disabled operations."""

import pytest

from lambdaweb.backend import RealLambdaBackend
from lambdaweb.examples import FACTORIAL_SOURCE, FIBONACCI_SOURCE
from lambdaweb.results import ActionStatus


@pytest.fixture
def backend():
    return RealLambdaBackend()


# ---- Lint -----------------------------------------------------------------

def test_lint_success_for_closed_program(backend):
    result = backend.lint('D0Eop2("+", D0Eint(20), D0Eint(22))')
    assert result.status == ActionStatus.SUCCESS


def test_lint_reports_undeclared_variable(backend):
    result = backend.lint('D0Evar("x")')
    assert result.status == ActionStatus.ERROR
    assert "x" in result.message


def test_lint_reports_multiple_undeclared_variables_in_deterministic_order(backend):
    result = backend.lint('D0Eop2("+", D0Evar("b"), D0Evar("a"))')
    assert result.status == ActionStatus.ERROR
    # sorted order: "a" must appear before "b" in the message
    assert result.message.index("a") < result.message.index("b")


def test_lint_does_not_evaluate_a_closed_program_that_would_fail_at_runtime(backend):
    # Division by zero would raise if evaluated; Lint must not evaluate.
    result = backend.lint('D0Eop2("/", D0Eint(1), D0Eint(0))')
    assert result.status == ActionStatus.SUCCESS


def test_lint_on_malformed_input_is_an_error_not_a_crash(backend):
    result = backend.lint("not a constructor expression!!!")
    assert result.status == ActionStatus.ERROR


def test_lint_and_interpret_are_independent(backend):
    # Passing Lint means the expression is closed, not that evaluation
    # succeeds (Assign04.md). Division by zero passes Lint (above) but
    # fails Interpret (below).
    div_by_zero = 'D0Eop2("/", D0Eint(1), D0Eint(0))'
    assert backend.lint(div_by_zero).status == ActionStatus.SUCCESS
    assert backend.interpret(div_by_zero).status == ActionStatus.ERROR


# ---- Interpret --------------------------------------------------------------

def test_interpret_arithmetic(backend):
    result = backend.interpret('D0Eop2("+", D0Eint(20), D0Eint(22))')
    assert result.status == ActionStatus.SUCCESS
    assert result.message == "D0Vint(arg1=42)"


def test_interpret_factorial_example(backend):
    result = backend.interpret(FACTORIAL_SOURCE)
    assert result.status == ActionStatus.SUCCESS
    assert result.message == "D0Vint(arg1=120)"  # 5! = 120


def test_interpret_factorial_base_case_zero(backend):
    source = (
        'D0Eapp(D0Efix("fact", "n", '
        'D0Eif0(D0Eop2("==", D0Evar("n"), D0Eint(0)), D0Eint(1), '
        'D0Eop2("*", D0Evar("n"), D0Eapp(D0Evar("fact"), D0Eop2("-", D0Evar("n"), D0Eint(1)))))), '
        'D0Eint(0))'
    )
    result = backend.interpret(source)
    assert result.status == ActionStatus.SUCCESS
    assert result.message == "D0Vint(arg1=1)"  # 0! = 1


def test_interpret_fibonacci_example(backend):
    result = backend.interpret(FIBONACCI_SOURCE)
    assert result.status == ActionStatus.SUCCESS
    assert result.message == "D0Vint(arg1=55)"  # fib(10) = 55


def test_interpret_fibonacci_base_cases(backend):
    def fib_of(n):
        return (
            'D0Eapp(D0Efix("fib", "n", '
            'D0Eif0(D0Eop2("<", D0Evar("n"), D0Eint(2)), D0Evar("n"), '
            'D0Eop2("+", D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(1))), '
            'D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(2)))))), '
            f'D0Eint({n}))'
        )
    r0 = backend.interpret(fib_of(0))
    r1 = backend.interpret(fib_of(1))
    assert r0.status == ActionStatus.SUCCESS and r0.message == "D0Vint(arg1=0)"
    assert r1.status == ActionStatus.SUCCESS and r1.message == "D0Vint(arg1=1)"


def test_interpret_reports_malformed_input(backend):
    result = backend.interpret("this is not valid !!!")
    assert result.status == ActionStatus.ERROR


def test_interpret_reports_runtime_failure_division_by_zero(backend):
    result = backend.interpret('D0Eop2("/", D0Eint(1), D0Eint(0))')
    assert result.status == ActionStatus.ERROR


def test_interpret_reports_runtime_failure_unbound_variable(backend):
    # A free variable passes the constructor reader but fails at runtime
    # (D0env_search returns the D0V000 error sentinel).
    result = backend.interpret('D0Evar("undeclared")')
    assert result.status == ActionStatus.ERROR


def test_interpret_times_out_on_an_expensive_computation():
    # A generous-looking but very short timeout, plus a computation heavy
    # enough to blow past it, exercises the real timeout path distinctly
    # from Python's own RecursionError.
    slow_backend = RealLambdaBackend(interpret_timeout=0.01)
    def fib_of(n):
        return (
            'D0Eapp(D0Efix("fib", "n", '
            'D0Eif0(D0Eop2("<", D0Evar("n"), D0Eint(2)), D0Evar("n"), '
            'D0Eop2("+", D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(1))), '
            'D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(2)))))), '
            f'D0Eint({n}))'
        )
    result = slow_backend.interpret(fib_of(28))
    assert result.status == ActionStatus.BACKEND_FAILURE
    assert "timed out" in result.message


# ---- Type-check / Compile placeholders --------------------------------------

def test_typecheck_is_not_implemented_for_valid_source(backend):
    result = backend.typecheck('D0Eint(1)')
    assert result.status == ActionStatus.NOT_IMPLEMENTED


def test_compile_is_not_implemented_for_valid_source(backend):
    result = backend.compile('D0Eint(1)')
    assert result.status == ActionStatus.NOT_IMPLEMENTED


def test_typecheck_still_reports_malformed_input_as_error_not_not_implemented(backend):
    result = backend.typecheck("not valid !!!")
    assert result.status == ActionStatus.ERROR


def test_compile_still_reports_malformed_input_as_error_not_not_implemented(backend):
    result = backend.compile("not valid !!!")
    assert result.status == ActionStatus.ERROR


# ---- Execute -----------------------------------------------------------------

def test_execute_is_disabled_without_an_artifact(backend):
    result = backend.execute(None)
    assert result.status == ActionStatus.DISABLED
