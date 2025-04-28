"""Main plugin."""

import os
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File
from include_configuration_stubs.config import ConfigScheme, check_empty_input
from include_configuration_stubs.utils import (
    get_repo,
    get_git_refs,
    get_config_stub,
    get_supported_file_formats,
)


class IncludeConfigurationsPlugin(BasePlugin[ConfigScheme]):
    def on_config(self, config):
        # Check that inputs are not empty
        for key in (
            "stubs_dir",
            "repo",
            "main_website_branch",
            "stubs_website_dir",
            "supported_file_formats",
        ):
            check_empty_input(getattr(config, key), key)
        # Set supported file formats
        self.supported_file_formats = get_supported_file_formats(config.supported_file_formats)
        self.repo = get_repo(config.repo)

    def on_files(self, files, config):
        """Hook to modify the files."""
        repo = self.repo
        refs = get_git_refs(
            repo,
            config.pattern,
            config.release_status,
        )
        for ref in refs:
            fname = get_config_stub(ref, repo, config.stubs_dir, self.supported_file_formats)
            if fname is not None:
                config_stub_file = File(
                    path=fname,
                    src_dir=os.path.join(config['docs_dir'], config['stubs_dir']),
                    dest_dir=os.path.join(config['site_dir'], config['stubs_website_dir']),
                    use_directory_urls=config['use_directory_urls'],
                    generated_by="mkdocs-include-configuration-stubs-plugin",
                )
                config_stub_file.content_string = f"Configuration stub for {ref}"
                files.append(config_stub_file)
        return files


        # Add the stubs for the configurations to the site

        # For example, you can add or remove files from the list
        # files.append('new_file.md')
        # files.remove('old_file.md')
        pass

    def on_nav(self, nav, config, files):
        """Hook to modify the navigation."""
        pass
