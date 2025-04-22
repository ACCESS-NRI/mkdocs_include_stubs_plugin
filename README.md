# mkdocs_include_configurations_plugin

## About
Mkdocs plugin to include configuration documentation for multiple branches within an ACCESS-NRI config repo.

## Options
- `repo_url`: str
    The URL of the repository used to retrieve branches and tags for the 
    configurations included in the MkDocs site. If not specified, the equivalent of 
    the output of `git remote get-url origin` for the current Git repository will be used.
- `pattern_released`: str
    Regular expression pattern used to select tags that represent released configurations.
    Default is `^release-.+`.
- `pattern_development`: str
    Regular expression pattern used to select branches that represent development configurations.
    Default is `^dev-.+`.

## Lincense
Apache Software License 2.0