"""Wrapper for 'mkdocs' CLI executable."""

import sys
import os
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from mkdocs.config.base import load_config
from mkdocs.__main__ import cli
from include_stubs.logging import get_custom_logger
from include_stubs.utils import print_exe_version, get_repo_from_input, run_command, get_default_branch_from_remote_repo

PLUGIN_NAME = "include-stubs"
ENTRY_POINT_NAME = "mkdocs"
SUPPORTED_COMMANDS = ("build", "serve")
ENV_VARIABLE_NAME = "MKDOCS_INCLUDE_STUBS_ADD_LOCAL_STUB"
REQUIRED_EXES = ["git", "gh"]

logger = get_custom_logger(PLUGIN_NAME)

def get_mkdocs_yaml_path(directory: str) -> str | None:
    """
    Recursively search a 'mkdocs.yml' file in the directory, and returns its path.

    Args:
        directory: Str
            The directory where the 'mkdocs.yml' file should be searched.

    Returns:
        The path to the 'mkdocs.yml' file, or None if it does not exist.
    """
    for filename in ["mkdocs.yml", "mkdocs.yaml"]:
        path = list(Path(directory).rglob(filename))
        if len(path) == 1:
            return str(path[0])
    return None

def get_git_clone_command(repo: str, branch: str | None, temp_dir: str) -> list[str]:
    """
    Get the git clone command to clone the repository branch.

    Args:
        repo: Str
            The repository to clone.
        branch: Str
            The branch to clone.
        temp_dir: Str
            The temporary directory where the repository will be cloned to.

    Returns:
        List[str]
            The git clone command.
    """
    command = ["git", "clone", "--depth=1", f"https://github.com/{repo}", temp_dir]
    if branch:
        command.extend(["--branch", branch])
    return command

def get_default_mkdocs_arguments(command: str, other_args: list) -> list:
    """
    Get the arguments to pass to the default mkdocs command based on the passed command-line arguments.

    Args:
        command: Str
            The command passed to the CLI.
        other_args: Str
            The other passed CLI arguments.
    
    Returns:
        List
            The default mkdocs command arguments.
    """
    return [command] + other_args if command else other_args

def run_default_mkdocs_command(parameters: list[str]) -> None:
    """
    Run the default mkdocs command.
    """
    # Change sys.argv to simulate mkdocs passed in the command line
    sys.argv[0] = "mkdocs"
    new_args = " ".join(parameters)
    logger.info(f"Running the command 'mkdocs {new_args}' using the default mkdocs executable.")
    cli(parameters)


def get_plugin_config(config_path=None) -> dict | None:
    """
    Get the plugin configuration from the mkdocs.yaml file.

    Returns:
        The plugin configuration as a dictionary.
    """
    # This function runs outside of the mkdocs context, therefore we need to parse the plugin configuration
    # from the mkdocs.yaml file.
    config = load_config(config_path)
    plugin_config = config.get("plugins", {}).get("include-stubs") # type: ignore
    if plugin_config:
        return plugin_config.config
    return None


