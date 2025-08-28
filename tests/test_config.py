import pytest

from include_stubs.config import (
    set_default_stubs_nav_path,
    GitRefType,
)

@pytest.mark.parametrize(
    "stubs_parent_url, expected_output",
    [
        ("configurations", "Configurations"),  # single_segment
        ("", ""),  # empty_string
        ("my/example/path", "My > Example > Path"),  # multiple_segments
        (
            "path_with/under_scores",
            "Path with > Under scores",
        ),  # underscores
        (
            "example /  path /with  spaces",
            "Example > Path > With  spaces",
        ),  # spaces
        (
            "path_with/ spaces _ and_/under_scores ",
            "Path with > Spaces   and > Under scores",
        ),  # mixed
        ("path/", "Path"),  # final_slash
        ("/path", "Path"),  # initial_slash
    ],
    ids=[
        "single_segment",
        "empty_string",
        "multiple_segments",
        "underscores",
        "spaces",
        "mixed",
        "final_slash",
        "initial_slash",
    ],
)
def test_set_default_stubs_nav_path(stubs_parent_url, expected_output):
    """Test the set_default_stubs_nav_path function."""
    assert set_default_stubs_nav_path(stubs_parent_url) == expected_output

@pytest.mark.parametrize(
    "enum, expected_value, expected_repr",
    [
        ("BRANCH", "branch", "branches"), # BRANCH
        ("TAG", "tag", "tags"), # TAG
        ("ALL", "all", "branches and tags"), # ALL
    ],
    ids=[
        "BRANCH",
        "TAG",
        "ALL",
    ],
)
def test_git_ref_type(enum, expected_value, expected_repr):
    """Test the GitRefType enum."""
    _enum = getattr(GitRefType, enum)
    assert str(_enum) == expected_repr
    assert _enum.value == expected_value