import pytest
import logging

from termcolor import colored
from include_stubs.logging import get_custom_logger

@pytest.fixture()
def logger():
    """
    Create a logger fixture using get_custom_logger, that clears handlers after usage to avoid polluting other tests.
    The get_custom_logger function will create the desired handler if logger doesn't have one already.
    """
    _logger = get_custom_logger("test_logger")
    yield _logger
    _logger.handlers.clear()
    _logger.setLevel(logging.NOTSET)
    _logger.propagate = False


@pytest.mark.parametrize(
    "levelname, levelcolor",
    [
        ("INFO", None), # info
        ("WARNING", "yellow"), # warning
    ],
    ids = [
        "info",
        "warning",
    ]
)
@pytest.mark.parametrize(
    "text_wrapper_width",
    [
        0, # no_text_wrapper_width
        1000, # with_text_wrapper_width
    ],
    ids = [
        "no_text_wrapper_width",
        "with_text_wrapper_width",
    ]
)
def test_logger_no_wrapping(logger, levelname, levelcolor, text_wrapper_width):
    """Test the name and format of the ColouredPrefixedLogger without wrapping."""
    assert logger.name == "mkdocs.plugins.test_logger"
    message = "Example message"
    formatter = logger.handlers[0].formatter
    formatter.text_wrapper.width=text_wrapper_width
    record = logger.makeRecord(
        name=logger.name,
        level=getattr(logging,levelname),
        fn="fake_file.py",
        lno=1,
        msg=message,
        args=(),
        exc_info=None
    )
    formatted = formatter.format(record)
    expected_prefix = colored("[test_logger]", "light_blue")
    level_prefix = f"{levelname:<8}-  "
    if levelcolor:
        level_prefix = colored(level_prefix, levelcolor)

    assert formatted == f"{level_prefix}{expected_prefix} {message}"

@pytest.mark.parametrize(
    "levelname, levelcolor",
    [
        ("INFO", None), # info
        ("WARNING", "yellow"), # warning
    ],
    ids = [
        "info",
        "warning",
    ]
)
def test_logger_wrapping(logger, levelname, levelcolor):
    """Test the name and format of the ColouredPrefixedLogger with wrapping."""
    assert logger.name == "mkdocs.plugins.test_logger"
    message = "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
    formatter = logger.handlers[0].formatter
    formatter.text_wrapper.width=22
    record = logger.makeRecord(
        name=logger.name,
        level=getattr(logging,levelname),
        fn="fake_file.py",
        lno=1,
        msg=message,
        args=(),
        exc_info=None
    )
    formatted = formatter.format(record)
    expected_prefix = colored("[test_logger]", "light_blue")
    level_prefix = f"{levelname:<8}-  "
    expected_wrapped_message = ("\n"+" "*len(level_prefix)).join([
        f"{expected_prefix}",
        "Lorem ipsum",
        "dolor sit",
        "amet,",
        "consectetur",
        "adipiscing",
        "elit."
    ])
    if levelcolor:
        level_prefix = colored(level_prefix, levelcolor)
    assert formatted == f"{level_prefix}{expected_wrapped_message}"