from pkdiagram.pyqt import *
from pkdiagram import util


class StatusBar(QStatusBar):
    pass


class TabBar(QTabBar):

    def __init__(self, parent=None):
        super().__init__(parent)

    def tabSizeHint(self, index):
        w = self.parent().width() / self.count()
        return QSize(w, 30)


class TabWidget(QTabWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBar(TabBar())
        self.tabBar().setExpanding(True)
        ss = """
QTabBar::tab {
    background: transparent;
    border-right: 1px solid #d0cfd1;
    min-width: 8ex;
    font-size: 10px;
}
QTabBar::tab:selected {
    color: blue;
    font-size: 11px;
}
QTabBar::tab:first {
    border-left: 0;
    border-top-left-radius: 5px;
}
QTabBar::tab:last {
    border-right: 0;
    border-top-right-radius: 5px;
}
PopUp QTabWidget,
Drawer QTabWidget {
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    background-color: transparent;
}
PopUp QTableView,
Drawer QTableView {
    border-top: 0;
}
LayerItemProperties QTabBar::tab {
    border: 0;
}
        """

        if util.CUtil.instance().isUIDarkMode():
            # name = QApplication.palette().color(QPalette.Active, QPalette.Highlight).name()
            name = util.CUtil.instance().appleControlAccentColor().name()
            ss += "QTabBar::tab:selected { color: " + name + " }"
        self.setStyleSheet(ss)

    def paintEvent(self, e):
        """Don't call super impl to avoid drawing QTabWidget frame."""
        h = self.tabBar().height()
        rect = QRect(0, h, self.width(), 1)
        if e.rect().intersects(rect):
            p = QPainter(self)
            pen = QPen(QColor("#d0cfd1"), 1)
            p.setPen(pen)
            p.drawLine(rect.topLeft(), rect.topRight())
            p = None

    # def adjust(self):
    #     width = (self.width() / self.count())

    # background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
    #                             stop: 0 #E1E1E1, stop: 0.4 #DDDDDD,
    #                             stop: 0.5 #D8D8D8, stop: 1.0 #D3D3D3);

    # width: %ipx;
    # background-color: #ffffff;
    # color: #000000;
    # border-right: 1px solid grey;

    # def resizeEvent(self, e):
    #     super().resizeEvent(e)
    #     self.adjust()

    # def addTab(self, *args, **kwargs):
    #     super().addTab(*args, **kwargs)
    #     self.adjust()


class PlainTextEdit(QPlainTextEdit):

    editingFinished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self.onTextChanged)
        self.dirty = False

    def onTextChanged(self):
        self.dirty = True

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        if self.dirty:
            self.editingFinished.emit()
            self.dirty = False


class Stylesheeter(QWidget):
    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)


class UndoView(QUndoView):
    pass


class ListView(QListView):
    pass


class TableView(QTableView):
    pass


class ListWidget(QListWidget):
    pass


class TableWidget(QTableWidget):
    pass


class DocTableWidget(TableWidget):

    deleteSelection = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDefaultDropAction(Qt.CopyAction)

    def mimeData(self, items):
        urls = {}
        for item in items:  # unique by row
            urls[self.row(item)] = QUrl(item.fpath)
        data = QMimeData()
        data.setUrls(urls.values())
        return data

    def startDrag(self, actions):
        """Override to only use copy action."""
        return super().startDrag(Qt.CopyAction)

    def canDeleteSelection(self):
        return bool(self.selectedItems())

    def onDeleteSelection(self):
        self.deleteSelection.emit()


from .button import PixmapButtonHelper, PixmapPushButton, PixmapToolButton
from .buttongroup import ButtonGroup
from .colorbox import ColorBox
from .drawer import Drawer
from .dialog import Dialog
from .popup import PopUp
from .timelinecallout import TimelineCallout
from .qmlwidgethelper import QmlWidgetHelper
