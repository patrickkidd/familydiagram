
try:
    import pdytools
    BUNDLE = True
except:
    BUNDLE = False


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

if not BUNDLE:
    try:
        from PyQt5.QtTest import *
    except:
        pass
if not hasattr(QSysInfo, 'macVersion') or not QSysInfo.macVersion() & QSysInfo.MV_IOS:
    from PyQt5.QtPrintSupport import *

def tr(s):
    return QCoreApplication.translate('A', s)

try:
    x = QApplePencilEvent
except:
    class QApplePencilEvent(QEvent): pass


QModelIndex.__str__ = lambda self: '<QModelIndex, row: %i, column: %i>' % (self.row(), self.column())
QModelIndex.__repr__ = lambda self: '<QModelIndex, row: %i, column: %i>' % (self.row(), self.column())
