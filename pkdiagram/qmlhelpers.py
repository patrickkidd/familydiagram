from .pyqt import *
from . import util

        

class LineEditBackEnd(QLineEdit):

    def __init__(self, parent):
        super().__init__(parent)
        self.setMaximumSize(QSize(0, 0))
        self.move(-10, -10)
        self.lower()
        self.hide()
        self.item = None

    # prevent a seg fault from calling `text` as property from qml
    @pyqtSlot(result=str)
    def getText(self):
        return self.text()
    
    @pyqtSlot(str, QQuickItem, int, int, int)
    def beginFocus(self, text, item, cursorPos, selectionStart, selectionEnd):
        if self.parent() is None:
            self.setParent(QApplication.activeWindow())
        self.blockSignals(True)
        self.setText(text)
        self.setCursorPosition(cursorPos)
        super().setSelection(selectionStart, selectionEnd-selectionStart)
        self.setFocus()
        self.blockSignals(False)
        self.show()
        QTimer.singleShot(1, lambda: item.forceActiveFocus()) # not sure why a timer

    @pyqtSlot()
    def endFocus(self):
        self.clearFocus()

    @pyqtSlot(str, int, int)
    def do_setSelection(self, text, start, end):
        self.blockSignals(True)
        if text != self.text():
            self.setText(text)
        super().setSelection(start, end-start)
        self.blockSignals(False)

    @pyqtSlot(int, int, int)
    def do_setCursorPosition(self, pos, start, end):
        self.blockSignals(True)
        super().setCursorPosition(pos)
        super().setSelection(start, end-start)
        self.blockSignals(False)

    @pyqtSlot(result=int)
    def getCursorPosition(self):
        return self.cursorPosition()
        
    @pyqtSlot(result=int)
    def selectionStart(self):
        return super().selectionStart()

    @pyqtSlot(result=int)
    def selectionEnd(self):
        return super().selectionEnd()

qmlRegisterType(LineEditBackEnd, 'LineEditBackEnd', 1, 0, 'LineEditBackEnd')



class TextEditBackEnd(QTextEdit):

    def __init__(self, parent):
        super().__init__(parent)
        self.setMaximumSize(QSize(0, 0))
        self.move(-10, -10)
        self.lower()
        self.hide()

    # prevent a seg fault from calling `text` as property from qml
    @pyqtSlot(result=str)
    def getPlainText(self):
        return self.toPlainText()
    
    @pyqtSlot(str, QQuickItem, int, int, int)
    def beginFocus(self, text, item, cursorPos, selectionStart, selectionEnd):
        if self.parent() is None:
            self.setParent(QApplication.activeWindow())
        self.blockSignals(True)
        self.setPlainText(text)
        cursor = self.textCursor()
        cursor.setPosition(cursorPos)
        cursor.setPosition(selectionEnd, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
        self.setFocus()
        self.blockSignals(False)
        self.show()
        QTimer.singleShot(1, lambda: item.forceActiveFocus()) # not sure why a timer

    @pyqtSlot()
    def endFocus(self):
        self.clearFocus()

    @pyqtSlot(str, int, int)
    def do_setSelection(self, text, start, end):
        self.blockSignals(True)
        if text != self.toPlainText():
            self.setPlainText(text)
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
        self.blockSignals(False)

    @pyqtSlot(int, int, int)
    def do_setCursorPosition(self, pos, start, end):
        self.blockSignals(True)
        cursor = self.textCursor()
        cursor.setPosition(pos)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
        self.blockSignals(False)

    @pyqtSlot(result=int)
    def getCursorPosition(self):
        return self.cursorPosition()
        
    @pyqtSlot(result=int)
    def selectionStart(self):
        return super().selectionStart()

    @pyqtSlot(result=int)
    def selectionEnd(self):
        return super().selectionEnd()

qmlRegisterType(TextEditBackEnd, 'TextEditBackEnd', 1, 0, 'TextEditBackEnd')



                 
