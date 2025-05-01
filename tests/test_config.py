import pytest

from include_configuration_stubs.config import (
    _Type,
)
from unittest.mock import patch

@pytest.fixture
def custom_type():
    return _Type(str)


@pytest.mark.parametrize(
    "input_value, expected_output, raises_error",
    [
        ("hello", "hello", False),  # valid_string
        ("  hello  ", "hello", False),  # string_with_spaces
        (123, 123, False),  # int_input
        ([1,2,3], [1,2,3], False),  # list_input
        (None, None, False),  # none_input
        ("", None, True),  # empty_string
        ("   ", None, True),  # empty_string_with_spaces
    ],
    ids=[
        "valid_string",
        "string_with_spacesing",
        "int_input",
        "list_input",
        "none_input",
        "empty_string",
        "empty_string_with_spaces",
    ],
)
def test_valid_string(custom_type, input_value, expected_output, raises_error):
    with patch('include_configuration_stubs.config.opt.Type.run_validation', return_value=input_value):
        if not raises_error:
            assert custom_type.run_validation(input_value) == expected_output
        else:
            with pytest.raises(ValueError) as excinfo:
                custom_type.run_validation(input_value)
                assert str(excinfo.value) == "String must not be empty."