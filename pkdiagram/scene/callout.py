from pkdiagram.pyqt import (
    Qt,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsView,
    QRectF,
    QPen,
    QBrush,
    QGraphicsTextItem,
    QPainterPath,
    QLineF,
    QMarginsF,
    QColor,
    QEvent,
    QSizeF,
    QFont,
    QPointF,
    QTextCursor,
)
from pkdiagram import util
from pkdiagram.scene import LayerItem


class PointHandle(QGraphicsEllipseItem):

    RADIUS = 7
    PEN_WIDTH = 1.5

    def __init__(self, callout, pos=None):
        super().__init__(callout)
        self.mousedown = False
        w = self.RADIUS
        self.setRect(QRectF(-w, -w, w * 2, w * 2))
        self.setPen(QPen(QBrush(Qt.black), self.PEN_WIDTH))
        if pos is not None:
            self.setPos(pos)
            self.isnew = False
            self.setBrush(QBrush(Qt.white))
        else:
            self.isnew = True
            self.setBrush(QBrush(Qt.cyan))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)  # after setPos()

    def mousePressEvent(self, e):
        if self.scene().view().dragMode() == QGraphicsView.ScrollHandDrag:
            e.ignore()
            return
        super().mousePressEvent(e)
        self.parentItem().setFlag(QGraphicsItem.ItemIsMovable, False)
        self.mousedown = True
        self.parentItem().onStartMovePoint(self)

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
        self.parentItem().setFlag(QGraphicsItem.ItemIsMovable, True)
        self.mousedown = False
        self.parentItem().onStopMovePoint(self)

    def itemChange(self, change, variant):
        if change == QGraphicsItem.ItemPositionHasChanged and self.mousedown:
            self.parentItem().onUpdateMovePoint(self)
        return super().itemChange(change, variant)


