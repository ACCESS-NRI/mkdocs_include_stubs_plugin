"""Main plugin."""

import os
from typing import Callable

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.livereload import LiveReloadServer
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import Files
from mkdocs.structure.nav import Navigation

from include_stubs.cli import ENV_VARIABLE_NAME
from include_stubs.config import (
    SUPPORTED_FILE_FORMATS,
    ConfigScheme,
    GitRefType,
)
from include_stubs.logging import get_custom_logger
from include_stubs.utils import (
    Stub,
    GitRef,
    StubList,
    add_pages_to_nav,
    get_git_refs,
    get_repo_from_input,
    is_main_website,
    keep_unique_refs,
    set_stubs_nav_path,
)

logger = get_custom_logger(__name__)
        

class IncludeStubsPlugin(BasePlugin[ConfigScheme]):
    _cached_stubs: StubList = None # type: ignore[assignment]
    repo: str = None # type: ignore[assignment]

    def on_config(self, config: MkDocsConfig) -> MkDocsConfig:
        # Get the repository only the first time the plugin runs
        if IncludeStubsPlugin.repo is None:
            IncludeStubsPlugin.repo = get_repo_from_input(self.config["repo"])
            logger.info(f"GitHub Repository set to '{self.repo}'.")
        self.stubs_nav_path = set_stubs_nav_path(
            self.config["stubs_nav_path"], self.config["stubs_parent_url"]
        )
        return config


    def get_git_refs_for_website(self) -> list[GitRef]:
        repo = self.repo
        is_build_for_main_website = is_main_website(
            self.config["main_website"]["branch"], repo
        )
        website_type = "main" if is_build_for_main_website else "preview"
        logger.info(f"Building for '{website_type}' website.")
        preview_website_config = self.config["preview_website"]
        main_website_config = self.config["main_website"]
        website_config = (
            main_website_config if is_build_for_main_website else preview_website_config
        )
        pattern = website_config["pattern"]
        if pattern.strip():
            ref_type = website_config["ref_type"]
            logger.info(
                f"Including '{website_type}' stubs from Git {GitRefType(ref_type)!s} following the pattern '{pattern}'."
            )
            # Add stubs to the site
            refs = get_git_refs(
                repo,
                pattern=pattern,
                ref_type=ref_type,
            )
        else:
            logger.info(
                f"No Git reference included for '{website_type}' website. Pattern was empty."
            )
            refs = []
        # If is a preview website and 'no_main' is False, include also the main website stubs
        if not is_build_for_main_website and not preview_website_config["no_main"]:
            pattern = main_website_config["pattern"]
            if pattern.strip():
                ref_type = main_website_config["ref_type"]
                logger.info(
                    f"Including 'main' stubs from Git {GitRefType(ref_type)!s} following the pattern '{pattern}'."
                )
                refs.extend(
                    get_git_refs(
                        repo,
                        pattern=main_website_config["pattern"],
                        ref_type=main_website_config["ref_type"],
                    )
                )
            else:
                logger.info(
                    "No Git reference included for 'main' website. Pattern was empty."
                )
        # Remove duplicate refs
        unique_refs = keep_unique_refs(refs)
        logger.info(f"Found the following Git references (Git SHAs): {unique_refs}.")
        return unique_refs


    def on_files(self, files: Files, config: MkDocsConfig) -> Files:
        """
        Dynamically add stubs to the MkDocs files list.
        """
        stubs_dir = self.config["stubs_dir"]
        logger.info(f"Looking for stubs in {stubs_dir!r}.")
        # Remote Stubs
        # Add stubs from the remote repository only if there are no cached stub files
        if IncludeStubsPlugin._cached_stubs is None:
            # Get all Git references to include in the site
            refs = self.get_git_refs_for_website()
            # Create the Stubs from the Git references
            stubs = [Stub(gitref=ref) for ref in refs]
            # Create the StubList
            IncludeStubsPlugin._cached_stubs = StubList(
                stubs=stubs,
                mkdocs_config=config,
                repo=self.repo,
                stubs_dir=stubs_dir,
                stubs_parent_url=self.config["stubs_parent_url"],
                supported_file_formats=SUPPORTED_FILE_FORMATS,
                files=files,
            )
            # Populate the stubs (fetch the data from GitHub)
            IncludeStubsPlugin._cached_stubs.populate_remote_stubs()
        # Local Stub
        # If a local stub is present, add it to the files so it's included in the site
        # Add the local stub only if a local mkdocs.yml was not found and the mkdocs.yml is
        # taken from the remote repo (i.e., when the ENV variable from the is set in cli.py)
        if os.environ.get(ENV_VARIABLE_NAME, None):
            IncludeStubsPlugin._cached_stubs.append_or_replace(Stub(is_remote=False))
            # Populate the local stub (fetch the data)
            IncludeStubsPlugin._cached_stubs.populate_local_stub()
        # Add files to the site
        for stub in IncludeStubsPlugin._cached_stubs:
            files.append(stub.file)
            logger.info(
                f"Added stub file {stub.file.src_uri!r} with title {stub.page.title!r} to the site."
            )
        return files

    def on_nav(self, nav: Navigation, config: MkDocsConfig, files: Files) -> Navigation:
        """Hook to modify the navigation."""
        all_pages = [stub.page for stub in IncludeStubsPlugin._cached_stubs]
        sorted_pages = sorted(
            all_pages,
            key=lambda page: page.title,
        )
        nav_path_segments = [seg.strip() for seg in self.stubs_nav_path.split(">")]
        # Add stubs to the navigation
        add_pages_to_nav(nav, sorted_pages, nav_path_segments)
        nav_path = " > ".join(nav_path_segments)
        logger.info(f"Added stubs pages in the site navigation under {nav_path!r}.")
        return nav

    def on_serve(
        self, server: LiveReloadServer, config: MkDocsConfig, builder: Callable
    ) -> LiveReloadServer:
        if local_stub := IncludeStubsPlugin._cached_stubs.local_stub:
            # Add the local stub file to the live-reload server so it is updated when using `mkdocs serve ...`
            server.watch(local_stub.file.abs_src_path, builder) # type: ignore[arg-type, union-attr]
        return server
