from pkdiagram.pyqt import (
    pyqtSignal,
    pyqtSlot,
    Qt,
    QFrame,
    QVBoxLayout,
    QVariantAnimation,
    QObject,
    QEvent,
    QCursor,
    QMargins,
    QWidget,
    QColor,
    QRect,
    QPen,
    QApplication,
    QPainter,
    QPalette,
    QStyleOption,
    QStyle,
    QAbstractAnimation,
)
from pkdiagram import util


class Drawer(QFrame):

    WIDTH = util.DRAWER_WIDTH
    OVER_WIDTH = util.DRAWER_OVER_WIDTH

    manuallyResized = pyqtSignal()

    # Signals the container that the drawer itself requested to hide, e.g. done
    # or cancel. Then the container can handle any response.
    hideRequested = pyqtSignal()

    def documentView(self):
        """Allows binding onDrawerAnimationStart for multiple Drawers (maybe for iOS?)."""
        if util.isInstance(self.parent(), "DocumentView"):
            return self.parent()
        elif self.parent() and util.isInstance(self.parent().parent(), "DocumentView"):
            return self.parent().parent()
        # else:
        #     self.here('View is null:', self, self.parent())

    def __init__(self, parent=None, resizable=False):
        super().__init__(parent)
        super().hide()

        self.scene = None  # convenience

        self.setAutoFillBackground(True)
        Layout = QVBoxLayout(self)
        Layout.setContentsMargins(1, 0, 0, 0)

        self.showing = False
        self.hiding = False
        self.expanding = False
        self.shrinking = False
        self.expanded = False
        self.shown = False
        self.resizable = False
        self.ideallyResizable = (
            resizable  # should resize, but temporarily not resizable (i.e. expanded)
        )
        self._lockResizeHandle = not resizable
        self.originalContentsMargins = None
        self.expandedContentsMargins = None

        self.isOverDrawer = None  # showing as secondary drawer over another drawer

        self.expandAnimation = QVariantAnimation(self)
        self.expandAnimation.setDuration(util.ANIM_DURATION_MS)
        self.expandAnimation.setEasingCurve(util.ANIM_EASING)
        self.expandAnimation.setStartValue(0.0)
        self.expandAnimation.setEndValue(1.0)
        self.expandAnimation.stateChanged.connect(self.onExpandAnimationStateChanged)
        self.expandAnimation.valueChanged.connect(self.onExpandAnimationTick)
        self.expandAnimation.finished.connect(self.onExpandAnimationFinished)

        # if resizable: # defer until after subclass ctor is finished
        #     QTimer.singleShot(0, self.setupResizable)
        # else:
        #     self.resizable = False
        #     self.setFixedWidth(self.WIDTH)

    def setupResizable(self):
        if self.resizable:
            return

        # Add a little padding-left so we can draw tha resize handle.
        class ResizeFilter(QObject):
            """Drag left side to resize"""

            def __init__(self, parent=None):
                super().__init__(parent)
                self.mouseDown = None
                self.mouseDownWidth = None
                self.mouseDownX = None
                self.minimumWidth = None
                self.parent().setMouseTracking(True)

            def inBounds(self, o, e):
                if self.parent()._lockResizeHandle:
                    return False
                if o is not self.parent():
                    return False
                margin = self.parent().layout().contentsMargins().left()
                return e.pos().x() < margin

            def eventFilter(self, o, e):
                if e.type() == QEvent.Enter:
                    if o is not self.parent():
                        self.parent().unsetCursor()
                    return False
                elif e.type() == QEvent.MouseButtonPress and self.inBounds(o, e):
                    self.mouseDown = e.globalPos()
                    self.mouseDownWidth = self.parent().width()
                    self.mouseDownX = self.parent().x()
                    return False
                elif e.type() == QEvent.MouseMove:
                    if self.inBounds(o, e) and not self.parent().expanded:
                        self.parent().setCursor(QCursor(Qt.SplitHCursor))
                    else:
                        self.parent().unsetCursor()
                        if not self.mouseDown:
                            return False
                    if self.mouseDown:
                        if self.minimumWidth is None:
                            self.minimumWidth = self.parent().width()
                        delta = e.globalPos().x() - self.mouseDown.x()
                        if not self.parent().expanded:
                            newWidth = max(
                                self.mouseDownWidth - delta, self.minimumWidth
                            )
                            newWidth = min(newWidth, self.parent().parent().width())
                            self.parent().resize(newWidth, self.parent().height())
                            maxX = (
                                self.parent().parent().width() - self.parent().width()
                            )
                            x = max(self.mouseDownX + delta, maxX)
                            x = min(x, maxX)
                            self.parent().move(x, self.parent().y())
                            self.parent().manuallyResized.emit()
                    return False
                elif e.type() == QEvent.MouseButtonRelease and o is self.parent():
                    self.parent().unsetCursor()
                    self.mouseDown = None
                    self.mouseDownWidth = None
                    self.mouseDownX = None
                    return False
                elif e.type() == QEvent.Leave:
                    self.parent().unsetCursor()
                return False

        if self.originalContentsMargins is None:
            self.originalContentsMargins = QMargins(self.layout().contentsMargins())
        self.setMinimumWidth(self.WIDTH)
        self.resize(self.WIDTH, self.height())
        margins = self.layout().contentsMargins()
        if margins.left() < util.RESIZE_HANDLE_WIDTH:
            margins.setLeft(util.RESIZE_HANDLE_WIDTH)
            self.expandedContentsMargins = margins
            self.layout().setContentsMargins(margins)
        self.resizeFilter = ResizeFilter(self)
        self.installEventFilter(self.resizeFilter)
        for child in self.findChildren(QWidget):
            child.installEventFilter(self.resizeFilter)
        if self.parent():
            self.resize(
                self.WIDTH, self.parent().height()
            )  # minimumWidth was being set to designer width. no idea.
        self.resizable = True

    def tearDownResizable(self):
        if not self.resizable:
            return
        self.removeEventFilter(self.resizeFilter)
        for child in self.findChildren(QWidget):
            child.removeEventFilter(self.resizeFilter)
        if self.ideallyResizable:
            self.setMinimumWidth(self.WIDTH)
        else:
            self.setFixedWidth(self.WIDTH)
        self.layout().setContentsMargins(self.originalContentsMargins)
        self.resizable = False

    def setScene(self, scene):
        """Really just here for testing."""
        self.scene = scene
        self.showing = False
        self.hiding = False
        self.expanding = False
        self.shrinking = False
        self.expanded = False
        self.shown = False
        if self.ideallyResizable:
            self.setupResizable()
        else:
            self.setFixedWidth(self.WIDTH)

    def deinit(self):
        if self.isVisible():
            self.hide(animate=False)

    def adjust(self):
        if self.showing or self.hiding or self.expanding or self.shrinking:
            return
        if self.parent():
            if self.isVisible():
                if self.expanded:
                    self.resize(self.parent().size())
                    self.move(0, 0)
                elif self.isVisible():
                    if self.ideallyResizable and not self.resizable:
                        self.resize(self.parent().size())
                    else:
                        self.resize(self.width(), self.parent().height())
                    self.move(self.parent().width() - self.width(), 0)
            else:
                self.move(self.parent().width(), 0)
                self.resize(self.width(), self.parent().height())

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setClipRegion(e.region())
        borderColor = QColor(util.QML_ITEM_BORDER_COLOR)
        # border-left: 1px solid lightGrey;
        outsideLeftRect = QRect(0, 0, 1, self.height())
        if e.region().intersects(outsideLeftRect):
            p.save()
            p.setPen(QPen(borderColor, 1))
            p.drawLine(outsideLeftRect.topLeft(), outsideLeftRect.bottomLeft())
            p.restore()
        # Resizable
        if not self.resizable or self._lockResizeHandle:
            p.save()
            p.setPen(QPen(borderColor, 1))
            p.drawLine(outsideLeftRect.topLeft(), outsideLeftRect.bottomLeft())
            p.restore()
        elif self.resizable and not self.expanded:
            if util.CUtil.instance().isUIDarkMode():
                if util.IS_IOS:
                    handleColor = QColor(util.QML_HEADER_BG)
                else:
                    handleColor = (
                        QApplication.instance().palette().color(QPalette.Button)
                    )
                handleEdgeColor = Qt.black
            else:
                handleColor = QColor(Qt.lightGray).lighter(130)
                handleEdgeColor = borderColor
            p.fillRect(
                QRect(0, 0, util.RESIZE_HANDLE_WIDTH, self.height()), handleColor
            )
            insideLeftRect = QRect(util.RESIZE_HANDLE_WIDTH, 0, 1, self.height())
            if e.rect().intersects(insideLeftRect):
                p.save()
                p.setPen(QPen(QColor(handleEdgeColor).lighter(110), 0))
                p.drawLine(
                    0, 0, 0, self.height()
                )  # insideLeftRect.topLeft(), insideLeftRect.bottomLeft())
                p.setPen(QPen(handleEdgeColor, 0))
                p.drawLine(
                    util.RESIZE_HANDLE_WIDTH, 0, util.RESIZE_HANDLE_WIDTH, self.height()
                )  # insideLeftRect.topLeft(), insideLeftRect.bottomLeft())
                p.restore()
            # Paint resize-handle on left side.
            opt = QStyleOption(0)
            opt.rect = QRect(0, 0, util.RESIZE_HANDLE_WIDTH, self.height())
            opt.state = QStyle.State_Horizontal
            opt.palette = self.palette()
            if e.rect().intersects(opt.rect):
                self.style().drawControl(QStyle.CE_Splitter, opt, p, self)
        # border-right: 1px solid grey;
        outsideRightRect = QRect(util.RESIZE_HANDLE_WIDTH - 1, 0, 1, self.height())
        if e.region().intersects(outsideRightRect):
            p.save()
            p.setPen(QPen(borderColor, 0))
            p.drawLine(outsideRightRect.topRight(), outsideRightRect.bottomRight())
            p.restore()
        p = None

    @staticmethod
    def shouldFullScreen():
        return util.IS_IPHONE

    def show(self, callback=None, animate=True, over=None):
        """
        over: open this drawer as secondary over another drawer.
        """
        if util.IS_TEST:
            animate = False
        self.isOverDrawer = over

        if self.resizable and self.shouldFullScreen():
            # the drawer is initially resizable but may be converted to
            # full screen once CUtil is initialized and operatingSystem()
            # can return a valid value
            self.tearDownResizable()

        if not self.resizable:
            if over:
                self.setFixedWidth(self.OVER_WIDTH)
            elif self.ideallyResizable:
                self.setMinimumWidth(self.WIDTH)
            else:
                self.setFixedWidth(self.WIDTH)

        def innerCallback():
            self.setFocus()
            if callback:
                callback()

        super().show()
        self.expandAnimation.stop()
        if animate:
            self.expandAnimation.setDuration(util.ANIM_DURATION_MS)
        else:
            self.expandAnimation.setDuration(0)
        # self.layout().setContentsMargins(QMargins(12, 12, 12, 12)) # bottom margin is wacky
        if self.expandAnimation.startValue() == self.expandAnimation.endValue():
            innerCallback()
            return
        elif callback:

            def doCallback():
                self.expandAnimation.finished.disconnect(doCallback)
                innerCallback()

            self.expandAnimation.finished.connect(doCallback)
        self.hiding = False
        self.showing = True
        self.expandAnimation.start()

    def hide(self, callback=None, animate=True, swapping=False):
        if util.IS_TEST:
            animate = False
        self.isOverDrawer = False
        if animate:
            self.expandAnimation.setDuration(util.ANIM_DURATION_MS)
        elif swapping:
            self.expandAnimation.setDuration(int(util.ANIM_DURATION_MS * 0.75))
        else:
            self.expandAnimation.setDuration(0)
        if callback:

            def doCallback():
                self.expandAnimation.finished.disconnect(doCallback)
                callback()

            self.expandAnimation.finished.connect(doCallback)
        self.expandAnimation.stop()
        if self.expandAnimation.startValue() == self.expandAnimation.endValue():
            if callback:
                callback()
            return
        self.hiding = True
        self.showing = False
        self.expandAnimation.start()
        self.raise_()  # makes a swap look cooler.

    def onDone(self):
        if self.documentView():
            self.documentView().setCurrentDrawer(None)
        else:
            self.hide()

    def onResize(self):
        self.toggleExpand()

    def updatePos(self):
        if not self.parent():
            return
        coeff = self.expandAnimation.currentValue()
        if self.showing:
            travelX = (
                self.parent().width() - self.width()
            ) - self._expandAnimStartGeo.x()
            travelW = 0
        elif self.hiding:
            travelX = self.parent().width() - self._expandAnimStartGeo.x()
            travelW = 0
        elif self.expanding or self.shouldFullScreen():
            travelX = -self._expandAnimStartGeo.x()
            travelW = self.parent().width() - self._expandAnimStartGeo.width()
        elif self.shrinking:
            # only shrinks after full window width
            travelX = self.parent().width() - self.WIDTH
            travelW = (self._expandAnimStartGeo.width() - self.WIDTH) * -1
        else:
            return
        x = self._expandAnimStartGeo.x() + travelX * coeff
        width = self._expandAnimStartGeo.width() + travelW * coeff
        self.setGeometry(int(x), self.y(), int(width), self.height())

    def onExpandAnimationStateChanged(self, newState, oldState):
        if newState == QAbstractAnimation.Running:
            self.onExpandAnimationStart()

    def onExpandAnimationStart(self):
        self._expandAnimStartGeo = self.geometry()
        # self.updatePos()
        if self.documentView():
            if self.showing:
                action = "showing"
            else:
                action = "hiding"
            self.documentView().onDrawerAnimationStart(
                self, action, self.expandAnimation.currentValue()
            )

    def onExpandAnimationTick(self, x):
        # valueChanged() is emitted even when just setting the end value
        if self.expandAnimation.state() == QAbstractAnimation.Running:
            self.updatePos()
            if self.documentView():
                progress = (
                    self.expandAnimation.currentTime()
                    / self.expandAnimation.totalDuration()
                )
                if self.hiding:
                    if progress == 0:
                        progress = 1.0
                    else:
                        progress = 1 - progress
                self.documentView().onDrawerAnimationTick(
                    self, self.expandAnimation.currentValue()
                )

    def onExpandAnimationFinished(self):
        self.updatePos()
        if self.documentView():
            self.documentView().onDrawerAnimationFinished(
                self, self.expandAnimation.currentValue()
            )
        if self.showing:
            self.showing = False
            self.shown = True
            if self.expandAnimation.duration() != util.ANIM_DURATION_MS:
                self.expandAnimation.setDuration(util.ANIM_DURATION_MS)
        elif self.hiding:
            self.hiding = False
            self.shown = False
            super().hide()
        elif self.expanding:
            self.expanded = True
            self.expanding = False
        elif self.shrinking:
            self.expanded = False
            self.shrinking = False
        if self.resizable:
            if self.expanded:
                self.layout().setContentsMargins(self.originalContentsMargins)
            else:
                self.layout().setContentsMargins(self.expandedContentsMargins)
        self.update()

    def isShown(self):
        return self.shown

    def expandTo(self, width, animate=True):
        if self.expanding or self.shrinking:
            return
        if not self.expanded:
            self.expanding = True
        else:
            self.shrinking = True
        if animate:
            self.expandAnimation.stop()
            self.expandAnimation.start()
        else:
            self.onExpandAnimationDone()

    @pyqtSlot()
    def toggleExpand(self):
        if self.expanded and not (self.expanding or self.shrinking):
            self.expandTo(self.WIDTH)
            self.documentView().session.trackView("Expand " + self.objectName())
        elif not (self.expanding or self.shrinking):
            self.documentView().session.trackView("Shrink " + self.objectName())
            if self.parent():
                self.expandTo(self.parent().width())
            else:
                self.expandTo(self.WIDTH)
        if self.documentView():
            self.documentView().scene.update()  # fixes bug where scene wouldn't update when hiding drawer.

    def setLockResizeHandle(self, on):
        self._lockResizeHandle = on
        self.update()
