from unittest.mock import MagicMock

import pytest
from mkdocs.structure.nav import Section, Navigation
from mkdocs.structure.pages import Page



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
def mock_mkdocs_config():
    mkdocs_config = MagicMock()
    mkdocs_config.get.return_value = None
    return mkdocs_config


@pytest.fixture
def mock_section(mock_mkdocs_config):
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