"""Make _pkdiagram resolve to PyQt5's bundled Qt on Windows (CI only).

_pkdiagram is built against Qt 5.15.2 and is imported by conftest BEFORE
PyQt5. Python 3.8+ does not use PATH for an extension's dependent DLLs, so
without help the Qt DLLs are not found; shipping a second Qt copy next to
the .pyd loads two Qt builds -> 0xC0000005. The macOS build rpath-points
_pkdiagram at PyQt5's Qt; this is the Windows equivalent: a .pth file runs
at interpreter startup (before any import, for every process using this
venv) and adds PyQt5's bundled Qt bin to the DLL search path.
"""
import os
import sysconfig

sp = sysconfig.get_paths()["purelib"]
line = (
    "import os, site; "
    "[os.add_dll_directory(os.path.join(s, 'PyQt5', 'Qt5', 'bin')) "
    "for s in site.getsitepackages() "
    "if os.name == 'nt' and os.path.isdir(os.path.join(s, 'PyQt5', 'Qt5', 'bin'))]\n"
)
dest = os.path.join(sp, "zz_qt_dll.pth")
with open(dest, "w") as f:
    f.write(line)
print("wrote", dest)
