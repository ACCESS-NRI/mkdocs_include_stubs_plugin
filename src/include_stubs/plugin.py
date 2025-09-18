"""Main plugin."""

import os
from typing import Callable, Optional

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.livereload import LiveReloadServer
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File, Files
from mkdocs.structure.nav import Navigation
from mkdocs.structure.pages import Page

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
    RemoteStubs,
    add_pages_to_nav,
    get_dest_uri_for_local_stub,
    get_git_refs,
    get_repo_from_input,
    get_stub,
    is_main_website,
    keep_unique_refs,
    make_file_unique,
    set_stubs_nav_path,
)

logger = get_custom_logger(__name__)
        

class IncludeStubsPlugin(BasePlugin[ConfigScheme]):
    _cached_remote_stubs: Optional[list[Stub]] = None
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


    def add_stub_to_site(
        self,
        config: MkDocsConfig,
        stub: Stub,
        stubs_dir: str,
        stubs_parent_url: str,
        files: Files,
        is_remote_stub: bool,
    ) -> None:
        """
        Add a stub to the site.
        If `is_remote_stub` is True, it will fetch the stub from the remote repository,
        otherwise it will fetch it from the local directory.
        """
        fname = stub.fname
        if not is_remote_stub:
            use_directory_urls = config["use_directory_urls"]
            #  Add the stub file to the site files
            stub_file = File(
                path=fname,
                src_dir=os.path.abspath(stubs_dir),
                dest_dir=config["site_dir"],
                use_directory_urls=use_directory_urls,
                dest_uri=get_dest_uri_for_local_stub(
                    fname,
                    stubs_parent_url,
                    use_directory_urls,
                    SUPPORTED_FILE_FORMATS,
                ),
            )
            self.local_stub_abs_path = stub_file.abs_src_path
            make_file_unique(stub_file, files)
        #  Include the stub file to the site
        files.append(stub_file)
        # Add the file to the stub object
        stub.file = stub_file
        #  Create a page for the stub file
        stub_page = Page(
            config=config,
            title=stub.title or stub_file.src_uri.capitalize(),
            file=stub_file,
        )
        # Add the page to the stub object
        stub.page = stub_page
        if is_remote_stub:
            # Add remote stub to the cache
            if IncludeStubsPlugin._cached_remote_stubs is None:
                IncludeStubsPlugin._cached_remote_stubs = []
            IncludeStubsPlugin._cached_remote_stubs.append(stub)
            logger.info(
                f"Stub {stub.fname!r} added to remote cache."
            )
            msg_location = f"Git ref {ref!r}"
        else:
            msg_location = f"{stub_file.src_dir!r}"
        logger.info(
            f"Stub {stub.fname!r} found in {msg_location}. "
            f"Added related page {stub_page.title!r} at {stub_file.dest_path!r}."
        )

    def on_files(self, files: Files, config: MkDocsConfig) -> Files:
        """
        Dynamically add stubs to the MkDocs files list.
        """
        stubs_dir = self.config["stubs_dir"]
        logger.info(f"Looking for stubs in {stubs_dir!r}.")
        stubs_parent_url = self.config["stubs_parent_url"]
        # If a local stub is present, add it to the files so it's included in the site and
        # it is updated live when using `mkdocs serve ...`
        # Add the local stub only if a local mkdocs.yml was not found and the mkdocs.yml is
        # taken from the remote repo
        if os.environ.get(ENV_VARIABLE_NAME, None):
            self.add_stub_to_site(
                config=config,
                stubs_dir=stubs_dir,
                stubs_parent_url=stubs_parent_url,
                files=files,
                is_remote_stub=False,
            )
        # All other stubs are added from the GitHub remote repository:
        # If there are cached remote files, append them to the files directly
        if IncludeStubsPlugin._cached_remote_stubs is not None:
            logger.info("Cached remote stubs found. Adding them to the site.")
            for stub in IncludeStubsPlugin._cached_remote_stubs:
                files.append(stub.file)
        else:
            logger.info(
                "No cached remote stubs found. Fetching files from remote stubs."
            )
            # For each remote ref, add the remote stub to the site if present
            refs = self.get_git_refs_for_website()
            # Create the remote Stubs
            remotestubs = RemoteStubs(
                stubs=[Stub(gitref=ref) for ref in refs],
                config=config,
                repo=self.repo,
                stubs_dir=stubs_dir,
                stubs_parent_url=stubs_parent_url,
                supported_file_formats=SUPPORTED_FILE_FORMATS,
                files=files,
            )
            
            for stub in remotestubs:
                self.add_stub_to_site(
                    config=config,
                    stub=stub,
                    stubs_dir=remotestubs.stubs_dir,
                    stubs_parent_url=stubs_parent_url,
                    files=files,
                    is_remote_stub=True,
                )
        return files

    def on_nav(self, nav: Navigation, config: MkDocsConfig, files: Files) -> Navigation:
        """Hook to modify the navigation."""
        all_pages = [stub.page for stub in IncludeStubsPlugin._cached_remote_stubs]
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
        if hasattr(self, "local_stub_abs_path"):
            # Add the local stub file to the live-reload server
            server.watch(self.local_stub_abs_path, builder)  # type: ignore[arg-type]
        return server
