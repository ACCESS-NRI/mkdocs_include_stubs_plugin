"""
Module for utility functions.
"""

import json
import re
import shutil
import subprocess
from enum import StrEnum, auto
from functools import partial
from typing import Sequence

GITHUB_URL = "https://github.com/"
GITHUB_SSH = "git@github.com:"


class ReleaseStatus(StrEnum):
    """
    Enum for release status.
    """

    DEVELOPMENT = auto()
    RELEASE = auto()


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


def get_supported_file_formats(file_formats: str) -> tuple[str, ...]:
    """
    Get the supported file formats from the given string.

    Args:
        file_formats: Str
            The string containing the supported file formats.

    Returns:
        Tuple of Str
            A tuple of supported file formats.
    """
    return tuple(f".{fformat}" for fformat in file_formats.split(","))


def get_git_refs(repo: str, pattern: str, status: ReleaseStatus) -> list[str]:
    """
    Get refs from the repository, formatted according to the specified pattern
    and status.

    Args:
        repo: Str
            The GitHub repository formatted as OWNER/REPO.
        pattern: Str
            The pattern to match the refs.
        status: ReleaseStatus
            The release status (DEVELOPMENT or RELEASE).

    Returns:
        List of Str
            The list of refs (git sha) that match the pattern for the specified repo.
    """
    repo_url = f"https://github.com/{repo}"
    # Set which git refs to select based on the release status
    refs_flag = "--heads" if status == ReleaseStatus.DEVELOPMENT else "--tags"
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
    raw_file_url = f"https://raw.githubusercontent.com/{repo}/{ref}/{stub_dir}/{file_name}"
    command = ["curl", "-s", raw_file_url]
    content = get_command_output(command)
    return {file_name: content}


def get_repo(repo_config_input: str | None) -> str:
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
    try:
        if repo_config_input is None:
            command = ["git", "remote", "get-url", "origin"]
            repo = get_command_output(command)
        else:
            repo = repo_config_input

        # Extract the repository name from the URL
        if repo.startswith(GITHUB_URL):
            repo_owner_name = "/".join(repo.split("/")[3:5])
        elif repo.startswith(GITHUB_SSH):
            repo_owner_name = "/".join(repo.split(":")[1].split("/")[0:2]).removesuffix(
                ".git"
            )
        else:
            repo_owner_name = repo
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", repo_owner_name):
            raise ValueError
    except (IndexError, ValueError):
        raise ValueError(f"Invalid GitHub repo: '{repo}'")
    except subprocess.CalledProcessError as e:
        raise ValueError(
            f"Failed to get the GitHub repository from local directory: {e.stderr.strip()}"
        ) from e
    return repo_owner_name
