"""
No dependencies allowed except PyQt5.
"""

try:
    import pdytools  # type: ignore

    IS_BUNDLE = True
except:
    IS_BUNDLE = False


import os
from PyQt5.QtCore import *
from PyQt5 import QtCore

try:
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
    from PyQt5.QtNetwork import *
    from PyQt5 import QtCore, QtGui, QtWidgets
except:
    pass

from PyQt5.QtNetwork import QSslSocket

assert QSslSocket.supportsSsl() == True


try:
    from PyQt5.QtQuick import *
    from PyQt5.QtQuickWidgets import *
    from PyQt5.QtQml import *
except:
    pass

if not IS_BUNDLE:
    try:
        from PyQt5.QtTest import *
    except:
        pass

from _pkdiagram import CUtil


_OS_IPHONE_SIMULATOR = (
    CUtil.operatingSystem() & CUtil.OperatingSystem.OS_iPhoneSimulator
    == CUtil.OperatingSystem.OS_iPhoneSimulator
)
_OS_IPHONE = (
    CUtil.operatingSystem() & CUtil.OperatingSystem.OS_iPhone
) == CUtil.OperatingSystem.OS_iPhone
_OS_MAC = (
    CUtil.operatingSystem() & CUtil.OperatingSystem.OS_Mac
    == CUtil.OperatingSystem.OS_Mac
)
_OS_WINDOWS = (
    CUtil.operatingSystem() & CUtil.OperatingSystem.OS_Windows
    == CUtil.OperatingSystem.OS_Windows
)

if _OS_MAC or _OS_WINDOWS:
    from PyQt5.QtPrintSupport import *


def tr(s):
    return QCoreApplication.translate("A", s)


try:
    x = QApplePencilEvent  # type: ignore
except:

    class QApplePencilEvent(QEvent):
        pass


QModelIndex.__str__ = lambda self: "<QModelIndex, row: %i, column: %i>" % (
    self.row(),
    self.column(),
)
QModelIndex.__repr__ = lambda self: "<QModelIndex, row: %i, column: %i>" % (
    self.row(),
    self.column(),
)
