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
    main_website_branch = opt.Type(
        str,
        default='main',
    )

class IncludeConfigurationsPlugin(BasePlugin[ConfigScheme]):
    def __init__(self):
        super().__init__()
        self.pattern_released = self.config.pattern_released or DEFAULT_PATTERN_RELEASED
        self.pattern_development = self.config.pattern_development or DEFAULT_PATTERN_DEVELOPMENT

    def on_files(self, files, config):
        """Hook to modify the files."""
        # Check This is where you can modify the files before they are processed
        # For example, you can add or remove files from the list
        # files.append('new_file.md')
        # files.remove('old_file.md')
        pass

    def on_nav(self, nav, config, files):
        """Hook to modify the navigation."""
        pass
