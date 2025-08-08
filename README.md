# MkDocs include-configuration-stubs plugin

## About
Mkdocs plugin to include configuration _stubs_ within the build of a website for multiple branches within an ACCESS-NRI config repo.
A configuration _stub_ consists of a file in either of the [supported file formats](#supported_file_formats).

This plugin adds _stub_ files to the website structure using the `on_files` mkdocs hook.
Make sure you include this plugin in the `mkdocs.yml` file before any other plugin that uses included files (for example the `macros` plugin), if you want the
files included by this plugin to be processed by those other plugins.

### Supported file formats
    - MarkDown (`.md`)
    - HTML (`.html`)

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
        Git Glob pattern for _Git_ refs to be included when searching for configuration stubs.
        To match multiple patterns, separate them with a space (e.g., "first-pattern second-pattern").
        Default value is `release-*`.
    - `ref_type`
        Type of _Git_ ref to be used when searching for configuration stubs.
        Possible values are `branch`, `tag`, `all`.
        Default value is `tag`.
    - `branch`
        _Git_ branch where the main website documentation resides.
        Default value is the repository's default branch.
- `preview_website`
    Configuration parameters for the PR preview and local preview websites.
    **Note**: The `main_website` configurations are also included when building preview websites. To exclude the main website from the preview websites, set `no_main` to `true`.
    Sub-parameters:
    - `pattern`
        Git Glob pattern for _Git_ refs to be included when searching for configuration stubs.
        To match multiple patterns, separate them with a space (e.g., "first-pattern second-pattern").
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
    For each configuration, the `stubs_dir` must contain  **exactly one file** in one of the [supported file formats](#supported_file_formats). It may also include other files or directories, as long as only **one file** matches a supported format.
    When filtering the _Git_ refs to determine which configurations to include, the following are **excluded**:
    - Refs that do not contain the `stubs_dir` path
    - Refs whose `stubs_dir` contains **multiple files** of the same [supported file format](#supported_file_formats)
    - Refs whose `stubs_dir` contains files from **multiple** [supported file format](#supported_file_formats)
    Default value is `documentation/stub`.
- `stubs_parent_url`
    Parent url path, relative to the root url, for the configuration stubs.
    Use an empty string (`""`) to specify the root url.
    Default value is `configurations`.
    
    Example: 
    If the root url is `www.examplesite.org` and `stubs_parent_url` is set to `configurations/stubs`, then a potential configuration stub named `stub1` will be added to the URL: `www.examplesite.org/configurations/stubs/stub1`
- `stubs_nav_path`
    Structure that defines where the configuration stubs reside within the site navigation.
    Each navigation section should be connected to its subsection with a "greater than" (`>`) symbol.
    Use an empty string (`""`) to place the stubs directly at the top level of the navigation.
    By default, the value is derived from `stubs_parent_url` by capitalizing each path segment, replacing underscores with spaces and forward slashes (`/`) with "greather than" (`>`) symbols.

    Example 1:
    If `stubs_nav_path` is set to `Configurations > Stubs`, the configuration stubs will be placed inside the `Stubs` subsection, under the top-level `Configurations` Section of the site navigation.

    Example 2:
    If no `stubs_nav_path` is specified and `stubs_parent_url` is set to `custom/navigation/configuration_stubs`, the `stubs_nav_path` becomes `Custom > Navigation > Configuration stubs`, placing the configuration stubs inside the `Configuration stubs` subsection, within the `Navigation` section, under the top-level `Custom` Section of the site navigation.

## MkDocs wrapper
This plugin also installs a `mkdocs` command line executable, which wraps around the default `mkdocs` command.
For more information, run:
```
mkdocs --help
```

## Lincense
Apache Software License 2.0