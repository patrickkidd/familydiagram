#    export CFLAGS="-O3 -arch armv7 -arch armv7s -arch arm64 -isysroot $XCODE_ROOT/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS${IPHONE_SDKVERSION}.sdk -mios-version-min=${IPHONE_SDKVERSION}"
#     make distclean
#     ./configure --host=arm-apple-darwin --prefix=$PREFIXDIR/iphone-build --disable-dependency-tracking --enable-static=yes --enable-shared=no
#     make
#     make install

import os
from pyqtdeploy import Component, ComponentLibrary, ComponentOption


class libpngComponent(Component):
    """libpng component."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lib_name = "png"

    def get_archive_name(self):
        return "libpng-{}.tar.xz".format(self.version)

    def get_archive_urls(self):
        return f"http://sourceforge.net/projects/libpng/files/libpng16/{self.version}/libpng-{self.version}.tar.xz"

    def install(self):
        """Install for the target."""
        if not self.install_from_source:
            return

        # Unpack the source.
        self.unpack_archive(self.get_archive())

        if self.target_platform_name == "ios":
            # Note that this doesn't create a library that can be used with
            # an x86-based simulator.
            os.environ["CFLAGS"] = (
                f"-O3 -arch armv7 -arch armv7s -arch arm64 -isysroot {self.apple_sdk}"
            )

        self.run(
            "./configure",
            "--host=arm-apple-darwin",
            f"--prefix={self.sysroot_dir}",
            "--disable-dependency-tracking",
            "--enable-static=yes",
            "--enable-shared=no",
        )
        self.run(self.host_make)
        self.run(self.host_make, "install")

        if self.target_platform_name == "ios":
            del os.environ["CFLAGS"]

    @property
    def provides(self):
        """The dict of parts provided by the component."""

        return {"png": ComponentLibrary(libs=("ios#-lpng",))}
