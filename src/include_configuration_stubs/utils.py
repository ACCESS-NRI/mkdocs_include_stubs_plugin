"""
Module for utility functions.
"""

import os
import re
import shutil
import subprocess
import requests
from markdown.extensions.toc import TocExtension
from markdown import Markdown
from collections import namedtuple
from functools import partial
from typing import Sequence, Optional
from itertools import count
from bs4 import BeautifulSoup

from mkdocs.structure.files import File, Files
from mkdocs.structure.pages import Page
from mkdocs.structure.nav import Section, Navigation
from include_configuration_stubs.config import GitRefType, set_default_stubs_nav_path

GITHUB_URL = "https://github.com/"
GITHUB_SSH = "git@github.com:"

ConfigStub = namedtuple("ConfigStub", ["fname", "title", "content"])

run_command = partial(subprocess.run, capture_output=True, text=True, check=True)


def get_command_output(command: Sequence[str]) -> str:
    """
    Run a command and return its output.

    Args:
        command: Sequence of Str
            The command to run.

    Returns:
        Str
            The output of the command.
    """
    result = run_command(command)
    return result.stdout.strip()


def check_is_installed(executable: str) -> None:
    """
    Check if a required executable is installed on the system.
    Raises an EnvironmentError if the executable is not found.

    Args:
        executable: Str
            The executable to check.

    Returns:
        None
            Raises an EnvironmentError if the executable is not found.
    """
    # Check if Git is installed
    if not shutil.which(executable):
        raise EnvironmentError(
            f"'{executable}' is required but not found. Please install it and try again."
        )


def get_git_refs(repo: str, pattern: str, ref_type: GitRefType) -> list[str]:
    """
    Retrieve Git references of the specified type from the given repository,
    filtering them according to the provided pattern.

    Args:
        repo: Str
            The GitHub repository formatted as OWNER/REPO.
        pattern: Str
            The pattern to match the refs.
        ref_type: GitRefType
            The Git ref type.

    Returns:
        List of Str
            The list of refs (git sha) that match the pattern for the specified repo.
    """
    repo_url = f"https://github.com/{repo}"
    # Set which git refs to select based on the release status
    if ref_type == GitRefType.BRANCH:
        refs_flag = "--heads"
    elif ref_type == GitRefType.TAG:
        refs_flag = "--tags"
    else:
        refs_flag = "--heads --tags"
    # Print all tags in the repository
    command = ["git", "ls-remote", refs_flag, repo_url, pattern]
    output = get_command_output(command)
    # Get first column of the output (git sha)
    refs = output.split()[::2]
    return refs


def get_config_stub_fname(
    ref: str, repo: str, stub_dir: str, supported_file_formats: tuple[str, ...]
) -> Optional[str]:
    """
    Get the name of the configuration stub file from the GitHub repository.
    If the given git ref includes the specified stub_dir containing exactly one
    file in a supported format, return the stub name.

    Args:
        ref: Str
            The git SHA.
        repo: Str
            The GitHub Repository in the format OWNER/REPO.
        stub_dir: Str
            Path to the directory expected to contain the config stub in a supported format.
        supported_file_formats: Tuple of Str
            Tuple of supported file formats.

    Returns:
        Str
            The configuration stub filename.
    """
    api_url = f"https://api.github.com/repos/{repo}/contents/{stub_dir}"
    params = {"ref": ref}
    try:
        resp = requests.get(api_url, params=params)
        resp.raise_for_status()
        entries = resp.json()
    except requests.RequestException:
        return None
    stubs = [
        e["name"]
        for e in entries
        for suffix in supported_file_formats
        if e["name"].endswith(suffix)
    ]
    if len(stubs) != 1:
        return None
    return stubs[0]


def get_config_stub_content(
    ref: str, repo: str, stub_dir: str, fname: str
) -> Optional[str]:
    """
    Get the content of the configuration stub from the GitHub repository.

    Args:
        ref: Str
            The git SHA.
        repo: Str
            The GitHub Repository in the format OWNER/REPO.
        stub_dir: Str
            Path to the directory expected to contain the config stub in a supported format.
        fname: Str
            The name of the configuration stub file.

    Returns:
        Str
            The configuration stub content.
    """
    raw_url = f"https://raw.githubusercontent.com/{repo}/{ref}/{stub_dir}/{fname}"
    try:
        raw_resp = requests.get(raw_url)
        raw_resp.raise_for_status()
        return raw_resp.text
    except requests.RequestException:
        return None


