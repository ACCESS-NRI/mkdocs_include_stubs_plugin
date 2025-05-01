# fp is a fixture provided by pytest-subprocess.

from subprocess import CalledProcessError
from unittest.mock import patch

import pytest

from include_configuration_stubs.config import GitRefType
from include_configuration_stubs.utils import (
    check_is_installed,
    get_command_output,
    get_config_stub,
    get_git_refs,
    get_remote_repo,
    get_repo_from_input,
    get_repo_from_url,
    is_main_website,
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
    with patch("include_configuration_stubs.utils.shutil.which", return_value=True):
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
    "ref_type",
    [
        GitRefType.BRANCH,  # ref_type_branch
        GitRefType.TAG,  # ref_type_tag
        GitRefType.ALL,  # ref_type_all
    ],
    ids=["ref_type_branch", "ref_type_tag", "ref_type_all"],
)
def test_get_git_refs(fp, ref_type):
    """Test the get_git_refs function."""
    if ref_type == GitRefType.BRANCH:
        refs_flag = "--heads"
    elif ref_type == GitRefType.TAG:
        refs_flag = "--tags"
    elif ref_type == GitRefType.ALL:
        refs_flag = "--heads --tags"
    repo = "example/repo"
    repo_url = f"https://github.com/{repo}"
    pattern = "random-pattern"
    command_output = (
        "sha1\trefs/heads/main\nsha2\trefs/heads/dev\nsha3\trefs/heads/branch1"
    )
    expected_output = ["sha1", "sha2", "sha3"]
    fp.register(
        ["git", "ls-remote", refs_flag, repo_url, pattern],
        stdout=command_output,
    )
    result = get_git_refs(repo, pattern, ref_type)
    assert result == expected_output
    assert ["git", "ls-remote", refs_flag, repo_url, pattern] in fp.calls


