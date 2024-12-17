from .pyqt import (
    QWidget,
    QColor,
    QPainter,
    QAbstractAnimation,
    QVariantAnimation,
)
from . import util


class HelpOverlay(QWidget):
    """A semi-opaque screen which is parent to tip pixmaps,
    under which view toolbars are shown."""

    def __init__(self, view):
        super().__init__(view)
        self._view = view
        self._opacity = 0
        self.showAnimation = QVariantAnimation()
        self.showAnimation.setDuration(util.ANIM_DURATION_MS)
        self.showAnimation.valueChanged.connect(self.onShowAnimationTick)
        self.showAnimation.finished.connect(self.onShowAnimationFinished)

    def paintEvent(self, e):
        painter = QPainter(self)
        color = QColor(0, 0, 0)
        color.setAlphaF(self._opacity)
        painter.fillRect(self.rect(), color)
        painter = None
        super().paintEvent(e)

    def adjust(self):
        self.move(0, 0)
        self.resize(self.parent().size())

    def _animateTo(self, opacity):
        if self.showAnimation.state() == QAbstractAnimation.Running:
            self.showAnimation.stop()
        self.showAnimation.setStartValue(float(self._opacity))
        self.showAnimation.setEndValue(float(opacity))
        self.showAnimation.start()

    def setVisible(self, on, animate=True):
        if on:
            if animate:
                self._animateTo(util.OVERLAY_OPACITY)
            super().setVisible(True)
        else:
            if animate:
                self._animateTo(0.0)
            else:
                super().setVisible(False)

    def onShowAnimationTick(self):
        self._opacity = self.showAnimation.currentValue()
        self.update()

    def onShowAnimationFinished(self):
        self._opacity = self.showAnimation.currentValue()
        if self.showAnimation.currentValue() == 0:
            super().setVisible(False)
        else:
            self.update()
