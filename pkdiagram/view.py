import time
from .pyqt import *
from .pyqt import (
    QWidget,
    QGraphicsOpacityEffect,
    QPropertyAnimation,
    QPainterPath,
    QPainter,
    QPen,
    QBrush,
    QColor,
    QPointF,
    QAbstractAnimation,
    QFontMetrics,
    QGraphicsOpacityEffect,
)
from . import util, toolbars, objects, widgets, commands
from . import panzoom, dragpan, wheelzoom
from . import legend
from .helpoverlay import HelpOverlay


HOTSPOT_SIZE = 64


class DateLabel(QWidget):

    STROKE = 10

    def __init__(self, parent):
        super().__init__(parent)
        eff = QGraphicsOpacityEffect()
        self.setGraphicsEffect(eff)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        eff.setOpacity(0)
        self.flashAnimation = QPropertyAnimation(eff, bytes(b"opacity"))
        self.flashAnimation.setDuration(600)
        self.flashAnimation.setStartValue(0)
        self.flashAnimation.setEndValue(1)
        self.path = QPainterPath()

    def timerEvent(self, e):
        print(self.geometry())
        self.update()

    def sizeHint(self):
        stroker = QPainterPathStroker(QPen(self.STROKE))
        path = stroker.createStroke(self.path)
        return path.controlPointRect().toRect().size() + QSize(self.STROKE, self.STROKE)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        if util.IS_UI_DARK_MODE:
            p.strokePath(self.path, QPen(QBrush(QColor(0, 0, 0, 255)), self.STROKE))
            p.fillPath(self.path, QBrush(QColor("white")))
        else:
            p.strokePath(
                self.path, QPen(QBrush(QColor(255, 255, 255, 255)), self.STROKE)
            )
            p.fillPath(self.path, QBrush(QColor("black")))
        p = None
        super().paintEvent(e)

    def setText(self, x, flash=True):
        fm = QFontMetrics(util.CURRENT_DATE_FONT, self)
        self.path = QPainterPath()
        self.path.addText(
            QPointF(self.STROKE / 2, fm.height() + self.STROKE / 2),
            util.CURRENT_DATE_FONT,
            x,
        )
        self.resize(self.sizeHint())
        if flash:
            if self.flashAnimation.state() == QAbstractAnimation.Running:
                self.flashAnimation.stop()
            self.flashAnimation.start()

        self.update()


def quadrantFor(rect, pos):
    """Return which quadrant this point is in,
    overshot to handle out of bounds coordinates."""
    qrect = type(rect)
    w = rect.width() / 2
    h = rect.height() / 2
    topLeft = qrect(-10000, -10000, w + 10000, h + 10000)
    topRight = qrect(rect.width() / 2, -10000, 10000, 10000 + h)
    bottomRight = qrect(w, h, 10000, 10000)
    bottomLeft = qrect(-10000, h, 10000 + w, 10000)
    if topLeft.contains(pos):
        return "north-west", topLeft
    elif topRight.contains(pos):
        return "north-east", topRight
    elif bottomLeft.contains(pos):
        return "south-west", bottomLeft
    elif bottomRight.contains(pos):
        return "south-east", bottomRight
    else:
        raise ValueError("%s is not in a quadrant." % pos)


