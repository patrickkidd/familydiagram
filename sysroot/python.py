import os
import contextlib


from mock import patch
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

        elif args[0] == qt.host_qmake and self.target_arch_name == "macos-64":
            _args += ("QMAKE_CFLAGS=-Wno-implicit-function-declaration",)
        #     self.verbose('*********** Adding args for debug build.')
        #     _args += ('CONFIG+=debug', 'QMAKE_CFLAGS=-g')

        with contextlib.ExitStack() as stack:
            if args[0] == self.host_make and self.target_arch_name == "ios-64":
                stack.enter_context(
                    patch.dict(
                        os.environ,
                        {"LDFLAGS": os.environ["LDFLAGS"] + " -framework Security"},
                    )
                )
            ret = super().run(*_args, capture=capture)

        return ret

    def unpack_archive(self, archive, chdir=True):
        archive_root = super().unpack_archive(archive, chdir)

        if self.target_platform_name != "win":
            self.patch_file("Python/bootstrap_hash.c", self._patch_boostrap_hash)
        if self.target_platform_name == "ios":
            self.patch_file("Modules/posixmodule.c", self._patch_posixmodule_ios)
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

    # @staticmethod
    # def _patch_posixmodule__arm64(line, patch_file):
    #     patch_file.write(
    #         line.replace("#ifdef HAVE_CHROOT", "#if !TARGET_OS_IPHONE")
    #         .replace("#ifdef HAVE_SENDFILE", "#if !TARGET_OS_IPHONE")
    #         .replace("defined(HAVE_SENDFILE)", "TARGET_OS_IPHONE")
    #     )

    @staticmethod
    def _patch_posixmodule_ios(line, patch_file):
        patch_file.write(
            line.replace(
                "#ifdef HAVE_CHROOT",
                "#if HAVE_CHROOT\n\n int chroot(const char *path) {return 1;}\n\n",
            ).replace(
                "#ifdef HAVE_SENDFILE",
                "#ifdef HAVE_SENDFILE\n\n int sendfile(int, int, off_t, off_t *, struct sf_hdtr *, int) {return -1;}",
            )
        )
