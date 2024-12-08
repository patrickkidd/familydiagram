import os.path
import shutil

from pyqtdeploy.sysroot.plugins import Qt


class QtComponent(Qt.QtComponent):

    def run(self, *args, capture=False):
        """Add multiprocessing to make."""
        _args = args
        if args[0] == self.host_make:
            self.verbose("Adding args for concurrent build.")
            if os.name == "nt":
                os.environ["CL"] = "/MP"
            else:
                _args += ("-j16",)
        return super().run(*_args, capture=capture)

    def unpack_archive(self, archive, chdir=True):
        """Override to patch 5.15+ on macos"""
        archive_root = super().unpack_archive(archive, chdir)

        # Patch Qt-5.15+ on macOS.

        if self.target_platform_name == "macos":
            self.patch_file(
                "qtbase/src/plugins/platforms/cocoa/qiosurfacegraphicsbuffer.h",
                self._patch_qiosurfacegraphicsbuffer,
            )
            # shutil.copyfile(
            #     "../../../toolchain-macos-13.prf",
            #     "qtbase/mkspecs/features/toolchain.prf",
            # )

        return archive_root

    @staticmethod
    def _patch_qiosurfacegraphicsbuffer(line, patch_file):
        """Qt-5.15 does not build on at least macOS Monterey."""

        patch_file.write(
            line.replace(
                "#include <qpa/qplatformgraphicsbuffer.h>",
                "#include <CoreGraphics/CoreGraphics.h>\n#include <qpa/qplatformgraphicsbuffer.h>",
            )
        )

    @staticmethod
    def _patch_toolchain_prf(line, patch_file):
        """Qt-5.15 does not build on GitHub Runner macos-13"""

        # if "isEmpty(QMAKE_DEFAULT_LIBDIRS)|isEmpty(QMAKE_DEFAULT_INCDIRS):" in line:
        patch_file.write(
            line.replace(
                "isEmpty(QMAKE_DEFAULT_LIBDIRS)|isEmpty(QMAKE_DEFAULT_INCDIRS):",
                "isEmpty(QMAKE_DEFAULT_INCDIRS):",
            )
            .replace(
                'error("failed to parse default search paths from compiler output")',
                """error("failed to parse default include paths from compiler output")
294
        isEmpty(QMAKE_DEFAULT_LIBDIRS): \
295
            !integrity:!darwin: \
296
                error("failed to parse default library paths from compiler output")""",
            )
            .replace(
                "unix:if(!cross_compile|host_build) {",
                "unix:!darwin:if(!cross_compile|host_build) {",
            )
        )
