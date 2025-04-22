"""
Module for utility functions related to Git operations.
"""

import os
from git import Repo, InvalidGitRepositoryError

def get_origin_url():
    """
    Get the URL of the origin remote for the current Git repository.

    Returns:
        str: The URL of the origin remote.
    """
    try:
        repo = Repo(search_parent_directories=True)
        return repo.remotes.origin.url
    except InvalidGitRepositoryError:
        current_dir = os.getcwd()
        raise InvalidGitRepositoryError("The current directory is not a Git repository.")