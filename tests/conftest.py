from unittest.mock import MagicMock

import pytest
from mkdocs.structure.nav import Navigation, Section
from mkdocs.structure.pages import Page
from include_stubs.utils import StubList, Stub, GitRef

@pytest.fixture
def mock_files():
    """Factory function to create the Files object."""

    def _filesmock(files=None):
        filesmock = MagicMock()
        filesmock._appended = files or []
        filesmock.append.side_effect = filesmock._appended.append
        filesmock.extend.side_effect = filesmock._appended.extend
        filesmock.__len__.side_effect = lambda: len(filesmock._appended)
        filesmock.__iter__.side_effect = lambda: iter(filesmock._appended)
        filesmock.__contains__.side_effect = lambda: filesmock._appended.__contains__
        filesmock.__getitem__.side_effect = (
            lambda *args, **kwargs: filesmock._appended.__getitem__(*args, **kwargs)
        )
        return filesmock

    return _filesmock


@pytest.fixture
def create_mock_mkdocs_config():
    """Factory function to create a mock MkDocs config."""
    def _config(**kwargs):
        mock_mkdocs_config = MagicMock(**kwargs)
        mock_mkdocs_config.__getitem__.side_effect = lambda key, default=None: kwargs.get(key, default)
        mock_mkdocs_config.get.side_effect = lambda key, default=None: kwargs.get(key, default)
        return mock_mkdocs_config
    return _config


@pytest.fixture
def mock_section(create_mock_mkdocs_config):
    mock_mkdocs_config = create_mock_mkdocs_config()
    return Section(
        title="Root",
        children=[
            Page(title="Page1", file=MagicMock(), config=mock_mkdocs_config),
            Section(
                title="Subsection",
                children=[
                    Page(title="Page2", file=MagicMock(), config=mock_mkdocs_config),
                ],
            ),
        ],
    )


@pytest.fixture
def mock_navigation(mock_section):
    navigation = MagicMock(spec=Navigation)
    navigation.items = [mock_section]
    return navigation

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
def mock_stublist(mock_files, create_mock_mkdocs_config):
    """Factory function to create a StubList instance with mock parameters."""

    def _remotestubs(
        stubs = None,
        config = None,
        files = None,
    ):
        if stubs is None:
            stubs = [
                Stub(gitref=GitRef(name="main", sha="abc123")),
                Stub(gitref=GitRef(name="dev", sha="def456")),
                Stub(gitref=GitRef(name="other", sha="123456")),
                Stub(is_remote=False),
                Stub(gitref=GitRef(name="other2", sha="345678")),
            ]
        if files is None:
            files = mock_files(
                [
                    MagicMock(),
                    MagicMock(),
                    MagicMock(),
                ]
            )
        if config is None:
            config = create_mock_mkdocs_config()
        return StubList(
            stubs=stubs,
            mkdocs_config=config,
            files=files,
            repo="example/repo",
            stubs_dir="stub/path",
            stubs_parent_url="parent/url",
            supported_file_formats=(".ext1", ".ext2"),
        )

    return _remotestubs