import os
from pyqtdeploy.sysroot.plugins import Python


class PythonComponent(Python.PythonComponent):

    def run(self, *args, capture=False):
        """Add multiprocessing to make."""
        qt = self.get_component("Qt")

        _args = tuple(args)
        if args[0] == self.host_make:
            self.verbose("Adding args for concurrent build.")
            if os.name == "nt":
                os.environ["CL"] = "/MP"
            else:
                _args += ("-j16",)
        elif args[0] == qt.host_qmake and self.target_arch_name in (
            "macos-64",
            "ios-64",
        ):
            _args += ("QMAKE_CFLAGS=-Wno-implicit-function-declaration",)
        #     self.verbose('*********** Adding args for debug build.')
        #     _args += ('CONFIG+=debug', 'QMAKE_CFLAGS=-g')
        return super().run(*_args, capture=capture)

    # def unpack_archive(self, archive, chdir=True):
    #     archive_root = super().unpack_archive(archive, chdir)

    #     if self.target_platform_name == "ios":
    #         self.patch_file("Python/bootstrap_hash.c", self._patch_bootstrap_hash)

    #     return archive_root

    # @staticmethod
    # def _patch_bootstrap_hash(line, patch_file):
    #     patch_file.write(
    #         line.replace(
    #             "res = getentropy(buffer, len);", "res = py_getentropy(buffer, len, 0);"
    #         )
    #     )
