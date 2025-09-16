"""
Module for utility functions.
"""

import os
import re
import subprocess
import requests
import json
from dataclasses import dataclass
from subprocess import SubprocessError
from functools import partial
from itertools import count
from typing import Optional, Sequence, Iterable
from bs4 import BeautifulSoup
from markdown import Markdown
from markdown.extensions.toc import TocExtension
from mkdocs.structure.files import File, Files
from mkdocs.structure.nav import Navigation, Section
from mkdocs.structure.pages import Page

from include_stubs.config import GitRefType, GitRef, set_default_stubs_nav_path
from include_stubs.logging import get_custom_logger

logger = get_custom_logger(__name__)
GITHUB_URL = "https://github.com/"
GITHUB_SSH = "git@github.com:"


class GitHubApiRateLimitError(Exception):
    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded. "
        "Please try again later or authenticate with GitHub CLI using `gh auth`.\n"
        "For more information about GitHub API rate limits, see: "
        "https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api",
    ) -> None:
        super().__init__(message)


@dataclass
class Stub:
    gitref: GitRef
    fname: Optional[str] = None
    content: Optional[str] = None
    title: Optional[str] = None
    file: Optional[File] = None
    page: Optional[Page] = None


def run_command(command: Sequence[str]) -> str:
    """
    Run a command by capturing stdout and stderr.
    If the command fails, print the error.
    if get_output is True, return the command output as a string.

    Args:
        command: Sequence of Str
            The command to run.
        get_output: Bool
            If True, the output is returned as a string.

    Returns:
        None or Str
            If get_output is True, the output is returned as a string, otherwise return None.
    """
    _run_command = partial(subprocess.run, capture_output=True, text=True, check=True)
    try:
        result = _run_command(command)
    except subprocess.CalledProcessError as e:
        raise SubprocessError(
            f"Command '{' '.join(command)}' failed with error: {e.stderr.strip()}"
        )
    return result.stdout.strip()


def print_exe_version(executable: str) -> None:
    """
    Print the executable version.
    Raises an EnvironmentError if the executable is not found.

    Args:
        executable: Str
            The executable to check.

    Returns:
        None
            Prints the executable version and raises an EnvironmentError if the executable is not found.
    """
    try:
        version = run_command([executable, "--version"])
    except SubprocessError:
        raise EnvironmentError(
            f"Failed to get '{executable}' version. Please ensure it is installed correctly."
        )
    else:
        logger.info(f"'{executable}' version: {version}")


def get_git_refs(repo: str, pattern: str, ref_type: GitRefType) -> list[GitRef]:
    """
    Retrieve Git references of the specified type from the given repository,
    filtering them according to the provided pattern.

    Args:
        repo: Str
            The GitHub repository formatted as OWNER/REPO.
        pattern: Str
            The pattern to match the refs.
        ref_type: GitRefType
            The Git ref type.

    Returns:
        List of GitRef
            The list of GitRefs that match the pattern for the specified repo.
    """
    repo_url = f"https://github.com/{repo}"
    # Set which git refs to select based on the release status
    if ref_type == GitRefType.BRANCH:
        refs_flag = ["--heads"]
    elif ref_type == GitRefType.TAG:
        refs_flag = ["--tags"]
    else:
        refs_flag = ["--heads", "--tags"]
    # Print all tags in the repository
    # Split the pattern so it's treated as multiple arguments
    pattern_list = pattern.split()
    command = ["git", "ls-remote", *refs_flag, repo_url, *pattern_list]
    output = run_command(command)
    refs = []
    local_branch = get_local_branch()
    if output:
        for ref in output.split("\n"):
            sha, name = ref.split("\t")
            if (
                # Exclude annotated tags (ending with '^{}') because the non-annotated
                # references (same name without '^{}') always exist and point to the same
                # working tree content
                not (name.startswith("refs/tags/") and name.endswith("^{}"))
                # Exclude the current local branch, because its files need to be added
                # directly from the local branch, to allow for the 'serve' command to
                # track changes to those files.
                and (name != f"refs/heads/{local_branch}")
            ):
                refs.append(
                    GitRef(
                        sha=sha,
                        name=name.removeprefix("refs/tags/").removeprefix(
                            "refs/heads/"
                        ),
                    )
                )
    return refs


