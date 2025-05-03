import os
import contextlib

from mock import patch
from pyqtdeploy.sysroot.plugins import zlib
from pyqtdeploy.sysroot import ComponentOption


class zlibComponent(zlib.zlibComponent):

    def run(self, *args, capture=False):

        IPHONE_SIMULATOR = (
            self.target_platform_name == "ios"
            and self._sysroot.target.platform.sdk_name == "iphonesimulator"
        )
        _args = args
        with contextlib.ExitStack() as stack:
            if (
                args[0] in (self.host_make, "./configure")
                and IPHONE_SIMULATOR
                and self.install_from_source
            ):
                stack.enter_context(
                    patch.dict(
                        os.environ,
                        {
                            "CFLAGS": "-fembed-bitcode -O3 -arch x86_64 -isysroot "
                            + self.apple_sdk
                        },
                    )
                )
            return super().run(*_args, capture=capture)
