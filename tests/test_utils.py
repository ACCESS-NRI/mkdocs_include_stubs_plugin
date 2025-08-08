# fp is a fixture provided by pytest-subprocess.

import logging
from subprocess import CalledProcessError
from unittest.mock import MagicMock, patch, mock_open

import pytest
from requests import RequestException

from include_configuration_stubs.config import GitRefType
from include_configuration_stubs.plugin import SUPPORTED_FILE_FORMATS
from include_configuration_stubs.utils import (
    ConfigStub,
    add_navigation_hierarchy,
    add_pages_to_nav,
    append_number_to_file_name,
    check_is_installed,
    get_config_stub,
    get_config_stub_content,
    get_config_stub_fname,
    get_config_stub_title,
    get_git_refs,
    get_html_title,
    get_md_title,
    get_remote_repo_from_local_repo,
    get_repo_from_input,
    get_repo_from_url,
    is_main_website,
    logger,
    make_file_unique,
    set_stubs_nav_path,
    get_default_branch_from_remote_repo,
    remove_local_branch_from_refs,
    run_command,
    get_dest_uri_for_local_stub,
)


@pytest.fixture(autouse=True)
def silence_logs():
    logger.setLevel(logging.CRITICAL)


@pytest.fixture
def mock_git_refs():
    pass


def test_run_command(fp):
    """Test the run_command function."""
    command = ["echo", "Hello, World!"]
    fp.register(command, stdout="Hello, World!")
    result = run_command(command)
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
@pytest.mark.parametrize(
    "pattern",
    ["random-pattern",""],
    ids=["non-empty-pattern", "empty-pattern"],
)
@patch("include_configuration_stubs.utils.get_local_branch")
@patch("include_configuration_stubs.utils.remove_local_branch_from_refs")
def test_get_git_refs(
    mock_remove_local_branch_from_refs, mock_get_local_branch, fp, ref_type, pattern,
):
    """Test the get_git_refs function."""
    if ref_type == GitRefType.BRANCH:
        refs_flag = "--heads"
    elif ref_type == GitRefType.TAG:
        refs_flag = "--tags"
    elif ref_type == GitRefType.ALL:
        refs_flag = "--heads --tags"
    repo = "example/repo"
    repo_url = f"https://github.com/{repo}"
    if pattern:
        expected_output = ["sha1", "sha2", "sha3"]
        command_output = (
            "sha1\trefs/heads/main\nsha2\trefs/heads/dev\nsha3\trefs/heads/branch1"
        )
        fp.register(
            ["git", "ls-remote", refs_flag, repo_url, pattern], stdout=command_output
        )
        result = get_git_refs(repo, pattern, ref_type)
        assert result == expected_output
        assert ["git", "ls-remote", refs_flag, repo_url, pattern] in fp.calls
    else:
        expected_output = []
        result = get_git_refs(repo, pattern, ref_type)
        assert result == expected_output

@pytest.mark.parametrize(
    "is_remote_stub, response_json, response_raise, os_listdir_output, expected_output",
    [
        (
            True,
            None,
            True,
            None,
            None,
        ),  # remote_requests_error
        (
            True,
            [
                {"name": "name_without_extensionmd"},
                {"name": "name_without_extensionhtml"},
                {"name": "name_with_other_extension.jpg"},
            ],
            False,
            None,
            None,
        ),  # remote_no_extension
        (
            False,
            None,
            False,
            [
                "name_without_extensionmd",
                "name_without_extensionhtml",
                "name_with_other_extension.jpg",
            ],
            None,
        ),  # local_no_extension
        (
            True,
            [
                {"name": "name_with_extension.md"},
                {"name": "name_with_not_supported_extension.jpg"},
            ],
            False,
            None,
            "name_with_extension.md",
        ),  # remote_multiple_files_valid
        (
            False,
            None,
            False,
            [
                "name_with_extension.md",
                "name_with_not_supported_extension.jpg",
            ],
            "name_with_extension.md",
        ),  # local_multiple_files_valid
        (
            True,
            [
                {"name": "name_with_extension.md"},
                {"name": "name_with_supported_extension.html"},
            ],
            False,
            None,
            None,
        ),  # remote_multiple_supported_files
        (
            False,
            None,
            False,
            [
                "name_with_extension.md",
                "name_with_supported_extension.html",
            ],
            None,
        ),  # local_multiple_supported_files
        (
            True,
            [
                {"name": "name_with_extension.md"},
                {"name": "name_with_supported_extension.md"},
            ],
            False,
            None,
            None,
        ),  # remote_same_supported_files
        (
            False,
            None,
            False,
            [
                "name_with_extension.md",
                "name_with_supported_extension.md",
            ],
            None,
        ),  # local_same_supported_files
        (
            True,
            [{"name": "name_with_extension.html"}],
            False,
            None,
            "name_with_extension.html",
        ),  # remote_single_file
        (
            False,
            None,
            False,
            ["name_with_extension.html"],
            "name_with_extension.html",
        ),  # local_single_file
    ],
    ids=[
        "remote_requests_error",
        "remote_no_extension",
        "local_no_extension",
        "remote_multiple_files_valid",
        "local_multiple_files_valid",
        "remote_multiple_supported_files",
        "local_multiple_supported_files",
        "remote_same_supported_files",
        "local_same_supported_files",
        "remote_single_file",
        "local_single_file",
    ],
)
@patch("include_configuration_stubs.utils.requests.get")
@patch("include_configuration_stubs.utils.os.listdir")
def test_get_config_stub_fname(
    mock_listdir, mock_requests_get, is_remote_stub, response_json, response_raise, os_listdir_output, expected_output
):
    """Test the get_config_stub_fname function."""
    if is_remote_stub:
        mock_response = MagicMock()
        mock_response.json.return_value = response_json
        if response_raise:
            mock_response.raise_for_status.side_effect = RequestException
        else:
            mock_response.raise_for_status.side_effect = None
        mock_requests_get.return_value = mock_response
    else:
        mock_listdir.return_value = os_listdir_output
    assert (
        get_config_stub_fname(
            stub_dir="config/path",
            supported_file_formats=SUPPORTED_FILE_FORMATS,
            is_remote_stub=is_remote_stub,
            ref="sha1234567",
            repo="owner/repo",
        )
        == expected_output
    )