def gh_rate_limit_reached() -> bool:
    """
    Check if the GitHub API rate limit has been reached.

    Returns:
        Bool
    """
    command = [
        "gh",
        "api",
        "rate_limit",
        "--jq",
        "[.resources.[] | .remaining] | any(. == 0)",
    ]
    limit_exceeded = run_command(command)
    return limit_exceeded == "true"


def get_stub_content(
    stub_dir: str,
    fname: str,
    is_remote_stub: bool = True,
    repo: Optional[str] = None,
    gitsha: Optional[str] = None,
) -> Optional[str]:
    """
    Get the content of the stub from the GitHub repository.
    If is_remote_stub is False, it will get the stub content from a local file.

    Args:
        stub_dir: Str
            Path to the directory expected to contain the stub in a supported format.
        fname: Str
            The name of the stub file.
        is_remote_stub: Bool
            If True, the function will try to fetch the stub from a remote GitHub repository.
            If False, it will look for a local file.
        repo: Str
            The GitHub Repository to fetch the stub from, when is_remote_stub = True.
            When is_remote_stub = False, this parameter is ignored.
        ref: Str
            The git SHA to fetch the stub from, when is_remote_stub = True.
            When is_remote_stub = False, this parameter is ignored.

    Returns:
        Str
            The stub content.
    """
    if is_remote_stub:
        raw_url = (
            f"https://raw.githubusercontent.com/{repo}/{gitsha}/{stub_dir}/{fname}"
        )
        try:
            raw_resp = requests.get(raw_url)
            raw_resp.raise_for_status()
            return raw_resp.text
        except requests.RequestException:
            return None
    else:
        with open(os.path.join(stub_dir, fname), "r", encoding="utf-8") as f:
            return f.read()


def get_stub_title(path: str, content: str) -> Optional[str]:
    """
    Get the title of a HTML or MarkDown file from its path and content.

    Args:
        path: Str
            The path to the file.
        content: Str
            The content of the file.

    Returns:
        Str
            The title of the file.
            Returns None if no title is found.
    """
    if path.endswith(".html"):  # html
        return get_html_title(content)
    else:  # markdown
        return get_md_title(content)


def get_stub(
    stub_dir: str,
    supported_file_formats: tuple[str, ...],
    is_remote_stub: bool = True,
    repo: Optional[str] = None,
    gitref: Optional[GitRef] = None,
) -> Optional[Stub]:
    """
    Get the stub information and return a Stub object.

    Args:
        stub_dir: Str
            Path to the directory expected to contain the stub in a supported format.
        supported_file_formats: Tuple of Str
            Tuple of supported file formats.
        is_remote_stub: Bool
            If True, the function will try to fetch the stub from a remote GitHub repository.
            If False, it will look for a local file.
        repo: Str
            The GitHub Repository to fetch the stub from, when is_remote_stub = True.
            When is_remote_stub = False, this parameter is ignored.
        ref: Str
            The git SHA to fetch the stub from, when is_remote_stub = True.
            When is_remote_stub = False, this parameter is ignored.

    Returns:
        Stub
            The Stub object.
    """
    # Get git SHA
    gitsha = gitref.sha if gitref else None
    # Get stub filename
    stub_name = get_stub_fname(
        stub_dir=stub_dir,
        supported_file_formats=supported_file_formats,
        is_remote_stub=is_remote_stub,
        repo=repo,
        gitsha=gitsha,
    )
    if stub_name is None:
        return None
    # Get stub content
    stub_content = get_stub_content(
        stub_dir=stub_dir,
        fname=stub_name,
        is_remote_stub=is_remote_stub,
        repo=repo,
        gitsha=gitsha,
    )
    if stub_content is None:
        return None
    # # Get stub title
    title = get_stub_title(stub_name, stub_content)
    return Stub(gitref=gitsha, fname=stub_name, content=stub_content, title=title)


def get_remote_repo_from_local_repo() -> str:
    """
    Get the remote repository url from the current directory.

    Returns:
        Str
            The remote repository GitHub URL or SSH.
    """
    command = ["git", "remote", "get-url", "origin"]
    return run_command(command)


