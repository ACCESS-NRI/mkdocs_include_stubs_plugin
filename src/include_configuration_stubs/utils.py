"""
Module for utility functions.
"""

import os
import json
import re
import shutil
import subprocess
from markdown.extensions.toc import TocExtension
from markdown import Markdown
from collections import namedtuple
from functools import partial
from typing import Sequence, Optional
from itertools import count
from bs4 import BeautifulSoup

from mkdocs.structure.files import File, Files
from include_configuration_stubs.config import GitRefType

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


def get_config_stub(
    ref: str,
    repo: str,
    stub_dir: str,
    supported_file_formats: tuple[str, ...],
) -> Optional[ConfigStub]:
    """
    If the given git ref includes the specified stub_dir containing exactly one
    file in a supported format, return the ConfigStub namedtuple with the stub name, 
    content and title.

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
            If the path exists at the given ref and contains exactly one supported
            document file, a ConfigStub namedtuple is returned.
            None is returned otherwise.
    """
    url = f"https://api.github.com/repos/{repo}/contents/{stub_dir}?ref={ref}"
    command = ["curl", "-s", url]
    output = get_command_output(command)
    try:
        json_object = json.loads(output)
    except json.JSONDecodeError:
        return None
    # Get the filename of the stub
    if not isinstance(json_object, list): # Object is the error 404 one
        return None
    stubs = [
        jo['name']
        for jo in json_object
        for suffix in supported_file_formats
        if jo['name'].endswith(suffix)
    ]
    if len(stubs) != 1:
        return None
    file_name = stubs[0]
    # Get content of the stub
    raw_file_url = (
        f"https://raw.githubusercontent.com/{repo}/{ref}/{stub_dir}/{file_name}"
    )
    command = ["curl", "-s", raw_file_url]
    content = get_command_output(command)
    # Get the title of the file
    title = get_title(file_name, content)
    return ConfigStub(fname = file_name, content = content, title = title)

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
            repo = "/".join(remainder.split('/')[0:2]).removesuffix(".git")
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
        repo = get_remote_repo() if repo_config_input is None else repo_config_input
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
    return (main_branch_config_input == local_branch) and (
        repo == remote_owner_name
    )

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
        for i in count(1): # pragma: no branch
            new_src = append_number_to_file_name(src, i)
            if use_directory_urls:
                dest_dir, dest_name = os.path.split(dest)
                new_dir = append_number_to_file_name(dest_dir, i)
                new_dest = os.path.join(new_dir, dest_name)
            else:
                new_dest = append_number_to_file_name(dest, i)
            if new_src not in existing_src_paths and new_dest not in existing_dest_paths:
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
        return toc_tokens[0]['name']  # First h1-level heading
    return None

def get_title(path: str, content: str) -> Optional[str]:
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
    if path.endswith(".html"): # html
        return get_html_title(content)
    else: # markdown
        return get_md_title(content)