@pytest.mark.parametrize(
    "is_remote_stub, response_text, response_raise, fread_output, expected_output",
    [
        (
            True,
            "example text",
            False,
            None,
            "example text",
        ),  # remote_valid
        (
            True,
            "example text",
            True,
            None,
            None,
        ),  # remote_response_error
        (
            False,
            None,
            False,
            "example text",
            "example text",
        ),  # local
    ],
    ids=[
            "remote_valid", 
            "remote_response_error",
            "local",
        ],
)
@patch("include_configuration_stubs.utils.requests.get")
def test_get_config_stub_content(
    mock_response_get, is_remote_stub, response_text, response_raise, fread_output, expected_output
):
    """Test the get_config_stub_content function."""
    stub_dir="config/path"
    fname="example_name"
    repo="owner/repo"
    ref="sha1234567"
    if is_remote_stub:
        mock_response = MagicMock()
        mock_response.text = response_text
        if response_raise:
            mock_response.raise_for_status.side_effect = RequestException
        else:
            mock_response.raise_for_status.side_effect = None
        mock_response_get.return_value = mock_response
        assert get_config_stub_content(
            stub_dir=stub_dir,
            fname=fname,
            is_remote_stub=is_remote_stub,
            repo=repo,
            ref=ref,
        ) == expected_output
    else:
        m = mock_open(read_data=fread_output)
        with patch("include_configuration_stubs.utils.open", m):
            output = get_config_stub_content(
                stub_dir=stub_dir,
                fname=fname,
                is_remote_stub=is_remote_stub,
                repo=repo,
                ref=ref,
            ) 
        assert output == expected_output
        m.assert_called_once_with(f"{stub_dir}/{fname}", "r", encoding="utf-8")


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
@pytest.mark.parametrize(
    "is_remote_stub",
    [True, False],
    ids=["remote", "local"],
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
    is_remote_stub,
):
    """Test the get_config_stub function."""
    mock_get_fname.return_value = fname_output
    mock_get_content.return_value = content_output
    mock_get_title.return_value = title_output
    assert get_config_stub(
        stub_dir="config/path",
        supported_file_formats=SUPPORTED_FILE_FORMATS,
        is_remote_stub=is_remote_stub,
        repo="owner/repo",
        ref="sha1234567",
    ) == expected_output
    assert mock_get_fname.call_args.kwargs.get('is_remote_stub') == is_remote_stub
    if mock_get_content.call_args is not None:
        assert mock_get_content.call_args.kwargs.get('is_remote_stub') == is_remote_stub


def test_get_remote_repo(fp):
    """
    Test the get_remote_repo_from_local_repo function.
    """
    mock_stdout = "mock_output"
    command = ["git", "remote", "get-url", "origin"]
    fp.register(command, stdout=mock_stdout)
    output = get_remote_repo_from_local_repo()
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
            "include_configuration_stubs.utils.get_remote_repo_from_local_repo"
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
            "include_configuration_stubs.utils.get_remote_repo_from_local_repo"
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
            "include_configuration_stubs.utils.get_remote_repo_from_local_repo"
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