def get_repo_from_url(repo_url: str) -> str:
    """
    Get the GitHub repo in the format OWNER/REPO from the GitHub URL or SSH.

    Returns:
        Str
            The remote repository URL.
    """
    for prefix in (GITHUB_URL, GITHUB_SSH):
        if repo_url.startswith(prefix):
            remainder = repo_url.removeprefix(prefix)
            repo = "/".join(remainder.split("/")[0:2]).removesuffix(".git")
            return repo
    raise ValueError(f"Invalid GitHub repo URL: '{repo_url}'")


def get_repo_from_input(repo_config_input: Optional[str]) -> str:
    """
    Return the GitHub repository in the format 'OWNER/REPO'.

    If repo_config_input is None, attempts to infer the repository from the local Git
    remote via `git remote get-url origin`. Accepts either a full GitHub URL, an SSH URL,
    or a direct 'OWNER/REPO' input.

    Args:
        repo_config_input: Str
            The input repository string, or None to auto-detect.

    Returns:
        Str
            A string in the format 'OWNER/REPO'.
    """
    try:
        repo = (
            get_remote_repo_from_local_repo()
            if not repo_config_input
            else repo_config_input
        )
    except SubprocessError:
        raise ValueError(
            "Cannot determine GitHub repository. No GitHub repository specified in the plugin configuration and local directory is not a git repository."
        )
    if repo.startswith(GITHUB_URL) or repo.startswith(GITHUB_SSH):
        repo = get_repo_from_url(repo)
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", repo):
        raise ValueError(f"Invalid GitHub repo: '{repo}'")
    return repo


def is_main_website(main_branch_config_input: Optional[str], repo: str) -> bool:
    """
    Determine whether the build is intended for the main website.

    Args:
        main_branch_config_input: Str or None
            The branch for the main site configuration.
        repo: Str
            The GitHub repository in the format OWNER/REPO.

    Returns:
        bool: True if both the branch and repository match the main site configuration;
            False otherwise.
    """
    if main_branch_config_input is None:
        main_branch_config_input = get_default_branch_from_remote_repo(repo)
    try:
        remote_repo = get_remote_repo_from_local_repo()
        local_branch = get_local_branch()
    except SubprocessError:
        return False
    remote_owner_name = get_repo_from_url(remote_repo)
    return (main_branch_config_input == local_branch) and (repo == remote_owner_name)


def append_number_to_file_name(
    filename: str,
    number: int,
) -> str:
    """
    Append a number to the file name, taking into account any extensions.

    Args:
        filename: Str
            The file name to modify.
        number: Int
            The number to append.

    Returns:
        Str
            The modified file name with a number appended.
    """
    name, ext = os.path.splitext(filename)
    return f"{name}{number}{ext}"


def make_file_unique(file: File, files: Files) -> None:
    """
    Make a MkDocs File unique by appending a number to its `src_path` if the file already exists
    in the Files list.
    Changes the object in place.

    Args:
        file_name: mkdocs.structure.files.File
            The original MkDocs file.
        files: mkdocs.structure.files.File
            The list of existing MkDocs files.
    """
    existing_src_paths = {f.src_path for f in files}
    existing_dest_paths = {f.dest_path for f in files}
    use_directory_urls = file.use_directory_urls
    src = file.src_path
    dest = file.dest_path

    if src in existing_src_paths or dest in existing_dest_paths:
        for i in count(1):  # pragma: no branch
            new_src = append_number_to_file_name(src, i)
            if use_directory_urls:
                dest_dir, dest_name = os.path.split(dest)
                new_dir = append_number_to_file_name(dest_dir, i)
                new_dest = os.path.join(new_dir, dest_name)
            else:
                new_dest = append_number_to_file_name(dest, i)
            if (
                new_src not in existing_src_paths
                and new_dest not in existing_dest_paths
            ):
                file.src_path = new_src
                file.dest_path = new_dest
                logger.warning(
                    f"File {src!r} already exists in the site. "
                    f"Changing its url to unique destination {new_dest!r}."
                )
                break


def get_html_title(content: str) -> Optional[str]:
    """
    Get the title of a HTML file from its content.
    Args:
        content: Str
            The content of the HTML file.
    Returns:
        Str
            The title of the HTML file.
            Returns None if no title is found.
    """
    soup = BeautifulSoup(content, "html.parser")
    h1 = soup.find("h1")
    return h1.get_text() if h1 else None


