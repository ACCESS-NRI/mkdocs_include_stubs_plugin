# mkdocs_include_configurations_plugin

## About
Mkdocs plugin to include configuration documentation for multiple branches within an ACCESS-NRI config repo.

## Requirements
In addition to the requirements specified in the `pyproject.toml` file, this plugin requires and uses the following executables:
- `git`
- `awk`

## Options
- `repo`
    The GitHub repository URL used to retrieve branches and tags for the configurations to be included in the MkDocs site.
    It can be specified as a full URL (in the form `https://github.com/OWNER/REPO`) or simply as `OWNER/REPO`.
    If not specified, the output of `git remote get-url origin` for the local directory will be used.
    Only GitHub repositories are supported.
- `pattern_released`
    Glob pattern used to select tags that represent released configurations.
    Default value is `release-*`.
- `pattern_development`
    Glob pattern used to select branches that represent development configurations.
    Default value is `dev-*`.
- `documentation_dir`
    Path to the directory containing the configuration file, relative to the root of the repository.
    This directory needs to contain **one single file**.
    Supported formats are:
    
    - MarkDown (`.md`)
    - HTML (`.html`)
    
    When filtering the _Git_ refs for configurations to be included, the following refs will be ignored:

    - Refs that do not contain this `documentation_dir` path
    - Refs whose `documentation_dir` contain multiple files
    - Refs whose `documentation_dir` contain a single file in a non-supported format
    Default value is `documentation`.

## Lincense
Apache Software License 2.0