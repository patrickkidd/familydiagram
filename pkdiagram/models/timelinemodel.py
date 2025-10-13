import logging
from dataclasses import dataclass

# from sortedcontainers import SortedList
from pkdiagram.pyqt import (
    Qt,
    QApplication,
    QVariant,
    QAbstractTableModel,
    QItemSelectionModel,
    QMessageBox,
    QDateTime,
    QModelIndex,
    QObject,
    pyqtProperty,
    pyqtSlot,
    qmlRegisterType,
)
from pkdiagram import util
from pkdiagram.scene import Event, EventKind
from .modelhelper import ModelHelper
from pkdiagram.sortedlist import SortedList

_log = logging.getLogger(__name__)


@dataclass
class TimelineRow:
    event: Event
    isEndMarker: bool = False

    def description(self) -> str:
        if self.isEndMarker:
            return f"{self.event.kind().name} ended"
        else:
            return self.event.kind().name

    def dateTime(self) -> QDateTime:
        if self.isEndMarker:
            return self.event.endDateTime()
        else:
            return self.event.dateTime()

    def __lt__(self, other):
        if self.dateTime() < other.dateTime():
            return True
        elif self.dateTime() > other.dateTime():
            return False
        else:
            return True


def selectedEvents(timelineModel: "TimelineModel", selectionModel: QItemSelectionModel):
    return [timelineModel.eventForRow(x.row()) for x in selectionModel.selectedRows()]


