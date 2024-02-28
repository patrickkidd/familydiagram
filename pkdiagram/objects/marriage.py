import logging
from ..pyqt import (
    QGraphicsItem,
    QPen,
    QPainterPath,
    QPointF,
    QDateTime,
    pyqtSignal,
    Qt,
    QFont,
    QRectF,
)
from .. import util
from . import ItemDetails, Event, PathItem, Property
from ..util import EventKinds

log = logging.getLogger(__name__)


class SeparationIndicator(PathItem):

    def __init__(self, marriage):
        super().__init__(marriage)
        self.isSeparationIndicator = True
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self._marriage = marriage
        self.setPos(QPointF(75, 0))

    def updateGeometry(self):
        if not self._marriage or not self._marriage.scene():
            return
        path = QPainterPath()
        marriage = self._marriage
        currentDateTime = marriage.scene().currentDateTime()
        custodyDirection = 0
        if marriage.custody() == marriage.people[0].id:
            if marriage.people[0].scenePos().x() < marriage.people[1].scenePos().x():
                custodyDirection = -1
            else:
                custodyDirection = 1
        elif marriage.custody() == marriage.people[1].id:
            if marriage.people[1].scenePos().x() < marriage.people[0].scenePos().x():
                custodyDirection = -1
            else:
                custodyDirection = 1
        a = Marriage.personConnectionPoint(marriage.people[0])
        b = Marriage.personConnectionPoint(marriage.people[1])
        size = util.sizeForPeople(marriage.people[0], marriage.people[1])
        personRect = QRectF(util.PERSON_RECT)
        lineRise = personRect.height() * 0.4
        lineRun = personRect.width() * 0.2 * custodyDirection
        y = personRect.height() * 0.15
        status = marriage.separationStatusFor(currentDateTime)
        if status in (EventKinds.Separated.value, EventKinds.Divorced.value):
            x = 0
            path.moveTo(x, y)
            path.lineTo(x + lineRun, y - lineRise)
        if status == EventKinds.Divorced.value:
            x = personRect.width() * 0.1
            path.moveTo(x, y)
            path.lineTo(x + lineRun, y - lineRise)
        self.setPath(path)

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        self.scene().clearSelection()

    def itemChange(self, change, variant):
        if change == QGraphicsItem.ItemPositionChange:
            variant = QPointF(variant.x(), 0)
            if self.scene() and self.scene().isDraggingSomething():
                self.scene().checkItemDragged(self, variant)
        return super().itemChange(change, variant)

    def isEmpty(self):
        return self.path().isEmpty()

    def updatePen(self):
        super().updatePen()
        self.setPen(self._marriage.pen())


