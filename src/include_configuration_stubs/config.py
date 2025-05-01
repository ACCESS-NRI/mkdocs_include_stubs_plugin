from enum import StrEnum
from typing import TypeVar

from mkdocs.config import Config
from mkdocs.config import config_options as opt

T = TypeVar("T")

DEFAULT_PATTERN_MAIN_WEBSITE = r"release-*"
DEFAULT_PATTERN_PREVIEW_WEBSITE = r"dev-*"
DEFAULT_STUBS_DIR_PATH = "documentation"
DEFAULT_MAIN_WEBSITE_BRANCH = "main"
DEFAULT_STUBS_WEBSITE_DIR_PATH = "configurations"
DEFAULT_SUPPORTED_FILE_FORMATS = [".md", ".html"]


class _Type(opt.Type):
    """
    A new mkdocs.config.Type class to ensure that string types are stripped and not empty.
    """

    def run_validation(self, value: object) -> object:
        value = super().run_validation(value)
        # Post-process strings to ensure they are stripped and not empty
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("String must not be empty.")
        return value


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

    branch = _Type(
        str,
        default=DEFAULT_MAIN_WEBSITE_BRANCH,
    )


class _PreviewWebsiteOptions(Config):
    """Sub-options for the preview_website option."""

    pattern = opt.Type(
        str,
        default=DEFAULT_PATTERN_PREVIEW_WEBSITE,
    )

    ref_type = opt.Choice([grt.value for grt in GitRefType], default="branch")

    no_main = _Type(
        bool,
        default=False,
    )


class ConfigScheme(Config):
    """Configuration for the plugin."""

    repo = _Type(
        str,
        default=None,
    )
    main_website = opt.SubConfig(_MainWebsiteOptions)
    preview_website = opt.SubConfig(_PreviewWebsiteOptions)
    stubs_dir = _Type(
        str,
        default=DEFAULT_STUBS_DIR_PATH,
    )
    stubs_site_dir = _Type(
        str,
        default=DEFAULT_STUBS_WEBSITE_DIR_PATH,
    )
    supported_file_formats = _Type(
        (str, list),
        default=DEFAULT_SUPPORTED_FILE_FORMATS,
    )