class TableHeaderModel(QAbstractTableModel):
    """Could be a QStringListModel but needs to be a header model for layout purposes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers = []

    def setHeaders(self, headers):
        self.headers = headers
        self.modelReset.emit()

    def rowCount(self, index=None):
        return 1

    def columnCount(self, index=None):
        ret = len(self.headers)
        return ret

    def data(self, index, role):
        ret = self.headers[index.column()]
        return ret


class TimelineModel(QAbstractTableModel, ModelHelper):

    CROSS_OUT_OPACITY = 200

    BUDDIES = "  "
    DATETIME = "Date/Time"
    UNSURE = "Unsure"
    DESCRIPTION = "Description"
    LOCATION = "Location"
    PARENT = "Person(s)"
    LOGGED = "Logged"
    COLOR = "Color"

    NODAL = "Nodal"
    TAGS = "Tags"

    COLUMNS = [
        BUDDIES,  # 0
        DATETIME,  # 1
        UNSURE,  # 2
        DESCRIPTION,  # 3
        LOCATION,  # 4
        PARENT,  # 5
        LOGGED,  # 6
        COLOR,  # 7
        NODAL,  # 8
        TAGS,
    ]  # 9

    FlagsRole = Qt.UserRole + 1
    NodalRole = FlagsRole + 1
    DateTimeRole = NodalRole + 1
    ColorRole = DateTimeRole + 1
    FirstBuddyRole = ColorRole + 1
    SecondBuddyRole = FirstBuddyRole + 1
    ParentIdRole = SecondBuddyRole + 1
    HasNotesRole = ParentIdRole + 1
    DisplayExpandedRole = HasNotesRole + 1
    TagsRole = DisplayExpandedRole + 1

    ModelHelper.registerQtProperties(
        [
            {"attr": "dateBuddies", "type": list},
            {"attr": "searchModel", "type": QObject, "default": None},
        ]
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = SortedList()
        self._columnHeaders = []
        self._headerModel = TableHeaderModel(self)
        self._settingData = False  # prevent recursion
        self._searchModel = None
        self.initModelHelper()

    # def __repr__(self):
    #     s = ''
    #     for i, event in enumerate(self._rows):
    #         s += ('    %s:\t%s\n' % (util.dateString(event.dateTime()), event.parent))
    #     return '%s: [\n%s]' % (self.__class__.__name__, s)

    ## Columns

    def getColumnHeaders(self):
        if self._scene:  # duplicated in onSceneProperty[attr == 'eventProperties']
            return self.COLUMNS + [x["name"] for x in self._scene.eventProperties()]
        else:
            return self.COLUMNS

    ## Rows

    def _shouldHide(self, row: TimelineRow):
        """Check if a timeline row should be hidden based on filters."""
        event = row.event
        hidden = False
        if event.dateTime() is None or event.dateTime().isNull():
            hidden = True
        elif not self._scene:  # SceneModel.nullTimelineModel
            hidden = False
        elif (
            event.kind() == EventKind.Shift
            and event.relationship()
            and row.isEndMarker
            and self._scene.emotionsFor(event)
        ):
            # Hide end markers for single-date emotions with Shift events
            emotions = self._scene.emotionsFor(event)
            if emotions:
                # Check if any emotion for this event is a singular date
                # (start and end are the same or no end date)
                for emotion in emotions:
                    if emotion.event() == event:
                        emotion_event = emotion.event()
                        if emotion_event:
                            start_dt = emotion_event.dateTime()
                            end_dt = emotion_event.endDateTime()
                            if not end_dt or (start_dt and start_dt == end_dt):
                                hidden = True
                                break
        elif self._searchModel and self._searchModel.shouldHide(row):
            hidden = True
        return hidden

    def _ensureEvent(self, event: Event, emit=True):
        for row in self._rows:
            if row.event == event:
                return
        # Check start event row
        startRow = TimelineRow(event=event, isEndMarker=False)
        if not self._shouldHide(startRow):
            newRow = self._rows.bisect_right(
                event
            )  # SortedList.add uses &.bisect_right()
            if emit:
                self.beginInsertRows(QModelIndex(), newRow, newRow)
            self._rows.add(startRow)
            if emit:
                self.endInsertRows()

        # Check end event row
        if event.endDateTime():
            endRow = TimelineRow(event=event, isEndMarker=True)
            if not self._shouldHide(endRow):
                newRow = self._rows.bisect_right(
                    event
                )  # SortedList.add uses &.bisect_right()
                if emit:
                    self.beginInsertRows(QModelIndex(), newRow, newRow)
                self._rows.add(endRow)
                if emit:
                    self.endInsertRows()

    def _removeEvent(self, event):
        rows = [x for x in self._rows if x.event == event]
        if not rows:
            return
        for row in rows:
            row = self._rows.index(row)
            self.beginRemoveRows(QModelIndex(), row, row)
            self._rows.remove(event)
            self.endRemoveRows()

    def refreshColumnHeaders(self, columnHeaders=None):
        """Account for event variables."""
        if columnHeaders is None:
            columnHeaders = self.getColumnHeaders()
        self._columnHeaders = columnHeaders
        self._headerModel.setHeaders(self._columnHeaders)

    def onSceneProperty(self, prop):
        # if prop.name() == "currentDateTime":
        #     self._refreshRows()
        if prop.name() == "eventProperties":
            prevColumns = list(self._columnHeaders)
            newColumns = self.getColumnHeaders()
            addedIndexes = [i for i, x in enumerate(newColumns) if not x in prevColumns]
            removedIndexes = [
                i for i, x in enumerate(prevColumns) if not x in newColumns
            ]
            removedNames = [x for x in prevColumns if not x in newColumns]
            # hack to sync internal data with signals
            afterRemove = [x for x in prevColumns if x not in removedNames]
            if removedIndexes:
                first = removedIndexes[0]
                last = removedIndexes[-1]
                self.beginRemoveColumns(QModelIndex(), first, last)
                self.refreshColumnHeaders(afterRemove)
                self.endRemoveColumns()
            if addedIndexes:
                first = addedIndexes[0]
                last = addedIndexes[-1]
                self.beginInsertColumns(QModelIndex(), first, last)
                self.refreshColumnHeaders(newColumns)
                self.endInsertColumns()
            self.headerDataChanged.emit(
                Qt.Horizontal, len(self.COLUMNS), self.columnCount()
            )

    def _refreshRows(self):
        """The core method to collect all the events from people, pair-bonds, and emotions."""
        if not self._scene:
            return
        # sort and filter
        self._rows = SortedList()
        for event in self._scene.events():
            self._ensureEvent(event, emit=False)
        self.refreshAllProperties()
        self.modelReset.emit()

    def rows(self) -> list[TimelineRow]:
        return list(self._rows)

    def onSearchChanged(self):
        self._refreshRows()

    def onEventAdded(self, event):
        self._ensureEvent(event)

    def onEventChanged(self, prop):
        if self._settingData:
            return
        event = prop.item
        rows = [self._rows.index(x) for x in self._rows if x.event == event]
        try:
            startRow = self._rows.index(event)
        except ValueError:
            row = -1
        if prop.name() == "dateTime" or prop.name() == "endDateTime":
            self._removeEvent(event)
            self._ensureEvent(event)
            self.refreshProperty("dateBuddies")
        elif prop.name() == "description":
            col = self.COLUMNS.index(self.DESCRIPTION)
            for row in rows:
                self.dataChanged.emit(self.index(row, col), self.index(row, col))
        elif prop.name() == "color":
            col = self.COLUMNS.index(self.COLOR)
            for row in rows:
                self.dataChanged.emit(
                    self.index(row, 0),
                    self.index(row, self.columnCount() - 1),
                    [self.ColorRole],
                )

        elif prop.name() == "location":
            col = self.COLUMNS.index(self.LOCATION)
            for row in rows:
                self.dataChanged.emit(self.index(row, col), self.index(row, col))
        elif (
            prop.name() == "parentName"
        ):  # possibly redundant b/c it is already removed/re-added
            col = self.COLUMNS.index(self.PARENT)
            for row in rows:
                self.dataChanged.emit(self.index(row, col), self.index(row, col))
        # elif prop.name() == "color":
        #     self.refreshProperty("dateBuddies")
        elif prop.name() == "itemPos":
            pass  # performance hit when dragging items with emotions
        else:
            # nodal, for example
            col = None
            for i, entry in enumerate(self._scene.eventProperties()):
                if entry["attr"] == prop.name():
                    col = len(self.COLUMNS) + i
                    break
            if col is not None:
                firstCol = lastCol = col
            else:  # 'nodal', for example
                firstCol = 0
                lastCol = self.columnCount() - 1
            for row in rows:
                self.dataChanged.emit(
                    self.index(row, firstCol), self.index(row, lastCol)
                )

    def onEventRemoved(self, event):
        self._removeEvent(event)

    def eventsAt(self, dateTime: QDateTime):
        return [x.event for x in self._rows if x.dateTime() == dateTime]

    # QObjectHelper

    def get(self, attr):
        ret = None
        # if attr == "dateBuddies":
        #     ret = [
        #         {"startRow": start, "endRow": end, "color": item.color()}
        #         for start, end, item in self.dateBuddiesInternal()
        #     ]
        if attr == "searchModel":
            ret = self._searchModel
        else:
            ret = super().get(attr)
        return ret

    def set(self, attr, value):
        if attr == "searchModel":
            if self._searchModel:
                self._searchModel.changed.disconnect(self.onSearchChanged)
            self._searchModel = value
            if self._searchModel:
                self._searchModel.changed.connect(self.onSearchChanged)
            self._refreshRows()
        if attr == "scene":
            if self._scene:
                self._scene.eventAdded[Event].disconnect(self.onEventAdded)
                self._scene.eventChanged[Event].disconnect(self.onEventChanged)
                self._scene.eventRemoved[Event].disconnect(self.onEventRemoved)
        super().set(attr, value)
        if attr == "scene":
            if self._scene:
                self._scene.eventAdded[Event].connect(self.onEventAdded)
                self._scene.eventChanged[Event].connect(self.onEventChanged)
                self._scene.eventRemoved[Event].connect(self.onEventRemoved)
            self._rows = SortedList()

    ## Qt Virtuals

    def roleNames(self):
        ret = super().roleNames()
        ret[self.DisplayExpandedRole] = b"displayExpanded"
        ret[self.FlagsRole] = b"flags"
        ret[self.NodalRole] = b"nodal"
        ret[self.DateTimeRole] = b"dateTime"
        ret[self.ColorRole] = b"color"
        ret[self.FirstBuddyRole] = b"firstBuddy"
        ret[self.SecondBuddyRole] = b"secondBuddy"
        ret[self.ParentIdRole] = b"parentId"
        ret[self.HasNotesRole] = b"hasNotes"
        ret[self.TagsRole] = b"tags"
        return ret

    def rowCount(self, index=QModelIndex()):
        return len(self._rows)

    def columnCount(self, index=QModelIndex()):
        return len(self._columnHeaders)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self._columnHeaders[section]
        return QVariant()

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        event = self._rows[index.row()].event
        ret = None
        if not self._scene:
            ret = None
        elif role == self.FlagsRole:
            ret = self.flags(index)
        elif role == self.DateTimeRole:
            ret = event.dateTime()
        elif role == self.NodalRole:
            ret = event.nodal()
        elif role == self.NodalRole:
            ret = ", ".join(event.tags())
        elif role == self.ColorRole:
            return event.color()
        elif role == self.FirstBuddyRole:
            buddyRow = self.dateBuddyForRow(index.row())
            if buddyRow is not None and buddyRow > index.row():
                ret = True
            else:
                ret = False
        elif role == self.SecondBuddyRole:
            buddyRow = self.dateBuddyForRow(index.row())
            if buddyRow is not None and buddyRow < index.row():
                ret = True
            else:
                ret = False
        elif role == self.ParentIdRole:
            person = event.person()
            return person.id if person else None
        elif role == self.HasNotesRole:
            ret = bool(event.notes())
        elif self.isColumn(index, self.BUDDIES):
            ret = ""
        elif self.isColumn(index, self.NODAL):
            ret = event.nodal()
        elif self.isColumn(index, self.DATETIME):
            if role == Qt.DisplayRole:
                ret = util.dateString(event.dateTime())
            elif role in (self.DisplayExpandedRole, self.DateTimeRole):
                ret = util.dateTimeString(event.dateTime())
        elif self.isColumn(index, self.UNSURE):
            ret = event.unsure()
        elif self.isColumn(index, self.DESCRIPTION):
            ret = event.description()
        elif self.isColumn(index, self.PARENT):
            person = event.person()
            ret = person.fullNameOrAlias() if person else ""
        elif self.isColumn(index, self.LOCATION):
            ret = event.location()
        elif self.isColumn(index, self.LOGGED):
            ret = util.dateString(event.loggedDateTime())
        elif self.isColumn(index, self.COLOR):
            return event.color()
        elif self.isColumn(index, self.TAGS):
            ret = ", ".join(event.tags())
        else:
            attr = self.dynamicPropertyAttr(index)
            if attr:
                prop = event.dynamicProperty(attr)
                ret = prop.get()
        return ret

    def setData(self, index, value, role=Qt.EditRole):
        if not self._items:
            return super().setData(index, value, role)
        if self._settingData:
            return False
        self._settingData = True  # block onItemChanged
        event = self._rows[index.row()].event
        success = True
        forceBlockEmit = False
        if self.isColumn(index, self.PARENT):
            if role in (Qt.DisplayRole, Qt.EditRole):
                success = False  # maybe set by searching for name?
            elif role == self.ParentIdRole:
                person = event.person()
                if person is None or value != person.id:
                    newPerson = self._scene.find(id=value)
                    event.setPerson(newPerson, undo=True)
                else:
                    success = False
        elif self.isColumn(index, self.NODAL):
            event.setNodal(value, undo=True)
        elif self.isColumn(index, self.DATETIME) or role == self.DateTimeRole:
            if role in (Qt.DisplayRole, Qt.EditRole, self.DisplayExpandedRole):
                if value == "":
                    value = None
                elif role in (Qt.EditRole, Qt.DisplayRole):  # date only
                    date = util.validatedDateTimeText(value).date()
                    dateTime = event.dateTime()
                    dateTime.setDate(date)
                    value = dateTime
                elif role == self.DisplayExpandedRole:  # date + time
                    value = util.validatedDateTimeText(value)
            elif role == self.DateTimeRole:
                if value.isNull():
                    value = None
                else:
                    value = value
            #
            if value is None:
                event.prop("dateTime").reset(undo=True)
            elif value != event.dateTime():
                event.setDateTime(value, undo=True)
            # can't call &.onEventChanged b/c it's blocked when setting data
            self._removeEvent(event)
            self._ensureEvent(event)
            self.refreshProperty("dateBuddies")
            forceBlockEmit = True
        elif self.isColumn(index, self.UNSURE):
            event.setUnsure(value)
        elif self.isColumn(index, self.DESCRIPTION):
            event.setDescription(value, undo=True)
        elif self.isColumn(index, self.LOCATION):
            event.setLocation(value, undo=True)
        elif event.kind() == EventKind.Shift:
            attr = self.dynamicPropertyAttr(index)
            if attr:
                prop = event.dynamicProperty(attr)
                if value:
                    prop.set(value, undo=True)
                else:
                    prop.reset(undo=True)
            else:
                success = False
        else:
            success = False
        self._settingData = False
        if success and not forceBlockEmit:
            self.dataChanged.emit(index, index, [role])
        return success

    def flags(self, index):
        ret = 0
        try:
            event = self._rows[index.row()].event
        except IndexError:
            return Qt.ItemFlag.NoItemFlags
        if self._scene and self._scene.readOnly():
            pass
        elif self.isColumn(index, label=self.BUDDIES):
            pass
        else:
            if event.person() is None:  # being removed, so pass
                pass
            elif self.dynamicPropertyAttr(index):
                ret |= Qt.ItemIsEditable
            if event.kind() != EventKind.Shift:
                pass
            elif self.isColumn(
                index,
                labels=[self.DATETIME, self.DESCRIPTION, self.LOCATION, self.PARENT],
            ):
                ret |= Qt.ItemIsEditable
        return super().flags(index) | ret

    ## Accessors

    @pyqtProperty(QAbstractTableModel, constant=True)
    def headerModel(self):
        return self._headerModel

    def isColumn(self, index, label=None, labels=None):
        indexLabel = self._columnHeaders[index.column()]
        if label is not None:
            return label == indexLabel
        else:
            return indexLabel in labels

    def columnIndex(self, label):
        col = -1
        if label in self.COLUMNS:
            col = self.COLUMNS.index(label)
        if col > -1:
            return col
        for i, entry in enumerate(self._scene.eventProperties()):
            if entry["name"] == label:
                return len(self.COLUMNS) + i

    def dynamicPropertyAttr(self, index):
        eventProperties = self._scene.eventProperties()
        if index.column() < len(self.COLUMNS):
            return None
        elif index.column() < (len(self.COLUMNS) + len(eventProperties)):
            iDynProp = index.column() - len(self.COLUMNS)
            return eventProperties[iDynProp]["attr"]
        else:
            return None

    ## Row Accessors

    @pyqtSlot(int, result=int)
    def idForRow(self, row):
        item = self.itemForRow(row)
        if item:
            return item.id

    @pyqtSlot(int, result=QVariant)
    def itemForRow(self, row):
        if row >= 0 and row < len(self._rows):
            event = self._rows[row].event
            return event.person() if event else None

    def rowForEvent(self, event):
        """Only used in tests."""
        try:
            return self._rows.index(event)
        except ValueError:
            return -1

    @pyqtSlot(int, result=QVariant)
    def eventForRow(self, row):
        if row >= 0 and row < len(self._rows):
            return self._rows[row].event

    def timelineRow(self, row: int) -> TimelineRow:
        return self._rows[row]

    def endRowForEvent(self, event: Event) -> TimelineRow:
        """Return the date buddy to this one."""
        for row in self._rows:
            if row.event == event and row.isEndMarker:
                return row

    def indexForEvent(self, event) -> QModelIndex:
        row = self.rowForEvent(event)
        if row >= 0:
            return self.index(row, 0)

    def rowIndexFor(self, timelineRow: TimelineRow) -> int:
        return self._rows.index(timelineRow)

    @pyqtSlot(int, result=QDateTime)
    def dateTimeForRow(self, row):
        if row >= 0 and row < len(self._rows):
            return self._rows[row].dateTime()
        else:
            return QDateTime()

    @pyqtSlot(QDateTime, result=int)
    def firstRowForDateTime(self, dateTime):
        # entries = self._dateItemCache.get(date, None)
        row = -1
        for i, timelineRow in enumerate(self._rows):
            if timelineRow.dateTime() == dateTime:
                row = i
                break
        return row

    @pyqtSlot(QDateTime, result=int)
    def lastRowForDateTime(self, dateTime):
        row = -1
        for i, timelineRow in enumerate(reversed(self._rows)):
            if timelineRow.dateTime() == dateTime:
                row = len(self._rows) - 1 - i
                break
        return row

    @pyqtSlot(QDateTime, result=QDateTime)
    def nextDateTimeAfter(self, dateTime: QDateTime) -> QDateTime:
        dummy = TimelineRow(dateTime=dateTime)
        nextRow = bisect.bisect_right(self._rows, dummy)
        if nextRow == len(self._rows):  # end
            return self.lastEventDateTime()
        else:
            return self._rows[nextRow].dateTime()

    @pyqtSlot(QDateTime, result=QDateTime)
    def prevDateTimeBefore(self, dateTime: QDateTime) -> QDateTime:
        dummy = TimelineRow(dateTime=dateTime)
        prevRow = bisect.bisect_left(self._rows, dummy) - 1
        if prevRow == -1:  # start
            return self.firstEventDateTime()
        else:
            return self._rows[prevRow].dateTime()

    @pyqtSlot(QDateTime, result=int)
    def dateBetweenRow(self, date):
        """Return the row that the date falls right after if not right on.
        Return -1 if an exact match is found to optimize the TimelineView algorithm.
        """
        if not date:
            return -1
        ret = -1
        rowDates = [row.dateTime() for i, row in enumerate(self._rows)]
        if not date in rowDates:
            if rowDates and date < rowDates[0]:
                return 0  # prior to first
            elif rowDates and date > rowDates[-1]:
                return len(rowDates) - 1
            else:
                for i, rowDate in enumerate(rowDates):
                    if rowDate > date:
                        ret = i - 1
                        break
        return ret

    def firstEventDateTime(self):
        if self._rows:
            return self._rows[0].dateTime()

    def lastEventDateTime(self):
        if self._rows:
            return self._rows[-1].dateTime()

    def dateBuddyForRow(self, row):
        """Return the emotion row that is a date buddy to this one."""
        row = self._rows[row]
        if row.endDateTime():
            return row.endDateTime()

    # def dateBuddiesInternal(self):
    #     ret = set()
    #     for event in self._rows:
    #         if event.parent.isEmotion:
    #             emotion = event.parent
    #             if (
    #                 emotion.startEvent in self._rows
    #                 and emotion.endEvent in self._rows
    #             ):
    #                 if emotion.startEvent.dateTime() == emotion.endEvent.dateTime():
    #                     ret.add(
    #                         (
    #                             self._rows.index(emotion.startEvent),
    #                             self._rows.index(emotion.startEvent),
    #                             emotion,
    #                         )
    #                     )
    #                 else:
    #                     ret.add(
    #                         (
    #                             self._rows.index(emotion.startEvent),
    #                             self._rows.index(emotion.endEvent),
    #                             emotion,
    #                         )
    #                     )
    #     return tuple(ret)

    ## Mutations

    @pyqtSlot(QItemSelectionModel)
    def removeSelection(self, selectionModel):
        """Convenience for lack of a qml API for QItemSelectionModel."""
        events = set()
        for index in selectionModel.selectedIndexes():
            if index.column() > 0:
                continue
            event = self.eventForRow(index.row())
            events.add(event)
        # for event in events:
        #     if event.kind() is not None:
        #         events.append(event)
        #         docsPath = event.documentsPath()
        #         if docsPath:
        #             eventDocPath = docsPath.replace(self.document().url().toLocalFile() + os.sep, '')
        #             for relativePath in self.document().fileList():
        #                 if relativePath.startswith(eventDocPath):
        #                         nFiles = nFiles + 1
        # btn = QMessageBox.question(self.view().mw, "Are you sure?",
        #                            "Are you sure you want to delete %i events and their %i files? You can undo the deletion of the event, but any files will still be deleted." % (len(events), nFiles))
        # if btn == QMessageBox.No:
        #     return
        btn = QMessageBox.question(
            QApplication.activeWindow(),
            "Are you sure?",
            "Are you sure you want to delete %i events?" % len(events),
        )
        if btn == QMessageBox.No:
            return
        if events:
            with self._scene.macro("Delete selected events"):
                for event in events:
                    self._scene.removeItem(event, undo=True)


qmlRegisterType(TimelineModel, "PK.Models", 1, 0, "TimelineModel")