def get_md_title(content: str) -> Optional[str]:
    """
    Get the title of a MarkDown file from its content.
    Args:
        content: Str
            The content of the MarkDown file.
    Returns:
        Str or None
            The title of the MarkDown file.
            Returns None if no title is found.
    """
    md = Markdown(extensions=[TocExtension(toc_depth="1")])
    md.convert(content)
    toc_tokens = md.toc_tokens

    if toc_tokens:
        return toc_tokens[0]["name"]  # First h1-level heading
    return None


def set_stubs_nav_path(
    stubs_nav_path: Optional[str],
    stubs_parent_url: str,
) -> str:
    """
    Set the structure of the stubs in the MkDocs navigation.

    Args:
        stubs_nav_path: Str
            The structure of the stubs in the MkDocs navigation.
        stubs_parent_url: Str
            The parent URL for the stubs.

    Returns:
        Str
            The structure of the stubs in the MkDocs navigation.
    """
    if stubs_nav_path is None:
        return set_default_stubs_nav_path(stubs_parent_url)
    return stubs_nav_path


def add_navigation_hierarchy(item: Section | Navigation, titles: list[str]) -> Section:
    """
    Add a nested hierarchy path to the navigation item.

    Example:
        titles = ["title1","title2","title3"]
        item = Section("Root",[Page("page1"), Page("page2")])
        => The item will become =>
            Section("Root",[
                Page("page1"),
                Page("page2"),
                Section("title1", children=[
                    Section("title2", children=[
                        Section("title3", children=[])
                    ])
                ]),
            ]

    Args:
        item: mkdocs.structure.nav.Section or mkdocs.structure.nav.Navigation
            The MkDocs navigation item to add the hierarchy to.
        titles: Str
            The titles for each of the section hierarchy.
    """
    # Create the root section
    if isinstance(item, Navigation):
        current_children = item.items
    else:
        current_children = item.children
    current_parent = item
    for title in titles:
        current_parent = Section(title, [])
        current_children.append(current_parent)
        current_children = current_parent.children
    return current_parent  # type: ignore[return-value]


def add_pages_to_nav(
    nav: Navigation,
    pages: list[Page],
    section_titles: list[str],
) -> None:
    """
    Add the stubs to the MkDocs navigation.

    Args:
        nav: mkdocs.structure.nav.Navigation
            The MkDocs navigation.
        pages: List of mkdocs.structure.pages.Page
            The pages to add to the deepest navigation Section.
        section_titles: List of Str
            The titles defining the hierarchical structure of the navigation Section where to place the stubs pages.
    """
    if not section_titles[0]:  # Case when the stubs_nav_path is empty (root nav path)
        section_titles = []
    current_parent: Section | Navigation = nav
    current_children = nav.items
    for it, title in enumerate(section_titles):
        # Try to find an existing Section with the current title
        section = next(
            (
                item
                for item in current_children
                if isinstance(item, Section) and item.title == title
            ),
            None,
        )
        # If no Section is found, create the navigation hierarchy
        if section is None:
            hierarchy = " -> ".join([section_titles[it - 1], title])
            logger.warning(
                f"Section {hierarchy!r} not found in the site navigation. "
                f"Creating a new {title!r} section for the stubs."
            )
            current_parent = add_navigation_hierarchy(
                current_parent, section_titles[it:]
            )
            break
        # Otherwise assign values for next iteration
        current_children = section.children
        current_parent = section
    # # Add pages
    # # Add parent to the pages
    if isinstance(current_parent, Section):
        current_children = current_parent.children
        for page in pages:
            page.parent = current_parent
    else:
        current_children = current_parent.items
    current_children.extend(pages)


def get_default_branch_from_remote_repo(remote_repo: str) -> str:
    """
    Get the name of the remote repository's default branch.

    Args:
        remote_repo: Str
            The remote repository in the format OWNER/REPO.

    Returns:
        Str
            The name of the remote repository's default branch.
    """
    api_url = f"repos/{remote_repo}"
    command = ["gh", "api", api_url, "--jq", ".default_branch"]
    try:
        default_branch = run_command(command)
    except SubprocessError:
        if gh_rate_limit_reached():
            raise GitHubApiRateLimitError()
        else:
            raise ValueError(
                f"Failed to retrieve the default branch for the repository {remote_repo!r}. "
                "Please check the repository name and your network connection."
            )
    return default_branch


