"""Tests for `plugin.py` module."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from include_stubs.plugin import (
    ENV_VARIABLE_NAME,
    IncludeStubsPlugin,
    logger,
)
from include_stubs.utils import GitRef, Stub


@pytest.fixture(autouse=True)
def silence_logs():
    logger.setLevel(logging.CRITICAL)


@pytest.fixture
def create_plugin(mock_plugin_config):
    """Factory function to create the plugin with the prescribed configuration options."""

    def _plugin(
        config=mock_plugin_config,
        repo="owner/repo",
        stubs_nav_path="",
        _cached_stubs=None,
    ):
        plugin = IncludeStubsPlugin()
        IncludeStubsPlugin._cached_stubs = _cached_stubs
        IncludeStubsPlugin.repo = repo
        plugin.load_config(config)
        plugin.stubs_nav_path = stubs_nav_path
        return plugin

    return _plugin


@pytest.mark.parametrize(
    "repo",
    ["some/repo", None],
    ids=[
        "repo_set",
        "repo_None",
    ],
)
@patch("include_stubs.plugin.get_repo_from_input")
def test_on_config(
    mock_get_repo,
    create_plugin,
    create_mock_mkdocs_config,
    repo,
):
    """Test the on_config method of the plugin."""
    plugin = create_plugin(repo=repo)
    plugin.on_config(create_mock_mkdocs_config())
    # Check that the attributes are set correctly
    if repo is None:
        assert plugin.repo == mock_get_repo.return_value
    else:
        assert plugin.repo == repo
        mock_get_repo.assert_not_called()


@pytest.mark.parametrize(
    "is_main_website_build",
    [True, False],
    ids=["main_website_build", "preview_website_build"],
)
@pytest.mark.parametrize(
    "no_main",
    [True, False],
    ids=["no_main_true", "no_main_false"],
)
@pytest.mark.parametrize(
    "main_pattern",
    ["non_empty", ""],
    ids=["main_pattern_non_empty", "main_pattern_empty"],
)
@pytest.mark.parametrize(
    "preview_pattern",
    ["non_empty", ""],
    ids=["preview_pattern_non_empty", "preview_pattern_empty"],
)
@patch("include_stubs.plugin.get_git_refs")
@patch("include_stubs.plugin.is_main_website")
def test_get_git_refs_for_website(
    mock_is_main,
    mock_get_git_refs,
    create_plugin,
    is_main_website_build,
    no_main,
    main_pattern,
    preview_pattern,
):
    """Test the get_git_refs_for_website method for the main website."""
    plugin = create_plugin()
    plugin.config["preview_website"]["no_main"] = no_main
    plugin.config["main_website"]["pattern"] = main_pattern
    plugin.config["preview_website"]["pattern"] = preview_pattern
    mock_is_main.return_value = is_main_website_build
    mock_get_git_refs.return_value = [
        GitRef(sha="123", name="ref1"),
        GitRef(sha="456", name="ref2"),
        GitRef(sha="123", name="ref4"),
        GitRef(sha="231", name="ref1"),
    ]
    refs = plugin.get_git_refs_for_website()
    if (
        not is_main_website_build  # build is for a preview website
        and not no_main  # main website included
        and main_pattern  # non-empty main_pattern
        and preview_pattern  # non-empty preview_pattern
    ):  # mock_get_refs should be called twice if the build is for a preview website, with main website included and both patterns non-empty.
        assert mock_get_git_refs.call_count == 2
        # First call for preview website
        first_call_args = mock_get_git_refs.call_args_list[0]
        assert first_call_args[0] == (plugin.repo,)  # args
        assert first_call_args[1] == {
            "pattern": plugin.config["preview_website"]["pattern"],
            "ref_type": plugin.config["preview_website"]["ref_type"],
        }  # kwargs
        # Second call for main website
        second_call_args = mock_get_git_refs.call_args_list[1]
        assert second_call_args[0] == (plugin.repo,)  # args
        assert second_call_args[1] == {
            "pattern": plugin.config["main_website"]["pattern"],
            "ref_type": plugin.config["main_website"]["ref_type"],
        }  # kwargs
    elif (
        (
            is_main_website_build and main_pattern
        )  # build for main website with non-empty main pattern
        or (
            not is_main_website_build
            and not no_main
            and not preview_pattern
            and main_pattern
        )  # build for preview website with main website, with empty preview pattern and non-empty main pattern
    ):
        mock_get_git_refs.assert_called_once_with(
            plugin.repo,
            pattern=plugin.config["main_website"]["pattern"],
            ref_type=plugin.config["main_website"]["ref_type"],
        )
    elif (
        (
            not is_main_website_build and no_main and preview_pattern
        )  # build for preview website without main website, with non-empty preview pattern
        or (
            not is_main_website_build
            and not no_main
            and preview_pattern
            and not main_pattern
        )  # build for preview website with main website, with non-empty preview pattern and empty main pattern
    ):
        mock_get_git_refs.assert_called_once_with(
            plugin.repo,
            pattern=plugin.config["preview_website"]["pattern"],
            ref_type=plugin.config["preview_website"]["ref_type"],
        )
    else:
        mock_get_git_refs.assert_not_called()
    if (
        (
            not main_pattern and not preview_pattern
        )  # Main and preview patterns are empty
        or (
            not main_pattern and is_main_website_build
        )  # Main website build and main pattern is empty
        or (
            not preview_pattern and not is_main_website_build and no_main
        )  # Preview website build without main and preview pattern is empty
    ):
        assert refs == []
    else:
        assert refs == [
            GitRef(sha="123", name="ref1"),
            GitRef(sha="456", name="ref2"),
            GitRef(sha="231", name="ref1"),
        ]


@pytest.mark.parametrize(
    "env_variable_value",
    ["1", ""],
    ids=[
        "local_stub_present",
        "local_stub_not_present",
    ],
)
@pytest.mark.parametrize(
    "cached_stubs",
    [True, False],
    ids=[
        "cached_stubs_set",
        "no_cached_stubs",
    ],
)
@patch("include_stubs.plugin.IncludeStubsPlugin.get_git_refs_for_website")
@patch("include_stubs.plugin.StubList")
def test_on_files(
    mock_Stublist,
    mock_get_git_refs_for_website,
    env_variable_value,
    cached_stubs,
    create_plugin,
    mock_files,
    create_mock_mkdocs_config,
    monkeypatch,
    mock_stublist,
):
    """Test the on_files method."""
    # Create a list of original files
    original_files = mock_files([MagicMock()] * 3)
    # Create a list of mocked files
    files = [MagicMock()] * 4
    # Create a mock StubList instance
    stublist = mock_stublist(
        stubs=[Stub(gitref=MagicMock(), file=f, page=MagicMock()) for f in files]
    )
    stublist[2].is_remote = False  # Make one stub a local stub
    stublist.populate_remote_stubs = MagicMock()
    stublist.populate_local_stub = MagicMock()
    stublist.append_or_replace = MagicMock()
    # Create a mock cached StubList instance
    cached_stublist = mock_stublist(
        stubs=[Stub(gitref=MagicMock(), file=f, page=MagicMock()) for f in files[:-1]]
    )
    cached_stublist[1].is_remote = False  # Make one stub a local stub
    cached_stublist.populate_remote_stubs = MagicMock()
    cached_stublist.populate_local_stub = MagicMock()
    cached_stublist.append_or_replace = MagicMock()
    # Set the ENV variable
    monkeypatch.setenv(ENV_VARIABLE_NAME, env_variable_value)
    # Set the return values of the mocks
    mock_Stublist.return_value = stublist
    mock_get_git_refs_for_website.return_value = [MagicMock()] * 2
    # Create a mock plugin
    plugin = create_plugin(
        _cached_stubs=cached_stublist if cached_stubs else None,
    )
    # Run the on_files method
    plugin.on_files(original_files, create_mock_mkdocs_config())
    # Assertions
    cached_stublist.populate_remote_stubs.assert_not_called()
    if cached_stubs:
        assert original_files[3:] == files[:-1]
        stublist.populate_remote_stubs.assert_not_called()
    else:
        assert original_files[3:] == files
        stublist.populate_remote_stubs.assert_called_once()
    mocked_instance = stublist if not cached_stubs else cached_stublist
    if env_variable_value:
        mocked_instance.append_or_replace.assert_called_once()
        mocked_instance.populate_local_stub.assert_called_once()
    else:
        mocked_instance.append_or_replace.assert_not_called()
        mocked_instance.populate_local_stub.assert_not_called()
    assert len(original_files) == 3 + len(mocked_instance)


@pytest.mark.parametrize(
    "stubs_nav_path",
    ["Root > Example > Path", "Root>Example>Path", "", "    "],
    ids=["space_path", "no_space_path", "empty_path", "blank_path"],
)
@patch("include_stubs.plugin.set_stubs_nav_path")
def test_on_nav(
    mock_set_stubs_nav_path,
    mock_files,
    create_plugin,
    create_mock_mkdocs_config,
    mock_navigation,
    stubs_nav_path,
):
    """Test the on_nav method."""
    mock_set_stubs_nav_path.return_value = stubs_nav_path
    # Create a mock plugin
    files = mock_files()
    pages = [
        MagicMock(title="B"),
        MagicMock(title="A"),
        MagicMock(title="C"),
    ]
    plugin = create_plugin(
        stubs_nav_path=stubs_nav_path,
        _cached_stubs=[
            Stub(
                gitref="some_ref",
                fname="key1",
                content="value1",
                title="B",
                page=pages[0],
            ),
            Stub(
                gitref="some_ref2",
                fname="key2",
                content="value2",
                title="A",
                page=pages[1],
            ),
            Stub(
                gitref="some_ref3",
                fname="key3",
                content="value3",
                title="C",
                page=pages[2],
            ),
        ],
    )
    plugin.get_git_refs_for_website = MagicMock(return_value={"ref1", "ref2"})
    # Create a mock nav object
    nav = mock_navigation
    # Call the on_nav method
    plugin.on_nav(nav, create_mock_mkdocs_config(), files)
    # Check that the correct sections/pages were added to the nav
    if stubs_nav_path.strip():
        assert len(nav.items) == 1
        assert (nav.items[0].title) == "Root"
        assert len(nav.items[0].children) == 3
        assert nav.items[0].children[2].title == "Example"
        assert len(nav.items[0].children[2].children) == 1
        assert nav.items[0].children[2].children[0].title == "Path"
        assert nav.items[0].children[2].children[0].children == [
            pages[1],
            pages[0],
            pages[2],
        ]
        for page in pages:
            assert page.parent == nav.items[0].children[2].children[0]
    else:
        assert len(nav.items) == 4
        assert (nav.items[0].title) == "Root"
        assert nav.items[1:] == [
            pages[1],
            pages[0],
            pages[2],
        ]
        assert len(nav.items[0].children) == 2


@pytest.mark.parametrize(
    "stubs, watch_called",
    [
        ([Stub(is_remote=False)], True),
        ([Stub(gitref=MagicMock())], False),
    ],
    ids=[
        "valid_local_stub",
        "no_local_stub",
    ],
)
def test_on_serve(
    create_plugin, create_mock_mkdocs_config, mock_stublist, stubs, watch_called
):
    """Test the on_serve method."""
    plugin = create_plugin(_cached_stubs=mock_stublist(stubs=stubs))
    plugin._cached_stubs[0].file = MagicMock()
    plugin._cached_stubs[0].file.abs_src_path = "local/stub/abs/path"
    server = MagicMock()
    builder = MagicMock()
    plugin.on_serve(server, create_mock_mkdocs_config(), builder)
    # Check that the on_serve method was called with the correct arguments
    if watch_called:
        server.watch.assert_called_once_with("local/stub/abs/path", builder)
    else:
        server.watch.assert_not_called()
