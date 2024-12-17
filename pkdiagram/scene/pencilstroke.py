from _pkdiagram import CUtil
from pkdiagram.pyqt import (
    QGraphicsRectItem,
    QGraphicsView,
    QGraphicsItem,
    Qt,
    QColor,
    QMarginsF,
    QRectF,
    QPen,
    QPoint,
    QRect,
    qAlpha,
)
from pkdiagram import util
from pkdiagram.scene import LayerItem


def bbox(p):
    """bounding-box-of-an-image"""
    l = p.width()
    t = p.height()
    r = 0
    b = 0

    for y in range(p.height()):
        rowFilled = False
        for x in range(p.width()):
            if qAlpha(p.pixel(x, y)):
                rowFilled = True
                r = max(r, x)
                if l > x:
                    l = x
        if rowFilled:
            t = min(t, y)
            b = y
    return QRect(QPoint(l, t), QPoint(r, b))


class PencilStroke(LayerItem):

    class Canvas(QGraphicsRectItem):

        def __init__(self):
            super().__init__()
            self.rect = QRectF()
            self.item = None
            self._scale = 1.0
            self._color = util.PEN.color()

        def isDrawing(self):
            return bool(self.item)

        def start(self, pos, pressure, parentItem=None):
            """Adjust to fix the view size every time - leave visible to ensure it's larger than the vsr."""
            vsr = self.scene().view().viewableSceneRect()
            rect = vsr.marginsAdded(
                QMarginsF(2, 2, 2, 2)
            )  # just a nudge to avoid being a partial pixel under the view
            self.setRect(rect)
            self.item = PencilStroke()
            self.item.setScale(self.scale())
            self.item.prop("scale").set(self.scale())
            self.item.setColor(self.color().name())
            if parentItem:
                self.item.setParentItem(parentItem)
            self.scene().addItem(self.item)
            self.item.addPoint(pos)

        def drawTo(self, pos, pressure):
            self.item.addPoint(pos)

        def finish(self):
            ret = self.item
            self.item = None
            return ret

        def setScale(self, x):
            self._scale = x

        def scale(self):
            return self._scale

        def setColor(self, x):
            self._color = x

        def color(self):
            return self._color

    LayerItem.registerProperties(
        ({"attr": "points", "type": list, "onset": "updateGeometry"},)
    )

    def __init__(self, **kwargs):
        super().__init__()
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.isPencilStroke = True
        self.selectionOutline = None
        self.setProperties(**kwargs)
        if not "points" in kwargs:  # avoid all scene using same default [] object
            self.setPoints([], notify=False, undo=False)
        self.setShapeMargin(1)
        self.setShapePathIsClosed(False)
        # self.dev_setShowPathItemShapes(True)

    def read(self, chunk, byId):
        super().read(chunk, byId)
        self.updatePen()
        self.updateGeometry()

    def clone(self, scene):
        x = super().clone(scene)
        x.setScale(self.scale())
        return x

    def itemName(self):
        return "Pencil Stroke"

    def addPoint(self, p):
        if self.parentItem() or self.scale() != 1.0:
            p = self.mapFromScene(p)
        self.points().append(p)
        self.updateGeometry()

    def updatePenAndGeometry(self):
        self.updatePen()
        self.updateGeometry()

    def updatePen(self):
        super().updatePen()
        pen = QPen(self.pen())
        pen.setWidthF(pen.widthF() * 1.5)
        if not self.isSelected():
            pen.setColor(QColor(self.color()))
        # Invert for dark mode
        color = pen.color()
        if color.red() == color.green() == color.blue():  # monochrome
            x = color.red()
            if util.IS_UI_DARK_MODE and x < 100:
                y = min(255, 255 - color.red())
                pen.setColor(QColor(y, y, y))
        self.setPen(pen)

    def onProperty(self, prop):
        super().onProperty(prop)
        if prop.name() == "color":
            self.updatePenAndGeometry()

    def itemChange(self, change, variant):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.updateGeometry()
        return super().itemChange(change, variant)

    def updateGeometry(self):
        super().updateGeometry()
        path = CUtil.splineFromPoints(self.points())
        # if self.isSelected():
        #     stroker = QPainterPathStroker()
        #     # stroker.setDashPattern(Qt.DashDotDotLine)
        #     stroker.setWidth(20)
        #     # stroker.setJoinStyle(Qt.MiterJoin)
        #     self.selectionOutline = stroker.createStroke(path).united(path)
        # else:
        #     self.selectionOutline = None
        self.setPath(path)
        self.updatePen()

    def mousePressEvent(self, e):
        if self.scene().view().dragMode() == QGraphicsView.ScrollHandDrag:
            e.ignore()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.scene().view().dragMode() == QGraphicsView.ScrollHandDrag:
            e.ignore()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.scene().view().dragMode() == QGraphicsView.ScrollHandDrag:
            e.ignore()
            return
        super().mouseReleaseEvent(e)

    def __paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        if self.selectionOutline:
            painter.save()
            painter.setPen(QPen(Qt.red))
            painter.drawPath(self.selectionOutline)
            painter.restore()
