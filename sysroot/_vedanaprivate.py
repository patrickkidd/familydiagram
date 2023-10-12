import os.path
from pyqtdeploy import Component, ExtensionModule


SOURCES = [
    "_vedanaprivate.cpp",
    "aes.cpp",
    "build/_vedanaprivate/sip_vedanaprivatecmodule.cpp",
]

MODULE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'vedanaprivate'))


class CVedanaPrivateComponent(Component):
    """ The _vedanaprivate component plugin. """

    must_install_from_source = False
    preinstalls = ['Python', 'SIP']
    provides = {
        '_vedanaprivate': ExtensionModule(
            source=[os.path.join(MODULE_DIR, x) for x in SOURCES],
            includepath=MODULE_DIR,
        )
    }

    def get_archive_name(self):
        return ''

    def install(self):
        orig_cwd = os.getcwd()
        try:
            _path = os.path.realpath(os.path.join(self._sysroot.sysroot_dir, '..', '..', 'vedanaprivate'))
            os.chdir(_path)
            self.run('sip-build')
        except Exception as e:
            self.verbose(str(e))
        finally:
            os.chdir(orig_cwd)
