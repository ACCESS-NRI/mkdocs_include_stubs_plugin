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
- `pattern_released`
    Glob pattern used to select tags that represent released configurations.
    These configurations are included in the "main" website, in the PR previews and local preview.
    Default value is `release-*`.
- `pattern_development`
    Glob pattern used to select branches that represent development configurations.
    These configurations are included in the PR previews and local preview. They are NOT included in the "main" website.
    Default value is `dev-*`.
- `stubs_dir`
    Path to the directory containing the configuration stubs, relative to the root of the repository.
    This directory needs to contain **one single file** in one of the `supported_file_formats` for each configuration.
    When filtering the _Git_ refs for configurations to be included, the following will be ignored:
    - Refs that do not contain this `stubs_dir` path
    - Refs whose `stubs_dir` contain multiple files
    - Refs whose `stubs_dir` contain a single file in a non-supported format
    Default value is `documentation`.
- `supported_file_formats`
    Comma-separated list of file extensions (without the dot) which represent the supported formats for the
    files in `stubs_dir`.
    Default value is `md,html` (MarkDown and HTML).
- `main_website_branch`
    _Git_ branch where the "main" website documentation resides.
    Default value is `main`.
- `stubs_website_dir`
    Path to the directory where the configuration stubs will be stored, relative to the `site_dir`.
    If the navigation (`nav` field in the `mkdoc.yaml` file) is defined, this will also be the parent 
    of the configuration pages in the website navigation tree.
    Default value is `Configurations`.

## Lincense
Apache Software License 2.0