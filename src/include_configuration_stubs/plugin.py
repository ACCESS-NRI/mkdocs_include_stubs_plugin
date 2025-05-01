"""Main plugin."""

import os

from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File

from include_configuration_stubs import PLUGIN_NAME
from include_configuration_stubs.config import ConfigScheme
from include_configuration_stubs.utils import (
    get_config_stub,
    get_git_refs,
    get_repo_from_input,
    is_main_website,
)


class IncludeConfigurationStubsPlugin(BasePlugin[ConfigScheme]):
    def on_config(self, config):
        self.repo = get_repo_from_input(self.config["repo"])
        self.is_main_website = is_main_website(
            self.config["main_website"]["branch"], self.repo
        )

    def on_files(self, files, config):
        """Hook to modify the files."""
        # Add the configuration stubs to the site
        repo = self.repo
        is_main_website = self.is_main_website
        main_website_config = self.config["main_website"]
        preview_website_config = self.config["preview_website"]
        website = main_website_config if is_main_website else preview_website_config
        # Add stubs to the site
        refs = get_git_refs(
            repo,
            pattern=website["pattern"],
            ref_type=website["ref_type"],
        )
        # If is a preview website and 'no_main' is False, include also the main website stubs
        if not is_main_website and not preview_website_config["no_main"]:
            refs.extend(
                get_git_refs(
                    repo,
                    pattern=main_website_config["pattern"],
                    ref_type=main_website_config["ref_type"],
                )
            )
        # Remove duplicate refs
        refs = set(refs)
        # For each ref, add its configuration stubs to the site, if present
        stubs_dir = self.config["stubs_dir"]
        stubs_site_dir = self.config["stubs_site_dir"]
        docs_dir = config["docs_dir"]
        site_dir = config["site_dir"]
        use_directory_urls = config["use_directory_urls"]
        for ref in refs:
            config_stub = get_config_stub(
                ref,
                repo,
                stubs_dir,
                self.config["supported_file_formats"],
            )
            if config_stub is not None:
                fname = next(iter(config_stub))
                config_stub_file = File(
                    path=fname,
                    src_dir=os.path.join(docs_dir, stubs_dir),
                    dest_dir=os.path.join(
                        site_dir,
                        stubs_site_dir,
                    ),
                    use_directory_urls=use_directory_urls,
                    generated_by=PLUGIN_NAME,
                )
                config_stub_file.content_string = config_stub[fname]
                files.append(config_stub_file)
        return files

    def on_nav(self, nav, config, files):
        """Hook to modify the navigation."""
        pass