class Marriage(PathItem):

    eventAdded = pyqtSignal(Event)
    eventRemoved = pyqtSignal(Event)
    eventChanged = pyqtSignal(Property)

    ITEM_Z = util.MARRIAGE_Z

    @staticmethod
    def personConnectionPoint(person):
        rect = person.boundingRect()
        stroke = person.pen().width()
        r = QPointF(
            rect.bottomLeft().x()
            + (rect.bottomRight().x() - rect.bottomLeft().x()) / 2,
            rect.bottomLeft().y(),
        )  # - stroke)
        return person.mapToScene(r)

    @staticmethod
    def pathFor(personA, personB=None, pos=None):
        # convert scene mouse end pos to path
        start = Marriage.personConnectionPoint(personA)
        size = util.sizeForPeople(personA, personB)
        personRect = util.personRectForSize(size)  # already scaled
        height = personRect.height() / 2.2
        if pos is None:
            pos = Marriage.personConnectionPoint(personB)
        y_bottom = max(start.y() + height, pos.y() + height)
        path = QPainterPath(start)
        path.lineTo(QPointF(start.x(), y_bottom))
        path.lineTo(QPointF(pos.x(), y_bottom))
        y_end = min(pos.y(), y_bottom)
        path.lineTo(QPointF(pos.x(), y_end))
        return path

    PathItem.registerProperties(
        (
            {"attr": "married", "default": True, "onset": "updateGeometryAndDetails"},
            {"attr": "separated", "default": False, "onset": "updateGeometry"},
            {"attr": "divorced", "default": False, "onset": "updateGeometry"},
            {"attr": "custody", "type": int, "default": -1, "onset": "updateGeometry"},
            {"attr": "diagramNotes", "onset": "updateDetails"},
            {"attr": "notes"},
            {"attr": "hideDetails", "default": False, "layered": True},
            {"attr": "bigFont", "type": bool, "default": False, "layered": True},
        )
    )

    def __init__(self, personA=None, personB=None, **kwargs):
        super().__init__(**kwargs)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.prop("itemPos").setLayered(False)
        self.isMarriage = True
        self.isInit = False
        self._Marriage_isUpdatingAll = False
        self.people = [personA, personB]
        self._events = []
        self._eventsCache = []  # used for add|remove signals
        self._aliasNotes = None
        self._onShowAliases = False
        self.children = (
            []
        )  # used for geometry changes and to notify children when deleting marriage.
        # self.centerItem = QGraphicsEllipseItem(QRectF(-3, -3, 6, 6), self)
        self.detailsText = ItemDetails(self, growUp=True)
        self.detailsText.setPos(
            QPointF(30, -self.detailsText.boundingRect().bottomLeft().y())
        )
        font = QFont(util.DETAILS_FONT)
        font.setPointSize(round(font.pointSize() * 0.9))
        self.detailsText.setFont(font)
        self.detailsText.setParentRequestsToShow(False)
        self.separationIndicator = SeparationIndicator(self)
        self.separationIndicator.hide()
        self.penCapStyle = Qt.FlatCap
        if personA:
            personA._onAddMarriage(self)
        if personB:
            personB._onAddMarriage(self)
        self.isInit = True

    ## Data

    def write(self, chunk):
        super().write(chunk)
        chunk["person_a"] = self.people[0].id
        chunk["person_b"] = self.people[1].id
        chunk["events"] = []
        for i in self._events:
            x = {}
            i.write(x)
            chunk["events"].append(x)
        chunk["detailsText"] = {}
        self.detailsText.write(chunk["detailsText"])
        chunk["separationIndicator"] = {}
        self.separationIndicator.write(chunk["separationIndicator"])

    def read(self, chunk, byId):
        self.isInit = False
        super().read(chunk, byId)
        self.people = [byId(chunk["person_a"]), byId(chunk["person_b"])]
        for eChunk in chunk.get("events", []):
            if util.IS_DEV:
                # test for duplicates from some bugs created in dev
                skip = False
                for e in self._events:
                    if e.id == eChunk["id"]:
                        log.warning(f"Ignoring duplicate event: {e.id}")
                        skip = True
                        break
                if skip:
                    continue
            event = Event(self, id=eChunk["id"])
            event.read(eChunk, byId)
        # need bounding rect for detailsPos
        self.updateDetails()  # before setPos?
        self.detailsText.read(chunk.get("detailsText", {}), byId)
        self.separationIndicator.read(chunk.get("separationIndicator", {}), byId)
        self.isInit = True

    ## Cloning

    def clone(self, scene):
        x = super().clone(scene)
        x._cloned_people_ids = [p.id for p in self.people]
        x._cloned_children_ids = [p.id for p in self.children]
        for event in self._events:  # I wonder if excluding events would be a good idea?
            event = event.clone(scene)
            x._events.append(event)
        x._cloned_custody_id = self.custody()
        return x

    def remap(self, map):
        self.people = [map.find(id) for id in self._cloned_people_ids]
        delattr(self, "_cloned_people_ids")
        self.children = [map.find(id) for id in self._cloned_children_ids]
        delattr(self, "_cloned_children_ids")
        if self._cloned_custody_id > -1:
            c = map.find(self._cloned_custody_id)
            self.setCustody(c.id)
        delattr(self, "_cloned_custody_id")
        return None not in self.people

    ## Attributes

    def itemName(self):
        ret = "Pair Bond"
        peopleNames = self.peopleNames()
        if peopleNames:
            ret = ret + "(%s)" % peopleNames
        return ret

    def peopleNames(self):
        ret = ""
        if not None in self.people:
            name1 = self.people[0].name()
            name2 = self.people[1].name()
            if name1 and name2:
                ret += "%s & %s" % (name1, name2)
            elif name1:
                ret += "%s" % name1
            elif name2:
                ret += "%s" % name2
        return ret

    def onPersonNameChanged(self, person):
        for event in self.events():
            event.updateParentName()

    def penStyleFor(self, dateTime):
        priorBondedEvents = []
        priorMarriedEvents = []
        priorDivorcedEvents = []
        anyMarriedEvents = []
        for e in self._events:
            if e.dateTime() and e.dateTime() <= dateTime:
                if e.uniqueId() == EventKinds.Bonded.value:
                    priorBondedEvents.append(e)
                elif e.uniqueId() == EventKinds.Married.value:
                    priorMarriedEvents.append(e)
                elif e.uniqueId() == EventKinds.Divorced.value:
                    priorDivorcedEvents.append(e)
            if e.uniqueId() == EventKinds.Married.value:
                anyMarriedEvents.append(e)
        # order matters here
        if priorMarriedEvents:
            return Qt.SolidLine
        elif (not priorMarriedEvents) and (not priorBondedEvents) and self.married():
            return Qt.SolidLine
        elif priorDivorcedEvents:
            return Qt.SolidLine
        elif priorBondedEvents and (not anyMarriedEvents) and not self.married():
            return Qt.DashLine
        elif priorBondedEvents and (not anyMarriedEvents) and self.married():
            return Qt.SolidLine
        elif self.divorced():
            return Qt.SolidLine
        else:
            return Qt.DashLine

    def separationStatusFor(self, dateTime):
        """Returns 'separated', 'divorced', None"""
        separatedEvents = []
        divorcedEvents = []
        for e in self._events:
            if (
                e.uniqueId() == EventKinds.Separated.value
                and e.dateTime()
                and e.dateTime() <= dateTime
            ):
                separatedEvents.append(e)
            elif (
                e.uniqueId() == EventKinds.Divorced.value
                and e.dateTime()
                and e.dateTime() <= dateTime
            ):
                divorcedEvents.append(e)
        if divorcedEvents or self.divorced():
            return EventKinds.Divorced.value
        elif separatedEvents or self.separated():
            return EventKinds.Separated.value
        else:
            return None

    def everMarried(self):
        """Return True if `married` is checked or married events exist."""
        return self.everDivorced() or self.married() or self.anyMarriedEvents()

    def everSeparated(self):
        """Return True if `separated` is checked or separated events exist."""
        return self.separated() or self.anySeparatedEvents()

    def everDivorced(self):
        """Return True if `married` is checked or married events exist."""
        return self.divorced() or self.anyDivorcedEvents()

    def anyMarriedEvents(self):
        for event in self.events():
            if event.uniqueId() == EventKinds.Married.value:
                return True
        return False

    def anySeparatedEvents(self):
        for event in self.events():
            if event.uniqueId() == EventKinds.Separated.value:
                return True
        return False

    def anyDivorcedEvents(self):
        for event in self.events():
            if event.uniqueId() == EventKinds.Divorced.value:
                return True
        return False

    def spouseOf(self, person):
        if person in self.people:
            if self.people[0] == person:
                return self.people[1]
            else:
                return self.people[0]

    def personA(self):
        return self.people[0]

    def personB(self):
        return self.people[1]

    ## Events

    def events(self):
        return list(self._events)

    def _onAddEvent(self, x):
        """Called from Event.setParent."""
        if not x in self._events:
            self._events.append(x)
            if self.scene():
                self.scene().addItem(x)
            self.updateDetails()
            self.updateEvents()

    def _onRemoveEvent(self, x):
        """Called from Event.setParent."""
        if x in self._events:
            self._events.remove(x)
            if self.scene():
                self.scene().removeItem(x)
            self.updateDetails()
            self.updateEvents()

    def updateEvents(self):
        """handle add|remove changes."""

        def byDate(event):
            if event.dateTime() is None:
                return QDateTime()
            else:
                return event.dateTime()

        added = []
        removed = []
        newEvents = self._events = sorted(self._events, key=byDate)
        oldEvents = self._eventsCache
        for newEvent in newEvents:
            if not newEvent in oldEvents:
                added.append(newEvent)
        for oldEvent in oldEvents:
            if not oldEvent in newEvents:
                removed.append(oldEvent)
        for event in added:
            self.eventAdded.emit(event)
        for event in removed:
            self.eventRemoved.emit(event)
        self._eventsCache = list(newEvents)
        return {
            "oldEvents": oldEvents,
            "newEvents": newEvents,
            "added": added,
            "removed": removed,
        }

    ## Internal Data

    def notesIconPos(self):
        return QPointF(0, self._notesIcon.boundingRect().height() * -0.25)

    def _onAddChild(self, c):
        if not c in self.children:
            self.children.append(c)
            self.children = sorted(
                self.children, key=lambda x: x.id is not None and x.id or 0
            )

    def _onRemoveChild(self, c):
        if c in self.children:
            self.children.remove(c)

    def onProperty(self, prop):
        if prop.name() == "notes":
            if not self._onShowAliases:
                self.updateNotes()
        elif prop.name() == "hideDetails":
            self.updateDetails()
        elif prop.name() == "bigFont":
            if prop.get():
                self.detailsText.setFont(util.DETAILS_BIG_FONT)
            else:
                self.detailsText.setFont(util.DETAILS_FONT)
            self.updateDetails()
        elif prop.name() in ("married", "separated", "divorced"):
            if prop.name() == "divorced":
                if prop.get():
                    self.setMarried(True)
                    self.setSeparated(True)
            self.updateEvents()
            self.updatePen()
        if prop.name() not in ("itemPos",):
            super().onProperty(prop)

    def onEventProperty(self, prop):
        if not self.isInit:
            return
        changes = self.updateEvents()
        if prop.item in changes["newEvents"] and not prop.item in changes["added"]:
            self.eventChanged.emit(prop)
        self.updateDetails()

    def updatePen(self):
        super().updatePen()
        pen = QPen(util.PEN)
        penStyle = self.penStyleFor(self.scene().currentDateTime())
        pen.setStyle(penStyle)
        self.setPen(pen)
        self.setBrush(Qt.transparent)
        self.detailsText.setMainTextColor(util.PEN.color())
        self.separationIndicator.updatePen()

    def shouldShowAliases(self):
        scene = self.scene()
        return scene and scene.shouldShowAliases()

    @util.fblocked
    def updateNotes(self):
        """Force re-write of aliases."""
        prop = self.prop("notes")
        notes = prop.get()
        if notes is not None:
            self._aliasNotes = self.scene().anonymize(notes)
        else:
            self._aliasNotes = None

    def notes(self):
        if self.shouldShowAliases():
            if self._aliasNotes is None and self.prop("notes").get():  # first time
                self.updateNotes()
            return self._aliasNotes
        else:
            # if self.prop('notes') is None:
            #     self.here(self._hasDeinit, self)
            return self.prop("notes").get()

    def onShowAliases(self):
        self._onShowAliases = True
        prop = self.prop("notes")
        if prop.get() != self._aliasNotes:
            self.onProperty(prop)
        self._onShowAliases = False

    def dependents(self):
        ret = []
        for person in self.children:
            if person.childOf.multipleBirth:
                ret.append(person.childOf.multipleBirth)
            else:
                ret.append(person.childOf)
        return ret

    def updateDependents(self):
        dependents = self.dependents()
        for item in dependents:
            item.updateGeometry()

    def updateGeometry(self):
        if None in self.people or not self.scene():
            return
        changed = False
        size = util.sizeForPeople(*self.people)
        scale = util.scaleForPersonSize(size)
        if scale != self.scale:
            self.setScale(scale)
            changed = True
        path = Marriage.pathFor(self.people[0], self.people[1])
        newPathSceneRect = path.controlPointRect()
        # (0, 0) is bottom center
        newScenePos = QPointF(
            newPathSceneRect.bottomLeft().x() + newPathSceneRect.width() / 2,
            newPathSceneRect.bottomLeft().y(),
        )
        if newScenePos != self.pos():
            self.setPos(newScenePos)
            changed = True
        path = self.mapFromScene(path)
        if path != self.path():
            self.setPath(path)
            changed = True
        if changed:
            super().updateGeometry()
            self.updatePen()
            self.updateDependents()
        self.updateDetails()

    def updateDetails(self):
        """`pos` is passed from read()"""
        if not self.isInit or self._Marriage_isUpdatingAll:
            return
        super().updateDetails()
        currentDateTime = self.scene() and self.scene().currentDateTime() or QDateTime()
        lines = []
        events = self.events()
        for event in events:
            uniqueId = event.uniqueId()
            if (
                not event.dateTime()
                or not currentDateTime
                or event.dateTime() > currentDateTime
            ):
                continue
            if uniqueId == EventKinds.Bonded.value and event.dateTime():
                lines.append("b. " + util.dateString(event.dateTime()))
            elif uniqueId == EventKinds.Married.value and event.dateTime():
                lines.append("m. " + util.dateString(event.dateTime()))
            elif uniqueId == EventKinds.Separated.value and event.dateTime():
                lines.append("s. " + util.dateString(event.dateTime()))
            elif uniqueId == EventKinds.Divorced.value and event.dateTime():
                lines.append("d. " + util.dateString(event.dateTime()))
            elif uniqueId == "moved" and event.dateTime():
                lines.append(
                    "%s %s" % (util.dateString(event.dateTime()), event.description())
                )
            elif event.includeOnDiagram():
                lines.append(
                    "%s %s" % (util.dateString(event.dateTime()), event.description())
                )
        if self.diagramNotes():
            for line in self.diagramNotes().split("\n"):
                lines.append(line)
        if lines:
            text = "\n".join(lines)
        else:
            text = None
        self.detailsText.setText(text)
        if self.hideDetails() or self.detailsText.isEmpty():
            self.detailsText.setParentRequestsToShow(False)
        else:
            self.detailsText.setParentRequestsToShow(True)
        self.separationIndicator.updateGeometry()
        if self.separationIndicator.isEmpty():
            self.separationIndicator.hide()
        else:
            self.separationIndicator.show()

    def updateGeometryAndDetails(self):
        self.updateGeometry()
        self.updateDetails()

    def onUpdateAll(self):
        self._Marriage_isUpdatingAll = True
        super().onUpdateAll()  # Optimize out redundant calls to updateDetails()
        self._Marriage_isUpdatingAll = False
        self.updateDetails()

    ## Scene Events

    def shouldShowFor(self, dateTime, tags=[], layers=[]):
        # 1
        if (
            self.isSelected()
        ):  # sort of an override to prevent prop sheets disappearing, updated in ItemSelectedChange
            return True
        # 2
        personAShown = self.people[0].shouldShowFor(dateTime, tags=tags, layers=layers)
        personBShown = self.people[1].shouldShowFor(dateTime, tags=tags, layers=layers)
        if False in (personAShown, personBShown):
            return False
        # 3
        for child in self.children:
            if child.shouldShowFor(dateTime, tags=tags, layers=layers):
                return True
        # 5
        anyBondedMarriedDates = [
            e.dateTime()
            for e in self._events
            if e.uniqueId() in (EventKinds.Bonded.value, EventKinds.Married.value)
        ]
        priorBondedMarriedDates = [
            d for d in anyBondedMarriedDates if d is not None and d <= dateTime
        ]
        if priorBondedMarriedDates:
            return True
        if not anyBondedMarriedDates:
            return True
        # 6
        return False

    def updatePathItemVisible(self):
        if self.scene():
            on = self.shouldShowFor(
                self.scene().currentDateTime(),
                tags=self.scene().searchModel.tags,
                layers=self.scene().activeLayers(),
            )
        else:
            on = True
        if not on:
            self.setPathItemVisible(False)
        else:
            opacity = 1.0
            for person in self.people:
                o = person.itemOpacity()
                if o is not None and (o > 0 and o < 1.0):
                    opacity = o
            self.setPathItemVisible(True, opacity=opacity)
            self.updateDetails()

    def itemChange(self, change, variant):
        if change == QGraphicsItem.ItemSceneChange:
            if self.scene():
                self.scene().removeItem(self.detailsText)
                self.scene().removeItem(self.separationIndicator)
                for event in self._events:
                    self.scene().removeItem(event)
        elif change == QGraphicsItem.ItemSceneHasChanged:
            if self.scene():
                self.detailsText.setParentItem(self)
                self.separationIndicator.setParentItem(self)
                self.scene().addItem(self.detailsText)
                self.scene().addItem(self.separationIndicator)
                for event in self._events:
                    self.scene().addItem(event)
                if not self.scene().readOnly():
                    self.detailsText.setFlag(QGraphicsItem.ItemIsMovable, True)
                    self.separationIndicator.setFlag(QGraphicsItem.ItemIsMovable, True)
                else:
                    self.detailsText.setFlag(QGraphicsItem.ItemIsMovable, False)
                    self.separationIndicator.setFlag(QGraphicsItem.ItemIsMovable, False)
                self.detailsText.setParentRequestsToShow(not self.detailsText.isEmpty())
        elif change == QGraphicsItem.ItemSelectedChange:
            if variant is False:
                self.updateAll()  # update after override in shouldShowFor
        return super().itemChange(change, variant)
