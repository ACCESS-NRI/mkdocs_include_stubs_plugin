"""Main plugin."""

import os
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File
from include_configuration_stubs.config import ConfigScheme
from include_configuration_stubs.utils import (
    get_repo_from_input,
    get_git_refs,
    get_config_stub,
    get_supported_file_formats,
    is_main_website,
)


class IncludeConfigurationsPlugin(BasePlugin[ConfigScheme]):
    def on_config(self, config):
        self.supported_file_formats = get_supported_file_formats(config.supported_file_formats)
        self.repo = get_repo_from_input(config.repo)
        self.is_main_website = is_main_website(config.main_website.branch, self.repo)
        self.pattern = config.pattern_preview_website

    def on_files(self, files, config):
        """Hook to modify the files."""
        # Add the configuration stubs to the site
        repo = self.repo
        refs = get_git_refs(
            repo,
            pattern = self.pattern,
            status = self.status,
        )
        for ref in refs:
            config_stub = get_config_stub(ref, repo, config.stubs_dir, self.supported_file_formats)
            if config_stub is not None:
                fname = next(iter(config_stub))
                config_stub_file = File(
                    path=fname,
                    src_dir=os.path.join(config['docs_dir'], config['stubs_dir']),
                    dest_dir=os.path.join(config['site_dir'], config['stubs_website_dir']),
                    use_directory_urls=config['use_directory_urls'],
                    generated_by="mkdocs-include-configuration-stubs-plugin",
                )
                config_stub_file.content_string = config_stub[fname]
                files.append(config_stub_file)
        return files


        

        # For example, you can add or remove files from the list
        # files.append('new_file.md')
        # files.remove('old_file.md')
        pass

    def on_nav(self, nav, config, files):
        """Hook to modify the navigation."""
        pass