def get_config_stub_title(path: str, content: str) -> Optional[str]:
    """
    Get the title of a HTML or MarkDown file from its path and content.

    Args:
        path: Str
            The path to the file.
        content: Str
            The content of the file.

    Returns:
        Str
            The title of the file.
            Returns None if no title is found.
    """
    if path.endswith(".html"):  # html
        return get_html_title(content)
    else:  # markdown
        return get_md_title(content)


def get_config_stub(
    ref: str,
    repo: str,
    stub_dir: str,
    supported_file_formats: tuple[str, ...],
) -> Optional[ConfigStub]:
    """
    Get the config stub name, content and title formatted as a ConfigStub namedtuple.

    Args:
        ref: Str
            The git SHA.
        repo: Str
            The GitHub Repository in the format OWNER/REPO.
        stub_dir: Str
            Path to the directory expected to contain a single file in a supported format.
        supported_file_formats: Tuple of Str
            Tuple of supported file formats.

    Returns:
        ConfigStub
            The ConfigStub namedtuple containing the config stub name, content and title.
    """
    # Get stub filename
    stub_name = get_config_stub_fname(ref, repo, stub_dir, supported_file_formats)
    if stub_name is None:
        return None
    # Get stub content
    stub_content = get_config_stub_content(ref, repo, stub_dir, stub_name)
    if stub_content is None:
        return None
    # # Get stub title
    title = get_config_stub_title(stub_name, stub_content)
    return ConfigStub(fname=stub_name, content=stub_content, title=title)


def get_remote_repo() -> str:
    """
    Get the remote repository url from the current directory.

    Returns:
        Str
            The remote repository GitHub URL or SSH.
    """
    command = ["git", "remote", "get-url", "origin"]
    return get_command_output(command)


def get_repo_from_url(repo_url: str) -> str:
    """
    Get the GitHub repo in the format OWNER/REPO from the GitHub URL or SSH.

    Returns:
        Str
            The remote repository URL.
    """
    for prefix in (GITHUB_URL, GITHUB_SSH):
        if repo_url.startswith(prefix):
            remainder = repo_url.removeprefix(prefix)
            repo = "/".join(remainder.split("/")[0:2]).removesuffix(".git")
            return repo
    raise ValueError(f"Invalid GitHub repo URL: '{repo_url}'")


def get_repo_from_input(repo_config_input: Optional[str]) -> str:
    """
    Return the GitHub repository in the format 'OWNER/REPO'.

    If repo_config_input is None, attempts to infer the repository from the local Git
    remote via `git remote get-url origin`. Accepts either a full GitHub URL, an SSH URL,
    or a direct 'OWNER/REPO' input.

    Args:
        repo_config_input: Str
            The input repository string, or None to auto-detect.

    Returns:
        Str
            A string in the format 'OWNER/REPO'.
    """
    try:
        repo = get_remote_repo() if not repo_config_input else repo_config_input
    except subprocess.CalledProcessError as e:
        raise ValueError(
            f"Failed to get the GitHub repository from local directory: {e.stderr.strip()}"
        ) from e
    if repo.startswith(GITHUB_URL) or repo.startswith(GITHUB_SSH):
        repo = get_repo_from_url(repo)
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", repo):
        raise ValueError(f"Invalid GitHub repo: '{repo}'")
    return repo


def is_main_website(main_branch_config_input: str, repo: str) -> bool:
    """
    Determine whether the build is intended for the main website.

    Args:
        main_branch_config_input: Str
            The branch for the main site configuration.
        repo: Str
            The GitHub repository in the format OWNER/REPO.

    Returns:
        bool: True if both the branch and repository match the main site configuration;
            False otherwise.
    """
    try:
        remote_repo = get_remote_repo()
        command = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
        local_branch = get_command_output(command)
    except subprocess.CalledProcessError:
        return False
    remote_owner_name = get_repo_from_url(remote_repo)
    return (main_branch_config_input == local_branch) and (repo == remote_owner_name)


def append_number_to_file_name(
    filename: str,
    number: int,
) -> str:
    """
    Append a number to the file name, taking into account any extensions.

    Args:
        filename: Str
            The file name to modify.
        number: Int
            The number to append.

    Returns:
        Str
            The modified file name with a number appended.
    """
    name, ext = os.path.splitext(filename)
    return f"{name}{number}{ext}"


