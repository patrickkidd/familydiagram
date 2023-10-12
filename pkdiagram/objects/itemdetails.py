from ..pyqt import QBrush, QGraphicsItem, QGraphicsSimpleTextItem, QGraphicsLineItem, QLineF, Qt, QRectF, QGraphicsView, QColor, QPainterPath, QFontMetrics, QRect, QPen, QMarginsF, QFont, QPointF
from .. import util
from .pathitem import PathItem
from .itemanimationhelper import ItemAnimationHelper


class FlashableTextItem(QGraphicsSimpleTextItem, ItemAnimationHelper):

    def __init__(self, parentItem=None):
        super().__init__(parentItem)
        self.initItemAnimationHelper()
        self.nominalBoundingRect = self.boundingRect()

    def setText(self, text):
        super().setText(text)
        self.nominalBoundingRect = self.boundingRect()
    

class ItemDetails(PathItem):
    """ Contain a stack of child QGraphicsSimpleTextItems which can
        be colored, opacitied, and flashed independently.
    """

    PathItem.registerProperties([])

    def __init__(self, parent, growUp=False):
        super().__init__(parent)
        self.isItemDetails = True
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setShapeMargin(0)
        self.setShapeIsBoundingRect(True)
        self.setShapeIncludesChildrenRect(True)
        self.setZValue(util.DETAILS_Z)
        self.mainTextItem = QGraphicsSimpleTextItem(self)
        self.mainTextItem.setPen(util.PEN)
        self.mainTextItem.setFont(util.DETAILS_FONT)
        self.variablesLineItem = QGraphicsLineItem(QLineF(0, 0, 125, 0), self)
        self.variablesLineItem.setPen(util.PEN)
        self.extraTextItems = []
        self._growUp = growUp
        self._parentRequestsToShow = True # normal visible state prior to being hidden for scaling too small.
        self._shouldHideForSmallSize = False # item is too small to be legible
        self._mouseDown = None # Mouse clicks without drags were often meant to select the overlapped parent item

    # Events

    def updatePen(self):
        super().updatePen()
        if self.hover:
            pen = QPen(util.HOVER_PEN)
        else:
            pen = QPen(util.PEN)
        pen.setCapStyle(self.penCapStyle)
        self.setPen(pen)
        self.variablesLineItem.setPen(self.mainTextItem.pen())
        
    def updateGeometry(self):
        self.updatePathItemData()
        super().updateGeometry()
        self.updatePen()

    def mousePressEvent(self, e):
        self._mouseDown = e.screenPos()
        if self.scene().view().dragMode() == QGraphicsView.ScrollHandDrag:
            e.ignore()
            return
        currentDrawer = self.scene().view().parent().currentDrawer
        if currentDrawer and currentDrawer is not self.scene().view().parent().caseProps:
            return
        super().mousePressEvent(e)
        self.scene().clearSelection()

    def mouseMoveEvent(self, e):
        if self.scene().view().dragMode() == QGraphicsView.ScrollHandDrag:
            e.ignore()
            return
        currentDrawer = self.scene().view().parent().currentDrawer
        if currentDrawer and currentDrawer is not self.scene().view().parent().caseProps:
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.screenPos() == self._mouseDown:
            if self.parentItem().sceneBoundingRect().contains(e.scenePos()):
                ## Clicks without drags were 
                self.parentItem().setSelected(True)
        self._mouseDown = None
        return super().mouseReleaseEvent(e)

    def itemChange(self, change, variant):
        if change == QGraphicsItem.ItemPositionHasChanged:
            if self.scene() and self.scene().mousePressOnDraggable:
                self.scene().checkItemDragged(self, variant)
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            if variant:
                self.setZValue(util.DETAILS_Z + util.SELECTED_Z_DELTA)
            else:
                self.setZValue(util.DETAILS_Z)
        return super().itemChange(change, variant)

    def shouldShowFor(self, dateTime, tags=[], layers=[]):
        """ virtual """
        return True # let parent show|hide 
        # if self.parentItem():
        #     return self.parentItem().shouldShowFor(date, tags=tags, layers=layers)
        # else:
        #     return False

    def setParentRequestsToShow(self, on):
        """ The parent item says it should show, though onVisibleSizeChanged() may still hide it. """
        self._parentRequestsToShow = on
        if self.scene():
            # upstream hack
            view = self.scene().view()
            if view:
                visibleSceneRectRatio = view.getVisibleSceneScaleRatio()
                self.onVisibleSizeChanged(view, visibleSceneRectRatio)
            else:
                self.updatePathItemVisible()

    def onVisibleSizeChanged(self, view, visibleSceneRectRatio):
        """ Hiding here trumps all other conditions. """
        ratio = visibleSceneRectRatio * self.parentItem().scale()
        if ratio <= .28:
            self._shouldHideForSmallSize = True
        else:
            self._shouldHideForSmallSize = False
        self.updatePathItemVisible()

    def updatePathItemVisible(self):
        """ Override to aggregate the following into the fade in|out:
            - shouldShowForDateAndLayerTags()
            - setParentRequestsToShow()
            - onVisibleSizeChanged()
        """
        if self._shouldHideForSmallSize:
            on = False # trumps all
        elif not self.shouldShowForDateAndLayerTags() or not self._parentRequestsToShow:
            on = False # `not shouldShowForDateAndLayerTags` means parent is hidden
        else:
            on = True
        self.setPathItemVisible(on)

    # Properties

    def isEmpty(self):
        for item in [self.mainTextItem] + self.extraTextItems:
            if item.text():
                return False
        return True

    def setFont(self, font):
        self.mainTextItem.setFont(font)
        for item in self.extraTextItems:
            item.setFont(font)
        self.updateGeometry()

    def setMainTextColor(self, c):
        self.mainTextItem.setPen(QPen(c, 1))
        self.mainTextItem.setBrush(c)
        self.variablesLineItem.setPen(self.mainTextItem.pen())

    def setExtraLineColor(self, iLine, color):
        if iLine >= 0 and iLine < len(self.extraTextItems):
            textItem = self.extraTextItems[iLine]
            textItem.setPen(QPen(color, 1))
            textItem.setBrush(color)

    def extraLineText(self, iLine):
        return self.extraTextItems[iLine].text()

    def extraLineColor(self, iLine):
        return self.extraTextItems[iLine].pen().color()

    def numExtraTextItems(self):
        return len([i for i in self.extraTextItems if (i.isVisible() and i.text())])

    def text(self):
        lines = [self.mainTextItem.text()] + [item.text() for item in self.extraTextItems]
        return '\n'.join(lines)

    def setText(self, mainText, extraLines=[]):
        oldBL = self.boundingRect().bottomLeft()
        # Main text
        self.mainTextItem.setText(mainText)
        _font = QFont(self.mainTextItem.font())
        while len(extraLines) > len(self.extraTextItems):
            textItem = FlashableTextItem(self)
            self.extraTextItems.append(textItem)
        self.setFont(self.mainTextItem.font())
        # Variables line
        if extraLines:
            self.variablesLineItem.setVisible(True)
            textItemRect = self.mapFromItem(self.mainTextItem, self.mainTextItem.boundingRect()).boundingRect()
            spacing = 5
            self.variablesLineItem.setPos(0, textItemRect.bottomLeft().y() + spacing)
            lastItem = self.variablesLineItem
        else:
            spacing = 0
            self.variablesLineItem.setVisible(False)
            lastItem = self.mainTextItem
        # Variables text
        for i, textItem in enumerate(self.extraTextItems):
            if i < len(extraLines):
                line = extraLines[i]
            else:
                line = ''
            textItem.setText(line)
            if isinstance(lastItem, FlashableTextItem):
                textItemRect = self.mapFromItem(lastItem, lastItem.nominalBoundingRect).boundingRect()
            else:
                textItemRect = self.mapFromItem(lastItem, lastItem.boundingRect()).boundingRect()
            textItem.setPos(0, textItemRect.bottomLeft().y() + spacing)
            spacing = 0
            lastItem = textItem
        self.updatePathItemData()
        if self._growUp:
            newBL = self.boundingRect().bottomLeft()
            if self.scene() and not self.scene().isInitializing:
                self.setPos(self.x(), self.y() + oldBL.y() - newBL.y())
        self.updateGeometry()

    def flashExtraLine(self, iLine):
        if iLine >= 0 and iLine < len(self.extraTextItems):
            self.extraTextItems[iLine].flash()

