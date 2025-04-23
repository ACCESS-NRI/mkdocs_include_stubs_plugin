"""
Module for utility functions.
"""

import json
import shutil
import subprocess
from enum import StrEnum, auto
from typing import Union, Sequence
from functools import partial

class ReleaseStatus(StrEnum):
    """
    Enum for release status.
    """

    DEVELOPMENT = auto()
    RELEASE = auto()


class SupportedFileFormats(StrEnum):
    """
    Enum for the supported file formats.
    """

    MARKDOWN = ".md"
    HTML = ".html"

run_command = partial(
    subprocess.run, 
    capture_output=True, 
    text=True, 
    check=True
)

def check_is_installed(executable) -> None:
    """
    Check if a required executable is installed on the system.
    Raises an EnvironmentError if the executable is not found.
    """
    # Check if Git is installed
    if not shutil.which(executable):
        raise EnvironmentError(
            f"'{executable}' is required but not found. Please install it and try again."
        )


def get_git_refs(repo_url: str, pattern: str, status: ReleaseStatus) -> list[str]:
    """
    Get refs from the repository, formatted according to the specified pattern
    and status.

    Args:
        repo_url: Str
            The URL of the repository.
        pattern: Str
            The pattern to match the refs.
        status: ReleaseStatus
            The release status (DEVELOPMENT or RELEASE).

    Returns:
        List of Str
            The list of refs (git sha) that match the pattern for the specified repo.
    """
    # Set which git refs to select based on the release status
    refs_flag = "--heads" if status == ReleaseStatus.DEVELOPMENT else "--tags"
    # Print all tags in the repository
    command = ["git", "ls-remote", refs_flag, repo_url, pattern]
    result = run_command(command)
    # Get first column of the output (git sha)
    refs = result.stdout.strip().split()[::2]
    return refs


def has_config_doc(
    ref: str,
    repo: str,
    config_doc_path: str,
) -> bool:
    """
    Check if the given git ref includes the specified config_doc_path,
    and that the path contains exactly one file in a supported format.

    Args:
        ref: Str
            The git SHA.
        repo: Str
            The GitHub Repository in the format OWNER/REPO.
        config_doc_path: Str
            Path to the directory expected to contain a single file in a supported format.

    Returns:
        Bool
            True if the path exists at the given ref and contains exactly one supported
            document file, False otherwise.
    """
    url = f"https://api.github.com/repos/{repo}/contents/{config_doc_path}?ref={ref}"
    result = run_command(["curl", "-s", url])
    try:
        json_object = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return False
    if len(json_object) != 1:
        return False
    file_name = json_object[0].get("name","")
    return file_name.endswith(tuple(fformat.value for fformat in SupportedFileFormats))

def get_repo(repo_config_input: Union[str, None]) -> str:
    """
    Get the repository in the format OWNER/REPO from the given repo_config_input.
    If the repo_config_input is None, get the repo from the output of the command
    `git remote get-url origin` for the current directory.

    Args:
        repo_config_input: Str or None
            The repository URL or GitHub repository in the format OWNER/REPO.

    Returns:
        Str
            The repository URL.
    """
    if repo_config_input is None:
        # Get the repository URL from the current directory
        command = ["git", "remote", "get-url", "origin"]
        result = run_command(command)
        repo_config_input = result.stdout.strip()
    # if repo.startswith("https://github.com/","git@github.com:"):
    return 'bubbi'
