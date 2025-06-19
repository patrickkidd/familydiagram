# debuggable entry point for sip-build.
# Just chdir to the project path and run build.main()


import os, os.path, sys
from sipbuild.tools import build

if sys.platform == "win32":
    sys.argv += ["--qmake", "c:\\Qt\\5.15.1\\msvc2019_64\\bin\\qmake.exe"]

# path = os.path.abspath(os.path.join(__file__, "_pkdiagram"))
# path = os.path.abspath(os.path.join(__file__, '..', 'pkdiagram', 'vedana'))
# os.chdir("_pkdiagram")

build.main()
