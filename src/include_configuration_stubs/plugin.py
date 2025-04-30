"""Main plugin."""

import os

from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File

from include_configuration_stubs.config import ConfigScheme
from include_configuration_stubs.utils import (
    get_config_stub,
    get_git_refs,
    get_repo_from_input,
    get_supported_file_formats,
    is_main_website,
)


class IncludeConfigurationsPlugin(BasePlugin[ConfigScheme]):
    def on_config(self, config):
        self.supported_file_formats = get_supported_file_formats(
            config.supported_file_formats
        )
        self.repo = get_repo_from_input(config.repo)
        self.is_main_website = is_main_website(config.main_website.branch, self.repo)

    def on_files(self, files, config):
        """Hook to modify the files."""
        # Add the configuration stubs to the site
        repo = self.repo
        is_main_website = self.is_main_website
        website = config.main_website if is_main_website else config.preview_website
        # Add stubs to the site
        refs = get_git_refs(
            repo,
            pattern=website.pattern,
            ref_type=website.ref_type,
        )
        # If is a preview website and 'no_main' is False, include also the main website stubs
        if not is_main_website and not config.preview_website.no_main:
            refs.extend(
                get_git_refs(
                    repo,
                    pattern=config.main_website.pattern,
                    ref_type=config.main_website.ref_type,
                )
            )
        # Remove duplicate refs
        refs = set(refs)
        # For each ref, add its configuration stubs to the site, if present
        for ref in refs:
            config_stub = get_config_stub(
                ref, repo, config.stubs_dir, self.supported_file_formats
            )
            if config_stub is not None:
                fname = next(iter(config_stub))
                config_stub_file = File(
                    path=fname,
                    src_dir=os.path.join(config["docs_dir"], config["stubs_dir"]),
                    dest_dir=os.path.join(
                        config["site_dir"], config["stubs_website_dir"]
                    ),
                    use_directory_urls=config["use_directory_urls"],
                    generated_by="mkdocs-include-configuration-stubs-plugin",
                )
                config_stub_file.content_string = config_stub[fname]
                files.append(config_stub_file)
        return files

    def on_nav(self, nav, config, files):
        """Hook to modify the navigation."""
        pass
