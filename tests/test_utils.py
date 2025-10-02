# fp is a fixture provided by pytest-subprocess.

from subprocess import CalledProcessError, SubprocessError
from unittest.mock import MagicMock, mock_open, patch

import pytest
from requests import RequestException

from include_stubs.config import GitRef, GitRefType
from include_stubs.plugin import SUPPORTED_FILE_FORMATS
from include_stubs.utils import (
    Stub,
    GitHubApiRateLimitError,
    add_navigation_hierarchy,
    add_pages_to_nav,
    append_number_to_file_name,
    get_default_branch_from_remote_repo,
    get_dest_uri_for_local_stub,
    get_git_refs,
    get_html_title,
    get_md_title,
    get_remote_repo_from_local_repo,
    get_repo_from_input,
    get_repo_from_url,
    get_unique_stub_fname,
    gh_rate_limit_reached,
    is_main_website,
    keep_unique_refs,
    make_file_unique,
    print_exe_version,
    run_command,
    set_stubs_nav_path,
)



@pytest.fixture
def graphql_query_string():
    return (
        'query { repository(owner: "example", name: "repo") {'
        'r_abc123: object(expression: "abc123:stub/path") { ... on Tree { entries { name type oid }}}'
        'r_def456: object(expression: "def456:stub/path") { ... on Tree { entries { name type oid }}}'
        'r_123456: object(expression: "123456:stub/path") { ... on Tree { entries { name type oid }}}'
        'r_345678: object(expression: "345678:stub/path") { ... on Tree { entries { name type oid }}}'
        "}}"
    )


def test_run_command(fp):
    """Test the run_command function."""
    command = ["echo", "Hello, World!"]
    fp.register(command, stdout="Hello, World!")
    result = run_command(command)
    assert result == "Hello, World!"
    assert command in fp.calls


@patch("include_stubs.utils.logger")
def test_print_exe_version_executable_installed(mock_logger):
    """Test the print_exe_version function when the executable is installed."""
    exe = "random_example_executable"
    with patch(
        "include_stubs.utils.run_command", return_value="1.2.3"
    ) as mock_run_command:
        print_exe_version(exe)
        mock_run_command.assert_called_once_with([exe, "--version"])
        mock_logger.info.assert_called_once_with(f"'{exe}' version: 1.2.3")


def test_print_exe_version_executable_not_installed(fp):
    """Test the print_exe_version function when the executable is installed."""
    exe = "random_example_executable"
    fp.register([f"{exe}", "--version"], returncode=1)
    with pytest.raises(EnvironmentError) as excinfo:
        print_exe_version(exe)
        assert (
            str(excinfo.value)
            == f"Failed to get '{exe}' version. Please ensure it is installed correctly."
        )


@pytest.mark.parametrize(
    "ref_type, ref_flag",
    [
        (GitRefType.BRANCH, ["--heads"]),  # ref_type_branch
        (GitRefType.TAG, ["--tags"]),  # ref_type_tag
        (GitRefType.ALL, ["--heads", "--tags"]),  # ref_type_all
    ],
    ids=["ref_type_branch", "ref_type_tag", "ref_type_all"],
)
@pytest.mark.parametrize(
    "command_output, expected_output",
    [
        (
            "sha1\trefs/heads/main\nsha2\trefs/tags/dev\nsha3\trefs/heads/example/branch1\nsha4\trefs/tags/example/tag^{}",
            [
                GitRef(sha="sha1", name="main"),
                GitRef(sha="sha2", name="dev"),
                GitRef(sha="sha3", name="example/branch1"),
            ],
        ),  # non-empty-command-output
        ("", []),  # empty-command-output
    ],
    ids=["non-empty-command-output", "empty-command-output"],
)
@patch("include_stubs.utils.get_local_branch")
def test_get_git_refs(
    mock_get_local_branch,
    fp,
    ref_type,
    ref_flag,
    command_output,
    expected_output,
):
    """Test the get_git_refs function."""
    repo = "example/repo"
    repo_url = f"https://github.com/{repo}"
    pattern = "random-pattern"
    fp.register(
        ["git", "ls-remote", *ref_flag, repo_url, pattern], stdout=command_output
    )
    result = get_git_refs(repo, pattern, ref_type)
    assert result == expected_output
    assert ["git", "ls-remote", *ref_flag, repo_url, pattern] in fp.calls
    if command_output:
        mock_get_local_branch.assert_called_once()


