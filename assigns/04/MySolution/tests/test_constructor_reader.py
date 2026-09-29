"""Restricted constructor reader: must accept well-formed constructor
expressions (including comments/multiline/nested calls) and must refuse
to execute arbitrary code, no matter how it is disguised."""

import pytest

from lambdaweb.constructor_reader import ConstructorReadError, MAX_SOURCE_BYTES, read_d0exp
from lambdaweb.lambda1 import D0Eint, D0Eop2


def test_reads_simple_constructor():
    result = read_d0exp('D0Eint(5)')
    assert result == D0Eint(5)


def test_reads_nested_constructors():
    result = read_d0exp('D0Eop2("+", D0Eint(20), D0Eint(22))')
    assert result == D0Eop2("+", D0Eint(20), D0Eint(22))


def test_reads_negative_int_literal():
    result = read_d0exp('D0Eint(-3)')
    assert result == D0Eint(-3)


def test_accepts_comments_and_multiline_expressions():
    source = """
    # a comment above the expression
    D0Eop2(
        "+",       # left operand below
        D0Eint(1),
        D0Eint(2)  # right operand
    )
    """
    result = read_d0exp(source)
    assert result == D0Eop2("+", D0Eint(1), D0Eint(2))


def test_rejects_empty_source():
    with pytest.raises(ConstructorReadError):
        read_d0exp("")


def test_rejects_whitespace_only_source():
    with pytest.raises(ConstructorReadError):
        read_d0exp("   \n\t  ")


def test_rejects_oversized_source():
    huge = "D0Eint(1)  # " + ("x" * (MAX_SOURCE_BYTES + 10))
    with pytest.raises(ConstructorReadError):
        read_d0exp(huge)


def test_rejects_unknown_constructor_name():
    with pytest.raises(ConstructorReadError):
        read_d0exp('SomeOtherThing(1)')


def test_rejects_wrong_argument_count():
    with pytest.raises(ConstructorReadError):
        read_d0exp('D0Eint(1, 2)')


def test_rejects_keyword_arguments():
    with pytest.raises(ConstructorReadError):
        read_d0exp('D0Eint(arg1=5)')


def test_does_not_execute_arbitrary_code_via_builtins():
    # Regression test for the core security requirement: this must raise
    # ConstructorReadError, and must NOT actually import os or run a
    # shell command.
    with pytest.raises(ConstructorReadError):
        read_d0exp("__import__('os').system('echo hacked')")


def test_does_not_execute_arbitrary_code_via_open():
    with pytest.raises(ConstructorReadError):
        read_d0exp("open('/etc/passwd').read()")


def test_rejects_attribute_access():
    with pytest.raises(ConstructorReadError):
        read_d0exp("D0Eint(5).arg1")


def test_rejects_list_and_dict_literals():
    with pytest.raises(ConstructorReadError):
        read_d0exp("[1, 2, 3]")
    with pytest.raises(ConstructorReadError):
        read_d0exp("{'a': 1}")