class Callout(LayerItem):

    DEFAULT_RECT = QRectF(-50, -15, 200, 30)
    BORDER_MARGIN = 8
    PEN_WIDTH = 3

    ANCHOR_HANDLE_SIZE = 10

    LayerItem.registerProperties(
        (
            {"attr": "text", "default": ""},
            {"attr": "width", "default": DEFAULT_RECT.width()},
            {"attr": "points", "default": []},
        )
    )

    def __init__(self, **kwargs):
        super().__init__()
        self.isCallout = True
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setEmitDoubleClick(False)
        self.setShapeMargin(0)
        self.textItem = QGraphicsTextItem(self)
        font = QFont(util.DETAILS_FONT)
        font.setPointSize(font.pointSize())
        self.textItem.setFont(font)
        self.textItem.document().contentsChanged.connect(self.onTextEdited)
        self.textItem.setPos(0, 0)
        self.textItem.installEventFilter(self)
        self.pointHandles = [PointHandle(self)]
        self.pointHandles[0].setVisible(False)
        self.bubbleRect = QRectF()
        self.adjustingWidth = None
        self.adjustingScale = None
        self.anchoredDrag = None
        self.modifiers = None
        self.mousePressPoints = None
        self.mouseMovePoints = None  # undo
        self.setShapeMargin(0)
        self.setProperties(**kwargs)
        self.textItem.setTextWidth(self.width())
        self.updateBubbleRect()
        self.updateGeometry()
        self.updatePen()
        #
        self._anchorPressHandle = None
        self._anchorPressRect = None
        self._anchorResizing = False

    ## Item

    def read(self, chunk, byId):
        super().read(chunk, byId)
        for p in self.points():
            item = PointHandle(self, p)
            self.pointHandles.append(item)
            item.setVisible(False)
        self.onProperty(self.prop("text"))
        self.onProperty(self.prop("width"))

    def write(self, chunk):
        super().write(chunk)

    def clone(self, scene):
        x = super().clone(scene)
        for p in self.points():
            item = PointHandle(x, p)
            item.setVisible(True)
            x.pointHandles.append(item)
        self.onProperty(self.prop("width"))
        self.onProperty(self.prop("text"))
        return x

    ## QGraphicsItem

    def updatePen(self):
        super().updatePen()
        pen = QPen(util.PEN)
        # if self.isSelected():
        #     pen.setColor(util.SELECTION_PEN.color())
        #     pen.setWidthF(self.PEN_WIDTH * 1.5)
        # else:
        #     pen.setColor(Qt.red)
        #     pen.setWidthF(self.PEN_WIDTH)
        pen.setColor(Qt.red)
        pen.setWidthF(self.PEN_WIDTH)
        self.setPen(pen)
        self.textItem.setDefaultTextColor(util.ACTIVE_TEXT_COLOR)

    def updateGeometry(self):
        super().updateGeometry()
        # path
        path = QPainterPath()
        path.setFillRule(Qt.WindingFill)
        path.addRoundedRect(
            self.bubbleRect, Callout.BORDER_MARGIN, Callout.BORDER_MARGIN
        )
        center = self.bubbleRect.center()  # should be (0, 0)
        # points
        for handle in self.pointHandles:
            if handle.parentItem() == self:
                p = handle.pos()
            else:
                p = self.mapFromScene(handle.scenePos())
            marker = QPainterPath()
            marker.moveTo(p)
            side = QLineF(self.bubbleRect.center(), p)
            side = side.normalVector()
            side.setLength(side.length() * 0.05)
            marker.lineTo(self.bubbleRect.center() + QPointF(side.dx(), side.dy()))
            marker.lineTo(self.bubbleRect.center() - QPointF(side.dx(), side.dy()))
            marker.closeSubpath()
            path = path.united(marker)
            path.setFillRule(Qt.WindingFill)
        self.setPath(path)
        for handle in self.pointHandles:
            if handle.isnew and not handle.mousedown:
                handle.setPos(self.defaultNextPointHandlePos())
        self.updatePen()

    def _paint(self, painter, option, widget):
        painter.save()
        painter.setPen(QColor(util.QML_ITEM_BORDER_COLOR))
        painter.setBrush(QColor(util.QML_WINDOW_BG))
        painter.drawPath(self.path)
        painter.restore()
        super().paint(painter, option, widget)

    def updateBubbleRect(self):
        m = self.BORDER_MARGIN
        textRect = self.mapFromItem(
            self.textItem, self.textItem.boundingRect()
        ).boundingRect()
        self.bubbleRect = QRectF(
            0, 0, max(textRect.width(), 50), textRect.height()
        ).marginsAdded(QMarginsF(m, m, m, m))

    def mouseDoubleClickEvent(self, e):
        super().mouseDoubleClickEvent(e)
        # TOOD: maybe only handle in bubble?
        e.accept()
        self.textItem.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.textItem.setFocus()
        if self.scene() and self.scene().view():
            self.scene().view().ignoreDelete = True
        cursor = self.textItem.textCursor()
        cursor.select(QTextCursor.Document)
        self.textItem.setTextCursor(cursor)

    def eventFilter(self, o, e):
        if o == self.textItem:
            if e.type() == QEvent.FocusOut:
                self.setText(self.textItem.toPlainText(), undo=True)
                self.textItem.setTextInteractionFlags(Qt.NoTextInteraction)
                if self.scene() and self.scene().view():
                    self.scene().view().ignoreDelete = False
                cursor = self.textItem.textCursor()
                cursor.clearSelection()
                self.textItem.setTextCursor(cursor)
        return False

    @util.blocked
    def onProperty(self, prop):
        if prop.name() == "text":
            if self.textItem.toPlainText() != self.text():
                self.textItem.setPlainText(self.text())
                self.textItem.setTextWidth(self.width())  # redundant?
                self.updateBubbleRect()
                self.updateGeometry()
        elif prop.name() == "width":
            self.textItem.setTextWidth(self.width())
            self.updateBubbleRect()
            for handle in self.pointHandles:
                if handle.isnew:
                    handle.setPos(self.defaultNextPointHandlePos())
            self.updateGeometry()  # call again to repaint
        elif prop.name() == "points":
            for handle in self.pointHandles:
                self.scene().removeItem(handle)
            if self.points():
                self.pointHandles = [
                    PointHandle(self, pos=pos) for pos in self.points()
                ]
            else:
                self.pointHandles = []
            nextHandle = PointHandle(self)
            nextHandle.setPos(self.defaultNextPointHandlePos())
            self.pointHandles.append(nextHandle)
            self.updateGeometry()
        self._blocked = False
        super().onProperty(prop)

    def onTextEdited(self):
        self.updateBubbleRect()
        for handle in self.pointHandles:
            if handle.isnew:
                handle.setPos(self.defaultNextPointHandlePos())
        self.updateGeometry()

    def onStartMovePoint(self, handle):
        pass

    def onUpdateMovePoint(self, handle):
        self.updateGeometry()

    @util.blocked
    def onStopMovePoint(self, handle):
        if handle.isnew:  # create
            handle.setBrush(QBrush(Qt.white))
            self.setPoints(
                [h.pos() for h in self.pointHandles], undo=True
            )  # don't add new one
            handle.isnew = False
            newHandle = PointHandle(self)
            newHandle.setPos(self.defaultNextPointHandlePos())
            self.pointHandles.append(newHandle)
            self.updateGeometry()
            return
        if self.bubbleRect.contains(handle.pos()):  # delete
            self.pointHandles.remove(handle)
            self.scene().removeItem(handle)
            handle.setParentItem(None)
        self.setPoints([h.pos() for h in self.pointHandles], undo=True)
        self.updateGeometry()

    def defaultNextPointHandlePos(self):
        p = self.bubbleRect.topRight() - QPointF(self.bubbleRect.width() / 3, 0)
        return p

    ## Width

    def widthHandle(self):
        northEastHandle = self.northEastHandle()
        height = self.southEastHandle().y() - northEastHandle.bottomLeft().y()
        return QRectF(
            northEastHandle.x(),
            northEastHandle.bottomLeft().y(),
            northEastHandle.width(),
            height,
        )

    def hoverMoveEvent(self, e):
        super().hoverMoveEvent(e)
        cursor = self.handleCursorFor(e.pos())
        if cursor is None:  # no cursor
            if self.widthHandle().contains(e.pos()):
                cursor = Qt.SizeHorCursor
            elif e.modifiers() & Qt.AltModifier:
                cursor = Qt.OpenHandCursor
        if cursor is not None:
            self.setCursor(cursor)
        else:
            self.unsetCursor()

    def hoverLeaveEvent(self, e):
        super().hoverLeaveEvent(e)
        self.unsetCursor()

    def setScale(self, x, notify=True, undo=None):
        x = max(0.07, x)
        super().setScale(x)
        self.prop("scale").set(x, notify=notify, undo=undo)

    def mousePressEvent(self, e):
        self.mousePressPoints = list(self.points())  # undo
        # anchor mouse press
        if (
            self.northWestHandle().contains(e.pos())
            or self.northEastHandle().contains(e.pos())
            or self.southEastHandle().contains(e.pos())
            or self.southWestHandle().contains(e.pos())
        ):
            self._anchorPressRect = self.bubbleRect
            self._anchorPressScenePos = e.scenePos()
            self._anchorPressWidgetPos = self.pos()
            self._anchorPressHandle = self.handleFor(e.pos())
            self._anchorPressScale = self.scale()
            self._anchorResizing = True
            e.accept()
            return
        else:
            self._anchorResizing = False
        #
        if self.widthHandle().contains(e.pos()):
            self.adjustingWidth = (e.pos(), self.width())
        else:
            super().mousePressEvent(e)
            if e.modifiers() & Qt.AltModifier:  # anchored-drag
                for handle in self.pointHandles:
                    if not handle.isnew:
                        p = handle.scenePos()
                        handle.setParentItem(None)
                        handle.setPos(p)
                self.anchoredDrag = dict(
                    [(h, h.scenePos()) for h in self.pointHandles if not h.isnew]
                )
                self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._anchorResizing:
            e.accept()
            handle, handleRect = self._anchorPressHandle
            size = self._anchorPressRect.size()
            pos = self._anchorPressScenePos
            widgetPos = self._anchorPressWidgetPos
            delta = e.scenePos() - self._anchorPressScenePos
            newPos = None
            newSize = None
            if handle == "north-west":
                newSize = QSizeF(size.width() - delta.x() / 2, size.height())
                # widthDiff = (size.width() - newSize.width())
                # ratio = newSize.width() / size.width()
                # newPos = QPointF(widgetPos.x() + widthDiff * 2,
                #                  widgetPos.y())
            elif handle == "north-east":
                # newPos = QPointF(widgetPos.x(),
                #                  widgetPos.y())
                newSize = QSizeF(size.width() + delta.x(), size.height() - delta.y())
            elif handle == "south-east":
                # newPos = widgetPos
                newSize = QSizeF(size.width() + delta.x(), size.height() + delta.y())
            elif handle == "south-west":
                # newPos = QPointF(widgetPos.x() + delta.x(),
                #                  widgetPos.y())
                newSize = QSizeF(size.width() - delta.x(), size.height() + delta.y())
            newScale = self._anchorPressScale * (newSize.width() / size.width())
            # self.setPos(newPos)
            self.setScale(newScale, notify=False, undo=True)
        elif self.adjustingWidth:
            origP, origW = self.adjustingWidth
            delta = e.pos().x() - origP.x()
            self.setWidth(origW + delta, undo=True)
        else:
            super().mouseMoveEvent(e)
            self.modifiers = e.modifiers()

    def mouseReleaseEvent(self, e):
        self.mousePressPoints = None
        self.mouseMovePoints = None
        if self._anchorResizing:
            self._anchorResizing = False
            cursor = self.handleCursorFor(e.pos())
            if cursor:
                self.setCursor(cursor)
            else:
                self.unsetCursor()
        if self.adjustingWidth:
            self.adjustingWidth = None
        else:
            super().mouseReleaseEvent(e)
            if self.anchoredDrag:
                for handle in self.pointHandles:
                    if not handle.isnew:
                        handle.setParentItem(self)
                        p = self.anchoredDrag[handle]
                        handle.setPos(self.mapFromScene(p))
                self.setPoints([h.pos() for h in self.pointHandles if not h.isnew])
                self.unsetCursor()
                self.anchoredDrag = None

    def itemChange(self, change, variant):
        if change == QGraphicsItem.ItemPositionHasChanged:
            if self.anchoredDrag:
                self.updateGeometry()
            if self.scene() and not self.scene().isInitializing:
                if self.scene().mousePressOnDraggable:
                    if self.anchoredDrag:
                        self.mouseMovePoints = [
                            self.mapFromScene(h.pos())
                            for h in self.pointHandles
                            if not h.isnew
                        ]
                    else:
                        self.mouseMovePoints = []
                    self.scene().checkItemDragged(self, variant)
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            for handle in self.pointHandles:
                handle.setVisible(variant)
        return super().itemChange(change, variant)

    def __paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        painter.setPen(Qt.blue)
        painter.drawRect(self.bubbleRect)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(self.widthHandle())
        painter.drawRect(self.northWestHandle())
        painter.drawRect(self.southWestHandle())
        painter.drawRect(self.northEastHandle())
        painter.drawRect(self.southEastHandle())

    ## Anchors

    def northWestHandle(self):
        return QRectF(
            self.bubbleRect.x(),
            self.bubbleRect.y(),
            self.ANCHOR_HANDLE_SIZE,
            self.ANCHOR_HANDLE_SIZE,
        )

    def northEastHandle(self):
        return QRectF(
            self.bubbleRect.topRight().x() - self.ANCHOR_HANDLE_SIZE,
            self.bubbleRect.y(),
            self.ANCHOR_HANDLE_SIZE,
            self.ANCHOR_HANDLE_SIZE,
        )

    def southEastHandle(self):
        return QRectF(
            self.bubbleRect.topRight().x() - self.ANCHOR_HANDLE_SIZE,
            self.bubbleRect.bottomRight().y() - self.ANCHOR_HANDLE_SIZE,
            self.ANCHOR_HANDLE_SIZE,
            self.ANCHOR_HANDLE_SIZE,
        )

    def southWestHandle(self):
        return QRectF(
            self.bubbleRect.x(),
            self.bubbleRect.bottomRight().y() - self.ANCHOR_HANDLE_SIZE,
            self.ANCHOR_HANDLE_SIZE,
            self.ANCHOR_HANDLE_SIZE,
        )

    def handleFor(self, pos):
        if self.northWestHandle().contains(pos):
            return "north-west", self.northWestHandle()
        elif self.northEastHandle().contains(pos):
            return "north-east", self.northEastHandle()
        elif self.southWestHandle().contains(pos):
            return "south-west", self.southWestHandle()
        elif self.southEastHandle().contains(pos):
            return "south-east", self.southEastHandle()

    def handleCursorFor(self, pos):
        handle = self.handleFor(pos)
        if handle is None:
            cursor = None
        elif handle[0] == "north-west":
            cursor = Qt.SizeFDiagCursor
        elif handle[0] == "south-east":
            cursor = Qt.SizeFDiagCursor
        elif handle[0] == "north-east":
            cursor = Qt.SizeBDiagCursor
        elif handle[0] == "south-west":
            cursor = Qt.SizeBDiagCursor
        return cursor
