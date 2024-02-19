from ..pyqt import pyqtSignal, QColor, Qt, QPalette, QPainter, QPen, QComboBox
from .. import util


class ColorBox(QComboBox):

    currentColorChanged = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        for row, c in enumerate(util.ABLETON_COLORS):
            self.addItem("")
            model = self.model()
            idx = model.index(row, 0)
            model.setData(idx, QColor(c), Qt.BackgroundColorRole)
            self.setItemData(row, c)
        self.currentIndexChanged[int].connect(self.onIndexChanged)
        p = self.palette()
        p.setColor(QPalette.Highlight, Qt.transparent)
        self.setPalette(p)
        self.setStyleSheet(
            "QComboBox QAbstractItemView { selection-background-color:rgba(0,0,0,0);}"
        )

    def paintEvent(self, e):
        if self.isEnabled():
            p = QPainter(self)
            p.fillRect(e.rect(), self.currentColor())
            p.end()
            # copt = QStyleOptionComboBox()
            # if self.style().styleHint(QStyle.SH_ComboBox_Popup, copt, self):
            #     opt = QStyleOption()
            #     opt.initFrom(self)
            #     p = QPainter(self)
            #     p.fillRect(opt.rect, self.currentColor())
            #     p.end()
        else:
            p = QPainter(self)
            p.setPen(QPen(self.palette().color(QPalette.Disabled, QPalette.Foreground)))
            p.drawRoundedRect(self.rect(), 5, 5)
            p.end()

    def currentColor(self):
        return QColor(self.itemData(self.currentIndex()))

    def setCurrentColor(self, c):
        if c is None:
            self.setCurrentIndex(0)
            return
        elif not isinstance(c, QColor):
            c = QColor(c)
        row = self.findData(c)
        if row == self.currentIndex():
            return
        if row == -1:
            self.addItem("")
            row = self.count() - 1
            index = self.model().index(row, 0)
            self.model().setData(index, c, Qt.BackgroundColorRole)
            self.setItemData(row, c)
        self.setCurrentIndex(row)

    def onIndexChanged(self, index):
        self.currentColorChanged[QColor].emit(self.currentColor())