def get_local_branch() -> str:
    """
    Get the name of the current local branch.

    Returns:
        Str
            The name of the current local branch.
    """
    command = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    return run_command(command)


def get_dest_uri_for_local_stub(
    stub_fname: str,
    stubs_parent_url: str,
    use_directory_urls: bool,
    supported_file_formats: tuple[str, ...],
) -> str:
    """
    Get the destination URI for a local stub file.

    Args:
        stub_fname: Str
            The name of the stub file.
        stubs_parent_url: Str
            The parent URL for the stubs on the site.
        use_directory_urls: Bool
            The use_directory_urls MkDocs config option.
        supported_file_formats: Tuple of Str
            Tuple of supported file formats.

    Returns:
        Str
            The destination URI for the local stub file.
    """
    for suffix in supported_file_formats:  # pragma: no branch
        if stub_fname.endswith(suffix):  # pragma: no branch
            stub_fname_no_suffix = stub_fname.removesuffix(suffix)
            break
    dest_uri = os.path.join(stubs_parent_url, stub_fname_no_suffix)
    return dest_uri if not use_directory_urls else os.path.join(dest_uri, "index.html")


def keep_unique_refs(refs: list[GitRef]) -> list[GitRef]:
    """
    Filter Git references keeping only
    first appearances of the same SHA.

    Args:
        refs: List of GitRef
            The list of Git references to filter.

    Returns:
        List of GitRef
            The list of unique Git references.
    """
    seen = set()
    unique_refs = []
    for ref in refs:
        if ref.sha not in seen:
            seen.add(ref.sha)
            unique_refs.append(ref)
    return unique_refs


def get_stub_fname(
    stub_dir: str,
    supported_file_formats: tuple[str, ...],
    is_remote_stub: bool = True,
    repo: Optional[str] = None,
    gitsha: Optional[str] = None,
) -> Optional[str]:
    """
    Get the name of the stub file from the GitHub repository.
    If is_remote_stub is False, it will get the stub name from a local file.
    If the specified stub_dir contains exactly one file in a supported format, return the stub name.

    Args:
        stub_dir: Str
            Path to the directory expected to contain the stub in a supported format.
        supported_file_formats: Tuple of Str
            Tuple of supported file formats.
        is_remote_stub: Bool
            If True, the function will try to fetch the stub from a remote GitHub repository.
            If False, it will look for a local file.
        repo: Str
            The GitHub Repository to fetch the stub from, when is_remote_stub = True.
            When is_remote_stub = False, this parameter is ignored.
        ref: Str
            The git SHA to fetch the stub from, when is_remote_stub = True.
            When is_remote_stub = False, this parameter is ignored.

    Returns:
        Str
            The stub filename.
    """
    if is_remote_stub:
        api_url = f"repos/{repo}/contents/{stub_dir}?ref={gitsha}"
        try:
            command = ["gh", "api", api_url, "--jq", ".[] | .name"]
            output = run_command(command)
        except SubprocessError:
            if gh_rate_limit_reached():
                raise GitHubApiRateLimitError()
            else:
                return None
        files = output.split("\n") if output else []
    else:
        files = os.listdir(stub_dir)
    stubs = [
        file
        for file in files
        for suffix in supported_file_formats
        if file.endswith(suffix)
    ]
    if len(stubs) != 1:
        return None
    return stubs[0]


def get_unique_stub_fname(
    filenames: Iterable[str],
    supported_file_formats: tuple[str, ...],
) -> Optional[str]:
    """
    From the GitHub GraphQL API response content, return the unique stub filename if exactly one file
    in a supported format is found, otherwise return None.

    Args:
        graphql_response: Dict
            The GitHub API response content for a specific git ref.

    Returns:
        Str or None
            The unique stub filename if exactly one file in a supported
            format is found, otherwise return None.
    """
    fname = [
        name
        for name in filenames
        for suffix in supported_file_formats
        if name.endswith(suffix)
    ]
    if len(fname) != 1:
        return None
    return fname[0]


