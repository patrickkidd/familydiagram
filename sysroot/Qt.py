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
            # Fix libpng fp.h issue on macOS 15+ SDK
            self.patch_file(
                "qtbase/src/3rdparty/libpng/pngpriv.h",
                self._patch_libpng_pngpriv,
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

    @staticmethod
    def _patch_libpng_pngpriv(line, patch_file):
        """Remove obsolete fp.h header for macOS 15+ SDK compatibility."""
        # Skip the obsolete macOS compiler check block that includes fp.h
        if "# if (defined(__MWERKS__)" in line:
            # Skip lines until we find the closing #endif for this block
            # Just write the standard math.h include instead
            patch_file.write("# include <math.h>\n")
            return

        # Skip the continuation of the __MWERKS__ condition
        if any(x in line for x in [
            "defined(THINK_C)",
            "/* We need to check that <math.h>",
            "* as it seems it doesn't agree with <fp.h>",
            "* <fp.h> if possible.",
            "# if !defined(__MATH_H__)",
            "# include <fp.h>",
        ]):
            return

        # Skip the #else and second math.h include (we already added it)
        if line.strip() == "# else" or (line.strip() == "# include <math.h>" and hasattr(patch_file, "_libpng_patched")):
            if line.strip() == "# else":
                patch_file._libpng_patched = True
            return

        # Write all other lines unchanged
        patch_file.write(line)
