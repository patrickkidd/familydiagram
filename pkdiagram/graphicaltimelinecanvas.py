import logging
from sortedcontainers import SortedList
from .pyqt import *
from . import util, objects


log = logging.getLogger(__name__)


class GraphicalTimelineCanvas(QWidget):

    W = util.CURRENT_DATE_INDICATOR_WIDTH * 2
    MARGIN = 30
    RIGHT_MARGIN = MARGIN * 4
    ANGLE = 55

    wheel = pyqtSignal(QWheelEvent)
    mouseButtonClicked = pyqtSignal(QPoint)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._events = SortedList()
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
        self.setMouseTracking(True)
        # data
        self.scene = None
        # Slider
        self._isSlider = False
        self.mousePressed = False

        QApplication.instance().paletteChanged.connect(self.onPaletteChanged)
        self.onPaletteChanged()

    def onPaletteChanged(self):
        self.setFont(QFont(util.FONT_FAMILY, util.TEXT_FONT_SIZE))

    def documentView(self):
        return self.parent().parent().parent().documentView()
        
    def setScene(self, scene):
        if self.scene:
            self.scene.timelineModel.modelReset.disconnect(self.refresh)
            self.scene.timelineModel.rowsInserted.disconnect(self.refresh)
            self.scene.timelineModel.rowsMoved.disconnect(self.refresh)
            self.scene.timelineModel.rowsRemoved.disconnect(self.refresh)
            self.scene.timelineModel.dataChanged.disconnect(self.refresh)
        self.scene = scene
        if self.scene:
            self.scene.timelineModel.modelReset.connect(self.refresh)
            self.scene.timelineModel.rowsInserted.connect(self.refresh)
            self.scene.timelineModel.rowsMoved.connect(self.refresh)
            self.scene.timelineModel.rowsRemoved.connect(self.refresh)
            self.scene.timelineModel.dataChanged.connect(self.refresh)
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
        self._events = self.scene.timelineModel.events()
        self._rows = []
        if not self.isSlider() and self.scene.searchModel.tags:
            # init day range
            if self.paintSullivanianTime():
                self._dayRange = 0 # take from tag with greatest day range
            elif self._events:
                firstEvent, lastEvent = self.firstAndLast(events=self._events)
                self._dayRange = firstEvent.dateTime().daysTo(lastEvent.dateTime())
            else:
                self._dayRange = 0
            # init rows
            for tag in self.scene.searchModel.tags:
                thisTagEvents = [e for e in self._events if e.hasTags([tag])]
                if not self.paintSullivanianTime():
                    if thisTagEvents and thisTagEvents[0] != firstEvent:
                        thisTagEvents = [firstEvent] + thisTagEvents
                        hideFirstEvent = True
                    else:
                        hideFirstEvent = False
                else:
                    hideFirstEvent = False
                self._rows.append((tag, thisTagEvents, hideFirstEvent))
                if self.paintSullivanianTime():
                    firstEvent, lastEvent = self.firstAndLast(events=thisTagEvents)
                    if firstEvent and lastEvent: # empty events?
                        _dayRange = firstEvent.dateTime().daysTo(lastEvent.dateTime())
                        if _dayRange > self._dayRange:
                            self._dayRange = _dayRange
        self.update()

    def firstAndLast(self, events=None): # should be sorted
        if self.scene.searchModel.startDateTime:
            firstE = objects.Event(
                dateTime=self.scene.searchModel.startDateTime,
                uniqueId='search_dummy'
            )
        else:
            firstE = None
            for event in events:
                if event.dateTime() and event.dateTime() != QDateTime(QDate(1, 1, 1)):
                    firstE = event
                    break
        if self.scene.searchModel.endDateTime:
            lastE = objects.Event(
                dateTime=self.scene.searchModel.endDateTime,
                uniqueId='search_dummy'
            )
        else:
            lastE = None
            for event in reversed(events):
                if event.dateTime() and event.dateTime() != QDateTime(QDate(1, 1, 1)):
                    lastE = event
                    break
        return firstE, lastE

    ## Qt Events

    def mousePressEvent(self, e):
        self._lastMousePos = e.pos()
        e.accept()
        self.mousePressed = True
        self.mouseButtonClicked.emit(e.pos())

    def mouseMoveEvent(self, e):
        e.accept()
        if self.mousePressed:
            self.mouseButtonClicked.emit(e.pos())
        self._lastMousePos = e.pos()
        if not self.paintSullivanianTime():
            self._lastMousePos = e.pos()
            self.update()

    def mouseReleaseEvent(self, e):
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
        """ Hack because leaveEvent() isn't called when moving the mouse fast. """
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
                rowHeight = (self.height() - self.MARGIN*2) / (len(self._rows))
                with util.painter_state(painter):
                    painter.setFont(self.labelFont)
                    bottomY -= self.MARGIN
                    # tag labels
                    for i, (tag, tagEvents, hideFirstEvent) in enumerate(self._rows):
                        y = bottomY -  (i * rowHeight) - 10
                        painter.drawText(-self.x() + self.MARGIN, int(y), tag)
                
                # event rows
                for i, (tag, tagEvents, hideFirstEvent) in enumerate(self._rows):
                    self._drawRow(painter, clipRect, bottomY -  (i * rowHeight) - 30, tagEvents,
                                dayRange=self._dayRange, hideFirstEvent=hideFirstEvent)
            else:
                if self.isSlider():
                    bottomY = self.height() / 2 # center
                self._drawRow(painter, clipRect, bottomY, self._events)

            # Draw hover date line
            with util.painter_state(painter):
                if not self.isSlider() and not self.paintSullivanianTime() and self._lastMousePos:
                    penColor = QColor(util.TEXT_COLOR)
                    penColor.setAlphaF(.6)
                    painter.setPen(penColor)
                    painter.drawLine(QPoint(self._lastMousePos.x(), 0), QPoint(self._lastMousePos.x(), self.height()))
                    dateTime = self._dateTimeForPoint(self._lastMousePos)
                    dateTimeString = util.dateString(dateTime)
                    textWidth = self.fontMetrics().size(Qt.TextSingleLine, dateTimeString).width()
                    p = self._lastMousePos + QPoint(-10 + -textWidth, 0)
                    painter.drawText(p, dateTimeString)

    ## Utils

    def _dateTimeForPoint(self, pos):
        """ assuming is slider. """
        firstEvent, lastEvent = self.firstAndLast(events=self._events)
        if not firstEvent or not lastEvent:
            return QDateTime()
        dayRange = firstEvent.dateTime().daysTo(lastEvent.dateTime())
        if dayRange == 0:
            return firstEvent.dateTime()
        firstP = QPointF(self.MARGIN, 0)
        if self.isSlider():
            lastP = QPointF(self.width() - self.MARGIN, 0)
        else:
            lastP = QPointF(self.width() - self.RIGHT_MARGIN, 0)
        dayPx = (lastP.x() - firstP.x()) / dayRange
        daysAfterFirst = round((pos.x() - firstP.x()) / dayPx)
        newDateTime = QDateTime(firstEvent.dateTime()).addDays(daysAfterFirst)
        return newDateTime

    def _drawCurrentDateTimeIndicator(self, painter, x, y):
        with util.painter_state(painter):
            rect = QRectF(
                x,
                y - util.GRAPHICAL_TIMELINE_SLIDER_HEIGHT / 2,
                self.W,
                util.GRAPHICAL_TIMELINE_SLIDER_HEIGHT
            )
            painter.setBrush(util.SELECTION_COLOR)
            painter.setPen(Qt.transparent)
            painter.drawRect(rect)
    
    def _drawRow(self, painter, clipRect, bottomY, events, dayRange=None, hideFirstEvent=False):
        """ Draw a single row for a tag. `y` is bottom left. """
        if self.isSlider():
            y = bottomY
        else:
            y = bottomY - (self.labelFont.pixelSize() + 5)
        firstP = QPointF(self.MARGIN, y)
        if self.isSlider():
            lastP = QPointF(self.width() - self.MARGIN, y)
        else:
            lastP = QPointF(self.width() - self.RIGHT_MARGIN, y)
        if events: # empty events?
            firstEvent, lastEvent = self.firstAndLast(events=events)
            if dayRange is None:
                dayRange = firstEvent.dateTime().daysTo(lastEvent.dateTime())
            if dayRange == 0:
                dayRange = 1
            firstR = QRectF(0, 0, self.W, self.W)
            firstR.moveCenter(firstP)
            dayPx = (lastP.x() - firstP.x()) / dayRange
            if firstEvent not in events:
                events.insert(0, firstEvent)
            if lastEvent not in events:
                events.append(lastEvent)

        isSullivanianTime = self.paintSullivanianTime() # cache

        # current date marker
        if events and not self.paintSullivanianTime():
            currentX = firstEvent.dateTime().daysTo(self.scene.currentDateTime()) * dayPx
            self._drawCurrentDateTimeIndicator(painter, firstR.x() + currentX, y)

        def xForDateTime(d):
            nDays = firstEvent.dateTime().daysTo(d)
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
                    minDay = QDateTime(QDate(1, 1, 1)).daysTo(firstEvent.dateTime()) # QDate(0, 0, 0) is invalid
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
                        if dayPx * 365 < 10: # responsive: year lines
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
                    if year % 10 == 0 or dayPx > .2:
                        if isSullivanianTime:
                            s = '%iy' % year
                        else:
                            s = '%i' % year
                        painter.drawText(p + QPoint(0, y + ascent), s)

        if not events:
            return

        if hideFirstEvent:
            paintedEvents = events[1:]
        else:
            paintedEvents = events

        # ellipses
        with util.painter_state(painter):
            deemphAlpha = 100
            #
            normalColor = util.TEXT_COLOR
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
            # nodalPen.setWidthF(normalPen.widthF() * 2)
            for event in paintedEvents:
                if event.dateTime() and event.dateTime() != QDate(QDate(1, 1, 1)):
                    days = firstEvent.dateTime().daysTo(event.dateTime())
                    x = dayPx * days
                    if x > clipRect.x() + clipRect.width():
                        continue
                    rect = firstR.translated(x, 0)
                    if event.nodal():
                        w = self.W*.75
                        # print('    NODAL', event.dateTime().year(), nodalPen.color().name(), nodalPen.color().alpha())
                        painter.setPen(nodalPen)
                        painter.setBrush(nodalBrush)
                        painter.drawEllipse(rect.marginsAdded(QMarginsF(w, w, w, w)))
                    elif event.uniqueId() == 'search_dummy' or self.scene.itemShownOnDiagram(event):
                        # print('    NORMAL', event.dateTime().year(), normalPen.color().name(), normalPen.color().alpha())
                        painter.setPen(normalPen)
                        painter.setBrush(normalBrush)
                        painter.drawEllipse(rect)
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
            for event in paintedEvents:
                if event.dateTime() and event.dateTime() != QDateTime(QDate(1, 1, 1)):
                    days = firstEvent.dateTime().daysTo(event.dateTime())
                    if days == prevDays:
                        nDupes += 1
                    else:
                        nDupes = 0
                    prevDays = days
                    x = dayPx * days
                    if x > clipRect.x() + clipRect.width():
                        continue
                    if prevX is not None and x - prevX < self.W*4: # and not item.nodal():
                        continue
                    prevX = x
                    eventP = firstP + QPointF(x, 0)
                    offset = firstP + QPointF(x, -((self.MARGIN/4) + nDupes*self.W*5))
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
                        s = ''
                    else:
                        s = util.dateString(event.dateTime())
                    if event.uniqueId() == 'search_dummy':
                        pass
                    elif event.parent != self.scene:
                        s += ': %s, %s' % (event.description(),
                                        event.parentName() is not None and event.parentName() or util.UNNAMED_TEXT)
                    else:
                        s += ': %s' % event.description()
                    painter.drawText(QPointF(5, 0), s)
                    painter.rotate(self.ANGLE)
                    painter.translate(-offset)

    def paintSullivanianTime(self):
        """ Only when tags are set. """
        if self.scene:
            return bool(self.scene.searchModel.tags and self.sullivanianTime)

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