@pytest.mark.parametrize(
    "command_output, expected_output",
    [
        ("false", False),  # rate_limit_not_reached
        ("true", True),  # rate_limit_reached
    ],
    ids=[
        "rate_limit_not_reached",
        "rate_limit_reached",
    ],
)
def test_gh_rate_limit_reached(fp, command_output, expected_output):
    """Test the gh_rate_limit_reached function."""
    command = [
        "gh",
        "api",
        "rate_limit",
        "--jq",
        "[.resources.[] | .remaining] | any(. == 0)",
    ]
    fp.register(command, stdout=command_output)
    result = gh_rate_limit_reached()
    assert result is expected_output


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
            assert str(excinfo.value) == "Invalid GitHub repo URL: '{repo_url}'"
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
            "include_stubs.utils.get_remote_repo_from_local_repo"
        ) as mock_get_remote_repo,
        patch(
            "include_stubs.utils.get_repo_from_url",
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
            "include_stubs.utils.get_remote_repo_from_local_repo"
        ) as mock_get_remote_repo,
        patch("include_stubs.utils.get_repo_from_url") as mock_get_repo_from_url,
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
            "include_stubs.utils.get_remote_repo_from_local_repo"
        ) as mock_get_remote_repo,
        patch("include_stubs.utils.get_repo_from_url") as mock_get_repo_from_url,
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
            "include_stubs.utils.get_remote_repo_from_local_repo",
            return_value=get_remote_repo_output,
        ) as mock_get_remote_repo,
        patch(
            "include_stubs.utils.get_repo_from_url",
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
            "include_stubs.utils.get_remote_repo_from_local_repo",
            side_effect=SubprocessError(),
        ) as mock_get_remote_repo,
        patch("include_stubs.utils.get_repo_from_url") as mock_get_repo_from_url,
        pytest.raises(ValueError) as excinfo,
    ):
        get_repo_from_input(config_input)
        assert (
            str(excinfo.value)
            == "Cannot determine GitHub repository. No GitHub repository specified in the plugin configuration and local directory is not a git repository."
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
    "include_stubs.utils.get_default_branch_from_remote_repo",
    return_value="default",
)
@patch("include_stubs.utils.get_local_branch")
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
            "include_stubs.utils.get_remote_repo_from_local_repo",
            return_value=remote_owner_name,
        ) as mock_get_remote_repo,
        patch(
            "include_stubs.utils.get_repo_from_url",
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
            "include_stubs.utils.get_remote_repo_from_local_repo",
            side_effect=CalledProcessError(
                returncode=1, cmd="example", stderr="example_error"
            ),
        ) as mock_get_remote_repo,
        patch(
            "include_stubs.utils.get_repo_from_url",
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
            "include_stubs.utils.get_remote_repo_from_local_repo",
        ) as mock_get_remote_repo,
        patch(
            "include_stubs.utils.get_repo_from_url",
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
        (
            "> Some random / Path /For/Navigation/ >>",
            "> Some random / Path /For/Navigation/ >>",
        ),  # string
        ("", ""),  # empty
        ("    ", "    "),  # blank
        (None, "default_output"),  # none
    ],
    ids=["string", "empty", "blank", "none"],
)
@patch("include_stubs.utils.set_default_stubs_nav_path")
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


def test_get_default_branch_from_remote_repo_valid(
    fp,
):
    """
    Test the get_default_branch_from_remote_repo function when the command is successful.
    """
    remote_repo = "owner/repo"
    api_url = f"repos/{remote_repo}"
    command = ["gh", "api", api_url, "--jq", ".default_branch"]
    fp.register(command, stdout="default")
    assert get_default_branch_from_remote_repo(remote_repo) == "default"


@pytest.mark.parametrize(
    "gh_rate_limit_reached",
    [True, False],
    ids=["gh_api_rate_limit_reached", "gh_api_rate_limit_not_reached"],
)
def test_get_default_branch_from_remote_repo_error(
    gh_rate_limit_reached,
    fp,
):
    """
    Test the get_default_branch_from_remote_repo function when the command is not successful.
    """
    remote_repo = "owner/repo"
    api_url = f"repos/{remote_repo}"
    command = ["gh", "api", api_url, "--jq", ".default_branch"]
    fp.register(command, returncode=1)
    exception_class = GitHubApiRateLimitError if gh_rate_limit_reached else ValueError
    with (
        patch(
            "include_stubs.utils.gh_rate_limit_reached",
            return_value=gh_rate_limit_reached,
        ),
        pytest.raises(exception_class),
    ):
        get_default_branch_from_remote_repo(remote_repo)


