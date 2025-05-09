# fp is a fixture provided by pytest-subprocess.

from subprocess import CalledProcessError
from unittest.mock import MagicMock, patch

import pytest
from requests import RequestException

from include_configuration_stubs.config import GitRefType
from include_configuration_stubs.plugin import SUPPORTED_FILE_FORMATS
from include_configuration_stubs.utils import (
    ConfigStub,
    append_number_to_file_name,
    check_is_installed,
    get_command_output,
    get_config_stub,
    get_config_stub_content,
    get_config_stub_fname,
    get_config_stub_title,
    get_git_refs,
    get_html_title,
    get_md_title,
    get_remote_repo,
    get_repo_from_input,
    get_repo_from_url,
    is_main_website,
    make_file_unique,
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
    "response_json, response_raise, expected_output",
    [
        (
            None,
            True,
            None,
        ),  # requests_error
        (
            [
                {"name": "name_without_extensionmd"},
                {"name": "name_without_extensionhtml"},
                {"name": "name_with_other_extension.jpg"},
            ],
            False,
            None,
        ),  # no_extension
        (
            [
                {"name": "name_with_extension.md"},
                {"name": "name_with_not_supported_extension.jpg"},
            ],
            False,
            "name_with_extension.md",
        ),  # multiple_files_valid
        (
            [
                {"name": "name_with_extension.md"},
                {"name": "name_with_supported_extension.html"},
            ],
            False,
            None,
        ),  # multiple_supported_files
        (
            [
                {"name": "name_with_extension.md"},
                {"name": "name_with_supported_extension.md"},
            ],
            False,
            None,
        ),  # same_supported_files
        (
            [{"name": "name_with_extension.html"}],
            False,
            "name_with_extension.html",
        ),  # single_file
    ],
    ids=[
        "requests_error",
        "no_extension",
        "multiple_files_valid",
        "multiple_supported_files",
        "same_supported_files",
        "single_file",
    ],
)
@patch("include_configuration_stubs.utils.requests.get")
def test_get_config_stub_fname(
    mock_requests_get, response_json, response_raise, expected_output
):
    """Test the get_config_stub_fname function."""
    mock_response = MagicMock()
    mock_response.json.return_value = response_json
    if response_raise:
        mock_response.raise_for_status.side_effect = RequestException
    else:
        mock_response.raise_for_status.side_effect = None
    mock_requests_get.return_value = mock_response
    ref = "sha1234567"
    repo = "owner/repo"
    path = "config/path"
    assert (
        get_config_stub_fname(ref, repo, path, SUPPORTED_FILE_FORMATS)
        == expected_output
    )


@pytest.mark.parametrize(
    "fname_output, content_output, title_output, expected_output",
    [
        (
            "example_name",
            "Example file content",
            "Example title",
            ConfigStub(
                fname="example_name",
                content="Example file content",
                title="Example title",
            ),
        ),  # valid
        (
            None,
            "Example file content",
            "Example title",
            None,
        ),  # no_fname
        (
            "example_name",
            None,
            "Example title",
            None,
        ),  # no_content
        (
            "example_name",
            "Example file content",
            None,
            ConfigStub(
                fname="example_name",
                content="Example file content",
                title=None,
            ),
        ),  # no_title
    ],
    ids=[
        "valid",
        "no_fname",
        "no_content",
        "no_title",
    ],
)
@patch("include_configuration_stubs.utils.get_config_stub_fname")
@patch("include_configuration_stubs.utils.get_config_stub_content")
@patch("include_configuration_stubs.utils.get_config_stub_title")
def test_get_config_stub(
    mock_get_title,
    mock_get_content,
    mock_get_fname,
    fname_output,
    content_output,
    title_output,
    expected_output,
):
    """Test the get_config_stub function."""
    mock_get_fname.return_value = fname_output
    mock_get_content.return_value = content_output
    mock_get_title.return_value = title_output
    ref = "sha1234567"
    repo = "owner/repo"
    path = "config/path"
    assert get_config_stub(ref, repo, path, SUPPORTED_FILE_FORMATS) == expected_output


@pytest.mark.parametrize(
    "response_text, response_raise, expected_output",
    [
        (
            "example text",
            False,
            "example text",
        ),  # valid
        (
            "example text",
            True,
            None,
        ),  # response_error
    ],
    ids=["valid", "response_error"],
)
@patch("include_configuration_stubs.utils.requests.get")
def test_get_config_stub_content(
    mock_response_get, response_text, response_raise, expected_output
):
    """Test the get_config_stub_content function."""
    mock_response = MagicMock()
    mock_response.text = response_text
    if response_raise:
        mock_response.raise_for_status.side_effect = RequestException
    else:
        mock_response.raise_for_status.side_effect = None
    mock_response_get.return_value = mock_response
    ref = "sha1234567"
    repo = "owner/repo"
    path = "config/path"
    fname = "example_name"
    assert get_config_stub_content(ref, repo, path, fname) == expected_output


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


