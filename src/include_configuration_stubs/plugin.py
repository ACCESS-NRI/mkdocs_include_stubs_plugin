"""Main plugin."""

import os

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin
from mkdocs.structure.pages import Page
from mkdocs.structure.nav import Navigation
from mkdocs.structure.files import Files, File
from mkdocs.livereload import LiveReloadServer

from typing import Callable, Optional
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
    get_dest_uri_for_local_stub,
)
from include_configuration_stubs.logging import get_custom_logger
from include_configuration_stubs.cli import ENV_VARIABLE_NAME

logger = get_custom_logger(__name__)
SUPPORTED_FILE_FORMATS = (".md", ".html")


class IncludeConfigurationStubsPlugin(BasePlugin[ConfigScheme]):
    def on_config(self, config: MkDocsConfig) -> MkDocsConfig:
        self.repo = get_repo_from_input(self.config["repo"])
        logger.info(f"GitHub Repository set to '{self.repo}'.")
        return config

    def get_git_refs_for_wesbsite(self) -> set:
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
                f"Including '{website_type}' configuration stubs from Git {GitRefType(ref_type)!s} following the pattern '{pattern}'."
            )
            # Add stubs to the site
            refs = get_git_refs(
                repo,
                pattern=pattern,
                ref_type=ref_type,
            )
        else:
            logger.info(
                f"No Git reference included for '{website_type}'. Pattern was empty."
            )
            refs = []
        # If is a preview website and 'no_main' is False, include also the main website stubs
        if not is_build_for_main_website and not preview_website_config["no_main"]:
            pattern = main_website_config["pattern"]
            if pattern.strip():
                ref_type = main_website_config["ref_type"]
                logger.info(
                    f"Including 'main' configuration stubs from Git {GitRefType(ref_type)!s} following the pattern '{pattern}'."
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
                    "No Git reference included for 'main'. Pattern was empty."
                )
        # Remove duplicate refs
        all_refs = set(refs)
        logger.info(f"Found the following Git references (Git SHAs): {all_refs}.")
        return all_refs

    def add_stub_to_site(
        self,
        config: MkDocsConfig,
        stubs_dir: str,
        stubs_parent_url: str,
        files: Files,
        is_remote_stub: bool,
        ref: Optional[str] = None,
    ) -> None:
        """
        Add a configuration stub to the site.
        If `is_remote_stub` is True, it will fetch the stub from the remote repository,
        otherwise it will fetch it from the local directory.
        """
        # Get the remote configuration stub file from the repository ref
        config_stub = get_config_stub(
            stub_dir=stubs_dir,
            supported_file_formats=SUPPORTED_FILE_FORMATS,
            is_remote_stub=is_remote_stub,
            repo=self.repo,
            ref=ref,
        )
        if config_stub:
            fname = config_stub.fname
            if is_remote_stub:
                #  Create the configuration stub file
                config_stub_file = File.generated(
                    config=config,
                    src_uri=fname,
                    content=config_stub.content,
                )
                # Change the destination path by prepending the stubs_parent_url
                config_stub_file.dest_path = os.path.join(
                    stubs_parent_url, config_stub_file.dest_path
                )
            else:
                use_directory_urls = config["use_directory_urls"]
                #  Add the configuration stub file to the site files
                config_stub_file = File(
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
                self.local_stub_abs_path = config_stub_file.abs_src_path
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
            if is_remote_stub:
                msg_location = f"Git ref {ref!r}"
            else:
                msg_location = f"{config_stub_file.src_dir!r}"
            logger.info(
                f"Configuration stub {config_stub.fname!r} found in {msg_location}. "
                f"Added related page {config_stub_page.title!r} at {config_stub_file.dest_path!r}."
            )
        else:
            if is_remote_stub:
                msg_location = f"{stubs_dir!r} for Git ref {ref!r}. Skipping this reference."
            else:
                msg_location = f"the local {stubs_dir!r} directory. Skipping addition of local stub."
            logger.warning(
                f"No uniquely identifiable configuration stub found in {msg_location} "
                f"This may happen if the {stubs_dir!r} directory is missing, or if no stub files or multiple conflicting candidates "
                "are found within it."
            )

    def on_files(self, files: Files, config: MkDocsConfig) -> Files:
        """
        Dynamically add configuration stubs to the MkDocs files list.
        """
        self.pages: list[Page] = []
        # Get the git refs for the website
        refs = self.get_git_refs_for_wesbsite()
        stubs_dir = self.config["stubs_dir"]
        logger.info(f"Looking for configuration stubs in {stubs_dir!r}.")
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
        # All other stubs are added from the Git repository:
        # For each ref, add its configuration stubs to the site, if present
        for ref in refs:
            self.add_stub_to_site(
                config=config,
                stubs_dir=stubs_dir,
                stubs_parent_url=stubs_parent_url,
                files=files,
                is_remote_stub=True,
                ref=ref,
            )
        return files

    def on_nav(self, nav: Navigation, config: MkDocsConfig, files: Files) -> Navigation:
        """Hook to modify the navigation."""
        sorted_pages = sorted(
            self.pages,
            key=lambda page: page.title,
        )
        stubs_nav_path = set_stubs_nav_path(
            self.config["stubs_nav_path"], self.config["stubs_parent_url"]
        )
        nav_path_segments = [seg.strip() for seg in stubs_nav_path.split(">")]
        # Add stubs to the navigation
        add_pages_to_nav(nav, sorted_pages, nav_path_segments)
        nav_path = " > ".join(nav_path_segments)
        logger.info(
            f"Added configuration stubs pages in the site navigation under {nav_path!r}."
        )
        return nav

    def on_serve(
        self, server: LiveReloadServer, config: MkDocsConfig, builder: Callable
    ) -> LiveReloadServer:
        if hasattr(self, "local_stub_abs_path"):
            # Add the local configuration stub file to the live-reload server
            server.watch(self.local_stub_abs_path, builder) # type: ignore[arg-type]
        return server