@pytest.mark.parametrize(
    "use_directory_urls, expected_output",
    [
        (True, "parent/url/example_stub/index.html"),  # use_directory_urls_true
        (False, "parent/url/example_stub"),  # use_directory_urls_false
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
    output = get_dest_uri_for_local_stub(
        stub_fname, stubs_parent_url, use_directory_urls, SUPPORTED_FILE_FORMATS
    )
    assert output == expected_output


def test_keep_unique_refs():
    """
    Test the keep_unique_refs function.
    """
    refs = [
        GitRef(sha="123", name="ref1"),
        GitRef(sha="456", name="ref2"),
        GitRef(sha="123", name="ref4"),  # duplicate
        GitRef(sha="231", name="ref1"),
        GitRef(sha="456", name="ref1"),  # duplicate
        GitRef(sha="431", name="ref1"),
    ]
    expected = [
        GitRef(sha="123", name="ref1"),
        GitRef(sha="456", name="ref2"),
        GitRef(sha="231", name="ref1"),
        GitRef(sha="431", name="ref1"),
    ]
    result = keep_unique_refs(refs)
    assert result == expected


@pytest.mark.parametrize(
    "filenames, expected_output",
    [
        (
            ["f.ext1", "f.txt", "f"],
            "f.ext1",
        ),
        (
            ["f.ext", "f.txt", "f"],
            None,
        ),
        (
            ["f.ext1", "f.ext2", "f"],
            None,
        ),
    ],
    ids=[
        "one supported file",
        "no supported files",
        "multiple supported files",
    ],
)
def test_get_unique_stub_fname(filenames, expected_output):
    """
    Test the get_unique_stub_fname function.
    """
    supported_file_formats = (".ext1", ".ext2")
    output = get_unique_stub_fname(filenames, supported_file_formats)
    assert expected_output == output


def test_StubList_init(mock_stublist, create_mock_mkdocs_config):
    """Test StubList initialisation."""
    mkdocs_config = create_mock_mkdocs_config(
        site_dir="some/site/dir", 
        use_directory_urls=True,
    )
    stublist = mock_stublist(config=mkdocs_config)
    assert stublist.mkdocs_config == mkdocs_config
    assert stublist.repo == "example/repo"
    assert stublist.stubs_dir == "stub/path"
    assert stublist.supported_file_formats == (".ext1", ".ext2")
    assert stublist.stubs_parent_url == "parent/url"
    assert len(stublist) == 5
    assert len(stublist.files) == 3


def test_StubList_remote_stubs(mock_stublist):
    """Test StubList's _remote_stubs property of StubList."""
    stublist = mock_stublist()
    assert stublist.remote_stubs == tuple(stublist[i] for i in (0, 1, 2, 4))


def test_StubList_local_stub(mock_stublist):
    """Test StubList's _local_stub property of StubList."""
    stublist = mock_stublist()
    assert stublist.local_stub == stublist[3]
    del stublist[3]
    assert stublist.local_stub is None

@pytest.mark.parametrize(
    "local_stub_present",
    [True, False],
    ids=[
        "with_local_stub",
        "no_local_stub",
    ],
)
def test_StubList_append_or_replace(mock_stublist, local_stub_present):
    """Test StubList's append_or_replace method."""
    stublist = mock_stublist()
    old_local_stub = stublist[3]
    new_local_stub = Stub(is_remote=False)
    if not local_stub_present:
        del stublist[3]
    # Remote stub throws error
    with pytest.raises(ValueError):
        stublist.append_or_replace(Stub(gitref='1234'))
    stublist.append_or_replace(new_local_stub)
    assert old_local_stub not in stublist
    assert new_local_stub in stublist
    assert len(stublist) == 5
    

def test_StubList_get_graphql_query_string(graphql_query_string, mock_stublist):
    """
    Test StubList's _get_graphql_query_string method.
    """
    stublist = mock_stublist()
    output = stublist._get_graphql_query_string()
    assert output == graphql_query_string


@patch(
    "include_stubs.utils.StubList._get_graphql_query_string",
    return_value=graphql_query_string,
)
@patch("include_stubs.utils.gh_rate_limit_reached")
@patch("include_stubs.utils.json.loads")
@patch("include_stubs.utils.get_unique_stub_fname")
def test_StubList_populate_remote_stub_fnames(
    mock_get_unique_stub_fname,
    mock_json_loads,
    mock_gh_rate_limit_reached,
    mock_get_graphql_query_string,
    fp,
    mock_stublist,
):
    """
    Test StubList's _populate_remote_stub_fnames method.
    """
    stublist = mock_stublist()
    command = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={mock_get_graphql_query_string.return_value}",
    ]
    fp.register(command)
    mock_json_loads.return_value = {
        "data": {
            "repository": {
                "r_abc123": MagicMock(),
                "r_def456": None,
                "r_123456": MagicMock(),
                "r_345678": MagicMock(),
            }
        }
    }
    # We set the side_effect to return different values on each call.
    # We return a valid filename on the first and second call, None on the third call.
    mock_get_unique_stub_fname.side_effect = ["file1", "file2", None]
    stublist._populate_remote_stub_fnames()
    mock_gh_rate_limit_reached.assert_not_called()
    assert len(stublist) == 3  # 2 remotes and 1 local
    assert stublist[0].fname == "file1"
    assert stublist[0].gitref.sha == "abc123"
    assert stublist[1].fname == "file2"
    assert stublist[1].gitref.sha == "123456"


@pytest.mark.parametrize(
    "fname",
    ["some_filename", None],
    ids=["valid_fname", "None_fname"],
)
@patch("include_stubs.utils.os.listdir")
@patch("include_stubs.utils.get_unique_stub_fname")
def test_StubList_populate_local_stub_fname(
    mock_get_unique_stub_fname,
    mock_os_listdir,
    fname,
    mock_stublist,
):
    """
    Test StubList's _populate_local_stub_fname method.
    """
    stublist = mock_stublist()
    mock_get_unique_stub_fname.return_value = fname
    stublist._populate_local_stub_fname()
    if fname is None:
        assert len(stublist) == 4  # only remotes
        assert all(stub.is_remote is True for stub in stublist)
    else:
        assert len(stublist) == 5  # all stublist
        stublist[3].fname = fname


@pytest.mark.parametrize(
    "rate_limit_reached",
    [True, False],
    ids=["rate_limit_reached", "rate_limit_not_reached"],
)
@patch(
    "include_stubs.utils.StubList._get_graphql_query_string",
    return_value=graphql_query_string,
)
def test_StubList_populate_remote_stub_fnames_api_request_fail(
    mock_get_graphql_query_string, rate_limit_reached, fp, mock_stublist
):
    """
    Test StubList's _populate_remote_stub_fnames method.
    """
    stublist = mock_stublist()
    command = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={mock_get_graphql_query_string.return_value}",
    ]
    fp.register(command, returncode=1)
    if rate_limit_reached:
        exc_class = GitHubApiRateLimitError
    else:
        exc_class = ValueError
    with (
        patch(
            "include_stubs.utils.gh_rate_limit_reached", return_value=rate_limit_reached
        ),
        pytest.raises(exc_class),
    ):
        stublist._populate_remote_stub_fnames()


