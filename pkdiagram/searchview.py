from pkdiagram.pyqt import (
    Qt,
    QWidget,
    QQmlEngine,
    QVBoxLayout,
    QAbstractAnimation,
    QVariantAnimation,
    QPainter,
    QColor,
)
from pkdiagram import util
from pkdiagram.qmlwidgethelper import QmlWidgetHelper


class SearchView(QWidget, QmlWidgetHelper):

    def __init__(self, engine: QQmlEngine, parent=None):
        super(SearchView, self).__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        self.initQmlWidgetHelper(engine, "qml/SearchView.qml")
        self.checkInitQml()
        self._opacity = 0
        self.showAnimation = QVariantAnimation()
        self.showAnimation.setDuration(util.ANIM_DURATION_MS)
        self.showAnimation.valueChanged.connect(self.onShowAnimationTick)
        self.showAnimation.finished.connect(self.onShowAnimationFinished)
        self.qml.setMaximumSize(600, 600)
        self.qml.setStyleSheet("QQuickWidget { border-radius: 10px; } ")

    def paintEvent(self, e):
        painter = QPainter(self)
        color = QColor(0, 0, 0)
        color.setAlphaF(self._opacity)
        painter.fillRect(self.rect(), color)
        painter = None
        super().paintEvent(e)

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
