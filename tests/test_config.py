import pytest
from include_configuration_stubs.config import (
    check_empty_input,
)



def test_check_empty_input_no_raise():
    """
    Test the check_empty_input function when passing.
    """
    test_value = "example"
    test_name = "example_input"
    check_empty_input(test_value, test_name)

def test_check_empty_input_raise():
    """
    Test the check_empty_input function when raising an Exception.
    """
    test_value = ""
    test_name = "example_input"
    with pytest.raises(ValueError) as excinfo:
        check_empty_input(test_value, test_name)
        assert excinfo == f"'{test_name}' cannot be empty."