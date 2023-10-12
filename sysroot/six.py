import os.path
from pyqtdeploy import Component, PythonModule

class SixComponent(Component):

    preinstalls = [ 'Python' ]
    provides = { 'six': PythonModule() }

    def get_archive_name(self):
        return ''

    # Could also possibly get &.install() to copy the source files from
    # os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site-packages') to
    # Component.target_modules_dir (/Users/patrick/dev/familydiagram/vendor/sysroot-macos-64/lib/python3.7/site-packages)
    # so pyqtdeploy-build will automatically find it there.

    target_modules_dir = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'site-packages'))

    def install(self):
        pass
