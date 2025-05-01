"""
Module for utility functions.
"""

import json
import re
import shutil
import subprocess
from functools import partial
from typing import Sequence

from include_configuration_stubs.config import GitRefType

GITHUB_URL = "https://github.com/"
GITHUB_SSH = "git@github.com:"


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
) -> dict[str, str] | None:
    """
    If the given git ref includes the specified stub_dir containing
    one file in a supported fortmat, return a dictionary with the name and content of the file.

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
        Dict | None
            If the path exists at the given ref and contains exactly one supported
            document file, a dictionary in the format {<file_name>: <file_content>} is returned.
            None is returned otherwise.
    """
    url = f"https://api.github.com/repos/{repo}/contents/{stub_dir}?ref={ref}"
    command = ["curl", "-s", url]
    output = get_command_output(command)
    try:
        json_object = json.loads(output)
    except json.JSONDecodeError:
        return None
    if len(json_object) != 1:
        return None
    file_name = json_object[0].get("name", "")
    if not file_name.endswith(supported_file_formats):
        return None
    raw_file_url = (
        f"https://raw.githubusercontent.com/{repo}/{ref}/{stub_dir}/{file_name}"
    )
    command = ["curl", "-s", raw_file_url]
    content = get_command_output(command)
    return {file_name: content}


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


def get_repo_from_input(repo_config_input: str | None) -> str:
    """
    Return the GitHub repository in the format 'OWNER/REPO'.

    If repo_config_input is None, attempts to infer the repository from the local Git
    remote via `git remote get-url origin`. Accepts either a full GitHub URL, an SSH URL,
    or a direct 'OWNER/REPO' input.

    Args:
        repo_config_input: Str or None
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
