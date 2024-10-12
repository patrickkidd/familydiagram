import os.path
from pyqtdeploy import Component, PythonPackage


class PipComponent(Component):

    preinstalls = ["Python"]
    provides = {"pip": PythonPackage()}

    def get_archive_name(self):
        return ""

    @property
    def target_modules_dir(self):
        import sysconfig

        return sysconfig.get_paths()["purelib"]

    def install(self):
        pass
