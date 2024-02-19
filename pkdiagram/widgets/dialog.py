from ..pyqt import (
    QWidget,
    QFrame,
    QPropertyAnimation,
    QPoint,
    QRect,
    QEvent,
    Qt,
    QColor,
    QPainter,
    pyqtSignal,
)
from .. import util


class Backdrop(QWidget):

    OPACITY = 0.5

    def __init__(self, parent=None):
        super().__init__(parent)
        self._opacity = 0.0

    def setOpacity(self, x):
        self._opacity = x * self.OPACITY
        self.update()

    def paintEvent(self, e):
        c = QColor("black")
        c.setAlphaF(self._opacity)
        p = QPainter(self)
        p.fillRect(self.rect(), c)


class Dialog(QFrame):
    """
    Animate from the top of parent
    """

    shown = pyqtSignal()
    hidden = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._shown = False
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Plain)
        self.posAnimation = QPropertyAnimation(self, b"pos")
        self.posAnimation.setDuration(util.ANIM_DURATION_MS)
        self.posAnimation.valueChanged.connect(self.onPosAnimationTick)
        self.posAnimation.finished.connect(self.onPosAnimationFinished)
        if parent:
            self.backdrop = Backdrop(parent)
            self.backdrop.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.backdrop.stackUnder(self)
            parent.installEventFilter(self)
            self.move(self._hiddenPos())

    def init(self):
        self.adjust()

    def eventFilter(self, o, e):
        if e.type() == QEvent.Resize:
            self.adjust()
        return super().eventFilter(o, e)

    def _x(self):
        x1 = round((self.parent().width() / 2) - (self.width() / 2))
        x = max(0, x1)
        return x

    def _shownPos(self):
        return QPoint(self._x(), 0)

    def _hiddenPos(self):
        return QPoint(self._x(), -self.height())

    def adjust(self):
        """ " Keep centered."""
        if self.parent():
            if self._shown:
                pos = self._shownPos()
            else:
                pos = self._hiddenPos()
            size = self.sizeHint().boundedTo(self.parentWidget().size())
            self.setGeometry(QRect(pos, size))
            self.backdrop.setGeometry(self.parent().rect())

    def resizeEvent(self, e):
        self.adjust()

    @util.blocked
    def onPosAnimationTick(self, x):
        if self.parent() and self.posAnimation.state() != self.posAnimation.Stopped:
            if self._shown:
                opacity = self.posAnimation.currentTime() / self.posAnimation.duration()
            else:
                opacity = 1 - (
                    self.posAnimation.currentTime() / self.posAnimation.duration()
                )
            self.backdrop.setOpacity(opacity)

    def onPosAnimationFinished(self):
        if self._shown:
            self.shown.emit()
        else:
            super().hide()
            self.hidden.emit()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.reject()

    def isShown(self):
        return self._shown

    @util.blocked
    def show(self):
        if self._shown:
            return
        super().show()
        self._shown = True
        if self.parent():
            self.posAnimation.stop()
            self.posAnimation.setStartValue(self.pos())
            self.posAnimation.setEndValue(self._shownPos())
            self.posAnimation.start()
        else:
            self.onPosAnimationFinished()

    @util.blocked
    def hide(self):
        if not self._shown:
            return
        self._shown = False
        if self.parent():
            self.posAnimation.stop()
            self.posAnimation.setStartValue(self.pos())
            self.posAnimation.setEndValue(self._hiddenPos())
            self.posAnimation.start()
        else:
            self.onPosAnimationFinished()

    def accept(self):
        self.hide()

    def reject(self):
        self.hide()