@patch("include_stubs.utils.requests.get")
def test_StubList_populate_remote_stub_contents(
    mock_requests_get,
    mock_stublist,
):
    """
    Test StubList's _populate_remote_stub_contents method.
    """
    stublist = mock_stublist()
    # Mock the requests.get method to return different contents for each call.
    mock_requests_get.side_effect = [
        MagicMock(text="example content", raise_for_status=MagicMock()),
        MagicMock(
            text="example content 2",
            raise_for_status=MagicMock(side_effect=RequestException),
        ),
        MagicMock(text="example content 3", raise_for_status=MagicMock()),
        MagicMock(text="example content 4", raise_for_status=MagicMock()),
    ]
    stublist._populate_remote_stub_contents()
    assert len(stublist) == 4  # 3 remotes and 1 local
    assert stublist[0].content == "example content"
    assert stublist[1].content == "example content 3"
    # stublist[2] is the local stub, which should not be modified.
    assert stublist[3].content == "example content 4"


@pytest.mark.parametrize(
    "local_stub_exists",
    [True, False],
    ids=["local_stub_exists", "no_local_stub"],
)
@patch("include_stubs.utils.os.path.join")
@patch("include_stubs.utils.open")
def test_StubList_populate_local_stub_content(
    mock_builtin_open,
    mock_os_path_join,
    local_stub_exists,
    mock_stublist,
):
    """
    Test StubList's _populate_local_stub_content method.
    """
    stublist = mock_stublist()
    mock_builtin_open.side_effect = mock_open(read_data="example content")
    if not local_stub_exists:
        del stublist[3]  # Remove the local stub if it shouldn't exist.
    stublist._populate_local_stub_content()
    if local_stub_exists:
        assert stublist[3].content == "example content"
    else:
        mock_os_path_join.assert_not_called()
        mock_builtin_open.assert_not_called()