class RemoteStubs(list):
    def __init__(
        self,
        repo: str,
        stubs_dir: str,
        supported_file_formats: tuple[str, ...],
        stubs: list[Stub] = [],
    ):
        super().__init__(stubs)
        self.repo = repo
        self.stubs_dir = stubs_dir
        self.supported_file_formats = supported_file_formats

    def _get_graphql_query_string(
        self,
    ) -> str:
        """
        Generate a GraphQL query string to fetch file
        names from a GitHub repository for each of the
        stubs in self.

        Returns:
            Str
                The GraphQL query string.
        """
        repo_owner, repo_name = self.repo.split("/")
        query_parts = [
            f'query {{ repository(owner: "{repo_owner}", name: "{repo_name}") {{',
        ]
        for i, stub in enumerate(self):
            gitsha = stub.gitref.sha
            # For simplicity, we alias each query with a unique 'r<index>' name based on the stub index
            query_parts.append(
                f'r{i}: object(expression: "{gitsha}:{self.stubs_dir}") {{ ... on Tree {{ entries {{ name type oid }}}}}}'
            )
        query_parts.append("}}")
        return "".join(query_parts)

    def _populate_remote_stub_fnames(
        self,
    ) -> None:
        """
        Uses GitHub GraphQL API to get the name of the remote stub file from its git ref, for each
        Stub in self.stubs.
        If exactly one file in a supported format is found, it sets the fname attribute of the
        corresponding Stub. Otherwise, it removes the Stub from self.stubs.

        Returns:
            None
                It modifies self.stubs in place.
        """
        query_string = self._get_graphql_query_string()
        try:
            command = ["gh", "api", "graphql", "-f", f"query={query_string}"]
            output = run_command(command)
        except SubprocessError:
            if gh_rate_limit_reached():
                raise GitHubApiRateLimitError()
            else:
                raise ValueError(
                    f"Failed to retrieve the remote stub filenames for the repository {self.repo!r}. "
                    "Please check the repository name and your network connection."
                )
        # For each ref, inspect the response and set the fname attribute if exactly one file in
        # the supported file format is found
        refcontents = list(json.loads(output)["data"]["repository"].values())
        for i in range(len(self) - 1, -1, -1):  # iterate backwards to allow deletion
            content = refcontents[i]
            if (
                content is not None
                and (
                    fname := get_unique_stub_fname(
                        (entry["name"] for entry in content["entries"]),
                        self.supported_file_formats,
                    )
                )
                is not None
            ):
                # If a unique file name is found, set it as the Stub fname attribute
                self[i].fname = fname
            else:
                # Otherwise, remove the Stub from the items
                del self[i]

    def _populate_remote_stub_contents(
        self,
    ) -> None:
        """
        Get the content of each Stub in self.stubs from the GitHub repository.

        Returns:
            None
                It modifies self.stubs in place.
        """
        for i in range(len(self) - 1, -1, -1):  # iterate backwards to allow deletion
            raw_url = f"https://raw.githubusercontent.com/{self.repo}/{self[i].gitref.sha}/{self.stubs_dir}/{self[i].fname}"
            try:
                raw_resp = requests.get(raw_url)
                raw_resp.raise_for_status()
                # If a content is found, set it as the Stub content attribute
                self[i].content = raw_resp.text
            except requests.RequestException:
                # Otherwise, remove the Stub from the items
                del self[i]

    def _populate_remote_stub_titles(
        self,
    ) -> None:
        """
        Get the title of each Stub in self.stubs from their contents.

        Returns:
            None
                It modifies self.stubs in place.
        """
        for i, stub in enumerate(self):
            if stub.fname.endswith(".html"):  # html
                self[i].title = get_html_title(stub.content)
            else:  # markdown
                self[i].title = get_md_title(stub.content)

    def populate_remote_stubs(
        self,
    ) -> None:
        """
        Populate the fname, content and title attributes of each Stub in self.stubs
        by fetching the data from the GitHub repository.

        Returns:
            None
                It modifies self.stubs in place.
        """
        self._populate_remote_stub_fnames()
        self._populate_remote_stub_contents()
        self._populate_remote_stub_titles()
