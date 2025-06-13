"""Tests for `plugin.py` module."""

from unittest.mock import MagicMock, patch

import pytest
import logging

from include_configuration_stubs.plugin import IncludeConfigurationStubsPlugin, logger
from include_configuration_stubs.utils import ConfigStub

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


@patch("include_configuration_stubs.plugin.get_git_refs")
@patch("include_configuration_stubs.plugin.is_main_website")
def test_get_git_refs_for_wesbsite_main(mock_is_main, mock_get_refs, create_plugin):
    """Test the get_git_refs_for_wesbsite method for the main website."""
    plugin = create_plugin(repo="some_repo")
    mock_is_main.return_value = True
    mock_get_refs.return_value = ["ref1", "ref2", "ref1"]

    refs = plugin.get_git_refs_for_wesbsite()

    # Should only call once, for main website
    mock_get_refs.assert_called_once_with(
        plugin.repo,
        pattern=plugin.config["main_website"]["pattern"],
        ref_type=plugin.config["main_website"]["ref_type"],
    )
    assert refs == {"ref1", "ref2"}


@patch("include_configuration_stubs.plugin.get_git_refs")
@patch("include_configuration_stubs.plugin.is_main_website")
def test_get_git_refs_for_wesbsite_preview_no_main_true(
    mock_is_main, mock_get_refs, create_plugin
):
    """Test the get_git_refs_for_wesbsite method for the preview website when preview_website.no_main is True."""
    plugin = create_plugin(repo="some_repo")
    mock_is_main.return_value = False
    plugin.config["preview_website"]["no_main"] = True
    mock_get_refs.return_value = ["ref1", "ref2", "ref1"]

    refs = plugin.get_git_refs_for_wesbsite()

    # Should only call once, for preview website
    mock_get_refs.assert_called_once_with(
        plugin.repo,
        pattern=plugin.config["preview_website"]["pattern"],
        ref_type=plugin.config["preview_website"]["ref_type"],
    )
    assert refs == {"ref1", "ref2"}


