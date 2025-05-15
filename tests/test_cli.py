from unittest.mock import patch, MagicMock

import pytest
import logging

from include_configuration_stubs.cli import (
    logger,
    is_default_mkdocs_to_be_run,
    run_default_mkdocs_command,
    get_plugin_config,
    get_default_mkdocs_arguments,
    parse_args,
    get_git_clone_command,
    get_mkdocs_yaml_path,
)


@pytest.mark.parametrize(
    "command, other_args, expected_output",
    [
        (None, ["arg1", "arg2"], ["arg1", "arg2"]),
        ("some_command", ["arg1", "arg2"], ["some_command", "arg1", "arg2"]),
    ],
    ids=[
        "no_command",
        "command",
    ],
)
def test_get_default_mkdocs_arguments(command, other_args, expected_output):
    """
    Test the get_default_mkdocs_arguments function.
    """
    assert get_default_mkdocs_arguments(command, other_args) == expected_output

@pytest.fixture(autouse=True)
def silence_logs():
    logger.setLevel(logging.CRITICAL)

def test_run_default_mkdocs_command():
    """
    Test the run_default_mkdocs_command function.
    """
    with (
        patch("include_configuration_stubs.cli.cli") as mock_cli,
        patch("include_configuration_stubs.cli.sys.argv", ['arg_0', 'arg_1']) as mock_sys_argv,
    ):
        parameters = ["arg1", "other-arg", "--option=1"]
        run_default_mkdocs_command(parameters)
        mock_cli.assert_called_once_with(parameters)
        assert mock_sys_argv[0] == "mkdocs"


@pytest.mark.parametrize(
    "load_config_output, expected_output",
    [
        (
            {
                "not_plugins": {
                    "somthing": MagicMock(),
                }
            },
            None,
        ), # not_plugins
        (
            {
                "plugins": {
                    "not_include_configuration_plugin": MagicMock(),
                }
            },
            None,
        ), # not_include_configuration_plugin
    ],
    ids=[
        "not_plugins",
        "not_include_configuration_plugin",
    ], 
)
def test_get_plugin_config_return_none(load_config_output, expected_output):
    """
    Test the get_plugin_config function.
    """
    with patch(
        "include_configuration_stubs.cli.load_config",
        return_value=load_config_output,
    ):
        get_plugin_config() == expected_output

def test_get_plugin_config():
    """
    Test the get_plugin_config function.
    """
    config_value = {"key": "value"}
    config_mock = MagicMock(config = config_value)
    load_config_output = {
        "plugins": {
            "include-configuration-stubs": config_mock,
        }
    }
    with patch(
        "include_configuration_stubs.cli.load_config",
        return_value=load_config_output,
    ):
        get_plugin_config() == config_value

@pytest.mark.parametrize(
    "command",
    [None, "other"],
    ids=["none_command","other_command"],
)
@pytest.mark.parametrize(
    "mkdocs_exists",
    [True, False],
    ids=["mkdocs_exists", "mkdocs_not_exists"],
)
@pytest.mark.parametrize(
    "other_args",
    [
        ["args", "-f"],  # f_flag
        ["other", "--config-file"],  # config-file_flag
        ["example", "--f"],  # no_flag
    ],
    ids=[
        "f_flag",
        "config-file_flag",
        "no_flag",
    ],
)
def test_is_default_mkdocs_to_be_run_wrong_command(command, mkdocs_exists, other_args):
    """
    Test the is_default_mkdocs_to_be_run function when the command passed is not 'serve' or 'build'.
    """
    expected_output = True
    with patch("include_configuration_stubs.cli.os.path.exists", return_value=mkdocs_exists):
        assert is_default_mkdocs_to_be_run(command, other_args) == expected_output


@pytest.mark.parametrize(
    "command",
    ["serve", "build"],
    ids=["serve_command","build_command"],
)
@pytest.mark.parametrize(
    "mkdocs_exists",
    [True, False],
    ids=["mkdocs_exists", "mkdocs_not_exists"],
)
@pytest.mark.parametrize(
    "other_args",
    [
        ["args", "-f"],  # f_flag
        ["other", "--config-file"],  # config-file_flag
        ["other", "--config-file=somethig"],  # config-file_flag_equal
    ],
    ids=[
        "f_flag",
        "config-file_flag",
        "config-file_flag_equal",
    ],
)
def test_is_default_mkdocs_to_be_run_good_command_f_option(command, mkdocs_exists, other_args):
    """
    Test the is_default_mkdocs_to_be_run function when the command passed is 'serve' or 'build'
    and the '-f' or '--config-file' option is also passed.
    """
    expected_output = True
    with patch("include_configuration_stubs.cli.os.path.exists", return_value=mkdocs_exists):
        assert is_default_mkdocs_to_be_run(command, other_args) == expected_output

