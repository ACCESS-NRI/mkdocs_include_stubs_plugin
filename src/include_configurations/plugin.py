"""Main plugin."""

from mkdocs.config import Config
from mkdocs.config import config_options as opt
from mkdocs.plugins import BasePlugin

DEFAULT_PATTERN_RELEASED = r"release-*"
DEFAULT_PATTERN_DEVELOPMENT = r"dev-*"
DEFAULT_DOCUMENTATION_DIR_PATH = 'documentation'

class ConfigScheme(Config):
    """Configuration for the plugin."""
    documentation_dir = opt.Type(
        str,
        default=DEFAULT_DOCUMENTATION_DIR_PATH,
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

class IncludeConfigurationsPlugin(BasePlugin[ConfigScheme]):
    def __init__(self):
        super().__init__()
        self.repo_url = self.config.repo_url or '.'
        self.pattern_released = self.config.pattern_released or DEFAULT_PATTERN_RELEASED
        self.pattern_development = self.config.pattern_development or DEFAULT_PATTERN_DEVELOPMENT

    def on_files(self, files, config):
        """Hook to modify the files."""
        # If no repo is provided, use the current directory

    def on_nav(self, nav, config, files):
        """Hook to modify the navigation."""
        pass
