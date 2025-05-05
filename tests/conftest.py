import pytest
from unittest.mock import MagicMock

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
        filesmock.__contains__.side_effect = lambda: (filesmock._appended.__contains__)
        return filesmock

    return _filesmock