@patch("include_configuration_stubs.plugin.get_git_refs")
@patch("include_configuration_stubs.plugin.is_main_website")
def test_get_git_refs_for_wesbsite_preview_no_main_false(
    mock_is_main, mock_get_refs, create_plugin
):
    """Test the get_git_refs_for_wesbsite method for the preview website when preview_website.no_main is False."""
    plugin = create_plugin(repo="some_repo")
    mock_is_main.return_value = False
    plugin.config["preview_website"]["no_main"] = False
    mock_get_refs.return_value = ["ref1", "ref2", "ref1"]

    refs = plugin.get_git_refs_for_wesbsite()

    # Should call twice, first for preview website and then for main website
    assert mock_get_refs.call_count == 2
    first_call_args, first_call_kwargs = mock_get_refs.call_args_list[0]
    second_call_args, second_call_kwargs = mock_get_refs.call_args_list[1]

    assert first_call_args == (plugin.repo,)
    assert first_call_kwargs == {
        "pattern": plugin.config["preview_website"]["pattern"],
        "ref_type": plugin.config["preview_website"]["ref_type"],
    }
    assert second_call_args == (plugin.repo,)
    assert second_call_kwargs == {
        "pattern": plugin.config["main_website"]["pattern"],
        "ref_type": plugin.config["main_website"]["ref_type"],
    }
    # Duplicates removed
    assert refs == {"ref1", "ref2"}


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
@patch("include_configuration_stubs.plugin.get_config_stub")
def test_add_remote_stub_to_site(
    mock_get_config_stub,
    config_stub_output,
    create_plugin,
    mock_files,
    create_mock_mkdocs_config,
):
    """Test the add_remote_stub_to_site method."""
    files = mock_files([MagicMock()])
    plugin = create_plugin(repo="example_repo")
    plugin.pages = [MagicMock(), MagicMock()]
    mock_get_config_stub.return_value = config_stub_output
    mock_mkdocs_config = create_mock_mkdocs_config(site_dir="site/dir")
    plugin.add_remote_stub_to_site(
        config=mock_mkdocs_config,
        stubs_dir="some/dir",
        ref="some_ref",
        stubs_parent_url="parent/url",
        files=files,
    )
    expected_len = 1 if config_stub_output is None else 2
    # Check that the config stubs were added to the files
    assert len(files) == expected_len
    # Check that the config stub page were added to the pages
    assert len(plugin.pages) == expected_len + 1
    if config_stub_output:
        # Check correctness of config stubs
        assert files[1].src_uri == config_stub_output.fname
        assert files[1]._content == config_stub_output.content
        assert files[1].dest_dir == "site/dir"
        # Check correctness of pages
        assert plugin.pages[2].file == files[1]
        assert plugin.pages[2].title == config_stub_output.title


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
@patch("include_configuration_stubs.plugin.get_config_stub")
@patch("include_configuration_stubs.plugin.get_dest_uri_for_local_stub")
@patch("include_configuration_stubs.plugin.os.path.abspath")
def test_add_local_stub_to_site(
    mock_abspath,
    mock_get_dest_uri_for_local_stub,
    mock_get_config_stub,
    config_stub_output,
    create_plugin,
    mock_files,
    create_mock_mkdocs_config,
):
    """Test the add_local_stub_to_site method."""
    files = mock_files([MagicMock()])
    plugin = create_plugin(repo="example_repo")
    plugin.pages = [MagicMock(), MagicMock()]
    mock_get_config_stub.return_value = config_stub_output
    mock_get_dest_uri_for_local_stub.return_value = "dest/uri"
    mock_mkdocs_config = create_mock_mkdocs_config(site_dir="site/dir")
    mock_abspath.return_value = "stub/file/abs/path"
    plugin.add_local_stub_to_site(
        config=mock_mkdocs_config,
        stubs_dir="some/dir",
        stubs_parent_url="parent/url",
        files=files,
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
        # Check correctness of pages
        assert plugin.pages[2].file == files[1]
        assert plugin.pages[2].title == config_stub_output.title
        # Check that the local stub absolute path is set correctly
        assert plugin.local_stub_abs_path == "stub/file/abs/path/key" 
    else:
        assert plugin.local_stub_abs_path is None

def test_on_files(
    create_plugin,
    mock_files,
    create_mock_mkdocs_config,
):
    """Test the on_files method."""
    files = mock_files()
    plugin = create_plugin(repo="example_repo")
    plugin.get_git_refs_for_wesbsite = MagicMock(return_value={"ref1", "ref2"})
    plugin.add_remote_stub_to_site = MagicMock()
    plugin.add_local_stub_to_site = MagicMock()
    plugin.on_files(files, create_mock_mkdocs_config())
    assert plugin.add_remote_stub_to_site.call_count == 2
    plugin.add_local_stub_to_site.assert_called_once()
    


@patch("include_configuration_stubs.plugin.set_stubs_nav_path")
def test_on_nav(mock_set_stubs_nav_path, mock_files, create_plugin, create_mock_mkdocs_config, mock_section):
    """Test the on_nav method."""
    mock_set_stubs_nav_path.return_value = "Root/Example/Path"
    # Create a mock plugin
    files = mock_files()
    plugin = create_plugin(repo="example_repo")
    plugin.get_git_refs_for_wesbsite = MagicMock(return_value={"ref1", "ref2"})
    pages = [
        MagicMock(title = "B"),
        MagicMock(title = "A"),
        MagicMock(title = "C"),
    ]
    plugin.pages = pages
    # Create a mock nav object
    nav = MagicMock()
    nav.items = [mock_section]
    # Call the on_nav method
    plugin.on_nav(nav, create_mock_mkdocs_config(), files)
    # Check that the correct sections/pages were added to the nav
    assert len(nav.items) == 1
    assert (nav.items[0].title) == "Root"
    assert len(nav.items[0].children) == 3
    assert nav.items[0].children[2].title == "Example"
    assert len(nav.items[0].children[2].children) == 1
    assert nav.items[0].children[2].children[0].title == "Path"
    assert nav.items[0].children[2].children[0].children == [pages[1], pages[0], pages[2]]
    for page in pages:
        assert page.parent == nav.items[0].children[2].children[0]


@pytest.mark.parametrize(
    "local_stub_abs_path",
    ["some/abs/path", None],
    ids=[
        "valid_local_path",
        "none_local_path",
    ],
)
def test_on_serve(create_plugin, create_mock_mkdocs_config, local_stub_abs_path):
    """Test the on_serve method."""
    plugin = create_plugin(repo="example_repo", local_stub_abs_path=local_stub_abs_path)
    server = MagicMock()
    builder = MagicMock()
    plugin.on_serve(server, create_mock_mkdocs_config(), builder)
    # Check that the on_serve method was called
    if local_stub_abs_path:
        server.watch.assert_called_once_with(
            local_stub_abs_path, builder
        )
    else:
        server.watch.assert_not_called()