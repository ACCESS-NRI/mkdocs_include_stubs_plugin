"""
Module for utility functions.
"""

import os
from git import Repo, InvalidGitRepositoryError

def get_origin_url() -> str:
    """
    Get the URL of the origin remote for the current Git repository.

    Returns:
        str: The URL of the origin remote.
    """
    try:
        repo = Repo(search_parent_directories=True)
        return repo.remotes.origin.url
    except InvalidGitRepositoryError:
        cwd = os.getcwd()
        raise InvalidGitRepositoryError(f"'{cwd}' is not a Git repository.")