def is_default_mkdocs_to_be_run(command: str, other_args: list) -> bool:
    """
    Check if the default mkdocs command should be run.

    Args:
        command: Str
            The command passed to the CLI.
        other_args: Str
            The other passed CLI arguments.
    Returns:
        True if the default mkdocs command should be run, False otherwise.
    """
    if command not in SUPPORTED_COMMANDS:
        logger.info(
            f"No command among {SUPPORTED_COMMANDS} passed."
        )
        return True
    if any(arg == "-f" or arg.startswith("--config-file") for arg in other_args):
        logger.info(
            "'-f' or '--config-file' option passed."
        )
        return True
    if os.path.exists("mkdocs.yml") or os.path.exists("mkdocs.yaml"):
        logger.info(
            "Found 'mkdocs.yml' in the current directory."
        )
        return True
    if mkdocs_path:=get_mkdocs_yaml_path(os.getcwd()): # pragma: no branch
        logger.warning(
            f"Found a 'mkdocs.yml' file in a subdirectory of the current directory ({mkdocs_path!r}). "
            "If you want to use this 'mkdocs.yml', please run with the '-f' or '--config-file' option."
        )
    return False


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    """
    Parse command-line arguments.

    Returns:
    argsparse.Namespace
        Parsed command-line arguments.
    """
    DESCRIPTION = (
        "Wrapper for the mkdocs CLI, designed to work with the include-stubs plugin.\n\n"
        "If you want to run the default mkdocs command with the same arguments passed to this wrapper, "
        f"run:\n\n {ENTRY_POINT_NAME} -- [arguments]\n\n"
        "When run from a directory without a 'mkdocs.yml' file (e.g., a stub local branch), "
        "it builds the site by fetching the 'mkdocs.yml' and related contents from the remote branch BRANCH_NAME "
        "of the public GitHub repository GITHUB_REPOSITORY.\n\n"
        "If a 'mkdocs.yml' exists in the local directory, if the '-f' or '--config-file' option is specified, "
        f"or if no passed command is among {SUPPORTED_COMMANDS}, it delegates to the standard `mkdocs` "
        "executable to run with the passed command-line arguments."
    )

    parser = argparse.ArgumentParser(
        description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Add command as a positional optional argument
    parser.add_argument(dest="command", nargs="?", metavar="arguments", help="Arguments that are passed to the default mkdocs command.")
    # Add optional arguments
    parser.add_argument(
        "--repo", "--repository", "-r",
        dest="repo",
        metavar="GITHUB_REPOSITORY", 
        help="When the 'mkdocs.yml' file is not found in the local directory (e.g., when the local branch contains a stub), " \
            "the specified repository is used to fetch the 'mkdocs.yml' and related contents to build the site. " \
            "It can be specified in one of the following formats: 1. GitHub URL (e.g., https://github.com/OWNER/REPO), " \
            "2. GitHub SSH (e.g., git@github.com:OWNER/REPO.git), 3. OWNER/REPO. " \
            "If not specified, the output of `git remote get-url origin` for the local directory will be used. " \
            "Only public GitHub repositories are supported.",
    )
    parser.add_argument(
        "--branch", "-b",
        dest="branch",
        metavar="BRANCH_NAME", 
        help="When the 'mkdocs.yml' file is not found in the local directory (e.g., when the local branch contains a stub), " \
            "the specified branch will be used to fetch the 'mkdocs.yml' and related contents from the repository to build the site. " \
            "If not specified, the repository's default branch will be used.",
    )

    # Return arguments
    return parser.parse_known_args()


def main():
    """
    Main function to run the CLI.
    """
    # If the first argument is '--', run the default mkdocs command 
    # with the same arguments passed to this script (without this first '--' argument)
    if sys.argv[1] == "--":
        logger.info(
            "'--' passed as the first argument.")
        run_default_mkdocs_command(sys.argv[2:])
    else:
        # Parse command-line arguments
        known_args, unknown_args = parse_args()
        command = known_args.command
        default_mkdocs_arguments = get_default_mkdocs_arguments(command, unknown_args)
        for exe in REQUIRED_EXES:
            print_exe_version(exe)
        if is_default_mkdocs_to_be_run(command, unknown_args):
            # Run the default mkdocs command with the same arguments passed to this script
            run_default_mkdocs_command(default_mkdocs_arguments)
        else:
            # Shallow clone the repository branch
            repo = get_repo_from_input(known_args.repo)
            branch = known_args.branch or get_default_branch_from_remote_repo(repo)
            logger.warning(
                "'mkdocs.yml' not found locally. The site will be built using the 'mkdocs.yml' "
                f"file and other contents from the {branch!r} branch of the {repo!r} GitHub repository."
            )
            with TemporaryDirectory(
                prefix=f"{PLUGIN_NAME}_temp_build_dir_",
                dir=os.getcwd(),
                ignore_cleanup_errors=True,
            ) as temp_dir:
                command = get_git_clone_command(repo, branch, temp_dir)
                run_command(command)
                # Get mkdocs configuration
                mkdocs_yaml_path = get_mkdocs_yaml_path(temp_dir)
                # Get the plugin configuration
                plugin_config = get_plugin_config(mkdocs_yaml_path)
                # If the plugin configuration is not found, run the default mkdocs command
                if not plugin_config:
                    logger.warning("The 'include-stubs' plugin is not included in the 'mkdocs.yml' config file.")
                    run_default_mkdocs_command(default_mkdocs_arguments)
                else:
                    # Run the default mkdocs command with the mkdocs config and contents from
                    # the specified repo and branch
                    default_mkdocs_arguments.extend(["-f", mkdocs_yaml_path])
                    os.environ[ENV_VARIABLE_NAME] = '1'
                    run_default_mkdocs_command(default_mkdocs_arguments)
                    