def test_append_number_to_file_name():
    """
    Test the append_number_to_file_name function.
    """
    filename = "example.extension"
    number = 31
    expected_output = "example31.extension"
    output = append_number_to_file_name(filename, number)
    assert output == expected_output


@pytest.mark.parametrize(
    "input_src_path, input_dest_path, use_directory_urls, expected_output_src_path, expected_output_dest_path",
    [
        (
            "other",
            "something/index.html",
            True,
            "other",
            "something/index.html",
        ),  # unique
        (
            "src_path",
            "other_dest/index.html",
            True,
            "src_path2",
            "other_dest2/index.html",
        ),  # same src_path
        (
            "other_src",
            "dest_path/index.html",
            True,
            "other_src1",
            "dest_path1/index.html",
        ),  # same dest_path
        (
            "src_path",
            "dest_path/index.html",
            True,
            "src_path4",
            "dest_path4/index.html",
        ),  # same src_path and dest_path
        (
            "src_path",
            "other_dest/index.html",
            False,
            "src_path2",
            "other_dest/index2.html",
        ),  # use_directory_urls_false
    ],
    ids=[
        "unique",
        "same_src_path",
        "same_dest_path",
        "same_src_path_and_dest_path",
        "use_directory_urls_false",
    ],
)
def test_make_file_unique(
    mock_files,
    input_src_path,
    input_dest_path,
    use_directory_urls,
    expected_output_src_path,
    expected_output_dest_path,
):
    """Test the make_file_unique function."""
    file = MagicMock(
        src_path=input_src_path,
        dest_path=input_dest_path,
        use_directory_urls=use_directory_urls,
    )
    files = mock_files(
        [
            MagicMock(src_path="src_path", dest_path="dest_path/index.html"),
            MagicMock(src_path="src_path1", dest_path="dest_path2/index.html"),
            MagicMock(src_path="src_path3", dest_path="other_dest_path/index.html"),
        ]
    )
    make_file_unique(file, files)
    assert file.src_path == expected_output_src_path
    assert file.dest_path == expected_output_dest_path


@pytest.mark.parametrize(
    "content, expected_output",
    [
        (
            "<html><body><h1>Example Title</h1></body></html>",
            "Example Title",
        ),  # one_title
        (
            "<html><body><h1>Example <b>Title</b></h1></body></html>",
            "Example Title",
        ),  # special_characters
        (
            "<html><body><h1>First Title</h1><h1>Second Title</h1></body></html>",
            "First Title",
        ),  # multiple_titles
        ("<html><body><h2>First Title</h2></body></html>", None),  # no_title
        (
            "<html><body><!-- <h1>First Title</h1> --></body></html>",
            None,
        ),  # commented_title
    ],
    ids=[
        "one_title",
        "special_characters",
        "multiple_titles",
        "no_title",
        "commented_title",
    ],
)
def test_get_html_title(content, expected_output):
    """
    Test the get_html_title function.
    """
    assert get_html_title(content) == expected_output


@pytest.mark.parametrize(
    "content, expected_output",
    [
        ("# Example Title \n Other text", "Example Title"),  # one_title
        ("# Example `Title` \n Other text", "Example Title"),  # special_characters
        (
            "# First Title \n Other text \n # Other title",
            "First Title",
        ),  # multiple_titles
        ("## No title \n Other text", None),  # no_title
        ("<!--  # Title --> \n Text", None),  # commented_title
    ],
    ids=[
        "one_title",
        "special_characters",
        "multiple_titles",
        "no_title",
        "commented_title",
    ],
)
def test_get_md_title(content, expected_output):
    """
    Test the get_md_title function.
    """
    assert get_md_title(content) == expected_output


@patch(
    "include_configuration_stubs.utils.get_html_title",
    return_value="html",
)
@patch(
    "include_configuration_stubs.utils.get_md_title",
    return_value="md",
)
def test_get_config_stub_title(path, expected_output):
    """
    Test the get_config_stub_title function.
    """
    assert get_config_stub_title("some/path.html", "example_content") == "html"
    assert get_config_stub_title("some/other/path.md", "example_content") == "md"
