import pytest

from include_configuration_stubs.config import (
    NonEmptyStr,
)



def test_NonEmptyStr_valid():
    assert NonEmptyStr("hello") == "hello"
    assert NonEmptyStr("  hello ") == "hello"
    assert isinstance(NonEmptyStr("hi"), NonEmptyStr)
    assert issubclass(type(NonEmptyStr("abc")), str)


@pytest.mark.parametrize(
    "input_value",
    [
        "",  # empty_string
        "  ",  # empty_string_with_spaces
    ],
    ids=[
        "empty_string",
        "empty_string_with_spaces",
    ],
)
def test_NonEmptyStr_empty(input_value):
    with pytest.raises(ValueError) as excinfo:
        NonEmptyStr(input_value)
        assert str(excinfo.value) == "String must not be empty."


@pytest.mark.parametrize(
    "input_value, type",
    [
        (123,"int"),  # int
        (None,"NoneType"),  # none
        ([1,2,'hello'],"list"),  # list
    ],
    ids=[
        "int",
        "none",
        "list",
    ],
)
def test_NonEmptyStr_non_string_input(input_value, type):
    with pytest.raises(ValueError) as excinfo:
        NonEmptyStr(input_value)
        assert str(excinfo.value) == f"Expected string, got {type}."
