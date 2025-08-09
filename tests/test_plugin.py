"""Tests for `plugin.py` module."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from include_configuration_stubs.plugin import (
    ENV_VARIABLE_NAME,
    IncludeConfigurationStubsPlugin,
    logger,
)
from include_configuration_stubs.utils import ConfigStub, GitRef


@pytest.fixture(autouse=True)
def silence_logs():
    logger.setLevel(logging.CRITICAL)


@pytest.fixture
def mock_plugin_config():
    return {
        "repo": "some_repo",
        "main_website": {
            "pattern": "some_pattern",
            "ref_type": "branch",
            "branch": "some_branch",
        },
        "preview_website": {
            "pattern": "preview/*",
            "ref_type": "tag",
            "no_main": False,
        },
        "stubs_dir": "stubs_dir",
        "stubs_parent_url": "parent/url/",
    }


@pytest.fixture
def create_plugin(mock_plugin_config):
    """Factory function to create the plugin with the prescribed configuration options."""

    def _plugin(config=mock_plugin_config, **kwargs):
        plugin = IncludeConfigurationStubsPlugin()
        plugin.load_config(config)
        for key, value in kwargs.items():
            setattr(plugin, key, value)
        return plugin

    return _plugin


def test_on_config(create_plugin, create_mock_mkdocs_config):
    """Test the on_config method of the plugin."""
    plugin = create_plugin()
    with patch(
        "include_configuration_stubs.plugin.get_repo_from_input"
    ) as mock_get_repo:
        output_repo = "example_output_repo"
        mock_get_repo.return_value = output_repo
        plugin.on_config(create_mock_mkdocs_config())
        # Check that the repo is set correctly
        assert plugin.repo == output_repo


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
@patch("include_configuration_stubs.plugin.get_git_refs")
@patch("include_configuration_stubs.plugin.is_main_website")
def test_get_git_refs_for_website(
    mock_is_main, mock_get_refs, create_plugin, is_main_website_build, no_main, main_pattern, preview_pattern
):
    """Test the get_git_refs_for_website method for the main website."""
    plugin = create_plugin(repo="some_repo")
    plugin.config["preview_website"]["no_main"] = no_main
    plugin.config["main_website"]["pattern"] = main_pattern
    plugin.config["preview_website"]["pattern"] = preview_pattern
    mock_is_main.return_value = is_main_website_build
    mock_get_refs.return_value = [
        GitRef(sha="123", name="ref1"),
        GitRef(sha="456", name="ref2"),
        GitRef(sha="123", name="ref4"),
        GitRef(sha="231", name="ref1"),
    ]
    refs = plugin.get_git_refs_for_website()
    if (
        not is_main_website_build # build is for a preview website
        and not no_main # main website included
        and main_pattern # non-empty main_pattern
        and preview_pattern # non-empty preview_pattern
    ):  # mock_get_refs should be called twice if the build is for a preview website, with main website included and both patterns non-empty.
        assert mock_get_refs.call_count == 2
        # First call for preview website
        first_call_args = mock_get_refs.call_args_list[0]
        assert first_call_args[0] == (plugin.repo,) #args
        assert first_call_args[1] == {
            "pattern": plugin.config["preview_website"]["pattern"],
            "ref_type": plugin.config["preview_website"]["ref_type"],
        } #kwargs
        # Second call for main website
        second_call_args = mock_get_refs.call_args_list[1]
        assert second_call_args[0] == (plugin.repo,) #args
        assert second_call_args[1] == {
            "pattern": plugin.config["main_website"]["pattern"],
            "ref_type": plugin.config["main_website"]["ref_type"],
        } #kwargs
    elif (
        (is_main_website_build and main_pattern) # build for main website with non-empty main pattern
        or (not is_main_website_build and not no_main and not preview_pattern and main_pattern) # build for preview website with main website, with empty preview pattern and non-empty main pattern
    ):
        mock_get_refs.assert_called_once_with(
            plugin.repo,
            pattern=plugin.config["main_website"]["pattern"],
            ref_type=plugin.config["main_website"]["ref_type"],
        )
    elif (
        (not is_main_website_build and no_main and preview_pattern) # build for preview website without main website, with non-empty preview pattern
        or (not is_main_website_build and not no_main and preview_pattern and not main_pattern) # build for preview website with main website, with non-empty preview pattern and empty main pattern
    ):
        mock_get_refs.assert_called_once_with(
            plugin.repo,
            pattern=plugin.config["preview_website"]["pattern"],
            ref_type=plugin.config["preview_website"]["ref_type"],
        )
    else:
        mock_get_refs.assert_not_called()
    if (
        (not main_pattern and not preview_pattern) # Main and preview patterns are empty
        or (not main_pattern and is_main_website_build) # Main website build and main pattern is empty
        or (not preview_pattern and not is_main_website_build and no_main) # Preview website build without main and preview pattern is empty
    ):
        assert refs == []
    else:
        assert refs == [
            GitRef(sha="123", name="ref1"),
            GitRef(sha="456", name="ref2"),
            GitRef(sha="231", name="ref1"),
        ]


@pytest.mark.parametrize(
    "config_stub_output",
    [
        ConfigStub(fname="key", content="value", title="title"),  # valid_config_stub
        None,  # None_config_stub
    ],
    ids=[
        "valid_config_stub",
        "None_config_stub",
    ],
)
@pytest.mark.parametrize(
    "is_remote_stub",
    [
        True,  # remote
        False,  # local
    ],
    ids=[
        "remote",
        "local",
    ],
)
@patch("include_configuration_stubs.plugin.get_config_stub")
@patch("include_configuration_stubs.plugin.get_dest_uri_for_local_stub")
@patch("include_configuration_stubs.plugin.os.path.abspath")
def test_add_stub_to_site(
    mock_abspath,
    mock_get_dest_uri_for_local_stub,
    mock_get_config_stub,
    config_stub_output,
    is_remote_stub,
    create_plugin,
    mock_files,
    create_mock_mkdocs_config,
):
    """Test the add_stub_to_site method."""
    files = mock_files([MagicMock()])
    plugin = create_plugin(repo="example_repo")
    plugin.pages = [MagicMock(), MagicMock()]
    mock_get_config_stub.return_value = config_stub_output
    mock_get_dest_uri_for_local_stub.return_value = "dest/uri"
    mock_mkdocs_config = create_mock_mkdocs_config(site_dir="site/dir")
    mock_abspath.return_value = "stub/file/abs/path"
    plugin.add_stub_to_site(
        config=mock_mkdocs_config,
        stubs_dir="some/dir",
        ref="some_ref",
        stubs_parent_url="parent/url",
        files=files,
        is_remote_stub=is_remote_stub,
    )
    expected_len = 1 if config_stub_output is None else 2
    # Check that the config stubs were added to the files
    assert len(files) == expected_len
    # Check that the config stub page were added to the pages
    assert len(plugin.pages) == expected_len + 1
    if config_stub_output:
        # Check correctness of config stubs
        assert files[1].src_uri == config_stub_output.fname
        assert files[1].dest_dir == "site/dir"
        if is_remote_stub:  # Check content only for remote stubs
            assert files[1]._content == config_stub_output.content
        # Check correctness of pages
        assert plugin.pages[2].file == files[1]
        assert plugin.pages[2].title == config_stub_output.title
        # Check that the local stub absolute path is set correctly
        if not is_remote_stub:
            assert plugin.local_stub_abs_path == "stub/file/abs/path/key"


@pytest.mark.parametrize(
    "env_variable_value",
    ["1", ""],
    ids=[
        "env_variable_set",
        "no_env_variable",
    ],
)
def test_on_files(
    create_plugin,
    mock_files,
    create_mock_mkdocs_config,
    env_variable_value,
    monkeypatch,
):
    """Test the on_files method."""
    files = mock_files()
    plugin = create_plugin(repo="example_repo")
    plugin.get_git_refs_for_website = MagicMock(return_value={"ref1", "ref2"})
    plugin.add_stub_to_site = MagicMock()
    monkeypatch.setenv(ENV_VARIABLE_NAME, env_variable_value)
    plugin.on_files(files, create_mock_mkdocs_config())
    if env_variable_value:
        assert plugin.add_stub_to_site.call_count == 3
    else:
        assert plugin.add_stub_to_site.call_count == 2


@pytest.mark.parametrize(
    "stubs_nav_path",
    ["Root > Example > Path", "Root>Example>Path", "", "    "],
    ids=["space_path","no_space_path", "empty_path", "blank_path"],
)
@patch("include_configuration_stubs.plugin.set_stubs_nav_path")
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
    plugin = create_plugin(repo="example_repo")
    plugin.get_git_refs_for_website = MagicMock(return_value={"ref1", "ref2"})
    pages = [
        MagicMock(title="B"),
        MagicMock(title="A"),
        MagicMock(title="C"),
    ]
    plugin.pages = pages
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
    "has_local_stub_abs_path",
    [True, False],
    ids=[
        "valid_local_path",
        "no_local_path",
    ],
)
def test_on_serve(create_plugin, create_mock_mkdocs_config, has_local_stub_abs_path):
    """Test the on_serve method."""
    plugin = create_plugin(repo="example_repo")
    if has_local_stub_abs_path:
        plugin.local_stub_abs_path = "local/stub/abs/path"
    server = MagicMock()
    builder = MagicMock()
    plugin.on_serve(server, create_mock_mkdocs_config(), builder)
    # Check that the on_serve method was called
    if has_local_stub_abs_path:
        server.watch.assert_called_once_with("local/stub/abs/path", builder)
    else:
        server.watch.assert_not_called()
