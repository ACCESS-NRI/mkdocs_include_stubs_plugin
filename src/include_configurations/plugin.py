"""Main plugin."""

from mkdocs.config import Config
from mkdocs.config import config_options as opt
from mkdocs.plugins import BasePlugin
from include_configurations.utils import get_origin_url

DEFAULT_PATTERN_RELEASED = r"^release-.+"
DEFAULT_PATTERN_DEVELOPMENT = r"^dev-.+"

class ConfigScheme(Config):
    """Configuration for the plugin."""
    repo_url = opt.Type(
        str,
        default=None,
    )
    pattern_released = opt.Type(
        str,
        default=DEFAULT_PATTERN_RELEASED,
    )
    pattern_development = opt.Type(
        str,
        default=DEFAULT_PATTERN_DEVELOPMENT,
    )


class IncludeConfigurationsPlugin(BasePlugin[ConfigScheme]):
    def on_files(self, files, config):
        """Hook to modify the files."""
        repo_url = self.config.repo_url or get_origin_url()
        # repo = Repo("/path/to/repo")

        

    def on_nav(self, nav, config, files):
        """Hook to modify the navigation."""
        pass