class View(QGraphicsView):

    LEGEND_MARGIN = util.BUTTON_SIZE

    zoomFitDirty = pyqtSignal(bool)
    escape = pyqtSignal()
    filePathDropped = pyqtSignal(str)

    _scene = None

    def __init__(self, parent, ui):
        super().__init__(parent)
        self.ui = ui
        self.mousePress = None
        self.touches = []
        self.lastZoomData = {
            "size": self.size(),
            "scale": 1.0,
            "viewableSceneRect": QRectF(),
            "fitRect": QRectF(),
        }
        self._isResizeEvent = False
        self.dragPanner = dragpan.DragPanner(self)
        self.wheelZoomer = wheelzoom.WheelZoomer(self)
        self.panZoomer = panzoom.PanZoomer(self)
        self.zoomScaleStart = None
        self.totalScaleFactor = 1.0
        self.pinchZooming = False
        self.dontInspect = False
        self.forceRightTBOffRightEdge_x = None  # hack to leave rightTB where the right edge will be after the drawer is hidden. Is the same as the drawerShim.width()
        self._zoomFitDirty = False
        self._zoomFitPendingTimer = QTimer(self, interval=100)
        self._zoomFitPendingTimer.timeout.connect(self.onPendingZoomFitTimer)
        self._finishingZoomFitAnim = False
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setFrameShadow(QFrame.Plain)
        self.setRenderHints(
            QPainter.Antialiasing
            | QPainter.HighQualityAntialiasing
            | QPainter.SmoothPixmapTransform
            | QPainter.TextAntialiasing
        )
        self.setDragMode(QGraphicsView.RubberBandDrag)
        # well, the bastard crashes when these are shown so just get rid of 'em
        # plus it's faster...
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.verticalScrollBar().valueChanged.connect(self.onScroll)
        self.horizontalScrollBar().valueChanged.connect(self.onScroll)
        self.setObjectName("view")
        QApplication.instance().paletteChanged.connect(self.onApplicationPaletteChanged)
        self.onApplicationPaletteChanged()
        # viewport().paintEngine() was NULL on first load on IOS, showing a black scene on first file load.
        # iOS should all be OpenGL anyway, so possibly no need to set it here...
        if util.ENABLE_OPENGL:
            vp = QOpenGLWidget()
            vp.setObjectName("viewViewport")
            fmt = QSurfaceFormat.defaultFormat()
            fmt.setSamples(util.OPENGL_SAMPLES)
            vp.setFormat(fmt)
            self.setViewport(vp)

        self.hiddenItemsLabel = QLabel(self)
        self.hiddenItemsLabel.setStyleSheet(
            """
        color: 'grey';
        font-family: '%s';
        font-size: 11px;
        qproperty-alignment: AlignRight;"""
            % util.FONT_FAMILY
        )

        self.noItemsCTALabel = QLabel(self)
        self.noItemsCTALabel.setText(util.S_NO_ITEMS_LABEL)
        font = QFont(util.NO_ITEMS_FONT_FAMILY, util.NO_ITEMS_FONT_PIXEL_SIZE * 2)
        font.setBold(True)
        self.noItemsCTALabel.setFont(font)
        self.noItemsCTALabel.setStyleSheet(f"color: {util.INACTIVE_TEXT_COLOR.name()}")
        self.noItemsCTALabel.setWordWrap(True)
        self.noItemsCTALabel.setMaximumWidth(util.NO_ITEMS_FONT_PIXEL_SIZE * 50)
        self.noItemsCTALabel.setAlignment(Qt.AlignCenter)

        self.zoomFitAnim = QVariantAnimation(self)
        self.zoomFitAnim.setDuration(util.ANIM_DURATION_MS)
        self.zoomFitAnim.setEasingCurve(util.ANIM_EASING)
        self.zoomFitAnim.valueChanged.connect(self.onZoomFitAnimTick)
        self.zoomFitAnim.finished.connect(self.onZoomFitAnimFinished)

        self.undoLabel = QLabel(self)
        self.undoLabel.setObjectName("undoLabel")
        self.undoLabel.resize(HOTSPOT_SIZE, HOTSPOT_SIZE)
        self.undoLabel.setScaledContents(True)
        self.undoLabel.setPixmap(QPixmap(util.QRC + "undo-button.png"))
        self.undoLabel.hide()
        eff = QGraphicsOpacityEffect(self.undoLabel)
        eff.setOpacity(0)
        self.undoLabel.setGraphicsEffect(eff)
        self.undoAnimation = QPropertyAnimation(eff, bytes(b"opacity"))
        self.undoAnimation.setDuration(1000)
        self.undoAnimation.setStartValue(1)
        self.undoAnimation.setEndValue(0)
        self.undoAnimation.finished.connect(self.onUndoRedoAnimFinished)

        self.redoLabel = QLabel(self)
        self.redoLabel.setObjectName("redoLabel")
        self.redoLabel.setPixmap(QPixmap(util.QRC + "redo-button.png"))
        self.redoLabel.resize(HOTSPOT_SIZE, HOTSPOT_SIZE)
        self.redoLabel.setScaledContents(True)
        self.redoLabel.hide()
        eff = QGraphicsOpacityEffect(self.redoLabel)
        eff.setOpacity(0)
        self.redoLabel.setGraphicsEffect(eff)
        self.redoAnimation = QPropertyAnimation(eff, bytes(b"opacity"))
        self.redoAnimation.setDuration(1000)
        self.redoAnimation.setStartValue(1)
        self.redoAnimation.setEndValue(0)
        self.redoAnimation.finished.connect(self.onUndoRedoAnimFinished)

        # double-tap hotspots
        self.undoHotspot = QRect()
        self.redoHotspot = QRect()
        self.lastMouseRelease = QTime.currentTime()

        # Current Date Label
        self.currentDateTimeLabel = DateLabel(self)
        self.currentDateTimeNormalPos = QPoint(5, 5)
        self.currentDateTimeLabel.move(self.currentDateTimeNormalPos)
        self.currentDateTimeShown = False

        self.showDateAnimation = QPropertyAnimation(
            self.currentDateTimeLabel, bytes(b"pos")
        )
        self.showDateAnimation.setDuration(util.ANIM_DURATION_MS)

        # Legend
        self.anchorIndicator = QWidget(self)
        self.anchorIndicator.setStyleSheet(
            """
        background-color: rgba(0, 20, 255, 15%);
        """
        )
        self.anchorIndicator.hide()
        self.legend = None

        self.helpOverlay = HelpOverlay(self)
        self.helpOverlay.setVisible(False, animate=False)

        # # Purchase Button
        # self.purchaseButton = widgets.PixmapPushButton(self,
        #                                                uncheckedPixmapPath=":/purchase-button.png",
        #                                                checkedPixmapPath=":/purchase-button-checked.png")
        # self.purchaseButton.setFixedSize(self.purchaseButton._uncheckedPixmap.size())
        # self.purchaseButton.setIconSize(self.purchaseButton._uncheckedPixmap.size())
        # if self.mw:
        #     self.purchaseButton.clicked.connect(self.mw.showAccount)
        # self.purchaseButton.hide()

        # Toolbars
        self.sceneToolBar = toolbars.SceneToolBar(self, ui)
        self.sceneTBAnimation = QPropertyAnimation(self.sceneToolBar, bytes(b"pos"))
        self.sceneTBAnimation.setDuration(util.ANIM_DURATION_MS)
        self.sceneTB_y = 0
        self.sceneToolBarShown = True
        #
        self.itemToolBar = toolbars.ItemToolBar(self, ui)
        self.itemTBAnimation = QPropertyAnimation(self.itemToolBar, bytes(b"pos"))
        self.itemTBAnimation.setDuration(util.ANIM_DURATION_MS)
        self.itemTB_x = 0
        self.itemToolBarShown = True
        #
        self.rightToolBar = toolbars.RightToolBar(self, ui)
        self.rightTBAnimation = QPropertyAnimation(self.rightToolBar, bytes(b"pos"))
        self.rightTBAnimation.setDuration(util.ANIM_DURATION_MS)
        self.rightTB_x = self.width() - self.rightToolBar.width()
        self.rightToolBarShown = True
        #
        self.showToolBarButton = widgets.PixmapPushButton(
            self, uncheckedPixmapPath=util.QRC + "hide-button.png"
        )
        eff = QGraphicsOpacityEffect()
        self.showToolBarButton.setGraphicsEffect(eff)
        eff.setOpacity(0)
        self.showTBButtonAnimation = QPropertyAnimation(eff, bytes(b"opacity"))
        self.showTBButtonAnimation.setDuration(util.ANIM_DURATION_MS)

        self.rightToolBar.raise_()

        # if util.IS_IOS and util.ENABLE_PENCIL: # Apple Pencil
        #     class AppFilter(QObject):
        #         def __init__(self, view):
        #             super().__init__(view)
        #             self.mw = view.mw
        #             self.app = QApplication.instance()
        #             self.app.installEventFilter(self)
        #             self.last = time.time()
        #             self.count = 0
        #         def eventFilter(self, o, e):
        #             if e.type() == QEvent.User: # QApplePencilEvent
        #                 #self.mw.here('>>>', time.time())
        #                 self.mw.scene.pencilEvent(e, e.point().point(), e.point().pressure())
        #                 was = self.last
        #                 now = time.time()
        #                 self.count += 1
        #                 if self.count > 20:
        #                     self.count = 0
        #                     fps = 1 / (now - was)
        #                     # self.mw.here('%.2f fps' % fps)
        #                 self.last = now
        #                 # self.mw.scene.update()
        #                 # self.mw.view.viewport().update()
        #                 return False
        #             elif e.type() == QEvent.MouseButtonPress:
        #                 self.here(QApplication.focusWidget())
        #             return False
        #     self.appFilter = AppFilter(self)

    ## Internal

    def scene(self):
        # Avoid latent timers accessing self.scene() after C++ object destroyed
        return self._scene

    def setScene(self, scene):
        if self.scene():
            self.scene().itemDragged.disconnect(self.onItemDragged)
            self.scene().itemRemoved.disconnect(self.onItemRemoved)
            self.scene().printRectChanged.disconnect(self.onScenePrintRectChanged)
            self.scene().propertyChanged[objects.Property].disconnect(
                self.onSceneProperty
            )
            self.scene().activeLayersChanged.disconnect(self.onActiveLayersChanged)
            self.scene().layerAnimationGroup.finished.disconnect(
                self.onLayerAnimationFinished
            )
            self.forceRightTBOffRightEdge_x = None
        super().setScene(scene)
        self._scene = scene
        self.sceneToolBar.setScene(scene)
        self.itemToolBar.setScene(scene)
        self.rightToolBar.setScene(scene)
        if scene:
            if self.legend:
                self.legend.setScene(scene)
                self.resetLegend(scene.legendData(), animate=False)
            scene.itemDragged.connect(self.onItemDragged)
            scene.itemAdded.connect(self.onItemAdded)
            scene.itemRemoved.connect(self.onItemRemoved)
            scene.printRectChanged.connect(self.onScenePrintRectChanged)
            scene.propertyChanged[objects.Property].connect(self.onSceneProperty)
            scene.activeLayersChanged.connect(self.onActiveLayersChanged)
            scene.layerAnimationGroup.finished.connect(self.onLayerAnimationFinished)
            self.onSceneProperty(scene.prop("currentDateTime"))
            if scene.people():
                self.noItemsCTALabel.hide()
            else:
                self.noItemsCTALabel.show()

            # auto-zoom fit on load screen
            # if this isn't delayed it gets the wrong scene rect, not sure why
            def delayedZoomFit():
                if self.scene():
                    self.zoomFit(animate=False, forLayers=self.scene().activeLayers())

            # One or the other are needed.
            QTimer.singleShot(10, delayedZoomFit)
            QTimer.singleShot(1000, delayedZoomFit)
            # init legend
            data = scene.legendData()
            if data["shown"]:
                self.onShowLegend(True, animate=False)
            else:
                self.onShowLegend(False, animate=False)
        else:
            if self.legend:
                self.legend.hide()
        self.adjust()
        self.updateSceneRect()
        self.viewport().setMouseTracking(True)

    def onApplicationPaletteChanged(self):
        self.setBackgroundBrush(util.WINDOW_BG)
        # if self.scene():
        #     # invalidate item caches
        #     for item in self.scene().items():
        #         item.setCacheMode(item.cacheMode())
        #     self.scene().update()

    def adjustToolBars(self):
        """Parsed out to adjust during show/hide animations."""
        size = self.size()
        self.sceneToolBar.adjust(size)
        margin = (self.width() - self.sceneToolBar.width()) / 2
        self.sceneToolBar.move(round(margin), round(self.sceneTB_y))
        #
        clipForSTB = False
        if self.sceneToolBar.x() < self.itemToolBar.width() + util.MARGIN_X:
            size.setHeight(size.height() - self.sceneToolBar.height())
            clipForSTB = True

        # item toolbar
        self.itemToolBar.adjust(size)
        if clipForSTB:
            yMiddle = (
                self.height() - self.itemToolBar.height()
            ) / 2  # after responsive
            y = yMiddle + (self.sceneToolBar.height() / 2)
        else:
            # just under the scene toolbar, right toolbar will match for symmetry
            y = self.sceneToolBar.height() + util.MARGIN_X
        self.itemToolBar.move(self.itemTB_x, round(y))

        # right toolbar, align top with item toolbar for symmetry
        self.rightToolBar.adjust(size)
        if self.forceRightTBOffRightEdge_x is None:
            # yMiddle = (self.height() - self.rightToolBar.height()) / 2 # after responsive
            # if clipForSTB and not clipForGT:
            #     y = yMiddle + (self.sceneToolBar.height() / 2)
            # elif not clipForSTB and clipForGT:
            #     y = yMiddle - ((self.height() - self.graphicalTimelineView.y()) / 2)
            # else:
            #     y = yMiddle
            if self.rightToolBarShown:
                self.rightTB_x = self.width() - self.rightToolBar.width()
            else:
                self.rightTB_x = self.width()
            self.rightToolBar.move(self.rightTB_x, self.itemToolBar.y())
        else:
            self.rightToolBar.move(
                (self.width() - self.rightToolBar.width())
                + self.forceRightTBOffRightEdge_x,
                self.itemToolBar.y(),
            )

    def adjust(self):
        if not self.scene():
            return

        self.adjustToolBars()
        self.helpOverlay.adjust()
        self.noItemsCTALabel.move(
            self.rect().center() - QPoint(self.noItemsCTALabel.rect().center())
        )
        #
        self.hiddenItemsLabel.move(
            self.width() - (self.hiddenItemsLabel.width() + 3), 0
        )
        # hotspots
        x = (self.width() / 2) - (self.undoLabel.width() / 2)
        y = (self.height() / 2) - (self.undoLabel.height() / 2)
        self.undoLabel.move(round(x), round(y))
        self.redoLabel.move(round(x), round(y))
        size = HOTSPOT_SIZE
        self.undoHotspot = QRect(0, self.viewport().height() - size, size, size)
        self.redoHotspot = QRect(
            self.viewport().width() - size, self.viewport().height() - size, size, size
        )
        #
        if not hasattr(self, "showTBButton_y"):
            self.showTBButton_y = self.sceneToolBar.hideButton.mapTo(
                self, QPoint(0, 0)
            ).y()
        p = self.sceneToolBar.hideButton.mapTo(self, QPoint(0, 0))
        p.setY(self.showTBButton_y)
        self.showToolBarButton.move(p)
        if self.scene() and self.legend and self.legend.isVisible():
            anchor = self.scene().legendData()["anchor"]
            pos = self.legendPosForAnchor(anchor)
            self.legend.move(pos, animate=False)
        # #
        # self.purchaseButton.move(self.width() - self.purchaseButton.width(), 0)

    ## Virtuals

    def resizeEvent(self, e):
        self._isResizeEvent = True
        super().resizeEvent(e)
        # self.adjust() # must happen here and in viewport event to be synchronous
        if self.scene():
            self.onViewableSceneRectChanged()
            fitRect = self.lastZoomData["viewableSceneRect"]
            # Don't write to self.lastZoomData['viewableSceneRect'] because we are trying to stick to the original
            self.fitInView(fitRect, Qt.KeepAspectRatio)
            self.updateHideSmallItems()
        self._isResizeEvent = False

    def wheelEvent(self, e):
        e.ignore()
        if self.panZoomer.begun():
            e.ignore()  # don't scroll
        elif self.wheelZoomer.begun():
            e.ignore()  # don't scroll
        # elif self.scene().isDraggingSomething():
        #     e.ignore()
        elif util.ENABLE_WHEEL_PAN:
            super().wheelEvent(e)

    def updateTouches(self, e):
        self.touches = [i for i in e.touchPoints()]

    def numTouches(self):
        return len(self.touches)
        ret = 0
        for t in self.touches:
            if t.state() & Qt.TouchPointPressed:
                ret += 1
        return ret

    def viewportEvent(self, e):
        if not self.scene():
            return super().viewportEvent(e)
        # cancel lingering wheel zoom
        if (
            e.type()
            in (
                QEvent.MouseButtonPress,
                QEvent.MouseMove,
                QEvent.MouseButtonRelease,
                QEvent.TouchBegin,
                QEvent.TouchEnd,
            )
            and self.wheelZoomer.begun()
        ):
            self.wheelZoomer.end()
        #
        if e.type() == QEvent.MouseButtonPress:
            self.mousePress = True
        elif e.type() == QEvent.MouseButtonRelease:
            self.mousePress = False
        # drag pan
        if isinstance(e, QInputEvent) and e.modifiers() & Qt.AltModifier:
            if e.type() == QEvent.Wheel:
                e.accept()
                if self.panZoomer.begun():
                    self.panZoomer.cancel()
                if not self.wheelZoomer.begun():
                    self.wheelZoomer.begin(e)
                self.wheelZoomer.update(e)
                return True
            elif e.type() == QEvent.MouseButtonPress:
                pos = self.mapToScene(e.pos())
                callouts = [
                    i for i in self.scene().items(pos) if isinstance(i, objects.Callout)
                ]
                if not callouts:
                    self.dragPanner.begin(e)
                else:
                    return super().viewportEvent(e)
                return True
            elif e.type() == QEvent.MouseMove and self.dragPanner.begun():
                self.dragPanner.update(e)
                return True
        if e.type() == QEvent.MouseMove:
            if self.dragPanner.begun():
                pass
            elif e.modifiers() & Qt.AltModifier:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.unsetCursor()
        elif e.type() == QEvent.MouseButtonRelease:
            if not e.modifiers() & Qt.AltModifier:
                self.unsetCursor()
            if self.dragPanner.begun():
                self.dragPanner.end(e)

        # if not util.ENABLE_PINCH_PAN_ZOOM:
        #     return super().viewportEvent(e)

        # pan zoom
        if e.type() == QEvent.TouchBegin and self.scene():
            # trackpad and not mouse on macOS; screen+converted to mouse if canceled on iOS
            e.accept()
            self.updateTouches(e)
            if self.numTouches() == 2:
                return True
            elif util.IS_IOS:
                for point in e.touchPoints():
                    scenePos = self.mapToScene(point.pos().toPoint())
                    if self.scene().selectableUnder(scenePos):
                        return False  # at least one finger on item
                if self.numTouches() == 1:
                    return False  # one finger on background (rubber band-select)
            return (
                True  # no more conversion to mouse events; disables rubber band-select
            )
        elif (
            e.type() == QEvent.TouchUpdate
            and self.scene()
            and not self.wheelZoomer.begun()
        ):
            self.updateTouches(e)
            canPinchZoom = False
            if util.IS_IOS:
                if self.numTouches() == 2 and self.rubberBandRect().isNull():
                    canPinchZoom = True
            else:
                if (
                    self.numTouches() == 2
                    and self.rubberBandRect().isNull()
                    and not self.mousePress
                ):
                    canPinchZoom = True
            if canPinchZoom:
                e.accept()
                if not self.panZoomer.begun():
                    sceneStartCenter = self.mapToScene(self.viewport().rect().center())
                    sceneStartScale = self.scene().scaleFactor()
                    crossed = self.panZoomer.test(
                        e.touchPoints(), sceneStartScale, sceneStartCenter
                    )
                    if crossed:
                        self.panZoomer.begin(
                            e.touchPoints(), sceneStartScale, sceneStartCenter
                        )
                if self.panZoomer.begun():
                    self.panZoomer.update(e.touchPoints())
                return True
            else:
                return super().viewportEvent(e)
        elif e.type() == QEvent.TouchEnd:
            self.updateTouches(e)
            begun = self.panZoomer.begun()
            self.panZoomer.end()
            if begun:
                e.accept()
                return True
        elif e.type() == QEvent.TouchCancel:
            self.updateTouches(e)
            begun = self.panZoomer.begun()
            self.panZoomer.cancel()
            if begun:
                e.accept()
                return True
        if e.type() == QEvent.Resize:
            self.adjust()  # must happen here and in resizeEvent to be synchronous
        return super().viewportEvent(e)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        # for double-tap hotspots, resize events
        diff = self.lastMouseRelease.elapsed()
        self.lastMouseRelease.start()
        if diff < QApplication.doubleClickInterval():
            if self.undoHotspot.contains(e.pos()):
                e.accept()
                if self.ui.actionUndo.isEnabled():
                    self.ui.actionUndo.trigger()
            elif self.redoHotspot.contains(e.pos()):
                e.accept()
                if self.ui.actionRedo.isEnabled():
                    self.ui.actionRedo.trigger()

    def onEscape(self):
        self.escape.emit()
        if self.scene():
            self.scene().clearSelection()
            self.scene().setItemMode(util.ITEM_NONE)
        return False

    def keyPressEvent(self, e):
        if QApplication.focusWidget() != self:  # how would this be possible
            return
        if e.key() in (Qt.Key_Escape,):
            self.onEscape()
        elif e.key() in (
            Qt.Key_Up,
            Qt.Key_Down,
            Qt.Key_Left,
            Qt.Key_Right,
            Qt.Key_PageUp,
            Qt.Key_PageDown,
        ):
            # disable arrow keys, page up/down, etc
            # These are the only keys the QGraphicsView/QAbstractScrollArea/QScrollArea implement anyway
            # super().keyPressEvent(e)
            e.ignore()
        else:
            super().keyPressEvent(e)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            for url in e.mimeData().urls():
                fileInfo = QFileInfo(url.toLocalFile())
                if (
                    fileInfo.isDir()
                    and QFileInfo(fileInfo.absolutePath()).suffix() == util.EXTENSION
                ):
                    e.acceptProposedAction()
                    return

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, e):
        e.acceptProposedAction()
        if e.mimeData().urls():
            self.filePathDropped.emit(e.mimeData().urls()[0].toLocalFile())

    ## Events

    @util.blocked
    def onSceneProperty(self, prop):
        if prop.name() == "currentDateTime":
            s = util.dateString(prop.get())
            self.currentDateTimeLabel.setText(s)
            self.updateHiddenItemsLabel()
        elif prop.name() == "hideToolBars":
            self.setSceneToolBarShown(not prop.get())
            self.setItemToolBarShown(not prop.get())
            self.setRightToolBarShown(not prop.get())
            self.setCurrentDateShown(not prop.get())
        elif prop.name() == "hideEmotionalProcess":
            on = not prop.get()
            self.itemToolBar.conflictButton.setEnabled(on)
            self.itemToolBar.projectionButton.setEnabled(on)
            self.itemToolBar.cutoffButton.setEnabled(on)
            self.itemToolBar.fusionButton.setEnabled(on)
            self.itemToolBar.distanceButton.setEnabled(on)
            self.itemToolBar.awayButton.setEnabled(on)
            self.itemToolBar.towardButton.setEnabled(on)
            self.itemToolBar.definedSelfButton.setEnabled(on)
            self.itemToolBar.insideButton.setEnabled(on)
            self.itemToolBar.outsideButton.setEnabled(on)
        elif prop.name() == "legendData":
            if self.legend:
                self.resetLegend(prop.get(), animate=True)
        elif prop.name() in ["tags"]:
            if not self.isZoomFitDirty():
                self.zoomFit()

    def numAnimatingItems(self):
        if not self.scene():
            return 0
        nAnimating = 0
        for item in self.scene().items():
            if isinstance(item, objects.Person) and item.animatingPos:
                nAnimating += 1
            elif (
                isinstance(item, objects.PathItem)
                and item.opacityAnimation.state() == QAbstractAnimation.Running
            ):
                nAnimating += 1
        return nAnimating

    def onActiveLayersChanged(self):
        """Wait to call zoomFit until after the layer animation is completed."""
        fitRect = self.getZoomFitRect(forLayers=self.scene().activeLayers())
        lastFitRect = self.lastZoomData["fitRect"]
        if (
            fitRect != lastFitRect
            and not self._zoomFitPendingTimer.isActive()
            and not self.scene().isAddingLayerItem()
        ):
            self.zoomFit(forLayers=self.scene().activeLayers())
            # Disable this in favor of a synchronous animation.
            # if self.numAnimatingItems() > 0:
            #     self._zoomFitPendingTimer.start()
            # else:
            #     self.onPendingZoomFitTimer()
        # self.updateHiddenItemsLabel()

    def onLayerAnimationFinished(self):
        self.updateHiddenItemsLabel()

    def updateHiddenItemsLabel(self):
        nVisiblePeople = sum([1 for p in self.scene().people() if not p.isVisible()])
        layerNames = ", ".join([layer.name() for layer in self.scene().activeLayers()])
        if nVisiblePeople or layerNames:
            s = "%s" % util.dateString(self.scene().currentDateTime())
            if layerNames:
                if len(self.scene().activeLayers()) > 1:
                    s = s + " Views: %s" % layerNames
                else:
                    s = s + " View: %s" % layerNames
            if nVisiblePeople:
                s = s + "  (Hiding %i people)" % nVisiblePeople
            self.hiddenItemsLabel.setText(s)
            self.hiddenItemsLabel.adjustSize()
            self.hiddenItemsLabel.show()
            self.adjust()
        else:
            self.hiddenItemsLabel.hide()

    def onPendingZoomFitTimer(self):
        nAnimating = self.numAnimatingItems()
        if nAnimating > 0:
            return
        self.zoomFit(forLayers=self.scene().activeLayers())
        self._zoomFitPendingTimer.stop()

    def onUndo(self):
        """Double-tap hotspot"""
        self.undoLabel.show()
        self.undoAnimation.stop()
        self.undoAnimation.start()

    def onRedo(self):
        """Double-tap hotspot"""
        self.redoLabel.show()
        self.redoAnimation.stop()
        self.redoAnimation.start()

    def onUndoRedoAnimFinished(self):
        self.undoLabel.hide()
        self.redoLabel.hide()

    def onPopUpHiding(self):
        pass

    ## Legend

    def resetLegend(self, data, animate=False):
        """Just to keep this with the other legend methods."""
        # self.legend.resize(data['size'])
        if data["shown"]:
            newPos = self.legendPosForAnchor(data["anchor"])
            if data["shown"] != self.legend.isVisible():
                self.legend.show(endPos=newPos, animate=animate)
            else:
                self.legend.move(newPos, animate=animate)
        else:
            self.legend.hide(animate=animate)

    def legendPosForAnchor(self, anchor):
        if anchor == "north-west":
            newPos = QPoint(self.LEGEND_MARGIN, self.LEGEND_MARGIN)
        elif anchor == "north-east":
            newPos = QPoint(
                self.width() - self.legend.width() - self.LEGEND_MARGIN,
                self.LEGEND_MARGIN,
            )
        elif anchor == "south-east":
            newPos = QPoint(
                self.width() - self.LEGEND_MARGIN - self.legend.width(),
                self.height() - self.LEGEND_MARGIN - self.legend.height(),
            )
        elif anchor == "south-west":
            newPos = QPoint(
                self.LEGEND_MARGIN,
                self.height() - self.LEGEND_MARGIN - self.legend.height(),
            )
        return newPos

    def onLegendDragPress(self, globalPos):
        anchor, rect = quadrantFor(self.rect(), self.mapFromGlobal(globalPos))
        self.anchorIndicator.setGeometry(rect)
        self.anchorIndicator.show()

    onLegendDragMove = onLegendDragPress

    def onLegendDragRelease(self, globalPos):
        anchor, handleRect = quadrantFor(self.rect(), self.mapFromGlobal(globalPos))
        newPos = self.legendPosForAnchor(anchor)
        if newPos != self.legend.pos():
            self.legend.move(newPos, animate=True)
        self.anchorIndicator.hide()

    def onShowLegend(self, on, animate=True):
        if on:
            if self.legend is None:
                self.legend = legend.Legend(self)
                self.legend.dragPress.connect(self.onLegendDragPress)
                self.legend.dragMove.connect(self.onLegendDragMove)
                self.legend.dragRelease.connect(self.onLegendDragRelease)
                self.legend.popupAnimationDone.connect(self.onLegendChanged)
                self.legend.resizeDone.connect(self.onLegendChanged)
                self.legend.hide(animate=False)
                self.legend.init(self.scene())
                self.legend.stackUnder(self.itemToolBar)
            anchor = self.scene().legendData()["anchor"]
            endPos = self.legendPosForAnchor(anchor)
            self.legend.show(endPos=endPos, animate=animate)
        else:
            if self.legend:
                self.legend.hide(animate=animate)

    @util.blocked
    def onLegendChanged(self):
        if not self.scene():  # closing
            return
        anchor = quadrantFor(self.rect(), self.legend.pos())[0]
        self.scene().setLegendData(
            {
                "shown": self.legend.isShown(),
                "size": self.legend.size(),
                "anchor": anchor,
            },
            undo=True,
        )

    ## Actions

    def nudgeLeft(self):
        self.scene().nudgeSelection(QPointF(-1, 0))

    def nudgeRight(self):
        self.scene().nudgeSelection(QPointF(1, 0))

    def nudgeUp(self):
        self.scene().nudgeSelection(QPointF(-0, -1))

    def nudgeDown(self):
        self.scene().nudgeSelection(QPointF(0, 1))

    def hardNudgeLeft(self):
        self.scene().nudgeSelection(QPointF(-10, 0))

    def hardNudgeRight(self):
        self.scene().nudgeSelection(QPointF(10, 0))

    def hardNudgeUp(self):
        self.scene().nudgeSelection(QPointF(0, -10))

    def hardNudgeDown(self):
        self.scene().nudgeSelection(QPointF(0, 10))

    def zoomAbsolute(self, x, remember=True):
        """Set the zoom immediately. Used for anim ticks."""
        if not self.scene():
            return
        x = min(max(0.07, x), 50.0)
        self.itemToolBar.onPencilSlider(100 / x)
        self.setTransform(QTransform.fromScale(x, x))
        self.scene().setScaleFactor(x)
        self.storeLastZoom()
        self.updateSceneRect()
        self.onViewableSceneRectChanged()
        self.updateHideSmallItems()

    def panAbsolute(self, p):
        """Set the pan immediately. Used for anim ticks."""
        if not self.scene():
            return
        self.centerOn(p)
        self.onViewableSceneRectChanged()

    def zoomIn(self):
        x = self.scene().scaleFactor()
        x = x + (x * 0.25)
        self.zoomAbsolute(x)

    def zoomOut(self):
        x = self.scene().scaleFactor()
        x = x - (x * 0.25)
        self.zoomAbsolute(x)

    def setShowHelpTips(self, on):
        self.helpOverlay.setVisible(on)

    ## Scene rect mgmt

    def sceneCenter(self):
        return self.mapToScene(self.viewport().rect().center())

    def viewableSceneRect(self):
        vpRect = QRect(0, 0, self.viewport().width(), self.viewport().height())
        return self.mapToScene(vpRect).boundingRect()

    def getZoomFitRect(self, forLayers=None):
        printRect = self.scene().getPrintRect(forLayers=forLayers)
        # Add extra margins for the toolbars if shown
        if self.itemToolBarShown or self.sceneToolBarShown:
            hM = printRect.width() * 0.1
            vM = printRect.height() * 0.1
            adjustedPrintRect = printRect.marginsAdded(QMarginsF(hM, vM, hM, 0))
        else:
            adjustedPrintRect = printRect
        # the items bounding rect will never be centered, so translate
        # the minimum rect to avoid a union displaying the items off center.
        minimumSceneRect = util.MINIMUM_SCENE_RECT.translated(
            adjustedPrintRect.center()
        )
        # ensure that the zoom doesn't go too far into only a few items.
        fitRect = minimumSceneRect.united(adjustedPrintRect)
        return fitRect

    def storeLastZoom(self):
        """Called when zoomed by wheel or pinch, and by zoom anim."""
        self.lastZoomData["size"] = self.size()
        self.lastZoomData["scale"] = self.scene().scaleFactor()
        self.lastZoomData["viewableSceneRect"] = self.viewableSceneRect()

    def isZoomFitDirty(self):
        """Clicking the zoom button would have some effect."""
        return self._zoomFitDirty

    def setZoomFitDirty(self, on):
        """
        Update zoomFitDirty when when:
            - View.sceneRect changes
            - pan|zoom changes
        """
        if on != self._zoomFitDirty:
            self._zoomFitDirty = on
            self.zoomFitDirty.emit(on)

    def checkZoomFitDirty(self):
        if self.scene():
            # the accuracy of this is questionable due to imprecise behavior of fitInView()??
            vsr = self.viewableSceneRect()
            fitRect = self.getZoomFitRect(forLayers=self.scene().activeLayers())
            on = vsr == fitRect
        else:
            on = False
        self.setZoomFitDirty(on)

    def getVisibleSceneScaleRatio(self):
        sceneRect = self.mapFromScene(QRectF(0, 0, 100, 100)).boundingRect()
        return sceneRect.width() / 100.0

    def updateHideSmallItems(self):
        if self.scene():
            ratio = self.getVisibleSceneScaleRatio()
            for item in self.scene().itemDetails():
                item.onVisibleSizeChanged(self, ratio)

    def onItemAdded(self, item):
        if item.isItemDetails:
            ratio = self.getVisibleSceneScaleRatio()
            item.onVisibleSizeChanged(self, ratio)
        if item.isPerson:
            self.noItemsCTALabel.hide()

    def onItemRemoved(self, item):
        if item.isPerson and len(self.scene().people()) == 0:
            self.noItemsCTALabel.show()

    def onItemDragged(self, item):
        if self.panZoomer.begun():
            self.panZoomer.cancel()

    def onScroll(self):
        if (
            self.parent()
            and not self.parent().isAnimatingDrawer
            and not self._isResizeEvent
        ):  # always retain original for animations+resizes
            self.lastZoomData["viewableSceneRect"] = self.viewableSceneRect()

    def onViewableSceneRectChanged(self):
        """Update print rect item."""
        if self.scene():
            if self.zoomFitAnim.state() != QAbstractAnimation.Running:
                self.setZoomFitDirty(True)
            self.scene().pencilCanvas.setRect(self.viewableSceneRect())

    def updateSceneRect(self, emitZoomFitDirty=True):
        """Update View.sceneRect (scrollable area) w margin rel. to vsr size when:
        - Scene.printRect has changed
        - Scene.printRect is not contained by current View.sceneRect
        - Zoom changes (not pan)
        """
        if not self.scene():
            return
        # 1) prevent view from scrolling because item bounding rect is too small or out of range
        printRect = self.scene().printRect(forLayers=self.scene().activeLayers())
        # Prevent view scrolling/jumping of first few people in new diagram.
        if self._finishingZoomFitAnim:
            return
        elif self.sceneRect() != util.MAXIMUM_SCENE_RECT and self.sceneRect().contains(
            printRect
        ):
            return
        vsr = self.viewableSceneRect()
        # set margin size in relation to viewable rect at current zoom
        mW = vsr.width() * 0.45
        mH = vsr.height() * 0.45
        potentialSceneRect = printRect.marginsAdded(QMarginsF(mW, mH, mW, mH))
        # the items bounding rect will never be centered, so translate
        # the minimum rect to avoid a union displaying the items off center.
        minimumSceneRect = util.MINIMUM_SCENE_RECT.translated(
            potentialSceneRect.center()
        )
        # ensure that the zoom doesn't go too far into only a few items.
        newSceneRect = minimumSceneRect.united(potentialSceneRect)
        center = (
            vsr.center()
        )  # >>> prevent scrolling from occuring (this method should not change viewable area/center point)
        self.setSceneRect(newSceneRect)
        self.centerOn(
            center
        )  # <<< prevent scrolling from occuring (this method should not change viewable area/center point)
        self.scene().viewSceneRectItem.setRect(self.sceneRect())
        if emitZoomFitDirty:
            self.setZoomFitDirty(True)

    def onScenePrintRectChanged(self):
        self.updateSceneRect()

    def zoomFit(self, dummy=None, animate=True, forLayers=None):
        """Move items to fit around scene center and zoom to fit."""
        # self.centerOn(QPointF(0, 0))
        if not self.scene():
            return
        people = [p for p in self.scene().people() if p.isVisible()]
        nPeople = len(people)
        vsr = self.viewableSceneRect()
        if nPeople == 0:
            self.zoomAbsolute(util.DEFAULT_SCENE_SCALE)
            self.setZoomFitDirty(
                False
            )  # so that it re-zoomFits when people are shown again
        else:
            # temporarily set sceneRect to super huge to avoid scrollbar limits interfering with zoom-panning
            self.setSceneRect(util.MAXIMUM_SCENE_RECT)
            fitRect = self.getZoomFitRect(forLayers=forLayers)
            if fitRect == vsr:
                self.setZoomFitDirty(False)
                return
            self.lastZoomData["fitRect"] = fitRect
            if self.zoomFitAnim.state() == QAbstractAnimation.Running:
                self.zoomFitAnim.stop()
            self.zoomFitAnim.setStartValue(vsr)
            self.zoomFitAnim.setEndValue(fitRect)
            if animate:
                self.zoomFitAnim.start()
            else:
                self.onZoomFitAnimTick(fitRect)
                self.onZoomFitAnimFinished()

    def onZoomFitAnimTick(self, x):
        if x is not None:  # bug somewhere else
            self.fitInView(x, Qt.KeepAspectRatio)

    def onZoomFitAnimFinished(self):
        """View.updateSceneRect() is called from more than one of these calls.
        Remember, the goal of updateSceneRect is to update the scrollable area without altering the center point.
        """
        self._finishingZoomFitAnim = True  # Don't call updateSceneRect() because it causes a jump for some reason.
        self.scene().setScaleFactor(self.transform().m11())  # x scale; y scale = m22()
        self.storeLastZoom()
        self.setZoomFitDirty(False)
        self.scene().checkPrintRectChanged()  # after Item animations
        self._finishingZoomFitAnim = False
        self.updateSceneRect()
        self.updateHideSmallItems()

    def onShowCurrentDateTime(self, on):
        self.currentDateTimeLabel.setVisible(on)

    ## Actions

    def setCurrentDateShown(self, on):
        self.currentDateTimeShown = on
        if on:
            self.showDateAnimation.setEndValue(
                QPoint(
                    self.currentDateTimeLabel.x(), -self.currentDateTimeLabel.height()
                )
            )
        else:
            self.showDateAnimation.setEndValue(self.currentDateTimeNormalPos)
        self.showDateAnimation.setStartValue(self.currentDateTimeLabel.pos())
        self.showDateAnimation.start()

    def setSceneToolBarShown(self, on):
        self.sceneToolBarShown = on
        if on:
            self.sceneTB_y = 0
            self.showTBButtonAnimation.setStartValue(1.0)
            self.showTBButtonAnimation.setEndValue(0)
        else:
            self.sceneTB_y = -self.sceneToolBar.height() - 10  # for the shadow
            self.showTBButtonAnimation.setStartValue(0)
            self.showTBButtonAnimation.setEndValue(1.0)
        self.sceneTBAnimation.setStartValue(self.sceneToolBar.pos())
        self.sceneTBAnimation.setEndValue(QPoint(self.sceneToolBar.x(), self.sceneTB_y))
        self.sceneTBAnimation.start()
        self.showTBButtonAnimation.start()

    def setItemToolBarShown(self, on):
        self.itemToolBarShown = on
        if on:
            self.itemTB_x = 0
        else:
            self.itemTB_x = -self.itemToolBar.width()
        self.itemTBAnimation.stop()
        self.itemTBAnimation.setStartValue(self.itemToolBar.pos())
        self.itemTBAnimation.setEndValue(QPoint(self.itemTB_x, self.itemToolBar.y()))
        self.itemTBAnimation.start()

    def setRightToolBarShown(self, on):
        self.rightToolBarShown = on
        if on:
            self.rightTB_x = self.width() - self.rightToolBar.width()
        else:
            self.rightTB_x = self.width()
        self.rightTBAnimation.stop()
        self.rightTBAnimation.setStartValue(self.rightToolBar.pos())
        self.rightTBAnimation.setEndValue(QPoint(self.rightTB_x, self.rightToolBar.y()))
        self.rightTBAnimation.start()

    def addParentsToSelection(self):
        selectedPeople = self.scene().selectedPeople()
        if not selectedPeople:
            return
        for person in selectedPeople:
            rect = person.mapToScene(person.boundingRect()).boundingRect()
            fatherPos = person.pos() - QPointF(rect.width() * 1.5, rect.height() * 2)
            motherPos = person.pos() - QPointF(rect.width() * -1.5, rect.height() * 2)
            father = commands.addPerson(self.scene(), "male", fatherPos, person.size())
            mother = commands.addPerson(
                self.scene(), "female", motherPos, person.size()
            )
            marriage = commands.addMarriage(self.scene(), father, mother)
            commands.setParents(person, marriage)

    def showItemsWithNotes(self, on):
        if self.scene():
            self.scene().setShowNotesIcons(on)


def __test__(scene, parent):
    w = View(parent, None)
    w.init()
    w.setScene(scene)
    w.show()
    parent.resize(800, 600)
    scene.setItemMode(util.ITEM_MALE)
    return w
