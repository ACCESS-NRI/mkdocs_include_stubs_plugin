"""Main plugin."""

from mkdocs.plugins import BasePlugin
from include_configuration_stubs.config import ConfigScheme, check_empty_input

class IncludeConfigurationsPlugin(BasePlugin[ConfigScheme]):
    def on_config(self, config):
        # Check that inputs are not empty
        for key in (
            "stubs_dir",
            "repo",
            "main_website_branch",
            "stubs_navigation_dir",
        ):
            check_empty_input(getattr(config, key), key)

    def on_files(self, files, config):
        """Hook to modify the files."""
        # Add the stubs for the released configurations to the site
        
        # For example, you can add or remove files from the list
        # files.append('new_file.md')
        # files.remove('old_file.md')
        pass

    def on_nav(self, nav, config, files):
        """Hook to modify the navigation."""
        pass
