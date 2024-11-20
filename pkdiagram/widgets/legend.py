import pickle
from pkdiagram.pyqt import (
    QGraphicsView,
    QPropertyAnimation,
    pyqtSignal,
    QPoint,
    Qt,
    QHBoxLayout,
    QAbstractAnimation,
    QTransform,
    QFile,
    QIODevice,
)
from pkdiagram import util
from pkdiagram.widgets import PopUp


class LegendView(QGraphicsView):
    pass


class Legend(PopUp):

    resizeDone = pyqtSignal()

    def __init__(self, view=None):
        from pkdiagram.scene import Scene

        super().__init__(view, effect=None)
        self.setMouseTracking(True)
        self.initialized = False
        self.legendView = LegendView(self)
        self.legendView.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.legendScene = Scene()
        self.legendView.setScene(self.legendScene)
        self.legendView.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.legendView.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet(
            """
        border-radius: 0;
        border: 2px solid black;
        """
        )
        self.posAnimation = QPropertyAnimation(self, b"pos")
        self.posAnimation.setDuration(util.ANIM_DURATION_MS)
        self.posAnimation.finished.connect(self.onPosAnimationDone)
        Layout = QHBoxLayout(self)
        Layout.addWidget(self.legendView)
        Layout.setContentsMargins(0, 0, 0, 0)

        file = QFile(util.QRC + "Legend-Scene.fd/diagram.pickle")
        file.open(QIODevice.ReadOnly)
        bdata = file.readAll().data()
        data = pickle.loads(bdata)
        self.legendScene.read(data)
        items = []
        for item in self.legendScene.items():
            if item.isVisible():
                items.append(item)
        x = 0.2
        self.legendView.setTransform(QTransform.fromScale(x, x))
        self.legendScene.setScaleFactor(x)

    def init(self):
        self.resize(util.DEFAULT_LEGEND_SIZE)

    def deinit(self):
        pass

    def onPosAnimationDone(self):
        self.popupAnimationDone.emit()

    def move(self, x, y=None, animate=False):
        if isinstance(x, QPoint):
            x, y = x.x(), x.y()
        if not animate:
            super().move(x, y)
        else:
            if self.posAnimation.state() == QAbstractAnimation.Running:
                self.posAnimation.stop()
            self.posAnimation.setStartValue(self.pos())
            self.posAnimation.setEndValue(QPoint(x, y))
            self.posAnimation.start()


def __test__(scene, parent):
    w = Legend(parent)
    w.setScene(scene)
    w.resize(parent.size())
    w.show()
    parent.resize(util.DEFAULT_LEGEND_SIZE)
    return w
