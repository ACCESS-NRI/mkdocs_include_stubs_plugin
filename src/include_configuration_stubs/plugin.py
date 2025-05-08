"""Main plugin."""

import os

from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File, Files
from mkdocs.config.defaults import MkDocsConfig
from include_configuration_stubs import PLUGIN_NAME

from include_configuration_stubs.config import (
    ConfigScheme,
    get_supported_file_formats,
    set_default_stubs_nav_path,
)
from include_configuration_stubs.utils import (
    get_config_stub,
    get_git_refs,
    get_repo_from_input,
    is_main_website,
    make_file_unique,
)


class IncludeConfigurationStubsPlugin(BasePlugin[ConfigScheme]):
    def on_config(self, config: MkDocsConfig) -> MkDocsConfig:
        self.repo = get_repo_from_input(self.config["repo"])
        return config

    def get_git_refs_for_wesbsite(self) -> set:
        is_build_for_main_website = is_main_website(
            self.config["main_website"]["branch"], self.repo
        )
        print(f"{PLUGIN_NAME}: building for {'main' if is_build_for_main_website else 'preview'} website.")
        preview_website_config = self.config["preview_website"]
        main_website_config = self.config["main_website"]
        website_config = main_website_config if is_build_for_main_website else preview_website_config
        # Add stubs to the site
        refs = get_git_refs(
            self.repo,
            pattern=website_config["pattern"],
            ref_type=website_config["ref_type"],
        )
        # If is a preview website and 'no_main' is False, include also the main website stubs
        if not is_build_for_main_website and not preview_website_config["no_main"]:
            refs.extend(
                get_git_refs(
                    self.repo,
                    pattern=main_website_config["pattern"],
                    ref_type=main_website_config["ref_type"],
                )
            )
        # Remove duplicate refs
        return set(refs)

    def on_files(self, files: Files, config: MkDocsConfig) -> Files:
        """
        Dynamically add congiguration stubs to the MkDocs files list.
        """
        # Get the git refs for the website
        refs = self.get_git_refs_for_wesbsite()
        
        stubs_dir = self.config["stubs_dir"]
        stubs_parent_url = self.config["stubs_parent_url"]
        # Get the supported file formats
        supported_file_formats = get_supported_file_formats(
            self.config["supported_file_formats"]
        )
        # For each ref, add its configuration stubs to the site, if present
        for ref in refs:
            config_stub = get_config_stub(
                ref,
                self.repo,
                stubs_dir,
                supported_file_formats,
            )
            if config_stub is not None:
                #  Create the configuration stub file
                config_stub_file = File.generated(
                    config=config,
                    src_uri=config_stub.fname,
                    content=config_stub.content,
                )
                # Change the destination path by prepending the stubs_parent_url
                config_stub_file.dest_path = os.path.join(
                    stubs_parent_url, config_stub_file.dest_path
                )
                #  Make the file unique
                make_file_unique(config_stub_file, files)
                #  Include the configuration stub file to the site
                files.append(config_stub_file)
        return files

    def on_nav(self, nav, config, files):
        """Hook to modify the navigation."""
        stubs_nav_path = self.config["stubs_nav_path"]
        if stubs_nav_path is None:
            stubs_nav_path = set_default_stubs_nav_path(self.config["stubs_parent_url"])
        # breakpoint()
        pass