@patch("include_stubs.utils.get_html_title")
@patch("include_stubs.utils.get_md_title")
def test_StubList_populate_remote_stub_titles(
    mock_get_md_title, mock_get_html_title, mock_stublist
):
    """
    Test StubList's _populate_remote_stub_titles method.
    """
    stublist = mock_stublist()
    # Set the fname for each remote stub.
    fnames = iter(("some_name.html", "some_other_name.md", ".md", ".html"))
    for i in (0, 1, 2, 4):
        stublist[i].fname = next(fnames)
    stublist._populate_remote_stub_titles()
    assert len(stublist) == 5
    assert stublist[0].title == mock_get_html_title.return_value
    assert stublist[1].title == mock_get_md_title.return_value
    assert stublist[2].title == mock_get_md_title.return_value
    assert stublist[3].title is None  # local stub should not be modified
    assert stublist[4].title == mock_get_html_title.return_value


@pytest.mark.parametrize(
    "fname",
    ["some_name.html", "some_other_name.md"],
    ids=["html_file", "md_file"],
)
@patch("include_stubs.utils.get_html_title")
@patch("include_stubs.utils.get_md_title")
def test_StubList_populate_local_stub_title(
    mock_get_md_title, mock_get_html_title, mock_stublist, fname
):
    """
    Test StubList's _populate_local_stub_title method.
    """
    stublist = mock_stublist()
    # Set the fname for the local stub.
    stublist[3].fname = fname
    stublist._populate_local_stub_title()
    assert len(stublist) == 5
    if fname.endswith(".html"):
        assert stublist[3].title == mock_get_html_title.return_value
    else:
        assert stublist[3].title == mock_get_md_title.return_value
    assert [stublist[i].title for i in (0, 1, 2, 4)] == [
        None
    ] * 4  # remote stubs should not be modified


@patch("include_stubs.utils.make_file_unique")
@patch("include_stubs.utils.StubList._create_stub_file")
def test_StubList_populate_remote_stub_files(
    mock_create_stub_file, mock_make_file_unique, mock_stublist
):
    """
    Test StubList's _populate_remote_stub_files method.
    """
    stublist = mock_stublist()
    stublist._populate_remote_stub_files()
    # Make sure that the make_file_unique function was called once for all remote stubs
    assert mock_create_stub_file.call_count == 4
    # Make sure the number of stubs hasn't changed
    assert len(stublist) == 5
    # Make sure the generated files have been added to the StubList files list
    assert stublist.files[-4:] == [mock_create_stub_file.return_value] * 4
    # Make sure each stub has the correct file assigned
    for i in (0, 1, 2, 4):
        assert stublist[i].file == mock_create_stub_file.return_value
    assert stublist[3].file is None  # Local stub should not be modified


@patch("include_stubs.utils.make_file_unique")
@patch("include_stubs.utils.StubList._create_stub_file")
def test_StubList_populate_local_stub_file(
    mock_create_stub_file, mock_make_file_unique, mock_stublist
):
    """
    Test StubList's _populate_local_stub_file method.
    """
    stublist = mock_stublist()
    stublist._populate_local_stub_file()
    # Make sure that the make_file_unique function was called once
    mock_create_stub_file.assert_called_once()
    # Make sure the number of stubs hasn't changed
    assert len(stublist) == 5
    # Make sure the generated files have been added to the StubList files list
    assert stublist.files[-1] == mock_create_stub_file.return_value
    # Make sure each stub has the correct file assigned
    assert stublist[3].file == mock_create_stub_file.return_value
    assert [stublist[i].file for i in (0, 1, 2, 4)] == [
        None
    ] * 4  # remote stubs should not be modified