@pytest.mark.parametrize(
    "command",
    ["serve", "build"],
    ids=["serve_command","build_command"],
)
@pytest.mark.parametrize(
    "mkdocs_exists",
    [True, False],
    ids=["mkdocs_exists", "mkdocs_not_exists"],
)
def test_is_default_mkdocs_to_be_run_good_command_no_f_option(command, mkdocs_exists):
    """
    Test the is_default_mkdocs_to_be_run function when the command passed is 'serve' or 'build'
    and the '-f' or '--config-file' option is also passed.
    """
    other_args = ["args", "--f"]
    with patch("include_configuration_stubs.cli.os.path.exists", return_value=mkdocs_exists):
        assert is_default_mkdocs_to_be_run(command, other_args) == mkdocs_exists

@pytest.mark.parametrize(
    "args, expected_command, expected_repo, expected_branch, expected_unknown_args",
    [
        [
            "", 
            None, 
            None, 
            None, 
            [],
        ],  # no_args
        [
            "--repo owner/example --other-flag", 
            None, 
            "owner/example", 
            None, 
            ["--other-flag"],
        ],  # no_command
        [
            "example_command --branch example -b other_branch", 
            "example_command",
            None,
            "example",
            ["-b", "other_branch"],
        ],  # command_before_flag
        [
            "--branch example --repo owner/repo example_command -b other_branch", 
            "example_command",
            "owner/repo",
            "example",
            ["-b", "other_branch"],
        ],  # command_after_known_flag
        [
            "-b other_branch example_command --branch other", 
            "other_branch",
            None,
            "other",
            ["-b", "example_command"],
        ],  # command_after_unknown_flag
    ],
    ids=[
        "no_args",
        "no_command",
        "command_before_flag",
        "command_after_known_flag",
        "command_after_unknown_flag",
    ],
)
def test_parse_args(args, expected_command, expected_repo, expected_branch, expected_unknown_args):
    """
    Test the parse_args function.
    """
    test_args = ['entry_point'] + args.split()
    # with patch('include_configuration_stubs.cli.sys.argv', test_args):
    with patch('include_configuration_stubs.cli.sys.argv', test_args):
        known_args, unknown_args = parse_args()
    assert known_args.command == expected_command
    assert known_args.repo == expected_repo
    assert known_args.branch == expected_branch
    assert unknown_args == expected_unknown_args

@pytest.mark.parametrize(
    "branch",
    [
        "example_branch", # valid_branch
        None, # none_branch
    ],
    ids=[
        "valid_branch",
        "none_branch",
    ],
)
def test_get_git_clone_command(branch):
    """
    Test the get_git_clone_command function.
    """
    repo = "owner/repo"
    temp_dir = "tmp_name"
    expected_output = ["git", "clone", "--depth=1", f"https://github.com/{repo}", temp_dir]
    if branch:
        expected_output.extend(["--branch", branch])
    output = get_git_clone_command(repo, branch, temp_dir)
    assert output == expected_output

@pytest.mark.parametrize(
    "rglob_output, expected_output",
    [
        (
            iter(["some/directory/mkdocs.yaml"]), 
            "some/directory/mkdocs.yaml",
        ), # one_file_yaml
        (
            iter(["some/directory/mkdocs.yml"]), 
            "some/directory/mkdocs.yml",
        ), # one_file_yml
        (
            iter(["some/directory/mkdocs.yml","other/mkdocs.yml"]), 
            None,
        ), # multiple_files
        (
            iter([]), 
            None,
        ), # no_file
    ],
    ids=[
        "one_file_yaml",
        "one_file_yml",
        "multiple_files",
        "no_file",
    ],
)
@patch("include_configuration_stubs.cli.Path.rglob")
def test_get_mkdocs_yaml_path(mock_rglob, rglob_output, expected_output):
    """
    Test the get_mkdocs_yaml_path function.
    """
    mock_rglob.return_value = rglob_output
    output = get_mkdocs_yaml_path("some/directory")
    assert output == expected_output