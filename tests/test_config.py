import pytest

from include_configuration_stubs.config import (
    get_supported_file_formats,
    set_default_stubs_nav_path,
)


@pytest.mark.parametrize(
    "input_formats, expected_output",
    [
        (["extension"], ("extension",)),  # single_item_list
        (
            [".md", ".html"],
            (
                ".md",
                ".html",
            ),
        ),  # multiple_items_list
        (".string", (".string",)),  # string
    ],
    ids=[
        "single_item_list",
        "multiple_items_list",
        "string",
    ],
)
def test_get_supported_file_formats(input_formats, expected_output):
    """Test the get_supported_file_formats function."""
    assert get_supported_file_formats(input_formats) == expected_output


@pytest.mark.parametrize(
    "stubs_parent_url, expected_output",
    [
        ("configurations", "Configurations"),  # single_segment
        ("", ""),  # empty_string
        ("my/example/path", "My/Example/Path"),  # multiple_segments
        (
            "path_with/under_scores",
            "Path with/Under scores",
        ),  # underscores
        (
            "example /  path /with  spaces",
            "Example/Path/With  spaces",
        ),  # spaces
        ("path/", "Path"),  # final_slash
        (
            "path_with/ spaces _ and_/under_scores ",
            "Path with/Spaces   and /Under scores",
        ),  # mixed
    ],
    ids=[
        "single_segment",
        "empty_string",
        "multiple_segments",
        "underscores",
        "spaces",
        "mixed",
        "final_slash",
    ],
)
def test_set_default_stubs_nav_path(stubs_parent_url, expected_output):
    """Test the set_default_stubs_nav_path function."""
    assert set_default_stubs_nav_path(stubs_parent_url) == expected_output
