from enum import StrEnum

from mkdocs.config import Config
from mkdocs.config import config_options as opt
from typing import Any

DEFAULT_PATTERN_MAIN_WEBSITE = r"release-*"
DEFAULT_PATTERN_PREVIEW_WEBSITE = r"dev-*"
DEFAULT_STUBS_DIR_PATH = "documentation"
DEFAULT_MAIN_WEBSITE_BRANCH = "main"
DEFAULT_STUBS_WEBSITE_DIR_PATH = "configurations"
DEFAULT_SUPPORTED_FILE_FORMATS = [".md", ".html"]

class NonEmptyStr(str):
    """
    A new type to use within mkdocs configuration to ensure that a string is stripped and not empty.
    """
    def __new__(cls, value: Any) -> "NonEmptyStr":
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value).__name__}")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("String must not be empty.")
        return str.__new__(cls, cleaned)


class GitRefType(StrEnum):
    """Enum for Git reference types."""

    BRANCH = "branch"
    TAG = "tag"
    ALL = "all"


class _MainWebsiteOptions(Config):
    """Sub-options for the main_website option."""

    pattern = opt.Type(
        str,
        default=DEFAULT_PATTERN_MAIN_WEBSITE,
    )

    ref_type = opt.Choice([grt.value for grt in GitRefType], default="tag")

    branch = opt.Type(
        NonEmptyStr,
        default=DEFAULT_MAIN_WEBSITE_BRANCH,
    )


class _PreviewWebsiteOptions(Config):
    """Sub-options for the preview_website option."""

    pattern = opt.Type(
        str,
        default=DEFAULT_PATTERN_PREVIEW_WEBSITE,
    )

    ref_type = opt.Choice([grt.value for grt in GitRefType], default="branch")

    no_main = opt.Type(
        bool,
        default=False,
    )


class ConfigScheme(Config):
    """Configuration for the plugin."""

    repo = opt.Type(
        NonEmptyStr,
        default=None,
    )
    main_website = opt.SubConfig(_MainWebsiteOptions)
    preview_website = opt.SubConfig(_PreviewWebsiteOptions)
    stubs_dir = opt.Type(
        NonEmptyStr,
        default=DEFAULT_STUBS_DIR_PATH,
    )
    stubs_site_dir = opt.Type(
        NonEmptyStr,
        default=DEFAULT_STUBS_WEBSITE_DIR_PATH,
    )
    supported_file_formats = opt.Type(
        (NonEmptyStr, list),
        default=DEFAULT_SUPPORTED_FILE_FORMATS,
    )