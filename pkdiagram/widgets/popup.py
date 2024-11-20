from pkdiagram.pyqt import (
    Qt,
    QPen,
    QColor,
    QTabWidget,
    QWidget,
    QFrame,
    QGraphicsOpacityEffect,
    QPropertyAnimation,
    QEasingCurve,
    QPointF,
    QPainter,
    QRect,
    pyqtSignal,
    QPoint,
)
from pkdiagram import util


class PopUp(QFrame):

    MARGIN = 15

    startHiding = pyqtSignal()
    dragPress = pyqtSignal(QPoint)
    dragMove = pyqtSignal(QPoint)
    dragRelease = pyqtSignal(QPoint)
    popupAnimationDone = pyqtSignal()

    def __init__(self, parent, effect=None):
        super().__init__(parent)
        if util.isInstance(parent, "View"):
            self.view = parent
        else:
            self.view = None
        self.showOver = None
        if effect == "drop-shadow":
            self.effect = util.makeDropShadow()
            self.setGraphicsEffect(self.effect)
        elif effect == "opacity":
            self.effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(self.effect)
        else:
            self.effect = None
        if isinstance(self.effect, QGraphicsOpacityEffect):
            self.showAnimation = QPropertyAnimation(self.effect, b"opacity")
        else:
            self.showAnimation = QPropertyAnimation(self, b"pos")
            if self.parent():
                self.hiddenY = self.parent().height() + self.height() + 10
            else:
                self.hiddenY = None
        self.showAnimation.setDuration(util.ANIM_DURATION_MS)
        self.showAnimation.finished.connect(self.onAnimationDone)
        # dragging
        self.mouseDown = None
        self.mouseDownPos = None
        self.showing = False
        self.hiding = False
        self.didAnimate = None

    def paintEvent(self, e):
        """
        background-color: white;
        border-radius: 5px;
        border: 1px solid #d8d8d8;
        """
        p = QPainter(self)
        p.setClipRegion(e.region())
        p.setBrush(Qt.white)
        p.setPen(QPen(QColor("#d8d8d8"), 2))
        p.drawRoundedRect(self.rect(), 5, 5)
        p = None

    # def paintEvent(self, event):
    #     """ style sheets """
    #     opt = QStyleOption()
    #     opt.initFrom(self)
    #     painter = QPainter(self)
    #     self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)

    def mousePressEvent(self, e):
        child = self.childAt(e.pos())
        if not child or type(child) in [QTabWidget, QWidget]:
            self.mouseDown = e.globalPos()
            self.mouseDownPos = self.pos()
            self.dragPress.emit(e.globalPos())
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.mouseDown:
            delta = e.globalPos() - self.mouseDown
            self.move(self.mouseDownPos + delta)
            self.dragMove.emit(e.globalPos())
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.mouseDown and e.pos() != self.mouseDownPos:
            self.dragRelease.emit(e.globalPos())
        self.mouseDown = None
        self.mouseDownPos = None
        super().mouseReleaseEvent(e)

    def setShowOver(self, w):
        self.showOver = w

    def show(self, items=[], over=None, endPos=None, animate=True):
        if over:
            self.setShowOver(over)
        if not isinstance(items, list):
            items = [items]
        x, y = self.x(), self.y()
        if endPos:
            x, y = endPos.x(), endPos.y()
        elif self.showOver:
            x = self.showOver.x() + util.MARGIN_X
            y = self.showOver.y() + util.MARGIN_Y
        elif self.view:
            # try not to cover the selected items.
            rect = QRect()
            for item in items:
                childrenRect = item.mapToScene(
                    item.childrenBoundingRect()
                ).boundingRect()
                itemRect = item.mapToScene(item.boundingRect()).boundingRect()
                rect |= self.view.mapFromScene(itemRect | childrenRect).boundingRect()
            if rect.center().x() > self.view.width() / 2:  # put to left
                x = rect.center().x() - self.width() - self.MARGIN
            else:  # put to right
                x = rect.bottomRight().x() + self.MARGIN
            x = max(
                self.MARGIN + self.view.itemToolBar.width(),
                min(x, self.view.width() - self.width() - self.MARGIN),
            )
            if rect.center().y() > self.view.height() / 2:  # put below
                y = rect.center().y() + self.MARGIN
            else:  # put above
                y = rect.center().y() - self.height() - self.MARGIN
            y = max(
                self.MARGIN + self.view.sceneToolBar.height(),
                min(y, self.view.height() - self.height() - self.MARGIN),
            )
        if self.parent():
            self.hiddenY = self.parent().height() + 15
        else:
            self.hiddenY = 0
        if animate and isinstance(self.effect, QGraphicsOpacityEffect):
            self.move(x, y)
            super().show()
            self.showAnimation.setStartValue(0)
            self.showAnimation.setEndValue(1)
            self.showAnimation.start()
            self.didAnimate = True
        elif animate:
            self.move(x, self.hiddenY)
            super().show()
            self.showAnimation.setEasingCurve(QEasingCurve.OutCubic)
            self.showAnimation.setStartValue(QPointF(x, self.hiddenY))
            self.showAnimation.setEndValue(QPointF(x, y))
            self.showAnimation.start()
            self.didAnimate = True
            self.showing = True
            self.hiding = False
        else:
            self.showing = True
            self.hiding = False
            self.didAnimate = False
            self.move(x, y)
            super().show()
            self.onAnimationDone()

    def hide(self, animate=True):
        if not self.parent() or not animate:
            super().hide()
            return
        if animate and isinstance(self.effect, QGraphicsOpacityEffect):
            self.showAnimation.setStartValue(1)
            self.showAnimation.setEndValue(0)
            self.showAnimation.start()
            self.didAnimate = True
        elif animate:
            self.showAnimation.setEasingCurve(QEasingCurve.InCubic)
            self.showAnimation.setStartValue(self.pos())
            self.showAnimation.setEndValue(QPointF(self.pos().x(), self.hiddenY))
            self.showAnimation.stop()
            self.showAnimation.start()
            self.showing = False
            self.hiding = True
            self.didAnimate = True
        else:
            self.showing = False
            self.hiding = True
            self.didAnimate = False
            self.onAnimationDone()
        self.startHiding.emit()

    def isShown(self):
        if self.hiding:
            return False
        elif self.isVisible() or self.showing:
            return True
        else:
            return False

    def onAnimationDone(self):
        self.showing = False
        self.hiding = False
        if isinstance(self.effect, QGraphicsOpacityEffect):
            if self.showAnimation.currentValue() == 0:
                super().hide()
        else:
            if self.pos().y() == self.hiddenY:
                super().hide()
        if self.didAnimate is True:
            self.popupAnimationDone.emit()
        self.didAnimate = None