def make_file_unique(file: File, files: Files) -> None:
    """
    Make a MkDocs File unique by appending a number to its `src_path` if the file already exists
    in the Files list.
    Changes the object in place.

    Args:
        file_name: mkdocs.structure.files.File
            The original MkDocs file.
        files: mkdocs.structure.files.File
            The list of existing MkDocs files.
    """
    existing_src_paths = {f.src_path for f in files}
    existing_dest_paths = {f.dest_path for f in files}
    use_directory_urls = file.use_directory_urls
    src = file.src_path
    dest = file.dest_path

    if src in existing_src_paths or dest in existing_dest_paths:
        for i in count(1):  # pragma: no branch
            new_src = append_number_to_file_name(src, i)
            if use_directory_urls:
                dest_dir, dest_name = os.path.split(dest)
                new_dir = append_number_to_file_name(dest_dir, i)
                new_dest = os.path.join(new_dir, dest_name)
            else:
                new_dest = append_number_to_file_name(dest, i)
            if (
                new_src not in existing_src_paths
                and new_dest not in existing_dest_paths
            ):
                file.src_path = new_src
                file.dest_path = new_dest
                # Log warning if the file name was changed
                break


def get_html_title(content: str) -> Optional[str]:
    """
    Get the title of a HTML file from its content.
    Args:
        content: Str
            The content of the HTML file.
    Returns:
        Str
            The title of the HTML file.
            Returns None if no title is found.
    """
    soup = BeautifulSoup(content, "html.parser")
    h1 = soup.find("h1")
    return h1.get_text() if h1 else None


def get_md_title(content: str) -> Optional[str]:
    """
    Get the title of a MarkDown file from its content.
    Args:
        content: Str
            The content of the MarkDown file.
    Returns:
        Str or None
            The title of the MarkDown file.
            Returns None if no title is found.
    """
    md = Markdown(extensions=[TocExtension(toc_depth="1")])
    md.convert(content)
    toc_tokens = md.toc_tokens

    if toc_tokens:
        return toc_tokens[0]["name"]  # First h1-level heading
    return None


def set_stubs_nav_path(
    stubs_nav_path: Optional[str],
    stubs_parent_url: str,
) -> str:
    """
    Set the path to the stubs in the MkDocs navigation.

    Args:
        stubs_nav_path: Str
            The path to the stubs in the MkDocs navigation.
        stubs_parent_url: Str
            The parent URL for the stubs.

    Returns:
        Str
            The path to the stubs in the MkDocs navigation.
    """
    if stubs_nav_path is None:
        return set_default_stubs_nav_path(stubs_parent_url)
    else:
        return stubs_nav_path.removesuffix("/")


def add_section_hierarchy(items: list, titles: list[str], pages: list[Page]) -> None:
    """
    Add a nested hierarchy path to the items of a navigation.
    The pages are added to the deepest section.

    Example:
      titles = ["title1","title2","title3"]
      items = [Page("page1"), Page("page2")]
      => [
            Page("page1"),
            Page("page2"),
            Section("title1", children=[
              Section("title2", children=[
                Section("title3", children=pages)
              ])
            ]),
         ]

    Args:
        titles: Str
            The titles for each of the section hierarchy.
        pages: List of mkdocs.structure.pages.Page
            The pages to add to the deepest section.
    """
    # Create the root section
    current_items = items
    if len(titles) > 0:
        # For each subsequent title, nest deeper
        for title in titles:
            child = Section(title, [])
            current_items.append(child)
            current_items = child.children
    # Add the pages to the deepest section
    current_items.extend(pages)


def add_pages_to_nav(
    nav: Navigation,
    pages: list[Page],
    stubs_nav_path: str,
) -> None:
    """
    Add the configuration stubs to the MkDocs navigation.

    Args:
        nav: mkdocs.structure.nav.Navigation
            The MkDocs navigation.
        pages: List of mkdocs.structure.pages.Page
            The pages to add to the deepest navigation Section.
        stubs_nav_path: Str
            The hierarchical structure of the navigation Section where to place the stubs pages.
    """
    section_titles = stubs_nav_path.split("/")
    current_items = nav.items
    while True:
        # Try to find an existing Section with this title
        section = next(
            (
                item
                for item in current_items
                if isinstance(item, Section) and item.title == section_titles[0]
            ),
            None,
        )
        if section is None:
            # Not found → create it and append to current_items
            add_section_hierarchy(current_items, section_titles, pages)
            break
        # Descend into this section’s children for next iteration
        current_items = section.children
        section_titles.pop(0)
