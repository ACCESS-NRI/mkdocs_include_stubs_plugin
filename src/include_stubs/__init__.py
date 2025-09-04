from . import _version
from include_stubs.utils import print_exe_version

REQUIRED_EXES = ["git", "gh"]

for exe in REQUIRED_EXES:
    print_exe_version(exe)

__version__ = _version.get_versions()["version"]
