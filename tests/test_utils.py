"""Tests for `mkdocs_include_configurations` package."""

# fp is a fixture provided by pytest-subprocess.

from unittest.mock import patch

import pytest

from include_configurations.utils import (
    ReleaseStatus,
    get_command_output,
    check_is_installed,
    get_git_refs,
    has_config_doc,
    get_repo,
)


@pytest.fixture
def mock_git_refs():
    pass

def test_get_command_output(fp):
    """Test the get_command_output function."""
    command = ["echo", "Hello, World!"]
    fp.register(command, stdout="Hello, World!")
    result = get_command_output(command)
    assert result == "Hello, World!"
    assert command in fp.calls

def test_check_is_installed_found():
    """Test the check_is_installed function when it passes."""
    exe = "random_example_executable"
    with patch("include_configurations.utils.shutil.which", return_value=True):
        check_is_installed(exe)


def test_check_is_installed_not_found():
    """Test the check_is_installed function when the executable is not found."""
    exe = "random_example_executable"
    with patch("shutil.which", return_value=False):
        with pytest.raises(EnvironmentError) as excinfo:
            check_is_installed(exe)
            assert (
                str(excinfo.value)
                == f"'{exe}' is required but not found. Please install it and try again."
            )


@pytest.mark.parametrize(
    "status, output_git_refs, expected_output",
    [
        (
            ReleaseStatus.DEVELOPMENT,
            "sha1\trefs/heads/main\nsha2\trefs/heads/dev\nsha3\trefs/heads/branch1",
            [
                "sha1",
                "sha2",
                "sha3",
            ],
        ), # development
        (
            ReleaseStatus.RELEASE,
            "sha4\trefs/tags/v1\nsha5\trefs/tags/v2\nsha6\trefs/tags/v3",
            [
                "sha4",
                "sha5",
                "sha6",
            ],
        ), # release
    ],
    ids=["development", "release"],
)
def test_get_git_refs(fp, status, output_git_refs, expected_output):
    """Test the get_git_refs function."""
    refs_flag = "--heads" if status == ReleaseStatus.DEVELOPMENT else "--tags"
    repo_url = "https://example.com/repo.git"
    pattern = "random-pattern"
    fp.register(
        ["git", "ls-remote", refs_flag, repo_url, pattern], stdout=output_git_refs
    )
    result = get_git_refs(repo_url, pattern, status)
    assert result == expected_output
    assert ["git", "ls-remote", refs_flag, repo_url, pattern] in fp.calls


@pytest.mark.parametrize(
    "output_json, expected_result",
    [
        ("", False),
        (
            r"""{
            "message": "Not Found",
            "documentation_url": "https://docs.github.com/rest/repos/contents#get-repository-content",
            "status": "404"
            }""",
            False,
        ),
        (
            r"""[{
            "name": "name_without_extensionmd"
            }]""",
            False,
        ),
        (
            r"""[
            {
            "name": "name_without_extensionmd"
            },
            {
            "name": "name_with_extension.md"
            }
            ]""",
            False,
        ),
        (
            r"""[{
            "name": "name_wit_extension.md"
            }]""",
            True,
        ),
        (
            r"""[{
            "name": "name_wit_extension.html"
            }]""",
            True,
        ),
    ],
    ids=[
        "empty",
        "not_found",
        "no_extension",
        "multiple_files",
        "single_file_md",
        "single_file_html",
    ],
)
def test_has_config_doc(fp, output_json, expected_result):
    """Test the has_config_doc function."""
    ref = "sha1234567"
    repo = "owner/repo"
    path = "config/path"
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    command = ["curl", "-s", url]
    fp.register(command, stdout=output_json)
    assert has_config_doc(ref, repo, path) is expected_result


@pytest.mark.parametrize(
    "config_input, expected_output, raises_error",
    [
        ("", None, True),  # input_empty
        (
            "https://github.com/OWNER/REPO/contents",
            "OWNER/REPO",
            False,
        ),  # valid_github_url
        (
            "git@github.com:example/name.git/other_part:example",
            "example/name",
            False,
        ),  # valid_github_ssh_url
        (
            "owner-example/repo_name",
            "owner-example/repo_name",
            False,
        ),  # valid_github_repo
        (
            "http://www.example.com/owner/repo",
            None,
            True,
        ),  # invalid_url
        (
            "invalid_repo_name",
            None,
            True,
        ),  # "invalid_repo"
        (
            "invalid/repo/name",
            None,
            True,
        ),  # "invalid_repo2"
    ],
    ids=[
        "empty",
        "valid_github_url",
        "valid_github_ssh_url",
        "valid_github_repo",
        "invalid_url",
        "invalid_repo",
        "invalid_repo2",
    ],
)
def test_get_repo(fp, config_input, expected_output, raises_error):
    """Test the get_repo function."""
    if not raises_error:
        output = get_repo(config_input)
        assert output == expected_output
    else:
        with pytest.raises(ValueError) as excinfo:
            get_repo(config_input)
            assert (
                str(excinfo.value).startswith(f"Invalid GitHub repo: '{config_input}'")
            )


@pytest.mark.parametrize(
    "command_stdout, expected_output, exit_code, raises_error",
    [
        (None, None, 1, True),  # error
        (
            "https://github.com/OWNER/REPO/example.md",
            "OWNER/REPO",
            0, 
            False,
        ),  # valid_github_url
        (
            "git@github.com:example/name.git/other_part:example", 
            "example/name",
            0, 
            False,
        ),  # valid_github_ssh_url
        (
            "https://gitlab.com/gitlab-org/gitlab",
            None,
            None,
            True,
        ) # not_github_url
    ],
    ids=[
        "error",
        "valid_github_url",
        "valid_github_ssh_url",
        "not_github_url",
    ],
)
def test_get_repo_input_none(fp, command_stdout, expected_output, exit_code, raises_error):
    """Test the get_repo function when input is None."""
    config_input = None
    command = ["git", "remote", "get-url", "origin"]
    fp.register(command, stdout=command_stdout, returncode=exit_code)
    if raises_error:
        with pytest.raises(ValueError):
            get_repo(config_input)
    else:
        output = get_repo(config_input)
        assert output == expected_output
        assert command in fp.calls
