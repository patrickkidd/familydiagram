import os.path
from pyqtdeploy import Component, PythonPackage


class BTCopilotComponent(Component):

    preinstalls = ["Python"]
    provides = {"btcopilot": PythonPackage()}

    def get_archive_name(self):
        return ""

    @property
    def target_modules_dir(self):
        import sysconfig

        # The site-packages dir, for wheels
        # return sysconfig.get_paths()["purelib"]

        # expect it to be cloned alongside this repo for any build?
        return os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "btcopilot")
        )

    def install(self):
        pass
