import os
import contextlib

from mock import patch
from pyqtdeploy import pyqtdeploysysroot_main

with contextlib.ExitStack() as stack:
    stack.enter_context(
        patch.dict(
            os.environ,
            {"PATH": "/Users/patrick/dev/lib/Qt/5.15.2/ios/bin:" + os.getenv("PATH")},
        )
    )
    if os.getenv("PK_IPHONE_SIMULATOR"):
        stack.enter_context(
            patch("pyqtdeploy.platforms.iOS.sdk_name", "iphonesimulator")
        )
        stack.enter_context(
            patch("pyqtdeploy.platforms.iOS.sdk_prefix", "iPhoneOSSimulator")
        )

    pyqtdeploysysroot_main.main()
