import logging

from pkdiagram.pyqt import (
    QPen,
    QFileInfo,
    QPushButton,
    QToolButton,
    QIcon,
    QPixmap,
    QPainter,
    QColor,
    QRect,
)
from pkdiagram import util

_log = logging.getLogger(__name__)


class PixmapButtonHelper:

    PADDING = 12
    RADIUS = 2

    def __init__(
        self, uncheckedPixmapPath=None, checkedPixmapPath=None, autoInvertColor=True
    ):
        self._autoInvertColor = autoInvertColor
        self._uncheckedPixmapPath = uncheckedPixmapPath
        self._checkedPixmapPath = checkedPixmapPath
        self.updateAll()

    def updateAll(self):
        self.setFixedSize(util.BUTTON_SIZE, util.BUTTON_SIZE)
        self.setAutoInvertColor(self._autoInvertColor)
        self.setUncheckedPixmapPath(self._uncheckedPixmapPath)
        self.setCheckedPixmapPath(self._checkedPixmapPath)

    def onApplicationPaletteChanged(self):
        """Called from toolbars.py"""
        self.updateAll()

    def setAutoInvertColor(self, on):
        self._autoInvertColor = on

    def setUncheckedPixmapPath(self, path):
        if path is None:
            path = ""
        if QFileInfo(path).isFile():
            self._uncheckedPixmapPath = path
        elif QFileInfo(util.QRC + path).isFile():
            self._uncheckedPixmapPath = util.QRC + path
        else:
            self._uncheckedPixmapPath = None
        if util.IS_UI_DARK_MODE and self._autoInvertColor:
            self._uncheckedPixmap = util.invertPixmap(
                QPixmap(self._uncheckedPixmapPath)
            )
        else:
            self._uncheckedPixmap = QPixmap(self._uncheckedPixmapPath)
        if self._uncheckedPixmap.isNull():
            _log.warning(f"Pixmap not found: {self._uncheckedPixmapPath}")
        self._uncheckedIcon = QIcon(self._uncheckedPixmap)

    def setCheckedPixmapPath(self, path):
        if path is None:
            path = ""
        if QFileInfo(path).isFile():
            self._checkedPixmapPath = path
        elif QFileInfo(util.QRC + path).isFile():
            self._checkedPixmapPath = util.QRC + path
        else:
            self._checkedPixmapPath = None
        if util.IS_UI_DARK_MODE and self._autoInvertColor:
            self._checkedPixmap = util.invertPixmap(QPixmap(self._checkedPixmapPath))
        else:
            self._checkedPixmap = QPixmap(self._checkedPixmapPath)
        self._checkedIcon = QIcon(self._checkedPixmap)

    def paintPixmapButton(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        if not self.isEnabled():  # hack
            p.setOpacity(0.5)

        if self.isDown() or self.isChecked():
            if self.isDown():
                p.setBrush(util.CONTROL_BG)
            if self.isChecked():
                p.setPen(QPen(QColor("#5a9adb"), 1))
            borderRect = self.rect()
            borderRect.setX(1)
            borderRect.setY(1)
            borderRect.setWidth(borderRect.width() - 2)
            borderRect.setHeight(borderRect.height() - 2)
            p.drawRoundedRect(borderRect, self.RADIUS, self.RADIUS)

        iconRect = QRect(
            self.PADDING,
            self.PADDING,
            self.width() - self.PADDING,
            self.height() - self.PADDING,
        )
        iconRect.moveCenter(self.rect().center())
        if self.isChecked() and not self._checkedIcon.isNull():
            icon = self._checkedIcon
        else:
            icon = self._uncheckedIcon
        icon.paint(p, iconRect)

        p.end()
        p = None


class PixmapPushButton(QPushButton, PixmapButtonHelper):

    def __init__(self, parent=None, **kwargs):
        super(QPushButton, self).__init__(parent, **kwargs)

    def paintEvent(self, e):
        self.paintPixmapButton(e)


class PixmapToolButton(QToolButton, PixmapButtonHelper):

    def __init__(self, parent=None, **kwargs):
        super(QToolButton, self).__init__(parent, **kwargs)

    def paintEvent(self, e):
        self.paintPixmapButton(e)
