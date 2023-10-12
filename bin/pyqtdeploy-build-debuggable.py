import os, os.path, sys
from pyqtdeploy import pyqtdeploybuild_main

path = os.path.abspath(os.path.join(__file__, '..', '..'))
os.chdir(path)


if os.name == 'posix':
    QMAKE = "/Users/patrick/dev/lib/Qt/5.15.2/clang_64/bin/qmake"
    os.environ['PATH'] = '/Users/patrick/dev/familydiagram/.direnv/python-3.7.8/bin:' + os.environ['PATH']
    sys.argv += ['--verbose', '--resources', '12', '--target', 'macos-64', '--build-dir', 'build/osx', 'familydiagram.pdt']
else:
    QMAKE = "C:\\Qt\\5.15.1\\msvc2019_64\\bin\\qmake.exe"
    os.environ['PATH'] = 'C:\\Strawberry\\perl\\bin;C:\\Users\\patrick\\AppData\\Local\\Programs\\Python\\Python37\\Scripts;' + os.environ['PATH']
    sys.argv += ['--verbose', '--resources', '12', '--target', 'win-64', 'familydiagram.pdt']

pyqtdeploybuild_main.main()

x = 1