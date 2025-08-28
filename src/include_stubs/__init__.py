from . import _version
from include_stubs.utils import check_is_installed

REQUIRED_EXECS = ["git"]

for exe in REQUIRED_EXECS:
    check_is_installed(exe)

__version__ = _version.get_versions()["version"]
