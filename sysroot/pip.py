import os.path
from pyqtdeploy import Component, PythonPackage


class PipComponent(Component):

    preinstalls = ["Python"]
    provides = {
        "pip": PythonPackage(),
        "pip._internal": PythonPackage(),
        "pip._internal.cli": PythonPackage(),
        "pip._internal.commands": PythonPackage(),
        "pip._internal.distributions": PythonPackage(),
        "pip._internal.index": PythonPackage(),
        "pip._internal.locations": PythonPackage(),
        "pip._internal.metadata": PythonPackage(),
        "pip._internal.metadata.importlib": PythonPackage(),
        "pip._internal.models": PythonPackage(),
        "pip._internal.network": PythonPackage(),
        "pip._internal.operations": PythonPackage(),
        "pip._internal.operations.build": PythonPackage(),
        "pip._internal.operations.install": PythonPackage(),
        "pip._internal.req": PythonPackage(),
        "pip._internal.resolution": PythonPackage(),
        "pip._internal.resolution.legacy": PythonPackage(),
        "pip._internal.resolution.resolvelib": PythonPackage(),
        "pip._internal.utils": PythonPackage(),
        "pip._internal.vcs": PythonPackage(),
        "pip._vendor": PythonPackage(),
        "pip._vendor.cachecontrol": PythonPackage(),
        "pip._vendor.cachecontrol.caches": PythonPackage(),
        "pip._vendor.certifi": PythonPackage(),
        "pip._vendor.distlib": PythonPackage(),
        "pip._vendor.distro": PythonPackage(),
        "pip._vendor.idna": PythonPackage(),
        "pip._vendor.msgpack": PythonPackage(),
        "pip._vendor.packaging": PythonPackage(),
        "pip._vendor.pkg_resources": PythonPackage(),
        "pip._vendor.platformdirs": PythonPackage(),
        "pip._vendor.pygments": PythonPackage(),
        "pip._vendor.filters": PythonPackage(),
        "pip._vendor.formatters": PythonPackage(),
        "pip._vendor.lexers": PythonPackage(),
        "pip._vendor.styles": PythonPackage(),
        "pip._vendor.pyproject_hooks": PythonPackage(),
        "pip._vendor.pyproject_hooks.in_process": PythonPackage(),
        "pip._vendor.requests": PythonPackage(),
        "pip._vendor.resolvelib": PythonPackage(),
        "pip._vendor.resolvelib.compat": PythonPackage(),
        "pip._vendor.rich": PythonPackage(),
        "pip._vendor.tomli": PythonPackage(),
        "pip._vendor.truststore": PythonPackage(),
        "pip._vendor.urllib3": PythonPackage(),
        "pip._vendor.urllib3.contrib": PythonPackage(),
        "pip._vendor.urllib3.contrib._securetransport": PythonPackage(),
        "pip._vendor.urllib3.packages": PythonPackage(),
        "pip._vendor.urllib3.packages.backports": PythonPackage(),
        "pip._vendor.urllib3.util": PythonPackage(),
    }

    def get_archive_name(self):
        return ""

    @property
    def target_modules_dir(self):
        import sysconfig

        return sysconfig.get_paths()["purelib"]

    def install(self):
        pass
