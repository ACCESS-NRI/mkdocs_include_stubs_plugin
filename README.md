# MkDocs include-configuration-stubs plugin

## About
Mkdocs plugin to include configuration _stubs_ within the build of a website for multiple branches within an ACCESS-NRI config repo.
A configuration _stub_ consists of a single file, in one of the `supported_file_formats`.

This plugin adds files to the website structure using the `on_files` mkdocs hook. 
Make sure you include this plugin in the `mkdocs.yml` file before any other plugin that uses included files (for example the `macros` plugin), if you want the
files included by this plugin to be processed by the other plugins.

## Requirements
In addition to the requirements specified in the `pyproject.toml` file, this plugin requires and uses the following executables:
- `git`

## Options
- `repo`
    The GitHub repository URL used to retrieve branches and tags for the configuration stubs to be included in the MkDocs site.
    It can be specified in one of the following formats:
    - GitHub URL (`https://github.com/OWNER/REPO`) 
    - GitHub SSH (`git@github.com:OWNER/REPO.git`)
    - `OWNER/REPO`
    If not specified, the output of `git remote get-url origin` for the local directory will be used.
    Only GitHub repositories are supported.
- `main_website`
    Configuration parameters for the main website.
    Sub-parameters:
    - `pattern`
        Glob pattern for _Git_ refs to be included when searching for configuration stubs.
        Default value is `release-*`.
    - `ref_type`
        Type of _Git_ ref to be used when searching for configuration stubs.
        Possible values are `branch`, `tag`, `all`.
        Default value is `tag`.
    - `branch`
        _Git_ branch where the main website documentation resides.
        Default value is `main`.
- `preview_website`
    Configuration parameters for the PR preview and local preview websites.
    **Note**: The `main_website` configurations are also included when building preview websites. To exclude the main website from the preview websites, set `no_main` to `true`.
    Sub-parameters:
    - `pattern`
        Glob pattern for _Git_ refs to be included when searching for configuration stubs.
        Default value is `dev-*`.
    - `ref_type`
        Type of _Git_ ref to be used when searching for configuration stubs.
        Possible values are `branch`, `tag`, `all`.
        Default value is `branch`.
    - `no_main`
        If set to `true`, don't include `main_website` configurations in the preview websites.
        Default value is `false`.
- `stubs_dir`
    Path to the directory containing the configuration stubs, relative to the root of the repository.
    This directory needs to contain **one single file** in one of the `supported_file_formats` for each configuration.
    When filtering the _Git_ refs for configurations to be included, the following will be ignored:
    - Refs that do not contain this `stubs_dir` path
    - Refs whose `stubs_dir` contain multiple files
    - Refs whose `stubs_dir` contain a single file in a non-supported format
    Default value is `documentation`.
- `stubs_parent_url`
    Parent url path relative to the root url (`site_url`) for the configuration stubs.
    Use an empty string (`""`) to specify the `site_dir`.
    Default value is `configurations`.
- `stubs_nav_path`
    '/'-separated path defining where the configuration stubs appear in the site navigation.
    Each segment corresponds to a section in the navigation hierarchy.
    Use an empty string (`""`) to place the stubs directly at the top level of the navigation.
    By default, the value is derived from `stubs_parent_url` by capitalizing each path segment and 
    replacing undersores with spaces.
    For example, a `stubs_parent_url` set to `custom/navigation/configuration_stubs` becomes `Custom/Navigation/Configuration stubs`, 
    placing the configuration stubs inside the `Configuration stubs` subsection, within the `Navigation` navigation section, under the top-level `Custom` Section.
- `supported_file_formats`
    List of file extensions (including the dot) which represent the supported formats for the
    files in `stubs_dir`.
    Default value is [`.md`, `.html`] (MarkDown and HTML).

## Lincense
Apache Software License 2.0