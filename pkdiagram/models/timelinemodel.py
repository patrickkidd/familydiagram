# from sortedcontainers import SortedList
from ..pyqt import (
    Qt,
    QApplication,
    QVariant,
    QAbstractTableModel,
    QItemSelectionModel,
    QMessageBox,
    QDate,
    QDateTime,
    QModelIndex,
    pyqtProperty,
    pyqtSlot,
    qmlRegisterType,
)
from .. import util, commands
from .modelhelper import ModelHelper


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

    ModelHelper.registerQtProperties([{"attr": "dateBuddies", "type": list}])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events = util.SortedList()
        self._columnHeaders = []
        self._headerModel = TableHeaderModel(self)
        self._settingData = False  # prevent recursion
        self.initModelHelper()

    # def __repr__(self):
    #     s = ''
    #     for i, event in enumerate(self._events):
    #         s += ('    %s:\t%s\n' % (util.dateString(event.dateTime()), event.parent))
    #     return '%s: [\n%s]' % (self.__class__.__name__, s)

    ## Columns

    def getColumnHeaders(self):
        if self._scene:  # duplicated in onSceneProperty[attr == 'eventProperties']
            return self.COLUMNS + [x["name"] for x in self._scene.eventProperties()]
        else:
            return self.COLUMNS

    def refreshColumnHeaders(self, columnHeaders=None):
        """Account for event variables."""
        if columnHeaders is None:
            columnHeaders = self.getColumnHeaders()
        self._columnHeaders = columnHeaders
        self._headerModel.setHeaders(self._columnHeaders)

    def onSceneProperty(self, prop):
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

    ## Rows

    def isSceneModel(self):
        return self._items and self._items[0].isScene

    def _shouldHide(self, event):
        hidden = False
        if not self.isSceneModel() and event.uniqueId() == "now":
            hidden = True
        elif not self._scene:  # SceneModel.nullTimelineModel
            hidden = False
        elif self._scene.searchModel.shouldHide(event):
            hidden = True
        return hidden

    def _ensureEvent(self, event, emit=True):
        if event in self._events:
            return
        if event.dateTime() is None:
            return
        if self._shouldHide(event):
            return
        newRow = self._events.bisect_right(
            event
        )  # SortedList.add uses &.bisect_right()
        if emit:
            self.beginInsertRows(QModelIndex(), newRow, newRow)
        self._events.add(event)
        if emit:
            self.endInsertRows()

    def _removeEvent(self, event):
        try:
            row = self._events.index(event)
        except ValueError:
            return
        self.beginRemoveRows(QModelIndex(), row, row)
        self._events.remove(event)
        self.endRemoveRows()

    def _refreshRows(self):
        """The core method to collect all the events from people, pair-bonds, and emotions."""
        if not self._scene:
            return
        # collect all
        events = set()
        for item in self._items:
            events.update(item.events())
            if item.isPerson:
                for marriage in item.marriages:
                    events.update(marriage.events())
            if item.isPerson or item.isScene:
                for emotion in item.emotions():
                    events.update(emotion.events())
        if not self._scene.nowEvent in events:
            events.add(self._scene.nowEvent)
        # sort and filter
        self._events = util.SortedList()
        for event in events:
            if not self._shouldHide(event):
                self._events.add(event)
        self.refreshAllProperties()
        self.modelReset.emit()

    def onSearchChanged(self):
        self._refreshRows()

    def onEventAdded(self, event):
        if self._items:
            self._ensureEvent(event)

    def onEventChanged(self, prop):
        if self._settingData:
            return
        event = prop.item
        try:
            row = self._events.index(event)
        except ValueError:
            row = -1
        if prop.name() == "dateTime":
            self._removeEvent(event)
            self._ensureEvent(event)
            self.refreshProperty("dateBuddies")
        elif prop.name() == "description":
            col = self.COLUMNS.index(self.DESCRIPTION)
            if row > -1:
                self.dataChanged.emit(self.index(row, col), self.index(row, col))
        elif prop.name() == "location":
            col = self.COLUMNS.index(self.LOCATION)
            if row > -1:
                self.dataChanged.emit(self.index(row, col), self.index(row, col))
        elif (
            prop.name() == "parentName"
        ):  # possibly redundant b/c it is already removed/re-added
            col = self.COLUMNS.index(self.PARENT)
            if row > -1:
                index = self.index(row, col)
                self.dataChanged.emit(index, index)
        elif prop.name() == "color":
            self.refreshProperty("dateBuddies")
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
            if row > -1:  # props before dates set on items
                self.dataChanged.emit(
                    self.index(row, firstCol), self.index(row, lastCol)
                )

    def onEventRemoved(self, event):
        if self._items:
            self._removeEvent(event)

    def onPersonMarriageAdded(self, item):
        item.eventAdded.connect(self.onEventAdded)
        item.eventRemoved.connect(self.onEventRemoved)

    def onPersonMarriageRemoved(self, item):
        item.eventAdded.disconnect(self.onEventAdded)
        item.eventRemoved.disconnect(self.onEventRemoved)

    def onEmotionAdded(self, emotion):
        self._ensureEvent(emotion.startEvent)
        self._ensureEvent(emotion.endEvent)
        # emotion.eventAdded.connect(self.onEventChanged)

    def onEmotionRemoved(self, emotion):
        self._removeEvent(emotion.startEvent)
        self._removeEvent(emotion.endEvent)
        # emotion.eventAdded.disconnect(self.onEventChanged)

    def cleanupBatchAddingRemovingItems(self, added, removed):
        """Just reset the model."""
        for item in added:
            if item.isEvent:
                self._ensureEvent(item)
            if item.isEmotion:
                self._ensureEvent(item.startEvent)
                self._ensureEvent(item.endEvent)
        for item in removed:
            if item.isEvent:
                self._removeEvent(item)
            if item.isEmotion:
                self._removeEvent(item.startEvent)
                self._removeEvent(item.endEvent)

    def events(self):
        return self._events.to_list()

    # QObjectHelper

    def get(self, attr):
        ret = None
        if attr == "dateBuddies":
            ret = [
                {"startRow": start, "endRow": end, "color": item.color()}
                for start, end, item in self.dateBuddiesInternal()
            ]
        else:
            ret = super().get(attr)
        return ret

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self._scene.searchModel.changed.disconnect(self.onSearchChanged)
        elif attr == "items":
            if self._items:
                for item in self._items:
                    item.eventAdded.disconnect(self.onEventAdded)
                    item.eventChanged.disconnect(self.onEventChanged)
                    item.eventRemoved.disconnect(self.onEventRemoved)
                    if item.isPerson:
                        item.marriageAdded.disconnect(self.onPersonMarriageAdded)
                        item.marriageRemoved.disconnect(self.onPersonMarriageRemoved)
                        for marriage in item.marriages:
                            marriage.eventAdded.disconnect(self.onEventAdded)
                            marriage.eventRemoved.disconnect(self.onEventRemoved)
                    if item.isScene or item.isPerson:
                        for emotion in item.emotions():
                            self.onEmotionRemoved(emotion)
            if value:
                for item in value:
                    item.eventAdded.connect(self.onEventAdded)
                    item.eventChanged.connect(self.onEventChanged)
                    item.eventRemoved.connect(self.onEventRemoved)
                    if item.isPerson:
                        item.marriageAdded.connect(self.onPersonMarriageAdded)
                        item.marriageRemoved.connect(self.onPersonMarriageRemoved)
                        for marriage in item.marriages:
                            marriage.eventAdded.connect(self.onEventAdded)
                            marriage.eventRemoved.connect(self.onEventRemoved)
                    # if item.isScene or item.isPerson:
                    #     for emotion in item.emotions():
                    #         emotion.eventChanged.disconnect(self.onEventChanged)
        super().set(attr, value)
        if attr == "scene":
            if self._scene:
                self._scene.searchModel.changed.connect(self.onSearchChanged)
        elif attr == "items":
            self.refreshColumnHeaders()
            self._refreshRows()

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
        return len(self._events)

    def columnCount(self, index=QModelIndex()):
        return len(self._columnHeaders)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self._columnHeaders[section]
        return QVariant()

    def data(self, index, role=Qt.DisplayRole):
        ret = None
        event = self._events[index.row()]
        if role == self.FlagsRole:
            ret = self.flags(index)
        elif role == self.DateTimeRole:
            ret = event.dateTime()
        elif role == self.NodalRole:
            ret = event.nodal()
        elif role == self.NodalRole:
            ret = ", ".join(event.tags())
        elif role == self.ColorRole:
            if event.parent.isEmotion:
                ret = event.parent.color()
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
            return event.parent.id
        elif role == self.HasNotesRole:
            ret = event.prop("notes").isset()
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
            if event.parent.isEmotion:
                ret = (
                    event.parent.parentName()
                )  # Direct translation - Maybe just use event.parentName()?
            else:
                ret = event.parentName()
        elif self.isColumn(index, self.LOCATION):
            ret = event.location()
        elif self.isColumn(index, self.LOGGED):
            ret = util.dateString(event.loggedDateTime())
        elif self.isColumn(index, self.COLOR):
            if event.parent.isEmotion:
                ret = event.parent.color()
        elif self.isColumn(index, self.TAGS):
            ret = ", ".join(event.tags())
        elif not event.parent.isScene:
            attr = self.dynamicPropertyAttr(index)
            if attr and event.uniqueId() != "now":
                prop = event.dynamicProperty(attr)
                ret = prop.get()
        return ret

    def setData(self, index, value, role=Qt.EditRole):
        if not self._items:
            return super().setData(index, value, role)
        if self._settingData:
            return False
        self._settingData = True  # block onItemChanged
        event = self._events[index.row()]
        success = True
        forceBlockEmit = False
        if self.isColumn(index, self.PARENT):
            if event.parent.isEmotion:
                success = False
            else:
                if role in (Qt.DisplayRole, Qt.EditRole):
                    success = False  # maybe set by searching for name?
                elif role == self.ParentIdRole:
                    if event.parent is None or value != event.parent.id:
                        person = self._scene.find(id=value)
                        commands.setEventParent(event, person)
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
            if event.parent.isEmotion:
                success = False
            else:
                event.setDescription(value, undo=True)
        elif self.isColumn(index, self.LOCATION):
            event.setLocation(value, undo=True)
        elif (
            not event.parent.isEmotion
        ):  # TODO: Remove condition if moving to allow vars on emotion events
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
        event = self._events[index.row()]
        if self._scene and self._scene.readOnly():
            pass
        elif self.isColumn(index, label=self.BUDDIES):
            pass
        else:
            if event.parent is None:  # being removed, so pass
                pass
            elif event.uniqueId() == "now":
                pass
            elif self.dynamicPropertyAttr(index):
                ret |= Qt.ItemIsEditable
            # elif event.parent.isMarriage:
            #     if self.isColumn(index, labels=[self.DATETIME, self.LOCATION]):
            #         ret |= Qt.ItemIsEditable
            elif event.uniqueId() is not None:
                if not self.isColumn(
                    index, labels=[self.DESCRIPTION, self.PARENT, self.LOGGED]
                ):
                    ret |= Qt.ItemIsEditable
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

    @pyqtSlot(result=int)
    def nowRow(self):
        if self._scene:
            try:
                return self._events.index(self._scene.nowEvent)
            except ValueError:
                return -1
        else:
            return -1

    @pyqtSlot(int, result=int)
    def idForRow(self, row):
        item = self.itemForRow(row)
        if item:
            return item.id

    @pyqtSlot(int, result=QVariant)
    def itemForRow(self, row):
        if row >= 0 and row < len(self._events):
            return self._events[row].parent

    def rowForEvent(self, event):
        """Only used in tests."""
        try:
            return self._events.index(event)
        except ValueError:
            return -1

    @pyqtSlot(int, result=QVariant)
    def eventForRow(self, row):
        try:
            return self._events[row]
        except IndexError:
            return None

    @pyqtSlot(int, result=QDateTime)
    def dateTimeForRow(self, row):
        if row >= 0 and row < len(self._events):
            return self._events[row].dateTime()
        else:
            return QDateTime()

    @pyqtSlot(QDateTime, result=int)
    def firstRowForDateTime(self, dateTime):
        # entries = self._dateItemCache.get(date, None)
        row = -1
        for i, event in enumerate(self._events):
            if event.dateTime() == dateTime:
                row = i
                break
        return row

    @pyqtSlot(QDateTime, result=int)
    def lastRowForDateTime(self, dateTime):
        row = -1
        for i, event in enumerate(reversed(self._events)):
            if event.dateTime() == dateTime:
                row = len(self._events) - 1 - i
                break
        return row

    @pyqtSlot(QDateTime, result=int)
    def dateBetweenRow(self, date):
        """Return the row that the date falls right after if not right on.
        Return -1 if an exact match is found to optimize the TimelineView algorithm.
        """
        ret = -1
        rowDates = [event.dateTime() for i, event in enumerate(self._events)]
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

    def dateBuddyForRow(self, row):
        """Return the emotion row that is a date buddy to this one."""
        event = self._events[row]
        if event.parent.isEmotion:
            emotion = event.parent
            if event is emotion.startEvent and emotion.endEvent in self._events:
                return self._events.index(emotion.endEvent)
            if event is emotion.endEvent and emotion.startEvent in self._events:
                return self._events.index(emotion.startEvent)

    def dateBuddiesInternal(self):
        ret = set()
        for event in self._events:
            if event.parent.isEmotion:
                emotion = event.parent
                if (
                    emotion.startEvent in self._events
                    and emotion.endEvent in self._events
                ):
                    if emotion.startEvent.dateTime() == emotion.endEvent.dateTime():
                        ret.add(
                            (
                                self._events.index(emotion.startEvent),
                                self._events.index(emotion.startEvent),
                                emotion,
                            )
                        )
                    else:
                        ret.add(
                            (
                                self._events.index(emotion.startEvent),
                                self._events.index(emotion.endEvent),
                                emotion,
                            )
                        )
        return tuple(ret)

    ## Mutations

    @pyqtSlot(QItemSelectionModel)
    def removeSelection(self, selectionModel):
        """Convenience for lack of a qml API for QItemSelectionModel."""
        events = set()
        for index in selectionModel.selectedIndexes():
            if index.column() > 0:
                continue
            event = self.eventForRow(index.row())
            if event.uniqueId() != "now":
                events.add(event)
        # for event in events:
        #     if event.uniqueId() is not None:
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
            commands.removeItems(self._scene, list(events))


qmlRegisterType(TimelineModel, "PK.Models", 1, 0, "TimelineModel")
