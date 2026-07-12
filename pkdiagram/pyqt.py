"""
No dependencies allowed except PySide6.
"""

try:
    import pdytools  # type: ignore

    IS_BUNDLE = True
except:
    IS_BUNDLE = False


import os
from PySide6.QtCore import *
from PySide6 import QtCore

try:
    from PySide6.QtGui import *
    from PySide6.QtWidgets import *
    from PySide6.QtNetwork import *
    from PySide6 import QtCore, QtGui, QtWidgets
except:
    pass

from PySide6.QtNetwork import QSslSocket

assert QSslSocket.supportsSsl() == True


try:
    from PySide6.QtQuick import *
    from PySide6.QtQuickWidgets import *
    from PySide6.QtQml import *
except:
    pass

if not IS_BUNDLE:
    try:
        from PySide6.QtTest import *
    except:
        pass

# Transitional aliases for files not yet ported off the old names (FD-340).
# Deleted when this shim dies.
pyqtSignal = Signal
pyqtSlot = Slot
pyqtProperty = Property
pyqtBoundSignal = SignalInstance

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
    from PySide6.QtPrintSupport import *


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
