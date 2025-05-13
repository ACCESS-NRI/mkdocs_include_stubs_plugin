"""Main plugin."""

import os

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin
from mkdocs.structure.pages import Page
from mkdocs.structure.files import Files, File

from include_configuration_stubs.config import (
    ConfigScheme,
    GitRefType,
)
from include_configuration_stubs.utils import (
    add_pages_to_nav,
    get_config_stub,
    get_git_refs,
    get_repo_from_input,
    is_main_website,
    make_file_unique,
    set_stubs_nav_path,
)
from include_configuration_stubs.logging import get_custom_logger

LOGGER = get_custom_logger(__name__)
SUPPORTED_FILE_FORMATS = (".md", ".html")

class IncludeConfigurationStubsPlugin(BasePlugin[ConfigScheme]):
    def on_config(self, config: MkDocsConfig) -> MkDocsConfig:
        self.repo = get_repo_from_input(self.config["repo"])
        LOGGER.info(f"GitHub Repository set to '{self.repo}'.")
        return config

    def get_git_refs_for_wesbsite(self) -> set:
        repo = self.repo
        is_build_for_main_website = is_main_website(
            self.config["main_website"]["branch"], repo
        )
        website_type = "main" if is_build_for_main_website else "preview"
        LOGGER.info(f"Building for '{website_type}' website.")
        preview_website_config = self.config["preview_website"]
        main_website_config = self.config["main_website"]
        website_config = (
            main_website_config if is_build_for_main_website else preview_website_config
        )
        pattern = website_config["pattern"]
        ref_type = website_config["ref_type"]
        LOGGER.info(
            f"Including '{website_type}' configuration stubs from Git {GitRefType(ref_type)!s} following the pattern '{pattern}'."
        )
        # Add stubs to the site
        refs = get_git_refs(
            repo,
            pattern=pattern,
            ref_type=ref_type,
        )
        # If is a preview website and 'no_main' is False, include also the main website stubs
        if not is_build_for_main_website and not preview_website_config["no_main"]:
            pattern = main_website_config["pattern"]
            ref_type = main_website_config["ref_type"]
            LOGGER.info(
                f"Including 'main' configuration stubs from Git {GitRefType(ref_type)!s} following the pattern '{pattern}'."
            )
            refs.extend(
                get_git_refs(
                    repo,
                    pattern=main_website_config["pattern"],
                    ref_type=main_website_config["ref_type"],
                )
            )
        # Remove duplicate refs
        all_refs = set(refs)
        LOGGER.info(f"Found the following Git references (Git SHAs): {all_refs}.")
        return all_refs

    def on_files(self, files: Files, config: MkDocsConfig) -> Files:
        """
        Dynamically add configuration stubs to the MkDocs files list.
        """
        self.pages = []
        # Get the git refs for the website
        refs = self.get_git_refs_for_wesbsite()

        stubs_dir = self.config["stubs_dir"]
        LOGGER.info(f"Looking for configuration stubs in {stubs_dir!r}.")
        stubs_parent_url = self.config["stubs_parent_url"]
        # For each ref, add its configuration stubs to the site, if present
        for ref in refs:
            config_stub = get_config_stub(
                ref,
                self.repo,
                stubs_dir,
                SUPPORTED_FILE_FORMATS,
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
                #  Create a page for the configuration stub file
                config_stub_page = Page(
                    config=config,
                    title=config_stub.title or config_stub_file.src_uri.capitalize(),
                    file=config_stub_file,
                )
                self.pages.append(config_stub_page)
                LOGGER.info(
                    f"Configuration stub {config_stub.fname!r} found in Git ref {ref!r}. "
                    f"Added related page {config_stub_page.title!r} at {config_stub_file.dest_path!r}."
                )
            else:
                LOGGER.warning(
                    f"No uniquely identifiable configuration stub found in {stubs_dir!r} for Git ref {ref!r}. Skipping reference. "
                    "Possible reasons include a missing stub directory, no stub files present, or multiple candidate files preventing unambiguous selection."
                )
        return files

    def on_nav(self, nav, config, files):
        """Hook to modify the navigation."""
        sorted_pages = sorted(
            self.pages,
            key=lambda page: page.title,
        )
        stubs_nav_path = set_stubs_nav_path(
            self.config["stubs_nav_path"], self.config["stubs_parent_url"]
        )
        nav_path_segments = stubs_nav_path.split("/")
        # Add stubs to the navigation
        add_pages_to_nav(nav, sorted_pages, nav_path_segments)
        nav_path = " -> ".join(nav_path_segments)
        LOGGER.info(
            f"Added configuration stubs pages in the site navigation under {nav_path!r}."
        )
        return nav
