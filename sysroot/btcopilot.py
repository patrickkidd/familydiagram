import os, os.path
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
        if os.getenv("GITHUB_ACTIONS"):
            return sysconfig.get_paths()["purelib"]
        else:
            # dev; could even just import and detect the path from there.
            return os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "btcopilot")
            )

    def install(self):
        pass
