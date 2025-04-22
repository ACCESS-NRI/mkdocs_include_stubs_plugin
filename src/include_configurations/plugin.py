"""Main plugin."""

from mkdocs.config import Config
from mkdocs.config import config_options as opt
from mkdocs.plugins import BasePlugin


class ConfigScheme(Config):
    """Configuration for the plugin."""
    repo_url = opt.Type(
        str,
        default=None,
        required=False,
        help="The URL of the repository used to retrieve branches and tags for the \
            configurations included in the MkDocs site. If not specified, the equivalent of \
            the output of `git remote get-url origin` for the current Git repository will be used.",
    )


class IncludeConfigurationsPlugin(BasePlugin[ConfigScheme]):
    def on_files(self, files, config):
        """Hook to modify the files."""
        pass

    def on_nav(self, nav, config, files):
        """Hook to modify the navigation."""
        pass
