import os
from pyqtdeploy.sysroot.plugins import Python


class PythonComponent(Python.PythonComponent):

    def run(self, *args, capture=False):
        """Add multiprocessing to make."""
        qt = self.get_component("Qt")

        was_ldflags = None

        _args = tuple(args)
        if args[0] == self.host_make:
            self.verbose("Adding args for concurrent build.")
            if os.name == "nt":
                os.environ["CL"] = "/MP"
            else:
                _args += ("-j16",)
            if self.target_arch_name == "ios-64":
                if "LDFLAGS" in os.environ:
                    was_ldflags = os.environ["LDFLAGS"]
                os.environ["LDFLAGS"] = os.environ["LDFLAGS"] + " -framework Security"

        elif args[0] == qt.host_qmake and self.target_arch_name == "macos-64":
            _args += ("QMAKE_CFLAGS=-Wno-implicit-function-declaration",)
        #     self.verbose('*********** Adding args for debug build.')
        #     _args += ('CONFIG+=debug', 'QMAKE_CFLAGS=-g')
        elif args[0] == qt.host_qmake and self.target_arch_name == "ios-64":
            _args += ("QMAKE_CFLAGS += -UHAVE_CHROOT -UHAVE_SENDFILE",)
        ret = super().run(*_args, capture=capture)

        if was_ldflags is not None:
            # Prevent from propagating to all components beyond just python
            os.environ["LDFLAGS"] = was_ldflags

        return ret

    def unpack_archive(self, archive, chdir=True):
        archive_root = super().unpack_archive(archive, chdir)

        if self.target_platform_name == "ios":
            self.patch_file("Python/bootstrap_hash.c", self._patch_boostrap_hash)
        # shutil.copyfile(
        #     "../../../toolchain-macos-13.prf",
        #     "qtbase/mkspecs/features/toolchain.prf",
        # )

        return archive_root

    @staticmethod
    def _patch_boostrap_hash(line, patch_file):
        patch_file.write(
            line.replace(
                '#include "Python.h"',
                """
#include "Python.h"
#include <Security/Security.h>
""",
            ).replace(
                "getentropy(buffer, len)",
                "SecRandomCopyBytes(kSecRandomDefault, size, buffer) == errSecSuccess ? 0 : -1",
            )
        )
