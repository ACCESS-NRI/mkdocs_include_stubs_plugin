from mkdocs.config import Config
from mkdocs.config import config_options as opt

DEFAULT_PATTERN_RELEASED = r"release-*"
DEFAULT_PATTERN_DEVELOPMENT = r"dev-*"
DEFAULT_STUBS_DIR_PATH = 'documentation'
DEFAULT_MAIN_WEBSITE_BRANCH = 'main'
DEFAULT_STUBS_NAVIGATION_DIR_PATH = 'Configurations'

class ConfigScheme(Config):
    """Configuration for the plugin."""
    stubs_dir = opt.Type(
        str,
        default=DEFAULT_STUBS_DIR_PATH,
    )
    pattern_development = opt.Type(
        str,
        default=DEFAULT_PATTERN_DEVELOPMENT,
    )
    pattern_released = opt.Type(
        str,
        default=DEFAULT_PATTERN_RELEASED,
    )
    repo = opt.Type(
        str,
        default=None,
    )
    main_website_branch = opt.Type(
        str,
        default=DEFAULT_MAIN_WEBSITE_BRANCH,
    )
    stubs_navigation_dir = opt.Type(
        str,
        default=DEFAULT_STUBS_NAVIGATION_DIR_PATH,
    )

def check_empty_input(input_value: str, input_name: str) -> None:
    """
    Raise a ValueError if a config input is empty.

    Args:
        input_value: Str 
            The value of the input to check.
        input_name: Str 
            The name of the input to check.
    """
    if input_value == "":
        raise ValueError(f"'{input_name}' cannot be empty.")