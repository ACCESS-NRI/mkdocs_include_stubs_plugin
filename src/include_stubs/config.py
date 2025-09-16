from enum import StrEnum
from typing import TypeVar
from dataclasses import dataclass

from mkdocs.config import Config
from mkdocs.config import config_options as opt

T = TypeVar("T")

SUPPORTED_FILE_FORMATS = (".md", ".html")
DEFAULT_PATTERN_MAIN_WEBSITE = r"release-*"
DEFAULT_PATTERN_PREVIEW_WEBSITE = r"dev-*"
DEFAULT_STUBS_DIR = "documentation/stub"
DEFAULT_STUBS_PARENT_URL = ""


class GitRefType(StrEnum):
    """Enum for Git reference types."""

    BRANCH = "branch"
    TAG = "tag"
    ALL = "all"

    def __str__(self) -> str:
        if self is GitRefType.BRANCH:
            return "branches"
        elif self is GitRefType.TAG:
            return "tags"
        else:
            return "branches and tags"    

@dataclass
class GitRef:
    name: str
    sha: str
    
    def __repr__(self) -> str:
        return f"{self.name} ({self.sha})"


class _MainWebsiteOptions(Config):
    """Sub-options for the main_website option."""

    pattern = opt.Type(
        str,
        default=DEFAULT_PATTERN_MAIN_WEBSITE,
    )

    ref_type = opt.Choice([grt.value for grt in GitRefType], default="tag")

    branch = opt.Optional(opt.Type(str))


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

    repo = opt.Optional(opt.Type(str))
    main_website = opt.SubConfig(_MainWebsiteOptions)
    preview_website = opt.SubConfig(_PreviewWebsiteOptions)
    stubs_dir = opt.Type(
        str,
        default=DEFAULT_STUBS_DIR,
    )
    stubs_parent_url = opt.Type(
        str,
        default=DEFAULT_STUBS_PARENT_URL,
    )
    stubs_nav_path = opt.Optional(opt.Type(str))


def set_default_stubs_nav_path(stubs_parent_url: str) -> str:
    """
    Set the default stubs navigation path from the stubs_parent_url by by
    capitalizing each path segment, replacing underscores with spaces and
    forward slashes with 'greater than' (>) symbols.

    Args:
        stubs_parent_url: Str
            The input stubs parent URL.

    Returns:
        Str
            The default stubs navigation path.
    """
    parts = stubs_parent_url.removesuffix("/").removeprefix("/").split("/")
    new_parts = [part.replace("_", " ").strip().capitalize() for part in parts]
    return " > ".join(new_parts)
