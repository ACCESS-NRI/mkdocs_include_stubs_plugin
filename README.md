# MkDocs include-stubs plugin

## About
Mkdocs plugin to include _stubs_ (single pages) from multiple GitHub branches of a repo within a mkdocs website build.
A _stub_ consists of a file in either of the [supported file formats](#supported_file_formats).

> [!IMPORTANT]
> This plugin adds _stub_ files to the website structure using the `on_files` mkdocs hook.
> Make sure you include this plugin in the `mkdocs.yml` file before any other plugin that uses included files (for example the `macros` plugin), if you want the files included by this plugin to be processed by those other plugins.

### Supported file formats
    - MarkDown (`.md`)
    - HTML (`.html`)

### Naming of the stub pages in the website navigation and url
The name of the stub pages in the website navigation and url will be inferred following the logic below:
- If the stub contains a title (`#` heading or `<h1>` block), that title will be used.
- If no title is found, the stub file name will be used instead.

## Requirements
In addition to the requirements specified in the `pyproject.toml` file, this plugin requires and uses the following executables:
- `git`
- `gh`

## Options
- `repo`
    The GitHub repository URL used to retrieve branches and tags for the stubs to be included in the MkDocs site.
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
        Git Glob pattern for _Git_ refs to be included when searching for stubs.
        To match multiple patterns, separate them with a space (e.g., "first-pattern second-pattern").
        An empty pattern will match no _Git_ refs.
        Default value is `release-*`.
    - `ref_type`
        Type of _Git_ ref to be used when searching for stubs.
        Possible values are `branch`, `tag`, `all`.
        Default value is `tag`.
    - `branch`
        _Git_ branch where the main website documentation resides.
        Default value is the repository's default branch.
- `preview_website`
    Configuration parameters for the PR preview and local preview websites.
    
    > [!IMPORTANT]
    > Stubs found for the `main_website` are also included automatically when building preview websites. To avoid this, set `no_main` to `true`.
    
    Sub-parameters:
    - `pattern`
        Git Glob pattern for _Git_ refs to be included when searching for stubs.
        To match multiple patterns, separate them with a space (e.g., "first-pattern second-pattern").
        Default value is `dev-*`.
    - `ref_type`
        Type of _Git_ ref to be used when searching for stubs.
        Possible values are `branch`, `tag`, `all`.
        Default value is `branch`.
    - `no_main`
        If set to `true`, don't include `main_website` configurations in the preview websites.
        Default value is `false`.
- `stubs_dir`
    Path to the directory containing the stubs, relative to the root of the repository.
    The `stubs_dir` must contain  **exactly one file** in one of the [supported file formats](#supported_file_formats). It may also include other files or directories, as long as only **one file** matches a supported format.
    When filtering the _Git_ refs to determine which to include, the following are **excluded**:
    - Refs that do not contain the `stubs_dir` path
    - Refs whose `stubs_dir` contains **multiple files** of the same [supported file format](#supported_file_formats)
    - Refs whose `stubs_dir` contains files from **multiple** [supported file format](#supported_file_formats)
    Default value is `documentation/stub`.
- `stubs_parent_url`
    Parent url path, relative to the website root url, for the stubs.
    Use an empty string (`""`) to specify the website root url.
    Default value is an empty string.
    
    Example: 
    If the root url is `www.examplesite.org` and `stubs_parent_url` is set to `added_pages/stubs`, then a stub file named `stub1.md` would be added to the URL: `www.examplesite.org/added_pages/stubs/stub1`
- `stubs_nav_path`
    Structure that defines where the stubs reside within the site navigation.
    Each navigation section should be connected to its subsection with a "greater than" (`>`) symbol.
    Use an empty string (`""`) to place the stubs directly at the top level of the navigation.
    If omitted, the value is derived from `stubs_parent_url` by capitalizing each path segment, replacing underscores with spaces and forward slashes (`/`) with "greather than" (`>`) symbols.

    Example 1:
    If `stubs_nav_path` is set to `Added pages > Stubs`, the stubs will be placed inside the `Stubs` subsection, under the top-level `Added pages` section of the site navigation.

    Example 2:
    If no `stubs_nav_path` is specified and `stubs_parent_url` is set to `custom/navigation/added_stubs`, the `stubs_nav_path` becomes `Custom > Navigation > Added stubs`, placing the stubs inside the `Added stubs` subsection, within the `Navigation` section, under the top-level `Custom` section of the site navigation.

## MkDocs wrapper
This plugin also installs a `mkdocs` command line executable, which wraps around the default `mkdocs` command.
For more information, run:
```
mkdocs --help
```

## Lincense
Apache Software License 2.0