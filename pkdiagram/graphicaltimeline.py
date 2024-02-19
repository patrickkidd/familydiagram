import logging
from .pyqt import *
from . import util
from .graphicaltimelinecanvas import GraphicalTimelineCanvas


log = logging.getLogger(__name__)


class GraphicalTimeline(QScrollArea):
    """Scroll area container for a GraphicalTimelineView that contains a GraphicalTimelineCanvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scene = None
        self.nominalWidth = 0
        self.scaleFactor = 1.0
        self.tags = []  # cache to maintain click order
        self.heightMultiplier = None
        self._freezeScroll = False
        self._isResizeEvent = False
        self._isWheelEvent = False
        self._expandedHScrollCoeff = 1.0
        self.horizontalScrollBar().valueChanged.connect(self.onHScroll)

        self.controls = QWidget(self)
        ControlsLayout = QHBoxLayout(self.controls)
        m = util.MARGIN_X
        ControlsLayout.setContentsMargins(m, m, m, m)

        self.heightLabel = QLabel("Height", self.controls)
        ControlsLayout.addWidget(self.heightLabel)

        self.heightSlider = QSlider(Qt.Horizontal, self.controls)
        self.heightSlider.setMinimum(100)
        self.heightSlider.setMaximum(175)
        self.heightSlider.setValue(100)
        self.heightSlider.setMinimumWidth(150)
        ControlsLayout.addWidget(self.heightSlider)

        self.sullivanianTimeBox = QCheckBox("Sullivanian Time", self.controls)
        ControlsLayout.addWidget(self.sullivanianTimeBox)

        self.canvas = GraphicalTimelineCanvas(self)
        self.setWidget(self.canvas)
        self.canvas.wheel[QWheelEvent].connect(self.wheelEvent)
        self.canvas.mouseButtonClicked[QPoint].connect(self.onCanvasMouseButtonClicked)
        self.sullivanianTimeBox.setChecked(self.canvas.sullivanianTime)
        self.sullivanianTimeBox.toggled[bool].connect(self.canvas.setSullivanianTime)
        self.heightSlider.setValue(self.heightSlider.minimum())
        self.heightSlider.valueChanged[int].connect(self.setRowHeight)
        self.scaleFactor = 1.0
        self.nominalWidth = self.canvas.width()
        QScroller.grabGesture(self.viewport(), QScroller.LeftMouseButtonGesture)

        self.controls.hide()

    def setScene(self, scene):
        if self.scene:
            self.scene.searchModel.tagsChanged.disconnect(self.onSearchTagsChanged)
            self.scene.searchModel.changed.disconnect(self.onSearchChanged)
        self.scene = scene
        if self.scene:
            self.scene.searchModel.tagsChanged.connect(self.onSearchTagsChanged)
            self.scene.searchModel.changed.connect(self.onSearchChanged)
        self.canvas.setScene(self.scene)
        self.canvas.resize(self.size())
        self.zoomAbsolute(self.scaleFactor)
        self.tags = []

    def onSearchTagsChanged(self, tags):
        self.setTags(tags)

    def onSearchChanged(self):
        self.zoomAbsolute(1.0)

    def wheelEvent(self, e):
        if self.isSlider():
            return
        self._isWheelEvent = True
        if util.IS_WINDOWS:
            delta = e.angleDelta().x()
        else:
            delta = e.pixelDelta().y()
        if e.modifiers() & Qt.AltModifier and delta:
            e.accept()
            self.scaleFactor = self.scaleFactor + delta * -0.002
            if self.scaleFactor < 1.0:
                self.scaleFactor = 1.0
                self.nominalWidth = self.rect().width()
            self.zoomAbsolute(self.scaleFactor, forWheelEvent=True)
        else:
            super().wheelEvent(e)
        self._isWheelEvent = False

    def resizeEvent(self, e):
        self._isResizeEvent = True
        # maintain scroll on manual resize (1)
        if (
            self.parent()
            and self.parent().animation.state() != QAbstractAnimation.Running
        ):
            hScroll = self.horizontalScrollBar()
            if hScroll.maximum() != hScroll.minimum():
                hCoeff = hScroll.value() / (
                    hScroll.maximum() - hScroll.minimum()
                )  # save relative scroll position
            else:
                hCoeff = 1.0
        super().resizeEvent(e)
        self.adjust()
        self._isResizeEvent = False
        # maintain scroll on manual resize (2)
        if (
            self.parent()
            and self.parent().animation.state() != QAbstractAnimation.Running
        ):
            newHScroll = (hScroll.maximum() - hScroll.minimum()) * hCoeff
            hScroll.setValue(round(newHScroll))

    def onHScroll(self, x):
        return
        if (
            self._isResizeEvent
            or self.parent().animation.state() == QAbstractAnimation.Running
        ):
            return
        hScroll = self.horizontalScrollBar()
        if hScroll.maximum() != hScroll.minimum():
            self._expandedHScrollCoeff = hScroll.value() / (
                hScroll.maximum() - hScroll.minimum()
            )  # save relative scroll position
        else:
            self._expandedHScrollCoeff = 1.0

    def showEvent(self, e):
        self.adjustCanvas()
        self.sullivanianTimeBox.adjustSize()

    def zoomAbsolute(self, x, forWheelEvent=False):
        self.scaleFactor = x
        self.adjustCanvas(forWheelEvent=forWheelEvent)

    def adjustCanvas(self, forWheelEvent=False):
        if not self.canvas:
            return
        # the x coeff should remain the same regardless of zoom;
        # save these before adjusting canvas size
        xCanvasOrig = self.canvas.mapFromGlobal(QCursor.pos()).x()
        origWidth = self.canvas.width()
        if origWidth:
            xCoeffOrig = xCanvasOrig / origWidth
        else:
            xCoeffOrig = 1
        #
        height = self.viewport().height()
        width = round(
            self.viewport().width() * self.scaleFactor
        )  # self.canvas.RIGHT_MARGIN
        if self.heightMultiplier is not None:
            height = round(height * self.heightMultiplier)
        self.canvas.resize(width, height)

        if not forWheelEvent:
            return

        # For QScrollArea, the range of the scroll bars match the
        # number of widget pixels outside of viewport
        if origWidth:
            xScaleDelta = self.canvas.width() / origWidth
        else:
            xScaleDelta = 1
        xCanvasNew = xCanvasOrig * xScaleDelta
        xCanvasDelta = xCanvasNew - xCanvasOrig
        hScroll = self.horizontalScrollBar()
        hNew = hScroll.value() + xCanvasDelta
        hScroll.setValue(round(hNew))

    def adjust(self):
        self.adjustCanvas()
        y = self.height() - self.controls.height() - 10
        self.controls.move(12, y)
        # self.sullivanianTimeBox.move(10, y)
        # self.heightSlider.move(self.sullivanianTimeBox.x() + self.sullivanianTimeBox.width(), y)

    def updatePersonNames(self):
        self.update()  # just repaint

    def setIsSlider(self, on):
        self.canvas.setIsSlider(on)
        self.updateControls()

    def isSlider(self):
        return self.canvas.isSlider()

    def updateControls(self):
        self.controls.setVisible(bool(self.tags) and not self.isSlider())
        if self.sullivanianTimeBox.isChecked() and len(self.tags) < 2:
            self.canvas.setSullivanianTime(False)
        elif self.sullivanianTimeBox.isChecked() and len(self.tags) >= 2:
            self.canvas.setSullivanianTime(True)

    def setTags(self, tags):
        if tags is None:
            tags = []
        # remove tags
        for oldTag in list(self.tags):
            if not oldTag in tags:
                self.tags.remove(oldTag)
        # add tags
        for tag in tags:
            if not tag in self.tags:
                self.tags.append(tag)
        self.canvas.refresh()  # min canvas height maybe changed
        self.updateControls()

    def setRowHeight(self, x):
        if self.tags:
            self.heightMultiplier = x / 100.0
        else:
            self.heightMultiplier = None
        self.adjust()

    def onCanvasMouseButtonClicked(self, pos):
        if self.scene:
            firstEvent, lastEvent = self.canvas.firstAndLast(events=self.canvas._events)
            dateTime = self.canvas._dateTimeForPoint(pos)
            if dateTime > lastEvent.dateTime():
                dateTime = lastEvent.dateTime()
            elif dateTime < firstEvent.dateTime():
                dateTime = firstEvent.dateTime()
            self.scene.setCurrentDateTime(dateTime)

    def onPrint(self):
        if not util.IS_IOS:
            from .pyqt import QPrinter, QPrintDialog
        printer = QPrinter()
        if printer.outputFormat() != QPrinter.NativeFormat:
            QMessageBox.information(
                self,
                "No printers available",
                "You need to set up a printer on your computer before you use this feature.",
            )
            return
        dlg = QPrintDialog(printer, self)
        ret = dlg.exec()
        if ret != QDialog.Accepted:
            self.writeImage(printer=printer)

    def onSaveAs(self):
        import os.path

        desktopPath = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
        filePath = util.prefs().value(
            "lastFileSavePath", type=str, defaultValue=desktopPath
        )
        if self.scene.shouldShowAliases():
            fileName = "[%s]" % self.scene.alias
        else:
            fileName = QFileInfo(self.scene.document.url().toLocalFile()).fileName()
        if QFileInfo(filePath).isFile():
            dirPath = QFileInfo(filePath).dir().absolutePath()
        else:
            dirPath = filePath
        filePath = os.path.join(dirPath, fileName)
        if util.suffix(filePath) == util.EXTENSION:
            filePath = filePath[: -len(util.EXTENSION)] + "jpg"
        filePath, types = QFileDialog.getSaveFileName(
            self,
            "Save File",
            filePath,
            "Image JPEG (*.jpg *.jpeg);; Image PNG (*.png)",
            "Image JPEG (*.jpg *.jpeg)",
        )
        if not filePath:
            return
        ext = filePath.rsplit(".")[1].lower()
        if ext in ["jpg", "jpeg"]:
            format = "JPEG"
        elif ext in ["png"]:
            format = "PNG"
        self.writeImage(imageFormat=format, filePath=filePath)

    def writeImage(self, imageFormat=None, filePath=None, printer=None):
        if not util.IS_IOS:
            from .pyqt import QPrinter, QPrintDialog
        size = self.canvas.size() * util.PRINT_DEVICE_PIXEL_RATIO
        image = QImage(size, QImage.Format_RGB32)
        image.setDevicePixelRatio(util.PRINT_DEVICE_PIXEL_RATIO)
        if imageFormat == "JPEG":
            image.fill(QColor("white"))
        painter = QPainter()
        painter.begin(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        # if imageFormat == 'PNG':
        #     afb = self.canvas.autoFillBackground()
        #     self.canvas.setAutoFillBackground(False)
        #     palette = self.canvas.palette()
        #     p = QPalette(self.canvas.palette())
        #     p.setColor(QPalette.Window, Qt.transparent)
        #     self.canvas.setPalette(p)
        self.canvas.render(painter)
        # if imageFormat == 'PNG':
        #     self.canvas.setAutoFillBackground(afb)
        #     self.canvas.setPalette(palette)
        painter.end()
        if filePath is not None:
            image.save(filePath, imageFormat, 80)
        elif printer is not None:
            p = QPainter()
            p.begin(printer)
            # make it fit
            printRect = printer.pageRect(QPrinter.Point).toRect()
            sourceRect = image.rect()
            if sourceRect.width() > sourceRect.height():
                scale = printRect.width() / sourceRect.width()
                targetRect = QRect(
                    printRect.x(),
                    printRect.y(),
                    sourceRect.width() * scale,
                    sourceRect.height() * scale,
                )
            else:
                scale = printRect.height() / sourceRect.height()
                targetRect = QRect(
                    printRect.x(),
                    printRect.y(),
                    sourceRect.width() * scale,
                    sourceRect.height() * scale,
                )
            p.drawImage(targetRect, image, sourceRect)
            p.end()


def __test__(scene, parent):
    from .graphicaltimelineview import SearchModel

    scene.setTags(["Tag 1", "Tag 2"])
    for i, event in enumerate(scene.events()):
        if i % 2:
            event.setTag("Tag 1")
        else:
            event.setTag("Tag 2")
    w = GraphicalTimeline(parent)
    model = SearchModel()
    model.tags = scene.tags()
    w.setScene(scene)
    w.show()
    parent.resize(800, 600)
    return w
