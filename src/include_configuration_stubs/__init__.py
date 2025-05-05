from . import _version
from include_configuration_stubs.utils import check_is_installed

REQUIRED_EXECS = ["git"]
PLUGIN_NAME = "mkdocs-include-configuration-stubs-plugin"

for exe in REQUIRED_EXECS:
    check_is_installed(exe)

__version__ = _version.get_versions()["version"]
