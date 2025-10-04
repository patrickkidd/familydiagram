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
            # Fix SDK version check for macOS 15+
            self.patch_file(
                "qtbase/mkspecs/common/macx.conf",
                self._patch_macos_sdk_version,
            )
            # Remove deprecated AGL framework for macOS 15+ SDK
            self.patch_file(
                "qtbase/mkspecs/common/mac.conf",
                self._patch_remove_agl_framework,
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
        # Track if we're inside the block to skip
        if not hasattr(patch_file, "_skip_fp_block"):
            patch_file._skip_fp_block = False

        # Detect start of the obsolete block - the #if with __MWERKS__ and macintosh
        if "#  if (defined(__MWERKS__)" in line and "defined(macintosh)" in line:
            patch_file._skip_fp_block = True
            # Replace entire block with just math.h include
            patch_file.write("#  include <math.h>\n")
            return

        # If we're skipping the block, skip lines until we hit #endif after #else
        if patch_file._skip_fp_block:
            # The block ends with "#  endif" at the same indent level
            if line.strip() == "#  endif":
                patch_file._skip_fp_block = False
                # Don't write the endif, it's part of the removed block
                return
            # Skip everything in between
            return

        # Write all other lines unchanged
        patch_file.write(line)

    @staticmethod
    def _patch_macos_sdk_version(line, patch_file):
        """Update QT_MAC_SDK_VERSION_MAX to support macOS 15+ SDK."""
        patch_file.write(
            line.replace(
                "QT_MAC_SDK_VERSION_MAX = 13",
                "QT_MAC_SDK_VERSION_MAX = 26",
            )
        )

    @staticmethod
    def _patch_remove_agl_framework(line, patch_file):
        """Remove deprecated AGL framework references for macOS 15+ SDK."""
        # Remove AGL from include paths
        if "QMAKE_INCDIR_OPENGL" in line and "AGL.framework" not in line:
            # This is the start of QMAKE_INCDIR_OPENGL, write it
            patch_file.write(line)
        elif "/System/Library/Frameworks/AGL.framework/Headers/" in line:
            # Skip the AGL include line entirely
            return
        elif "QMAKE_LIBS_OPENGL" in line:
            # Remove -framework AGL from libs
            patch_file.write(
                line.replace(" -framework AGL", "")
            )
        else:
            # Write all other lines unchanged
            patch_file.write(line)