@patch("include_stubs.utils.File")
@patch("include_stubs.utils.get_dest_uri_for_local_stub")
def test_StubList_create_stub_file(
    mock_get_dest_uri_for_local_stub, mock_File, mock_stublist
):
    """
    Test StubList's _create_stub_file method.
    """
    stublist = mock_stublist()
    output = stublist._create_stub_file(stublist[0])
    assert output == mock_File.generated.return_value
    mock_get_dest_uri_for_local_stub.assert_not_called()
    output = stublist._create_stub_file(stublist[3])
    assert output == mock_File.return_value
    mock_get_dest_uri_for_local_stub.assert_called_once()


def test_StubList_populate_remote_stub_pages(mock_stublist):
    """
    Test StubList's _populate_remote_stub_pages method.
    """
    stublist = mock_stublist()
    # Set stubs files
    for i in (0, 1, 2, 4):
        stublist[i].file = MagicMock(src_uri=f"ex_uri_{i}")
    # Set some stubs titles
    stublist[1].title = "example title"
    stublist[2].title = "title"
    stublist._populate_remote_stub_pages()
    # Make sure the number of stubs hasn't changed
    assert len(stublist) == 5
    assert stublist[0].page.title == "Ex_uri_0"
    assert stublist[1].page.title == "example title"
    assert stublist[2].page.title == "title"
    assert stublist[3].page is None  # local stub should not be modified
    assert stublist[4].page.title == "Ex_uri_4"


@pytest.mark.parametrize(
    "title",
    ["some title", None],
    ids=["valid_title", "title_None"],
)
def test_StubList_populate_local_stub_page(mock_stublist, title):
    """
    Test StubList's _populate_local_stub_page method.
    """
    stublist = mock_stublist()
    # Set stubs file
    stublist[3].file = MagicMock(src_uri="example_uri")
    # Set a title
    stublist[3].title = title
    stublist._populate_local_stub_page()
    # Make sure the number of stubs hasn't changed
    assert len(stublist) == 5
    for i in (0, 1, 2, 4):
        assert stublist[0].page is None  # remote stubs should not be modified
    if title is None:
        assert stublist[3].page.title == "Example_uri"
    else:
        assert stublist[3].page.title == title


@patch("include_stubs.utils.StubList._populate_remote_stub_fnames")
@patch("include_stubs.utils.StubList._populate_remote_stub_contents")
@patch("include_stubs.utils.StubList._populate_remote_stub_titles")
@patch("include_stubs.utils.StubList._populate_remote_stub_files")
@patch("include_stubs.utils.StubList._populate_remote_stub_pages")
def test_StubList_populate_remote_stubs(
    mock_populate_remote_pages,
    mock_populate_remote_files,
    mock_populate_remote_titles,
    mock_populate_remote_contents,
    mock_populate_remote_fnames,
    mock_stublist,
):
    """
    Test StubList's populate_remote_stubs method.
    """
    stublist = mock_stublist()
    stublist.populate_remote_stubs()
    mock_populate_remote_pages.assert_called_once()
    mock_populate_remote_files.assert_called_once()
    mock_populate_remote_titles.assert_called_once()
    mock_populate_remote_contents.assert_called_once()
    mock_populate_remote_fnames.assert_called_once()


@patch("include_stubs.utils.StubList._populate_local_stub_fname")
@patch("include_stubs.utils.StubList._populate_local_stub_content")
@patch("include_stubs.utils.StubList._populate_local_stub_title")
@patch("include_stubs.utils.StubList._populate_local_stub_file")
@patch("include_stubs.utils.StubList._populate_local_stub_page")
def test_StubList_populate_local_stub(
    mock_populate_local_page,
    mock_populate_local_file,
    mock_populate_local_title,
    mock_populate_local_content,
    mock_populate_local_fname,
    mock_stublist,
):
    """
    Test StubList's populate_local_stub method.
    """
    stublist = mock_stublist()
    stublist.populate_local_stub()
    mock_populate_local_page.assert_called_once()
    mock_populate_local_file.assert_called_once()
    mock_populate_local_title.assert_called_once()
    mock_populate_local_content.assert_called_once()
    mock_populate_local_fname.assert_called_once()

def test_Stub_init_raise():
    """Test Stub initialisation."""
    with pytest.raises(ValueError):
        Stub(is_remote=True)