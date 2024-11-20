import logging
from sortedcontainers import SortedList
from pkdiagram.pyqt import (
    pyqtSignal,
    Qt,
    QWheelEvent,
    QDateTime,
    QDate,
    QPoint,
    QRectF,
    QFont,
    QFontMetrics,
    QPen,
    QBrush,
    QPainter,
    QApplication,
    QWidget,
    QCursor,
    QColor,
    QRect,
    QMarginsF,
    QPointF,
    QRubberBand,
    QItemSelection,
    QItemSelectionModel,
)
from pkdiagram import util


_log = logging.getLogger(__name__)


class GraphicalTimelineCanvas(QWidget):

    W = util.CURRENT_DATE_INDICATOR_WIDTH * 2
    MARGIN = 30
    RIGHT_MARGIN = MARGIN * 4
    ANGLE = 55

    wheel = pyqtSignal(QWheelEvent)
    dateTimeClicked = pyqtSignal(QDateTime)
    eventsSelected = pyqtSignal(list)

    def __init__(
        self,
        searchModel,
        timelineModel,
        selectionModel: QItemSelectionModel,
        parent=None,
    ):
        super().__init__(parent)
        self._searchModel = searchModel
        self._timelineModel = timelineModel
        self._selectionModel = selectionModel
        self._isSelectingEvents = False
        self._events = SortedList()
        # A list for quick lookup, events can be listed more than once in
        # sullivanian time.
        self._eventRectCache = []
        self._rows = []
        self._lastMousePos = None
        self._hoverTimer = None
        self.rowHeight = 150
        self.sullivanianTime = False
        self._dayRange = 0
        self.refreshPending = False
        self.blockRefresh = False
        self.labelFont = QFont(util.DETAILS_FONT)
        self.labelFont.setPixelSize(32)
        self.labelFont.setWeight(QFont.ExtraBold)
        self._rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.setMouseTracking(True)
        # data
        self.scene = None
        # Slider
        self._isSlider = False
        self.mousePressed = False
        self._mousePressPos = None

        QApplication.instance().paletteChanged.connect(self.onPaletteChanged)
        self.onPaletteChanged()

        self._timelineModel.modelReset.connect(self.refresh)
        self._timelineModel.rowsInserted.connect(self.refresh)
        self._timelineModel.rowsMoved.connect(self.refresh)
        self._timelineModel.rowsRemoved.connect(self.refresh)
        self._timelineModel.dataChanged.connect(self.refresh)
        self.refresh()

    def onPaletteChanged(self):
        self.setFont(QFont(util.FONT_FAMILY, util.TEXT_FONT_SIZE))

    def documentView(self):
        return self.parent().parent().parent().documentView()

    def setScene(self, scene):
        self.scene = scene
        self.refresh()

    def refresh(self):
        if self.blockRefresh or not self.isVisible():
            self.refreshPending = True
            return
        self._events = SortedList()
        if not self.scene:
            self.update()
            return
        self.refreshPending = False
        self._events = self._timelineModel.events()
        self._rows = []
        if not self.isSlider() and self._searchModel.tags:
            # init day range
            if self.paintSullivanianTime():
                self._dayRange = 0  # take from tag with greatest day range
            elif self._events:
                firstDateTime, lastDateTime = self.dateTimeRange(events=self._events)
                self._dayRange = firstDateTime.daysTo(lastDateTime)
            else:
                self._dayRange = 0
            # init rows
            for tag in self._searchModel.tags:
                thisTagEvents = [e for e in self._events if e.hasTags([tag])]
                self._rows.append((tag, thisTagEvents))
                if self.paintSullivanianTime():
                    firstDateTime, lastDateTime = self.dateTimeRange(
                        events=thisTagEvents
                    )
                    if firstDateTime and lastDateTime:  # empty events?
                        _dayRange = firstDateTime.daysTo(lastDateTime)
                        if _dayRange > self._dayRange:
                            self._dayRange = _dayRange
        self.update()

    def dateTimeRange(self, events=None):  # should be sorted
        if self._searchModel.startDateTime:
            first = self._searchModel.startDateTime
        else:
            first = None
            for event in events:
                if event.dateTime() and event.dateTime() != QDateTime(QDate(1, 1, 1)):
                    first = event.dateTime()
                    break
        if self._searchModel.endDateTime:
            last = self._searchModel.endDateTime
        else:
            last = None
            for event in reversed(events):
                if event.dateTime() and event.dateTime() != QDateTime(QDate(1, 1, 1)):
                    last = event.dateTime()
                    break
        return first, last

    def selectEventsInRect(self, selectionRect: QRectF):
        selection = QItemSelection()
        events = set(
            [
                event
                for event, rectF in self._eventRectCache
                if selectionRect.intersects(rectF.toRect())
            ]
        )
        rows = []
        for event in events:
            row = self._timelineModel.rowForEvent(event)
            index = self._timelineModel.index(row, 0)
            selection.select(index, index)
            rows.append(row)
        self._isSelectingEvents = True
        if len(selection) > 0:
            self._selectionModel.select(
                selection,
                QItemSelectionModel.SelectionFlag.Clear
                | QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
        else:
            self._selectionModel.clearSelection()
        self._isSelectingEvents = False

    def isSelectingEvents(self) -> bool:
        return self._isSelectingEvents

    ## Qt Events

    def mousePressEvent(self, e):
        self._mousePressPos = e.pos()
        self._lastMousePos = e.pos()
        self.selectEventsInRect(QRect())
        e.accept()
        self.mousePressed = True
        if not self.isSlider():
            self._rubberBand.show()
            self._rubberBand.setGeometry(
                QRect(self._mousePressPos, self._mousePressPos).normalized()
            )
            self.selectEventsInRect(self._rubberBand.geometry())
        else:
            self._rubberBand.hide()
            self.dateTimeClicked.emit(self._dateTimeForPoint(e.pos()))

    def mouseMoveEvent(self, e):
        e.accept()
        if self._rubberBand.isVisible():
            self._rubberBand.setGeometry(
                QRect(self._mousePressPos, e.pos()).normalized()
            )
            self.selectEventsInRect(self._rubberBand.geometry())
        else:
            if self._rubberBand.isVisible():
                self._rubberBand.hide()
            if self.mousePressed:
                self.dateTimeClicked.emit(self._dateTimeForPoint(e.pos()))
        self._lastMousePos = e.pos()
        if not self.paintSullivanianTime():
            self.update()

    def mouseReleaseEvent(self, e):
        if self._rubberBand.isVisible():
            self._rubberBand.hide()
        if self.isSlider() and len(self._events) > 1:
            e.accept()
        self.mousePressed = False
        self._lastMousePos = None

    def showEvent(self, e):
        super().showEvent(e)
        if self.refreshPending:
            self.refresh()

    def wheelEvent(self, e):
        if not self._isSlider:
            self.wheel.emit(e)
            if not self.isSlider():
                self._lastMousePos = self.mapFromGlobal(QCursor.pos())

    def leaveEvent(self, e):
        self._lastMousePos = None
        self.update()

    def timerEvent(self, e):
        """Hack because leaveEvent() isn't called when moving the mouse fast."""
        pos = QCursor.pos()
        if not self.window().geometry().contains(pos):
            if self._lastMousePos:
                self._lastMousePos = None
                self.update()
        if self.isSlider() and self._hoverTimer:
            self.killTimer(self._hoverTimer)
            self._hoverTimer = None
            self._lastMousePos = None

    def paintEvent(self, e):
        self._eventRectCache = []
        if not self.scene or (not self._events and not self._rows):
            e.ignore()
            return
        painter = QPainter(self)
        with util.paint_event(painter):
            painter.setPen(util.TEXT_COLOR)
            painter.setClipRegion(e.region())
            clipRect = e.region().boundingRect()
            painter.setRenderHint(QPainter.Antialiasing, True)
            bottomY = self.height() - self.MARGIN
            if not self.isSlider() and len(self._rows):
                # add one to keep last row under top of widget
                rowHeight = (self.height() - self.MARGIN * 2) / (len(self._rows))
                with util.painter_state(painter):
                    painter.setFont(self.labelFont)
                    bottomY -= self.MARGIN
                    # tag labels
                    for i, (tag, tagEvents) in enumerate(self._rows):
                        y = bottomY - (i * rowHeight) - 10
                        painter.drawText(-self.x() + self.MARGIN, int(y), tag)

                # event rows
                for i, (tag, tagEvents) in enumerate(self._rows):
                    self._drawRow(
                        painter,
                        clipRect,
                        bottomY - (i * rowHeight) - 30,
                        tagEvents,
                        dayRange=self._dayRange,
                    )
            else:
                if self.isSlider():
                    bottomY = self.height() / 2  # center
                self._drawRow(painter, clipRect, bottomY, self._events)

            # Draw hover date line
            with util.painter_state(painter):
                if (
                    not self.isSlider()
                    and not self.paintSullivanianTime()
                    and self._lastMousePos
                ):
                    penColor = QColor(util.TEXT_COLOR)
                    penColor.setAlphaF(0.6)
                    painter.setPen(penColor)
                    painter.drawLine(
                        QPoint(self._lastMousePos.x(), 0),
                        QPoint(self._lastMousePos.x(), self.height()),
                    )
                    dateTime = self._dateTimeForPoint(self._lastMousePos)
                    dateTimeString = util.dateString(dateTime)
                    textWidth = (
                        self.fontMetrics()
                        .size(Qt.TextSingleLine, dateTimeString)
                        .width()
                    )
                    p = self._lastMousePos + QPoint(-10 + -textWidth, 0)
                    painter.drawText(p, dateTimeString)

    ## Utils

    def _dateTimeForPoint(self, pos):
        """assuming is slider."""
        firstDateTime, lastDateTime = self.dateTimeRange(events=self._events)
        if not firstDateTime or not lastDateTime:
            return QDateTime()
        dayRange = firstDateTime.daysTo(lastDateTime)
        if dayRange == 0:
            return firstDateTime
        firstP = QPointF(self.MARGIN, 0)
        if self.isSlider():
            lastP = QPointF(self.width() - self.MARGIN, 0)
        else:
            lastP = QPointF(self.width() - self.RIGHT_MARGIN, 0)
        dayPx = (lastP.x() - firstP.x()) / dayRange
        daysAfterFirst = round((pos.x() - firstP.x()) / dayPx)
        newDateTime = QDateTime(firstDateTime).addDays(daysAfterFirst)
        return newDateTime

    def _drawCurrentDateTimeIndicator(self, painter, x, y):
        with util.painter_state(painter):
            rect = self.currentDateTimeIndicatorRect(QPointF(x, y))
            painter.setBrush(util.SELECTION_COLOR)
            painter.setPen(Qt.transparent)
            painter.drawRect(rect)

    def currentDateTimeIndicatorRect(self, upperLeft: QPoint = None) -> QRectF:
        if not self.scene:
            return QRectF()
        if upperLeft:
            x, y = upperLeft.x(), upperLeft.y()
        if upperLeft is None and self.isSlider():
            firstDateTime, lastDateTime = self.dateTimeRange(events=self._events)
            dayRange = firstDateTime.daysTo(lastDateTime)
            if dayRange == 0:
                dayRange = 1
            y = self.height()
            firstP = QPointF(self.MARGIN, y)
            lastP = QPointF(self.width() - self.MARGIN, y)
            firstR = QRectF(0, 0, self.W, self.W)
            firstR.moveCenter(firstP)
            dayPx = (lastP.x() - firstP.x()) / dayRange
            currentX = firstDateTime.daysTo(self.scene.currentDateTime()) * dayPx
            x = firstR.x() + currentX
        return QRectF(
            x,
            y - util.GRAPHICAL_TIMELINE_SLIDER_HEIGHT / 2,
            self.W,
            util.GRAPHICAL_TIMELINE_SLIDER_HEIGHT,
        )

    def _drawRow(self, painter, clipRect, bottomY, events, dayRange=None):
        """Draw a single row for a tag. `y` is bottom left."""
        if self.isSlider():
            y = bottomY
        else:
            y = bottomY - (self.labelFont.pixelSize() + 5)
        firstP = QPointF(self.MARGIN, y)
        if self.isSlider():
            lastP = QPointF(self.width() - self.MARGIN, y)
        else:
            lastP = QPointF(self.width() - self.RIGHT_MARGIN, y)
        if events:  # empty events?
            firstDateTime, lastDateTime = self.dateTimeRange(events=events)
            if dayRange is None:
                dayRange = firstDateTime.daysTo(lastDateTime)
            if dayRange == 0:
                dayRange = 1
            firstR = QRectF(0, 0, self.W, self.W)
            firstR.moveCenter(firstP)
            dayPx = (lastP.x() - firstP.x()) / dayRange

        isSullivanianTime = self.paintSullivanianTime()  # cache

        # current date marker
        if events and not self.paintSullivanianTime():
            currentX = firstDateTime.daysTo(self.scene.currentDateTime()) * dayPx
            self._drawCurrentDateTimeIndicator(painter, firstR.x() + currentX, y)

        def xForDateTime(d):
            nDays = firstDateTime.daysTo(d)
            return firstP.x() + (nDays * dayPx)

        # timeline
        with util.painter_state(painter):
            painter.drawLine(firstP, lastP)

        # year markers
        if events:
            with util.painter_state(painter):
                pen = QPen(painter.pen())
                pen.setWidth(2)
                painter.setPen(pen)
                ascent = QFontMetrics(painter.font()).ascent()
                if isSullivanianTime:
                    minDay = 0
                    maxDay = dayRange
                    dayOffset = 0
                else:
                    minDay = QDateTime(QDate(1, 1, 1)).daysTo(
                        firstDateTime
                    )  # QDate(0, 0, 0) is invalid
                    maxDay = minDay + dayRange
                    minDate = QDateTime(QDate(1, 1, 1)).addDays(minDay)
                    minYear = minDate.date().year()
                    dayOffset = minDate.daysTo(QDateTime(QDate(minYear, 1, 1)))
                for iDay in range(minDay, maxDay, 365):
                    year = int(iDay / 365)
                    if year == 0:
                        continue
                    elif year % 10 == 0:
                        y = 10
                    else:
                        if dayPx * 365 < 10:  # responsive: year lines
                            continue
                        elif year % 5 == 0:
                            y = 6
                        else:
                            y = 3
                    if isSullivanianTime:
                        x = firstP.x() + (iDay - minDay) * dayPx + (dayOffset * dayPx)
                    else:
                        x = xForDateTime(QDateTime(QDate(year, 1, 1)))
                    if x < self.MARGIN:
                        continue
                    p = QPoint(round(x), round(firstP.y()))
                    painter.drawLine(p, p + QPoint(0, y))
                    if year % 10 == 0 or dayPx > 0.2:
                        if isSullivanianTime:
                            s = "%iy" % year
                        else:
                            s = "%i" % year
                        painter.drawText(p + QPoint(0, y + ascent), s)

        if not events:
            return

        # ellipses
        with util.painter_state(painter):
            deemphAlpha = 100
            #
            normalColor = util.PEN.color()
            normalBrush = painter.brush()
            normalBrush.setColor(normalColor)
            normalPen = QPen(normalColor, self.W / 2)
            #
            deemphColor = QColor(normalColor)
            deemphColor.setAlpha(deemphAlpha)
            deemphBrush = painter.brush()
            deemphBrush.setColor(deemphColor)
            deemphPen = QPen(deemphColor, self.W / 2)
            #
            nodalColor = QColor(util.NODAL_COLOR)
            nodalColor.setAlpha(deemphAlpha)
            nodalBrush = QBrush(nodalColor)
            nodalPen = QPen()
            nodalPen.setColor(deemphColor)
            #
            selectedColor = QColor(util.SELECTION_COLOR)
            selectedPen = QPen()
            selectedPen.setColor(selectedColor)
            selectedBrush = QBrush(selectedColor)
            # nodalPen.setWidthF(normalPen.widthF() * 2)
            for event in events:
                if event.dateTime() and event.dateTime() != QDate(QDate(1, 1, 1)):
                    days = firstDateTime.daysTo(event.dateTime())
                    x = dayPx * days
                    rect = firstR.translated(x, 0)
                    self._eventRectCache.append((event, rect))
                    if x > clipRect.x() + clipRect.width():
                        continue
                    if event.nodal():
                        w = self.W * 0.75
                        rect = rect.marginsAdded(QMarginsF(w, w, w, w))
                    # Events can be shown in more than one place
                    row = self._timelineModel.rowForEvent(event)
                    if self._selectionModel.isRowSelected(row):
                        painter.setPen(selectedPen)
                        painter.setBrush(selectedBrush)
                    elif event.nodal():
                        # print('    NODAL', event.dateTime().year(), nodalPen.color().name(), nodalPen.color().alpha())
                        painter.setPen(nodalPen)
                        painter.setBrush(nodalBrush)
                    elif self.scene.itemShownOnDiagram(event):
                        # print('    NORMAL', event.dateTime().year(), normalPen.color().name(), normalPen.color().alpha())
                        painter.setPen(normalPen)
                        painter.setBrush(normalBrush)
                    else:
                        # print('    DEEMPH', event.dateTime().year(), deemphPen.color().name(), deemphPen.color().alpha())
                        painter.setPen(deemphPen)
                        painter.setBrush(deemphBrush)
                    painter.drawEllipse(rect)

        if self.isSlider():
            return

        # event labels
        with util.painter_state(painter):
            painter.setPen(QPen(util.TEXT_COLOR, 1))
            prevDays = None
            prevX = None
            nDupes = 0
            for event in events:
                if event.dateTime() and event.dateTime() != QDateTime(QDate(1, 1, 1)):
                    days = firstDateTime.daysTo(event.dateTime())
                    if days == prevDays:
                        nDupes += 1
                    else:
                        nDupes = 0
                    prevDays = days
                    x = dayPx * days
                    if x > clipRect.x() + clipRect.width():
                        continue
                    if (
                        prevX is not None and x - prevX < self.W * 4
                    ):  # and not item.nodal():
                        continue
                    prevX = x
                    eventP = firstP + QPointF(x, 0)
                    offset = firstP + QPointF(
                        x, -((self.MARGIN / 4) + nDupes * self.W * 5)
                    )
                    if nDupes == 0:
                        painter.drawLine(eventP, offset)
                    painter.translate(offset)
                    painter.rotate(-self.ANGLE)
                    # if item.isEvent and item.parent.isPerson:
                    #     if self.scene.showAliases():
                    #         personName = item.parent.alias()
                    #     else:
                    #         personName = item.parent.name()
                    if self.paintSullivanianTime():
                        s = ""
                    else:
                        s = util.dateString(event.dateTime())
                    if event.parent != self.scene:
                        s += ": %s, %s" % (
                            event.description(),
                            event.parentName() is not None
                            and event.parentName()
                            or util.UNNAMED_TEXT,
                        )
                    else:
                        s += ": %s" % event.description()
                    painter.drawText(QPointF(5, 0), s)
                    painter.rotate(self.ANGLE)
                    painter.translate(-offset)

    def paintSullivanianTime(self):
        """Only when tags are set."""
        if self.scene:
            return bool(self._searchModel.tags and self.sullivanianTime)

    def setSullivanianTime(self, on):
        if on != self.sullivanianTime:
            self.sullivanianTime = on
            self.refresh()

    def isSlider(self):
        return self._isSlider

    def setIsSlider(self, on):
        if on != self._isSlider:
            self._isSlider = on
            self.update()
        self.refresh()
        if not on and not self._hoverTimer:
            self._hoverTimer = self.startTimer(200)

    def events(self):
        return self._events
