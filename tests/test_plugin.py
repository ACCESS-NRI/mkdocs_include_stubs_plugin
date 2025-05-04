"""Tests for `plugin.py` module."""

from unittest.mock import MagicMock, patch

import pytest

from include_configuration_stubs.plugin import IncludeConfigurationStubsPlugin


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
        "supported_file_formats": [".md", ".extension"],
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


@pytest.fixture
def mock_file():
    """Mock file object."""
    filemock = MagicMock()
    filemock.generated.return_value = MagicMock()
    return filemock

@pytest.fixture
def mock_files():
    """Factory function to create the Files object."""

    def _filesmock():
        filesmock = MagicMock()
        filesmock._appended = []
        filesmock.append.side_effect = filesmock._appended.append
        filesmock.__len__.side_effect = lambda: len(filesmock._appended)
        filesmock.__iter__.side_effect = lambda: iter(filesmock._appended)
        return filesmock

    return _filesmock


def test_on_config(create_plugin, mock_plugin_config):
    """Test the on_config method of the plugin."""
    plugin = create_plugin()
    with patch(
        "include_configuration_stubs.plugin.get_repo_from_input"
    ) as mock_get_repo:
        output_repo = "example_output_repo"
        mock_get_repo.return_value = output_repo
        plugin.on_config(mock_plugin_config)
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
    "config_stub_output, expected_len",
    [
        ({"key": "value"}, 3), # valid_config_stub
        (None, 0), # None_config_stub
    ],
    ids= [
        "valid_config_stub", 
        "None_config_stub",
    ],
)
@patch("include_configuration_stubs.plugin.get_config_stub")
@patch("include_configuration_stubs.plugin.get_supported_file_formats")
@patch("include_configuration_stubs.plugin.File.generated")
def test_on_files_adds_stub_file(
    mock_File_generated,
    mock_get_supported_file_formats,
    mock_get_config_stub,
    config_stub_output,
    expected_len,
    create_plugin,
    mock_file,
    mock_files,
):
    """Test the on_files method."""
    mkdocs_config = MagicMock()
    mock_File_generated.return_value = mock_file
    files = mock_files()  # Empty list of files
    plugin = create_plugin(repo="example_repo")
    plugin.get_git_refs_for_wesbsite = MagicMock(return_value={"ref1", "ref2", "ref3"})
    mock_get_config_stub.return_value = config_stub_output
    result_files = plugin.on_files(files, mkdocs_config)

    assert len(result_files) == expected_len
    if config_stub_output is not None:
        for rf in result_files:
            assert rf.dest_path.startswith("parent/url/") 