@pytest.mark.parametrize(
    "output_json, expected_file_name",
    [
        ("", None),
        (
            r"""{
            "message": "Not Found",
            "documentation_url": "https://docs.github.com/rest/repos/contents#get-repository-content",
            "status": "404"
            }""",
            None,
        ),
        (
            r"""[{
            "name": "name_without_extensionmd"
            }]""",
            None,
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
            None,
        ),
        (
            r"""[{
            "name": "name_with_extension.md"
            }]""",
            "name_with_extension.md",
        ),
        (
            r"""[{
            "name": "name_with_extension.html"
            }]""",
            "name_with_extension.html",
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
def test_get_config_stub(fp, output_json, expected_file_name):
    """Test the get_config_stub function."""
    example_file_content = "Example file content" if expected_file_name else None
    ref = "sha1234567"
    repo = "owner/repo"
    path = "config/path"
    supported_file_formats = (".md", ".html")
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    raw_url = (
        f"https://raw.githubusercontent.com/{repo}/{ref}/{path}/{expected_file_name}"
    )
    command1 = ["curl", "-s", url]
    command2 = ["curl", "-s", raw_url]
    fp.register(command1, stdout=output_json)
    fp.register(command2, stdout=example_file_content)
    expected_output = (
        {expected_file_name: example_file_content} if expected_file_name else None
    )
    assert get_config_stub(ref, repo, path, supported_file_formats) == expected_output

def test_get_remote_repo(fp):
    """
    Test the get_remote_repo function.
    """
    mock_stdout = "mock_output"
    command = ["git", "remote", "get-url", "origin"]
    fp.register(command, stdout=mock_stdout)
    output = get_remote_repo()
    assert output == mock_stdout
    assert command in fp.calls


@pytest.mark.parametrize(
    "repo_url, expected_output, raises_error",
    [
        (
            "https://github.com/ACCESS-NRI/access-hive.org.au/other/parts",
            "ACCESS-NRI/access-hive.org.au",
            False,
        ),  # valid_github_url
        (
            "git@github.com:ACCESS-NRI/access-hive.org.au.git/other:parts/",
            "ACCESS-NRI/access-hive.org.au",
            False,
        ),  # valid_github_ssh
        ("invalid/repo", None, True),  # invalid
    ],
    ids=[
        "valid_github_url",
        "valid_github_ssh",
        "invalid",
    ],
)
def test_get_repo_from_url(repo_url, expected_output, raises_error):
    """
    Test the get_repo_from_url function.
    """
    if raises_error:
        with pytest.raises(ValueError) as excinfo:
            get_repo_from_url(repo_url)
            # assert str(excinfo.value) == "Invalid GitHub repo URL: '{repo_url}'"
    else:
        output = get_repo_from_url(repo_url)
        assert output == expected_output


@pytest.mark.parametrize(
    "config_input, get_repo_from_url_output",
    [
        (
            "https://github.com/OWNER/REPO/contents",
            "OWNER/REPO",
        ),  # valid_github_url
        (
            "git@github.com:example/name.git/other_part:example",
            "example/name",
        ),  # valid_github_ssh_url
    ],
    ids=[
        "valid_github_url",
        "valid_github_ssh_url",
    ],
)
def test_get_repo_from_input_url_input(config_input, get_repo_from_url_output):
    """Test the get_repo_from_input function."""
    with (
        patch(
            "include_configuration_stubs.utils.get_remote_repo"
        ) as mock_get_remote_repo,
        patch(
            "include_configuration_stubs.utils.get_repo_from_url",
            return_value=get_repo_from_url_output,
        ) as mock_get_repo_from_url,
    ):
        output = get_repo_from_input(config_input)
        assert output == get_repo_from_url_output
        mock_get_remote_repo.assert_not_called()
        mock_get_repo_from_url.assert_called_with(config_input)


def test_get_repo_from_input_repo_input():
    """
    Test the get_repo_from_input function when the input is in the 'OWNER/REPO' format.
    """
    config_input = "owner-example/repo_name"
    with (
        patch(
            "include_configuration_stubs.utils.get_remote_repo"
        ) as mock_get_remote_repo,
        patch(
            "include_configuration_stubs.utils.get_repo_from_url"
        ) as mock_get_repo_from_url,
    ):
        output = get_repo_from_input(config_input)
        assert output == config_input
        mock_get_remote_repo.assert_not_called()
        mock_get_repo_from_url.assert_not_called()


@pytest.mark.parametrize(
    "config_input",
    ["www.example.com/owner/repo", "invalid_repo_name", "invalid/repo/name"],
    ids=[
        "not_a_github_url",
        "no_slash",
        "multiple_slashes",
    ],
)
def test_get_repo_from_input_repo_input_invalid(config_input):
    """
    Test the get_repo_from_input function when the input is invalid.
    """
    with (
        patch(
            "include_configuration_stubs.utils.get_remote_repo"
        ) as mock_get_remote_repo,
        patch(
            "include_configuration_stubs.utils.get_repo_from_url"
        ) as mock_get_repo_from_url,
        pytest.raises(ValueError) as excinfo,
    ):
        get_repo_from_input(config_input)
        assert str(excinfo.value) == f"Invalid GitHub repo: '{config_input}'"
        mock_get_remote_repo.assert_not_called()
        mock_get_repo_from_url.assert_not_called()


def test_get_repo_from_input_none_input():
    """
    Test the get_repo_from_input function when the input is None.
    """
    config_input = None
    get_remote_repo_output = "https://github.com/example/repo"
    get_repo_from_url_output = "example/repo"
    with (
        patch(
            "include_configuration_stubs.utils.get_remote_repo",
            return_value=get_remote_repo_output,
        ) as mock_get_remote_repo,
        patch(
            "include_configuration_stubs.utils.get_repo_from_url",
            return_value=get_repo_from_url_output,
        ) as mock_get_repo_from_url,
    ):
        output = get_repo_from_input(config_input)
        assert output == get_repo_from_url_output
        mock_get_remote_repo.assert_called()
        mock_get_repo_from_url.assert_called_with(get_remote_repo_output)


def test_get_repo_from_input_none_input_error():
    """
    Test the get_repo_from_input function when the input is None.
    """
    config_input = None
    with (
        patch(
            "include_configuration_stubs.utils.get_remote_repo",
            side_effect=CalledProcessError(
                returncode=1, cmd="example", stderr="example_error"
            ),
        ) as mock_get_remote_repo,
        patch(
            "include_configuration_stubs.utils.get_repo_from_url"
        ) as mock_get_repo_from_url,
        pytest.raises(ValueError) as excinfo,
    ):
        get_repo_from_input(config_input)
        assert str(excinfo.value).startswith(
            "Failed to get the GitHub repository from local directory:"
        )
        mock_get_remote_repo.assert_called()
        mock_get_repo_from_url.assert_not_called()


@pytest.mark.parametrize(
    "main_branch_config_input, repo, command_output, get_repo_from_url_output, expected_output",
    [
        ("main", "example/repo", "main", "example/repo", True),  # true
        ("main", "example/repo", "not_main", "example/repo", False),  # not_main_branch
        (
            "main",
            "example/repo",
            "not_main",
            "example/different_repo",
            False,
        ),  # not_main_repo
    ],
    ids=[
        "true",
        "not_main_branch",
        "not_main_repo",
    ],
)
def test_is_main_website(
    fp,
    main_branch_config_input,
    repo,
    command_output,
    get_repo_from_url_output,
    expected_output,
):
    """
    Test the is_main_website function.
    """
    command = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    fp.register(command, stdout=command_output)
    with (
        patch(
            "include_configuration_stubs.utils.get_remote_repo",
            return_value=get_repo_from_url_output,
        ) as mock_get_remote_repo,
        patch(
            "include_configuration_stubs.utils.get_repo_from_url",
            return_value=repo,
        ) as mock_get_repo_from_url,
    ):
        output = is_main_website(main_branch_config_input, repo)
        assert output is expected_output
        mock_get_remote_repo.assert_called()
        mock_get_repo_from_url.assert_called()


def test_is_main_website_get_remote_repo_exception(fp):
    """
    Test the is_main_website function when the get_remote_repo raises an exception.
    """
    main_branch_config_input = "test"
    repo = "another_example/name"
    command = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    fp.register(command, stdout="example_command_output")
    with (
        patch(
            "include_configuration_stubs.utils.get_remote_repo",
            side_effect=CalledProcessError(
                returncode=1, cmd="example", stderr="example_error"
            ),
        ) as mock_get_remote_repo,
        patch(
            "include_configuration_stubs.utils.get_repo_from_url",
        ) as mock_get_repo_from_url,
    ):
        output = is_main_website(main_branch_config_input, repo)
        assert output is False
        mock_get_remote_repo.assert_called()
        mock_get_repo_from_url.assert_not_called()


def test_is_main_website_command_exception(fp):
    """
    Test the is_main_website function when the 'git rev-parse --abbrev-ref HEAD' command raises an exception.
    """
    main_branch_config_input = "test"
    repo = "another_example/name"
    command = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    fp.register(command, stdout="example_command_output", returncode=1)
    with (
        patch(
            "include_configuration_stubs.utils.get_remote_repo",
        ) as mock_get_remote_repo,
        patch(
            "include_configuration_stubs.utils.get_repo_from_url",
        ) as mock_get_repo_from_url,
    ):
        output = is_main_website(main_branch_config_input, repo)
        assert output is False
        mock_get_remote_repo.assert_called()
        mock_get_repo_from_url.assert_not_called()
