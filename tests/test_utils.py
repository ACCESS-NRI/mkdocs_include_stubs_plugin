"""Tests for `mkdocs_include_configurations` package."""

import pytest
from include_configurations.utils import get_origin_url
from unittest.mock import patch, MagicMock
from git import InvalidGitRepositoryError

def test_get_origin_url():
    """Test the `get_origin_url` function."""
    # Mock the Repo class
    expected = "https://example/repo/url/.git"
    mock_repo = MagicMock()
    mock_repo.remotes.origin.url = expected
    with patch("include_configurations.utils.Repo", return_value=mock_repo):
        # Mock the Repo instance
        result = get_origin_url()
    assert result == expected

@patch("include_configurations.utils.os.getcwd", return_value="/")
def test_get_origin_url_invalid_repo(mock_getcwd):
    """Test the `get_origin_url` function when the current directory is an invalid repo."""
    with pytest.raises(InvalidGitRepositoryError):
        get_origin_url()