@pytest.mark.parametrize(
    "config_input",
    ["", None],
    ids=["empty", "none"],
)
def test_get_repo_from_input_no_input(config_input):
    """
    Test the get_repo_from_input function when the input is None or empty.
    """
    get_remote_repo_output = "https://github.com/example/repo"
    get_repo_from_url_output = "example/repo"
    with (
        patch(
            "include_configuration_stubs.utils.get_remote_repo_from_local_repo",
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


@pytest.mark.parametrize(
    "config_input",
    ["", None],
    ids=["empty", "none"],
)
def test_get_repo_from_input_no_input_error(config_input):
    """
    Test the get_repo_from_input function when the input is None or empty
    and get_remote_repo_from_local_repo raises an exception.
    """
    with (
        patch(
            "include_configuration_stubs.utils.get_remote_repo_from_local_repo",
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
    "main_branch_config_input, local_branch, remote_owner_name, expected_output",
    [
        ("branch", "branch", "example/repo", True),  # true
        ("main_branch", "not_main_branch", "example/repo", False),  # not_main_branch
        ("branch", "branch", "example/different_repo", False),  # not_main_repo
        (None, "default", "example/repo", True),  # none_branch_true
        (None, "default", "example/different_repo", False),  # none_branch_false
    ],
    ids=[
        "true",
        "not_main_branch",
        "not_main_repo",
        "none_branch_true",
        "none_branch_false",
    ],
)
@patch(
    "include_configuration_stubs.utils.get_default_branch_from_remote_repo",
    return_value="default",
)
@patch("include_configuration_stubs.utils.get_local_branch")
def test_is_main_website(
    mock_get_local_branch,
    mock_get_default_branch_from_remote_repo,
    main_branch_config_input,
    local_branch,
    remote_owner_name,
    expected_output,
):
    """
    Test the is_main_website function.
    """
    repo = "example/repo"
    mock_get_local_branch.return_value = local_branch
    with (
        patch(
            "include_configuration_stubs.utils.get_remote_repo_from_local_repo",
            return_value=remote_owner_name,
        ) as mock_get_remote_repo,
        patch(
            "include_configuration_stubs.utils.get_repo_from_url",
            return_value=remote_owner_name,
        ) as mock_get_repo_from_url,
    ):
        output = is_main_website(main_branch_config_input, repo)
        assert output is expected_output
        mock_get_remote_repo.assert_called()
        mock_get_repo_from_url.assert_called()


def test_is_main_website_get_remote_repo_exception(fp):
    """
    Test the is_main_website function when the get_remote_repo_from_local_repo raises an exception.
    """
    main_branch_config_input = "test"
    repo = "another_example/name"
    command = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    fp.register(command, stdout="example_command_output")
    with (
        patch(
            "include_configuration_stubs.utils.get_remote_repo_from_local_repo",
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
            "include_configuration_stubs.utils.get_remote_repo_from_local_repo",
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


@pytest.mark.parametrize(
    "path, expected_output",
    [
        ("Some/ Path /For/Navigation/", "Some/ Path /For/Navigation"),  # string
        ("", ""),  # empty
        (None, "default_output"),  # none
    ],
    ids=["string", "empty", "none"],
)
@patch("include_configuration_stubs.utils.set_default_stubs_nav_path")
def test_set_stubs_nav_path(mock_set_default_stubs_nav_path, path, expected_output):
    """
    Test the set_stubs_nav_path function.
    """
    mock_set_default_stubs_nav_path.return_value = "default_output"
    assert set_stubs_nav_path(path, "stub") == expected_output


def test_add_navigation_hierarchy(mock_section):
    """
    Test the add_navigation_hierarchy function.
    """
    root_item = mock_section
    titles = ["Section 1", "Section 2"]
    add_navigation_hierarchy(root_item, titles)
    assert len(root_item.children) == 3
    assert root_item.children[-1].title == "Section 1"
    assert len(root_item.children[-1].children) == 1
    assert root_item.children[-1].children[0].title == "Section 2"


def test_add_navigation_hierarchy_navigation_input(mock_navigation):
    """
    Test the add_navigation_hierarchy function when the input item is the entire navigation.
    """
    root_item = mock_navigation
    titles = ["Section 1", "Section 2"]
    add_navigation_hierarchy(root_item, titles)
    assert len(root_item.items) == 2
    assert root_item.items[-1].title == "Section 1"
    assert len(root_item.items[-1].children) == 1
    assert root_item.items[-1].children[0].title == "Section 2"


def test_add_pages_to_nav_no_section_creation(mock_navigation):
    """
    Test the add_pages_to_nav function when all the subsections are present.
    """
    pages = [MagicMock(), MagicMock()]
    nav = mock_navigation
    nav_titles = ["Root", "Subsection"]
    add_pages_to_nav(nav, pages, nav_titles)
    assert len(nav.items) == 1
    assert nav.items[0].title == "Root"
    assert len(nav.items[0].children) == 2
    assert nav.items[0].children[1].title == "Subsection"
    assert len(nav.items[0].children[1].children) == 3
    assert nav.items[0].children[1].children[-2:] == pages
    for page in pages:
        assert page.parent == nav.items[0].children[1]


def test_add_pages_to_nav_section_created(mock_navigation):
    """
    Test the add_pages_to_nav function when the section needs to be created.
    """
    pages = [MagicMock(), MagicMock()]
    nav = mock_navigation
    nav_titles = ["Root", "New Section"]
    add_pages_to_nav(nav, pages, nav_titles)
    assert len(nav.items) == 1
    assert nav.items[0].title == "Root"
    assert len(nav.items[0].children) == 3
    assert nav.items[0].children[1].title == "Subsection"
    assert nav.items[0].children[2].title == "New Section"
    assert len(nav.items[0].children[1].children) == 1
    assert nav.items[0].children[2].children[-2:] == pages
    for page in pages:
        assert page.parent == nav.items[0].children[2]


def test_add_pages_to_nav_root(mock_navigation):
    """
    Test the add_pages_to_nav function when the pages are added to the root navigation.
    """
    pages = [MagicMock(), MagicMock()]
    nav = mock_navigation
    nav_titles = [""]
    add_pages_to_nav(nav, pages, nav_titles)
    assert len(nav.items) == 3
    assert nav.items[0].title == "Root"
    assert nav.items[-2:] == pages
    for page in pages:
        assert isinstance(page.parent, MagicMock)


@pytest.mark.parametrize(
    "response_json, response_raise, expected_output",
    [
        (
            None,
            True,
            None,
        ),  # requests_error
        (
            {
                "something": "example",
                "default_branch": "default",
                "name": "some_name",
            },
            False,
            "default",
        ),  # valid
    ],
    ids=[
        "requests_error",
        "valid",
    ],
)
@patch("include_configuration_stubs.utils.requests.get")
def test_get_default_branch_from_remote_repo(
    mock_requests_get, response_json, response_raise, expected_output
):
    """
    Test the get_default_branch_from_remote_repo function.
    """
    repo = "owner/repo"
    mock_response = MagicMock()
    mock_response.json.return_value = response_json
    mock_requests_get.return_value = mock_response
    if response_raise:
        mock_response.ok = False
        with pytest.raises(ValueError):
            get_default_branch_from_remote_repo(repo)
    else:
        assert get_default_branch_from_remote_repo(repo) == expected_output


@pytest.mark.parametrize(
    "local_branch, expected_output",
    [
        (
            "some_branch",
            [
                ["sha1", "some/repo/ref1"],
                ["sha2", "some/repo/ref2"],
                ["sha3", "some/repo/ref3"],
            ],
        ),  # no_local_branch_in_refs
        (
            "ref2",
            [["sha1", "some/repo/ref1"], ["sha3", "some/repo/ref3"]],
        ),  # local_branch_in_refs
    ],
    ids=[
        "no_local_branch_in_refs",
        "local_branch_in_refs",
    ],
)
def test_remove_local_branch_from_refs(local_branch, expected_output):
    """
    Test the remove_local_branch_from_refs function.
    """
    refs = [
        ["sha1", "some/repo/ref1"],
        ["sha2", "some/repo/ref2"],
        ["sha3", "some/repo/ref3"],
    ]
    remove_local_branch_from_refs(refs, local_branch)
    assert refs == expected_output


@pytest.mark.parametrize(
    "use_directory_urls, expected_output",
    [
        (True, "parent/url/example_stub/index.html"), # use_directory_urls_true
        (False, "parent/url/example_stub") # use_directory_urls_false
    ],
    ids=[
        "use_directory_urls_true",
        "use_directory_urls_false",
    ],
)
def test_get_dest_uri_for_local_stub(use_directory_urls, expected_output):
    """
    Test the get_dest_uri_for_local_stub function.
    """
    stub_fname = "example_stub.md"
    stubs_parent_url = "parent/url"
    output = get_dest_uri_for_local_stub(stub_fname, stubs_parent_url, use_directory_urls, SUPPORTED_FILE_FORMATS)
    assert output == expected_output