import os, shutil, random, logging, math
from typing import Union

from _pkdiagram import PersonDelegate
from pkdiagram.pyqt import (
    pyqtSignal,
    pyqtSlot,
    Qt,
    QColor,
    QBrush,
    QPen,
    QDateTime,
    QGraphicsView,
    QRectF,
    QGraphicsItem,
    QFileInfo,
    QGraphicsSimpleTextItem,
    QGraphicsPathItem,
    QPainterPath,
    QMarginsF,
    QFont,
    QVariantAnimation,
    QAbstractAnimation,
    QPointF,
)
from pkdiagram import util, slugify
from pkdiagram.scene import (
    EventKind,
    Property,
    PathItem,
    ItemDetails,
    Event,
    Emotion,
    Marriage,
    ChildOf,
    MultipleBirth,
    VariablesDatabase,
    random_names,
    ItemMode,
)
from pkdiagram.scene.commands import SetParents


_log = logging.getLogger(__name__)


ANXIETY_COLORS = {
    util.VAR_VALUE_UP: "red",
    util.VAR_VALUE_SAME: QColor(0, 0, 255, 127),
    util.VAR_VALUE_DOWN: "green",
}

FUNCTIONING_COLORS = {
    util.VAR_VALUE_UP: "green",
    util.VAR_VALUE_SAME: QColor(0, 0, 255, 127),
    util.VAR_VALUE_DOWN: "red",
}


class Person(PathItem):

    VARIABLE_BASE_COLOR_LIGHT_MODE = QColor(0, 0, 255)
    VARIABLE_BASE_COLOR_DARK_MODE = QColor(100, 255, 100)

    PathItem.registerProperties(
        (
            {"attr": "name", "onset": "updateDetails", "strip": True},
            {"attr": "middleName", "onset": "updateDetails", "strip": True},
            {"attr": "lastName", "onset": "updateDetails", "strip": True},
            {"attr": "nickName", "onset": "updateDetails", "strip": True},
            {"attr": "birthName", "onset": "updateDetails", "strip": True},
            {"attr": "alias"},
            {"attr": "primary", "default": False, "onset": "updateGeometry"},
            {"attr": "deceased", "default": False, "onset": "updateGeometryAndDetails"},
            {"attr": "deceasedReason", "onset": "updateDetails"},
            {"attr": "adopted", "default": False, "onset": "updateDetailsAndChild"},
            {
                "attr": "gender",
                "default": util.PERSON_KIND_MALE,
                "onset": "updateGeometryAndDetails",
            },
            {"attr": "diagramNotes", "onset": "updateDetails"},
            {"attr": "notes"},
            {
                "attr": "showLastName",
                "type": bool,
                "default": True,
                "onset": "updateDetails",
            },
            {
                "attr": "showMiddleName",
                "type": bool,
                "default": True,
                "onset": "updateDetails",
            },
            {
                "attr": "showNickName",
                "type": bool,
                "default": True,
                "onset": "updateDetails",
            },
            {
                "attr": "showVariableColors",
                "type": bool,
                "default": True,
                "onset": "updateGeometry",
            },
            {"attr": "hideDetails", "default": False, "layered": True},
            {"attr": "hideDates", "default": False, "layered": True},
            {"attr": "hideVariables", "default": False, "layered": True},
            {"attr": "color", "layered": True, "onset": "updatePenAndGeometry"},
            {"attr": "itemOpacity", "type": float, "layered": True},
            {
                "attr": "size",
                "type": int,
                "default": util.DEFAULT_PERSON_SIZE,
                "layered": True,
                "layerIgnoreAttr": "storeGeometry",
            },
            {"attr": "bigFont", "type": bool, "default": False, "layered": True},
            {"attr": "layers", "default": []},  # [id, id, id]
        )
    )

    @staticmethod
    def pathFor(
        kind,
        pos,
        size=None,
        primary=False,
        anxiety=None,
        functioning=None,
        symptom=None,
    ):
        rect = QRectF(util.PERSON_RECT)
        path = QPainterPath()
        scale = 1.0

        ANXIETY_JAGGEDNESS_DOWN = 3
        ANXIETY_JAGGEDNESS_SAME = 5
        ANXIETY_JAGGEDNESS_UP = 10

        ANXIETY_STEP_DOWN = 15
        ANXIETY_STEP_SAME = 10
        ANXIETY_STEP_UP = 5

        if anxiety == util.VAR_ANXIETY_DOWN:
            JAGGEDNESS = ANXIETY_JAGGEDNESS_DOWN
            STEP = ANXIETY_STEP_DOWN
        elif anxiety == util.VAR_ANXIETY_SAME:
            JAGGEDNESS = ANXIETY_JAGGEDNESS_SAME
            STEP = ANXIETY_STEP_SAME
        elif anxiety == util.VAR_ANXIETY_UP:
            JAGGEDNESS = ANXIETY_JAGGEDNESS_UP
            STEP = ANXIETY_STEP_UP

        if size is not None:
            scale = util.scaleForPersonSize(size)
        if kind == util.PERSON_KIND_MALE:
            if anxiety in (
                util.VAR_ANXIETY_DOWN,
                util.VAR_ANXIETY_SAME,
                util.VAR_ANXIETY_UP,
            ):
                WIDTH = int(rect.width() * scale)
                CENTER_X, CENTER_Y = 0, 0
                start_x = int(CENTER_X - WIDTH / 2)
                start_y = int(CENTER_Y - WIDTH / 2)
                path.moveTo(start_x, start_y)
                # top
                for i, x in enumerate(range(int(WIDTH * -0.5), int(WIDTH * 0.5), STEP)):
                    y = WIDTH * -0.5 + random.uniform(-JAGGEDNESS, JAGGEDNESS)
                    path.lineTo(x, y)
                    # _log.info(f"top, x: {x}, y: {y}")
                # right
                for i, y in enumerate(range(int(WIDTH * -0.5), int(WIDTH * 0.5), STEP)):
                    x = (WIDTH * 0.5) + random.uniform(-JAGGEDNESS, JAGGEDNESS)
                    path.lineTo(x, y)
                    # _log.info(f"right, x: {x}, y: {y}")
                # bottom
                for i, x in enumerate(
                    reversed(range(int(WIDTH * -0.5), int(WIDTH * 0.5), STEP))
                ):
                    y = WIDTH * 0.5 + random.uniform(-JAGGEDNESS, JAGGEDNESS)
                    path.lineTo(x, y)
                    # _log.info(f"bottom, x: {x}, y: {y}")
                # left
                for i, y in enumerate(
                    reversed(range(int(WIDTH * -0.5), int(WIDTH * 0.5), STEP))
                ):
                    x = (WIDTH * -0.5) + random.uniform(-JAGGEDNESS, JAGGEDNESS)
                    path.lineTo(x, y)
                    # _log.info(f"left, x: {x}, y: {y}")
                path.closeSubpath()
            else:
                path.addRect(rect)
                if primary:
                    m = 10 * scale
                    rect = rect.marginsAdded(QMarginsF(m, m, m, m))
                    path.addRect(rect)
            path.closeSubpath()
        elif kind == util.PERSON_KIND_FEMALE:
            if anxiety in (
                util.VAR_ANXIETY_DOWN,
                util.VAR_ANXIETY_SAME,
                util.VAR_ANXIETY_UP,
            ):
                CENTER_X, CENTER_Y = 0, 0
                radius = (rect.width() / 2) * scale
                start_angle = 90
                for angle in range(start_angle, 360 + start_angle, STEP):
                    radians = angle * (3.14159 / 180)
                    random_offset = random.uniform(-JAGGEDNESS, JAGGEDNESS)
                    x = CENTER_X + (radius + random_offset) * math.cos(radians)
                    y = CENTER_Y + (radius + random_offset) * math.sin(radians)
                    if angle == start_angle:
                        path.moveTo(x, y)
                    else:
                        path.lineTo(x, y)
            else:
                path.addEllipse(rect)
                if primary:
                    m = 10 * scale
                    rect = rect.marginsAdded(QMarginsF(m, m, m, m))
                    path.addEllipse(rect)
            path.closeSubpath()
        elif kind in ["abortion", "miscarriage"]:
            midX = rect.topRight().x() - (
                (rect.topRight().x() - rect.topLeft().x()) / 2
            )
            topMiddle = QPointF(midX, rect.topRight().y())
            path.moveTo(topMiddle)
            path.lineTo(rect.bottomLeft())
            path.lineTo(rect.bottomRight())
            path.lineTo(topMiddle)
        elif kind == "unknown":
            path.addRoundedRect(rect, 40, 40, Qt.RelativeSize)

        return path

    # eventAdded = pyqtSignal(Event)
    # eventRemoved = pyqtSignal(Event)
    # eventChanged = pyqtSignal(Property)
    fileAdded = pyqtSignal(str)

    ITEM_Z = util.PERSON_Z

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.isPerson = True
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setAcceptDrops(True)
        # delegate
        font = QFont(util.AGE_FONT)
        font.setPointSize(font.pointSize() * 2)
        self.ageItem = QGraphicsSimpleTextItem(self)
        self.ageItem.setFont(font)
        self.ageItem.setAcceptedMouseButtons(Qt.NoButton)
        self.functioningItem = QGraphicsPathItem(self)
        self._delegate = PersonDelegate(self)
        self.setPathItemDelegate(self._delegate)
        #
        self.isInit = False
        self.isUpdatingDependents = False
        self.childOf = None
        self.marriages = []
        self.setShapeMargin(0)  # override from PathItem
        self.setShapeIsBoundingRect(True)
        self._eventsCache = []  # Used for efficiently updating self.variablesDatabase
        self._emotions = []
        self._layers = []  # cache for &.prop('layers')
        self._layerItems = []
        self._aliasNotes = None
        self._onShowAliases = False
        self._lastVariableLines = []
        self.variablesDatabase = VariablesDatabase()
        self.snappedOther = (
            None  # person this item is snapped to; set on master person only
        )
        self.draggingWithMe_origPos = None
        self.draggingWithMe = []
        self.draggingMaster = (
            None  # the person that recieved the mouse down for multi-select-drag
        )
        self.mouseDownPos = None
        self.mouseMovePos = None
        self.mouseDownPersonPos = None
        self.nudging = False
        self.cachedPosChangeOldPos = None
        self.sizeAnimation = QVariantAnimation(self)
        self.sizeAnimation.setDuration(self.penAnimation.duration())
        self.sizeAnimation.valueChanged.connect(self.onSizeAnimTick)
        self.sizeAnimation.finished.connect(self.onSizeAnimFinished)
        self.detailsText = ItemDetails(self)
        # top-right
        # pos = util.PERSON_RECT.center() + QPointF(util.PERSON_RECT.width() * .02,
        #                                           -util.PERSON_RECT.height())
        # right
        pos = self.initialDetailsPos()
        self.detailsText.setPos(pos)
        self.detailsText.setItemPos(pos, notify=False)
        self.detailsText.setParentRequestsToShow(False)
        if not "alias" in kwargs:
            self.initAlias()
        if "layers" in kwargs:
            raise KeyError(
                'Use "Person.setLayers" instead of the "layers=" kwarg in Person.__init__()'
            )
        self.isInit = True

    def initialDetailsPos(self):
        ret = util.PERSON_RECT.topRight() + QPointF(util.PERSON_RECT.width() * 0.2, 0)
        return ret

    def initAlias(self):
        alias = None
        if self.scene():
            allAliases = [person.alias() for person in self.scene().people()]
            while alias is None or alias in allAliases:
                if self.gender() == util.PERSON_KIND_MALE:
                    alias = random.choice(random_names.MALE_NAMES)
                else:
                    alias = random.choice(random_names.FEMALE_NAMES)
        else:
            if self.gender() == util.PERSON_KIND_MALE:
                alias = random.choice(random_names.MALE_NAMES)
            else:
                alias = random.choice(random_names.FEMALE_NAMES)
        self.setAlias(alias, notify=False)

    ## Data

    def write(self, chunk):
        super().write(chunk)
        # Don't write internal layers
        assert set(self.layers()) == set(x.id for x in self._layers)
        chunk["layers"] = [l.id for l in self._layers if not l.internal()]
        #
        chunk["marriages"] = [m.id for m in self.marriages]
        chunk["childOf"] = {}
        if self.childOf:
            self.childOf.write(chunk["childOf"])
        chunk["detailsText"] = {}
        self.detailsText.write(chunk["detailsText"])

    def read(self, chunk, byId):
        self.isInit = False
        super().read(chunk, byId)
        # Defensive, also done in onProperty
        self._layers = []
        for layerId in self.layers():
            layer = byId(layerId)
            if not layer:
                _log.warning("Person.read: layer not found: %s" % layerId)
                continue
            self._layers.append(layer)
        self.prop("layers").set([x.id for x in self._layers])
        # self._layers = [byId(id) for id in self.layers()]
        # validate empty strings (maybe do for all properties?)
        if self.name() is not None and not self.name():
            self.setName(None, notify=False)
        #
        if chunk.get("childOf", {}):
            self.childOf = ChildOf(self, None)
            self.childOf.read(chunk["childOf"], byId)
        #
        if "detailsText" in chunk:
            self.detailsText.read(chunk["detailsText"], byId)
        if self.alias() is None:
            self.initAlias()
        #
        self.marriages = list(set([byId(id) for id in chunk.get("marriages", [])]))
        if None in self.marriages:
            _log.warning("*** None in self.marriages!")
            self.marriages = [m for m in self.marriages if m]
        #
        self.updateVariablesDatabase()
        self._delegate.setPrimary(self.primary())
        self._delegate.setGender(self.gender())
        self.isInit = True

    ## Cloning

    def clone(self, scene):
        x = super().clone(scene)
        self.initAlias()
        if self.childOf:
            x._cloned_childOf_id = self.childOf.id
        else:
            x._cloned_childOf_id = None
        x.setScale(util.scaleForPersonSize(x.size()))
        x.variablesDatabase = self.variablesDatabase.clone()  # does a deep copy
        return x

    def remap(self, map):
        self.childOf = map.find(self._cloned_childOf_id)
        delattr(self, "_cloned_childOf_id")
        return True

    ## Attributes

    def parents(self):
        if self.childOf:
            return self.childOf.parents()

    def firstNameOrAlias(self):
        if self.scene() and self.scene().hideNames():
            return ""
        elif self.scene() and self.scene().shouldShowAliases():
            return "[%s]" % self.alias()
        else:
            return self.name()

    @pyqtSlot(result=str)
    def fullNameOrAlias(self):
        ret = ""
        if self.scene() and self.scene().hideNames():
            pass
        elif self.scene() and self.scene().shouldShowAliases():
            if self.name():
                ret = "[%s]" % self.alias()
        else:
            ret = ""
            if self.name():
                ret += self.name()
            if self.middleName() and self.showMiddleName():
                ret += " " + self.middleName()
            if self.lastName() and self.showLastName():
                ret += " " + self.lastName()
            if self.nickName() and self.showNickName():
                if ret:
                    ret += " "
                ret += "(%s)" % self.nickName()
        return ret

    @pyqtSlot(str, result=bool)
    def matchesName(self, searchText: str):
        selfText = self.fullNameOrAlias().lower()
        otherText = searchText.lower()
        ret = otherText in selfText
        # _log.info(f"Person['{selfText}'].matchesName('{otherText}'): {ret}")
        return ret

    @pyqtSlot(result=str)
    def listLabel(self):
        """
        Some more richer label to help identify the person when there are
        duplicate names.
        """
        return self.fullNameOrAlias()

    def itemName(self):
        return self.fullNameOrAlias()

    def birthDateTime(self) -> QDateTime:
        for event in self.eventsFor(self):
            if event.kind() == EventKind.Birth:
                return event.dateTime()
        return QDateTime()

    def deceased(self) -> bool:
        if self.prop("deceased").get():
            return True
        for event in self.eventsFor(self):
            if event.kind() == EventKind.Death:
                return True
        return False

    def deceasedDateTime(self) -> QDateTime:
        for event in self.eventsFor(self):
            if event.kind() == EventKind.Death:
                return event.dateTime()
        return QDateTime()

    def age(self):
        if self.birthDateTime() and not self.deceased():
            age = int(self.birthDateTime().daysTo(self.scene().currentDateTime()) / 365)
            return age
        elif self.birthDateTime() and self.deceased() and not self.deceasedDateTime():
            return None  # don't show very high age when age at death is unknown.
        elif (
            self.birthDateTime()
            and self.deceased()
            and (
                self.deceasedDateTime()
                and self.deceasedDateTime() <= self.scene().currentDateTime()
            )
        ):
            age = int(self.birthDateTime().daysTo(self.deceasedDateTime()) / 365)
            return age
        elif self.birthDateTime() and (
            self.birthDateTime()
            <= (
                self.scene()
                and self.scene().currentDateTime()
                or QDateTime.currentDateTime()
            )
        ):
            age = int(
                self.birthDateTime().daysTo(
                    self.scene()
                    and self.scene().currentDateTime()
                    or QDateTime.currentDateTime()
                )
                / 365
            )
            return age

    def anxietyLevelNow(self):
        """
        Formalize dynamic variable since drawing uses it now.
        """
        if self.scene() and not self.scene().hideVariableSteadyStates():
            anxiety, ok = self.variablesDatabase.get(
                util.ATTR_ANXIETY, self.scene().currentDateTime()
            )
            if ok:
                return anxiety

    def functioningLevelNow(self):
        """
        Formalize dynamic variable since drawing uses it now.
        """
        if self.scene() and not self.scene().hideVariableSteadyStates():
            functioning, ok = self.variablesDatabase.get(
                util.ATTR_FUNCTIONING, self.scene().currentDateTime()
            )
            if ok:
                return functioning

    def symptomLevelNow(self):
        """
        Formalize dynamic variable since drawing uses it now.
        """
        if self.scene() and not self.scene().hideVariableSteadyStates():
            symptom, ok = self.variablesDatabase.get(
                util.ATTR_SYMPTOM, self.scene().currentDateTime()
            )
            if ok:
                return symptom

    ## Scene Events

    def multipleBirth(self):
        if self.childOf:
            return self.childOf.multipleBirth

    def _do_setParents(self, parentItem):
        """
        The single entry point for adding+removing a person to a pair-bond.
        `parentItem` can be a Marriage, ChildOf, or MultipleBirth.
        """
        # Remove existing parent(s)
        if self.childOf:
            if self.childOf.multipleBirth:
                multipleBirth = self.childOf.multipleBirth
                parents = multipleBirth.parents()
                children = list(multipleBirth.children())
                if (
                    self in children
                ):  # children is empty when this is called recursively from just below
                    children.remove(self)
                self.childOf.multipleBirth._onRemoveChild(self)
                if len(children) == 1:
                    children[0].setParents(parents)
                if (
                    len(multipleBirth.children()) == 0
                    and multipleBirth.scene() is self.scene()
                ):
                    self.scene().removeItem(multipleBirth)
                self.childOf._onRemoveMultipleBirth()
            self.parents()._onRemoveChild(self)
            self.scene().removeItem(self.childOf)
            self.childOf = None
        #
        if parentItem:
            # First ensure childOf is created
            if parentItem.isMarriage:
                self.childOf = ChildOf(self, parentItem)
            elif parentItem.isChildOf or parentItem.isMultipleBirth:
                self.childOf = ChildOf(self, parentItem.parents())

            # Then do setup for the specific configuration
            if parentItem.isMarriage:
                parentItem._onAddChild(self)

            elif parentItem.isMultipleBirth:
                self.childOf._onSetMultipleBirth(parentItem)
                parentItem._onAddChild(self)
                parentItem.parents()._onAddChild(self)

            elif parentItem.isChildOf:
                if parentItem.multipleBirth:
                    self.childOf._onSetMultipleBirth(parentItem.multipleBirth)
                    parentItem.parents()._onAddChild(self)
                    parentItem.multipleBirth._onAddChild(self)
                else:
                    multipleBirth = MultipleBirth(
                        parentItem.parents(), parentItem, self
                    )
                    parentItem.parents()._onAddChild(self)
                    parentItem._onSetMultipleBirth(multipleBirth)
                    self.childOf._onSetMultipleBirth(multipleBirth)

            # Post config init
            if self.scene():
                self.scene().addItem(self.childOf)
                if self.childOf.multipleBirth:
                    self.scene().addItem(self.childOf.multipleBirth)
            if self.scene() and not self.scene().isInitializing:
                self.childOf.updateGeometry()

    def setParents(self, target: Union[Marriage, ChildOf], undo=False):
        if undo:
            self.scene().push(SetParents(self, target))
        else:
            self._do_setParents(target)

    def _onAddMarriage(self, m):
        if not m in self.marriages:
            self.marriages.append(m)

    def _onRemoveMarriage(self, m):
        if m in self.marriages:
            self.marriages.remove(m)

    def shouldShowAliases(self):
        scene = self.scene()
        return scene and scene.shouldShowAliases()

    def onShowAliases(self):
        self._onShowAliases = True
        self.updateDetails()
        prop = self.prop("notes")
        if prop.get() != self._aliasNotes:
            self.onProperty(prop)
        self._onShowAliases = False

    def onHideVariablesOnDiagram(self):
        self.updateDetails()

    def onHideVariableSteadyStates(self):
        self.updateDetails()

    @util.fblocked
    def updateNotes(self):
        """Force re-write of aliases."""
        prop = self.prop("notes")
        notes = prop.get()
        if notes is not None and self.scene():
            self._aliasNotes = self.scene().anonymize(notes)
        else:
            self._aliasNotes = None

    def notes(self):
        if self.shouldShowAliases():
            if self._aliasNotes is None and self.prop("notes").get():  # first time
                self.updateNotes()
            return self._aliasNotes
        else:
            return self.prop("notes").get()

    def notesIconPos(self):
        return QPointF(0, self._notesIcon.boundingRect().height() * -0.5)

    @pyqtSlot(result=str)
    def gender(self):
        return self.prop("gender").get()

    ## Properties

    @util.blocked
    def onProperty(self, prop):
        if prop.name() == "gender":
            self._delegate.setGender(prop.get())
            self.updateAgeText()
            self.initAlias()
        elif prop.name() in ("adopted", "deceased"):
            if prop.name() == "deceased":
                self.onAgeChanged()
            self.updateEvents()
        elif prop.name() == "color" and prop.get() != self.pen().color().name():
            # old
            oldPenColor = self.pen().color()
            if self.itemAnimationGroup.state() == QAbstractAnimation.Running:
                oldBrushColor = self.brushAnimation.currentValue()
                self.itemAnimationGroup.stop()
            else:
                oldBrushColor = self.brush().color()
            # new
            newPenColor = self.currentBasePen().color()
            if prop.isset():
                newBrushColor = QColor(newPenColor)
                newBrushColor.setAlpha(100)
            else:
                newBrushColor = QColor(Qt.transparent)
            self.penAnimation.blockSignals(
                True
            )  # setEndValue was calling callback with final value
            self.penAnimation.setStartValue(oldPenColor)
            self.penAnimation.setEndValue(newPenColor)
            self.penAnimation.blockSignals(False)
            self.brushAnimation.blockSignals(True)
            self.brushAnimation.setStartValue(oldBrushColor)
            self.brushAnimation.setEndValue(newBrushColor)
            self.brushAnimation.blockSignals(False)
            self.scaleAnimation.setStartValue(None)
            self.scaleAnimation.setEndValue(None)
            self.startLayerAnimation(self.itemAnimationGroup)
        elif prop.name() == "itemOpacity" and prop.get() != self.opacity():
            self.updatePathItemVisible()
            # x = prop.isset() and prop.get() or 1.0
            # self.fadeToOpacity(x)
            # for item in self.dependents():
            #     item.fadeToOpacity(x)
        elif prop.name() == "size":
            endScale = util.scaleForPersonSize(prop.get())
            if endScale != self.scale():
                self.sizeAnimation.blockSignals(True)
                self.sizeAnimation.setStartValue(self.scale())
                self.sizeAnimation.setEndValue(endScale)
                self.sizeAnimation.blockSignals(False)
                self.startLayerAnimation(self.sizeAnimation)
        elif prop.name() in ("hideDetails", "hideDates", "hideVariables"):
            self.updateDetails()
        elif prop.name() == "bigFont":
            if prop.get():
                self.detailsText.setFont(util.DETAILS_BIG_FONT)
            else:
                self.detailsText.setFont(util.DETAILS_FONT)
            self.updateDetails()
        elif prop.name() == "notes":
            if not self._onShowAliases:
                self.updateNotes()
        elif prop.name() == "primary":
            self._delegate.setPrimary(prop.get())
            for emotion in self.emotions():
                if emotion.kind() == RelationshipKind.Cutoff:
                    emotion.updateGeometry()
        elif prop.name() == "layers":
            if self.scene():
                # Defensive, some layers were disappearing. Emotional Units?
                self._layers = []
                for layerId in prop.get():
                    layer = self.scene().find(id=layerId)
                    if not layer:
                        _log.warning(
                            f"Person.onProperty[layers]: layer not found: {layerId}"
                        )
                        continue
                    self._layers.append(layer)
                self.onActiveLayersChanged()
            else:
                self._layers = []
        super().onProperty(prop)

    ## Events

    def updateEvents(self):
        """handle add|remove changes."""
        added = []
        removed = []
        newEvents = self.eventsFor(self)
        oldEvents = self._eventsCache
        for newEvent in newEvents:
            if not newEvent in oldEvents:
                added.append(newEvent)
        for oldEvent in oldEvents:
            if not oldEvent in newEvents:
                removed.append(oldEvent)
        self._eventsCache = newEvents
        for event in added:
            # When variables are set in AddEventDialog
            for prop in event.dynamicProperties:
                if prop.isset():
                    self.variablesDatabase.set(prop.attr, event.dateTime(), prop.get())
            # self.eventAdded.emit(event)
        for event in removed:
            for prop in event.dynamicProperties:
                self.variablesDatabase.unset(prop.attr, event.dateTime())
            # self.eventRemoved.emit(event)
        return {
            "oldEvents": oldEvents,
            "newEvents": newEvents,
            "added": added,
            "removed": removed,
        }

    def onEventAdded(self):
        self.updateEvents()  # Recalc variables database
        self.updateDetails()  # Birth/death dates affect display
        self.updateGeometry()  # Adopted status affects visuals

    def onEventRemoved(self):
        self.updateEvents()
        self.updateDetails()
        self.updateGeometry()

    def onEventProperty(self, prop):
        if not self.isInit:
            return
        changes = self.updateEvents()
        if prop.item.kind() in (EventKind.Birth, EventKind.Adopted, EventKind.Death):
            self.updateGeometry()
            self.onAgeChanged()
            self.updatePathItemVisible()
        if (
            prop.item.kind() in (EventKind.Birth, EventKind.Death)
            and prop.name() == "dateTime"
        ):
            self.onAgeChanged()
        # if prop.item in changes["newEvents"] and not prop.item in changes["added"]:
        #     self.eventChanged.emit(prop)
        if prop.isDynamic:
            self.variablesDatabase.set(prop.attr, prop.item.dateTime(), prop.get())

    # Showing / Hiding

    @util.fblocked  # needed to avoid recursion in multiple births
    def updatePathItemVisible(self):
        """Override."""
        if self.shouldShowForDateAndLayerTags():
            opacity = self.itemOpacity()
            if opacity is None:
                opacity = 1.0
            self.setPathItemVisible(True, opacity=opacity)
            # if opacity < 1.0 and opacity > 0: # hack so that deemphasized person takes priority if one exists.
            for item in self.dependents():
                item.updatePathItemVisible()
                # # 1) hiding based on item.shouldShowFor takes first priority
                # # 2) 0 < opacity < 1.0 takes second priority
                # on = item.shouldShowFor(self.scene().currentDateTime(),
                #                         reverseTags=self.scene().reverseTags())
                # self.here(opacity, self.name())
                # if not on or opacity == 0:
                #     item.setPathItemVisible(False)
                # else:
                #     item.setPathItemVisible(True, opacity=opacity)
        else:
            self.setPathItemVisible(False)

    def updateVariablesDatabase(self):
        self.variablesDatabase.clear()
        for event in self.eventsFor(self):
            for prop in event.dynamicProperties:
                if event.dateTime() and prop.isset():
                    self.variablesDatabase.set(prop.attr, event.dateTime(), prop.get())

    def onAgeChanged(self):
        if self.scene():
            self.updateAgeText()
            self.updatePen()

    ## Layers and Layer Items

    def layerItems(self):
        return list(self._layerItems)

    def _onAddLayerItem(self, layerItem):
        if not layerItem in self._layerItems:
            self._layerItems.append(layerItem)

    def _onRemoveLayerItem(self, layerItem):
        if layerItem in self._layerItems:
            self._layerItems.remove(layerItem)

    ## Internal data

    def updatePen(self):
        super().updatePen()
        pen = self.currentBasePen()
        if self.hover:
            brush = QBrush(util.HOVER_BRUSH)
            pen = QPen(util.HOVER_PEN)
            self._delegate.setForceNoPaintBackground(False)
        elif self.isSelected():
            brush = QBrush(util.SELECTION_BRUSH)
            pen.setColor(util.contrastTo(brush.color()))
            self._delegate.setForceNoPaintBackground(True)
        else:
            anxiety = self.anxietyLevelNow()
            if anxiety in (
                util.VAR_ANXIETY_DOWN,
                util.VAR_ANXIETY_SAME,
                util.VAR_ANXIETY_UP,
            ):
                c = QColor(ANXIETY_COLORS[anxiety])
                pen.setColor(c)
                c.setAlpha(100)
                brush = QBrush(c)
            else:
                brush = QBrush(util.WINDOW_BG)
            self._delegate.setForceNoPaintBackground(True)
        self.setBrush(brush)
        self.setPen(pen)
        # Children items
        if self.childOf:
            self.childOf.updatePen()
        if self.gender() == "unknown":
            c = pen.color()
            c.setAlpha(100)
            pen.setColor(c)
        agePen = QPen(self.ageItem.pen())
        if self.isSelected() and not self.primary():
            c = util.contrastTo(brush.color())
            agePen.setColor(c)
        else:
            agePen.setColor(pen.color())
        self.setPen(pen)
        self.setBrush(brush)
        self.ageItem.setPen(agePen)
        self.ageItem.setBrush(agePen.color())
        self.detailsText.setMainTextColor(util.PEN.color())
        if util.IS_UI_DARK_MODE:
            vBaseColor = QColor(self.VARIABLE_BASE_COLOR_DARK_MODE)
        else:
            vBaseColor = QColor(self.VARIABLE_BASE_COLOR_LIGHT_MODE)
        for iLine in range(self.detailsText.numExtraTextItems()):
            oldColor = self.detailsText.extraLineColor(iLine)
            newColor = QColor(vBaseColor)
            if oldColor.alphaF() < 1.0:
                newColor.setAlphaF(0.7)
            self.detailsText.setExtraLineColor(iLine, newColor)

    def currentBasePen(self):
        """Return the layered color otherwise the default pen color."""
        pen = QPen(util.PEN)
        if self.prop("color").isset():
            c = QColor(self.color())
        else:
            if self.hover:
                c = util.HOVER_PEN.color()
            else:
                c = util.PEN.color()
        pen.setColor(c)
        return pen

    def updateGeometryAndDependents(self):
        """Also update dependents."""
        self.updateGeometry()
        self.updateDetails()
        self.updateDependents()

    def updateDependents(self):
        """in order"""
        self.isUpdatingDependents = True
        dependents = self.dependents()
        for item in dependents:
            item.updateGeometry()
        self.isUpdatingDependents = False

    def dependents(self):
        """The main graphical dependency graph for updateGeometry()."""
        ret = []
        for m in self.marriages:
            ret.append(m)
            for child in m.children:
                ret.append(child.childOf)
                if child.childOf.multipleBirth:
                    # just update the vertical line from marriage to multiple birth
                    ret.append(child.childOf.multipleBirth)
        for e in self._emotions:
            ret.append(e)
        if self.childOf:
            if self.childOf.scene():
                ret.append(self.childOf)
            if self.childOf.multipleBirth:
                ret.append(self.childOf.multipleBirth)
                for partnerChildOf in self.childOf.multipleBirth.children():
                    ret.append(partnerChildOf)
                    if partnerChildOf.childOf.isVisible():
                        ret.append(partnerChildOf.childOf)
        return list(set(ret))

    def updateGeometry(self):
        super().updateGeometry()
        if self.scene():  # get this from somewhere else
            currentDateTime = self.scene().currentDateTime()
        else:
            currentDateTime = QDateTime()
        path = self.pathFor(
            self.gender(),
            self.pos(),
            primary=self.primary(),
            anxiety=self.anxietyLevelNow(),
            functioning=self.functioningLevelNow(),
            symptom=self.symptomLevelNow(),
        )
        rect = path.controlPointRect()
        ignoreDeath = (
            self.deceasedDateTime() and self.deceasedDateTime() > currentDateTime
        )
        if self.deceased() and not ignoreDeath:
            if self.age() is None:
                path.moveTo(rect.topLeft())
                path.lineTo(rect.bottomRight())
                path.moveTo(rect.topRight())
                path.lineTo(rect.bottomLeft())
            else:
                # leave space for age
                w = (rect.topRight().x() - rect.topLeft().x()) * 0.3
                path.moveTo(rect.topLeft())
                path.lineTo(rect.topLeft().x() + w, rect.topLeft().y() + w)
                path.moveTo(rect.topRight())
                path.lineTo(rect.topRight().x() - w, rect.topRight().y() + w)
                path.moveTo(rect.bottomLeft())
                path.lineTo(rect.bottomLeft().x() + w, rect.bottomLeft().y() - w)
                path.moveTo(rect.bottomRight())
                path.lineTo(rect.bottomRight().x() - w, rect.bottomRight().y() - w)
        self.setPath(path)

        functioning = self.functioningLevelNow()
        if functioning in (
            util.VAR_FUNCTIONING_DOWN,
            util.VAR_FUNCTIONING_SAME,
            util.VAR_FUNCTIONING_UP,
        ):
            if functioning == util.VAR_FUNCTIONING_DOWN:
                num = 1
            elif functioning == util.VAR_FUNCTIONING_SAME:
                num = 2
            elif functioning == util.VAR_FUNCTIONING_UP:
                num = 3
            functioningPath = util.bolts_path(self.boundingRect().width(), num)
            self.functioningItem.setPath(functioningPath)
            self.functioningItem.setPen(
                QPen(
                    QColor(FUNCTIONING_COLORS[functioning]),
                    util.PEN.widthF(),
                    join=Qt.PenJoinStyle.MiterJoin,
                )
            )
        else:
            self.functioningItem.setPath(QPainterPath())

        self.updatePen()
        self.updateDetails()

    def updateAgeText(self):
        if not self.scene():
            return
        # age text
        if self.gender() == "unknown":
            self.ageItem.setText("?")
        else:
            age = self.age()
            if age is not None and age > -1:
                self.ageItem.setText(str(age))
            else:
                self.ageItem.setText("")
                self.ageItem.hide()
        if self.ageItem.text():
            r = self.ageItem.boundingRect()
            self.ageItem.setPos(r.width() / -2, r.height() / -2)
            if not self.ageItem.isVisible():
                self.ageItem.show()
        else:
            if self.ageItem.isVisible():
                self.ageItem.hide()

    def updateDetails(self):
        super().updateDetails()
        hideDetails = self.hideDetails()
        hideDates = self.hideDates()
        hideVariables = self.hideVariables()
        self.updateAgeText()

        # Compile Built-in Details
        lines = []
        if self.scene():
            currentDateTime = self.scene().currentDateTime()
        else:
            currentDateTime = QDateTime.currentDateTime()

        if not hideDetails:
            name = self.fullNameOrAlias()
            if name:
                lines.append(name)

        # Compile Dates
        if not hideDates and self.birthDateTime():
            lines.append("b. " + util.dateString(self.birthDateTime()))
        if self.gender() == "abortion":
            lines.append("(abortion)")
        elif self.gender() == "miscarriage":
            lines.append("(miscarriage)")
        if not hideDates and self.deceased():
            ignoreDeath = (
                self.deceasedDateTime() and self.deceasedDateTime() > currentDateTime
            )
            if self.deceasedDateTime() and not ignoreDeath:
                lines.append("d. " + util.dateString(self.deceasedDateTime()))
            if self.deceasedReason() and not ignoreDeath:
                lines.append(self.deceasedReason())
        if not hideDates and self.adopted():
            ignoreAdoption = (
                self.adoptedDateTime() and self.adoptedDateTime() > currentDateTime
            )
            if self.adoptedDateTime() and not ignoreAdoption:
                lines.append("a. " + util.dateString(self.adoptedDateTime()))

        # Compile Custom Details
        if not hideDetails and self.diagramNotes():
            for line in self.diagramNotes().split("\n"):
                lines.append(line)
        mainText = "\n".join(lines).strip()

        # Compile Variables
        variableLines = []
        variableColors = []
        if (
            not hideVariables
            and self.scene()
            and not self.scene().hideVariablesOnDiagram()
        ):
            if util.IS_UI_DARK_MODE:
                vBaseColor = QColor(self.VARIABLE_BASE_COLOR_DARK_MODE)
            else:
                vBaseColor = QColor(self.VARIABLE_BASE_COLOR_LIGHT_MODE)
            hideVariableSteadyStates = self.scene().hideVariableSteadyStates()
            for i, entry in enumerate(self.scene().eventProperties()):
                value, isChange = self.variablesDatabase.get(
                    entry["attr"], currentDateTime
                )
                if value is None or (not isChange and hideVariableSteadyStates):
                    continue
                # if entry["attr"] in (slugify(util.ATTR_ANXIETY),) and value in (
                #     util.VAR_ANXIETY_DOWN,
                #     util.VAR_ANXIETY_SAME,
                #     util.VAR_ANXIETY_UP,
                # ):
                #     continue
                # if entry["attr"] in (slugify(util.ATTR_FUNCTIONING),) and value in (
                #     util.VAR_FUNCTIONING_DOWN,
                #     util.VAR_FUNCTIONING_SAME,
                #     util.VAR_FUNCTIONING_UP,
                # ):
                #     continue
                variableLines.append("%s: %s" % (entry["name"], value))
                if isChange:
                    alpha = 1.0
                else:
                    alpha = 0.4
                color = QColor(vBaseColor)
                color.setAlphaF(alpha)
                variableColors.append(color)

        # Do Update
        if mainText and variableLines:
            self.detailsText.setText(mainText, variableLines)
            for i, color in enumerate(variableColors):
                self.detailsText.setExtraLineColor(i, color)
            # flash lines that have changed
            if not self.isUpdatingAll():
                for i in range(max(len(variableLines), len(self._lastVariableLines))):
                    if i < len(variableLines):
                        if i < len(self._lastVariableLines):
                            lastLine = self._lastVariableLines[i]
                        else:
                            lastLine = None
                        if lastLine != variableLines[i]:
                            self.detailsText.flashExtraLine(i)
        else:
            self.detailsText.setText(mainText)
        self._lastVariableLines = variableLines
        requestToHide = self.detailsText.isEmpty() or (
            hideDetails and hideDates and hideVariables
        )
        self.detailsText.setParentRequestsToShow(not requestToHide)

    def updatePenAndGeometry(self):
        self.updatePen()
        self.updateGeometry()

    def updateDetailsAndChild(self):
        """Adopted"""
        self.updateDetails()
        if self.childOf:
            self.childOf.updateGeometry()

    def updateGeometryAndDetails(self):
        self.updateGeometry()
        self.updateDetails()

    def shouldShowFor(self, dateTime, tags=[], layers=[]):
        if (
            self.isSelected()
        ):  # sort of an override to prevent prop sheets disappearing, updated in ItemSelectedChange
            # if self.name(): self.here('True:isSelected', self.name())
            return True
        found = False
        if layers and not set(layers).intersection(set(self._layers)):
            ret = False
        elif self.birthDateTime():
            ret = self.birthDateTime() <= dateTime
        else:
            ret = True
        # failed attempt at linking people without birthdates
        # elif not self.marriages and not self.parents():
        #     return True
        # else:
        #     for marriage in self.marriages:
        #         spouse = marriage.spouseOf(self)
        #         if spouse.birthDateTime() and spouse.shouldShowFor(date):
        #             return True
        #     if self.parents():
        #         for parent in (self.parents().personA(), self.parents().personB()):
        #             if parent.birthDateTime() and parent.shouldShowFor(date):
        #                 return True
        #     return False
        return ret

    # def __paint(self, painter, option, widget):
    #     # paint background
    #     painter.save()
    #     painter.setBrush(self.brush())
    #     painter.setPen(Qt.transparent)
    #     path = QPainterPath(self.path())
    #     path.setFillRule(Qt.WindingFill)
    #     painter.drawPath(path)
    #     painter.restore()
    #     super().paint(painter, option, widget)
    #     if self.gender() == "unknown":
    #         painter.save()
    #         painter.setPen(self.pen())
    #         font = QFont(util.AGE_FONT)
    #         font.setPointSize(font.pointSize() * 2)
    #         painter.setFont(font)
    #         painter.drawText(self.boundingRect(), Qt.AlignCenter, "?")
    #         painter.restore()
    #     elif self.age() is not None:
    #         painter.save()
    #         p = QPen(self.pen())
    #         if self.isSelected() and not self.primary():
    #             p.setColor(util.contrastTo(self.brush().color()))
    #         painter.setPen(p)
    #         font = QFont(util.AGE_FONT)
    #         font.setPointSize(font.pointSize() * 2)
    #         painter.setFont(font)
    #         painter.drawText(self.boundingRect(), Qt.AlignCenter, str(self.age()))
    #         painter.restore()

    def mousePressEvent(self, e):
        if self.view().dragMode() == QGraphicsView.ScrollHandDrag:
            e.ignore()
            return
        super().mousePressEvent(
            e
        )  # must come first to select before updating draggingWithMe
        self.mouseDownPos = e.scenePos()
        self.mouseMovePos = e.scenePos()
        self.mouseDownPersonPos = self.pos()
        self.mouseDownSceneBoundingRect = self.sceneBoundingRect()
        self.draggingWithMe = []
        for person in self.scene().people():
            if person.isSelected() and person is not self:
                person.setFlag(QGraphicsItem.ItemIsMovable, False)
                person.draggingMaster = self
                person.draggingWithMe_origPos = person.scenePos()
                self.draggingWithMe.append(person)

    def mouseMoveEvent(self, e):
        if self.view().dragMode() == QGraphicsView.ScrollHandDrag:
            e.ignore()
            return
        self.mouseMovePos = e.scenePos()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.view().dragMode() == QGraphicsView.ScrollHandDrag:
            e.ignore()
            return
        super().mouseReleaseEvent(
            e
        )  # must come first to deselect before updating draggingWithMe
        self.mouseDownPos = None
        self.mouseMovePos = None
        self.mouseDownPersonPos = None
        self.mouseDownSceneBoundingRect = None
        if self.snappedOther:
            self.scene().onPersonUnsnapped(self)
            self.snappedOther = None
        for person in list(self.draggingWithMe):
            person.setFlag(QGraphicsItem.ItemIsMovable, True)
            person.draggingMaster = None
            person.draggingWithMe_origPos = None
            self.draggingWithMe.remove(person)

    def itemChange(self, change, variant):
        if hasattr(self, "isInit") and not self.isInit:
            return super().itemChange(change, variant)
        if change == QGraphicsItem.ItemSceneChange:
            if self.scene():
                if self.childOf:
                    self.scene().removeItem(self.childOf)
                self.scene().removeItem(self.detailsText)
            self.updateDetails()
        elif change == QGraphicsItem.ItemSceneHasChanged:
            if self.scene():
                if self.childOf:
                    self.childOf.setParentItem(self)
                    self.scene().addItem(self.childOf)
                    if self.childOf.multipleBirth:
                        self.scene().addItem(self.childOf.multipleBirth)
                self.detailsText.setParentItem(self)
                self.scene().addItem(self.detailsText)
                if self.scene().readOnly():
                    self.setFlag(QGraphicsItem.ItemIsMovable, False)
                else:
                    self.setFlag(QGraphicsItem.ItemIsMovable, True)
                self.updateVariablesDatabase()
        elif change == QGraphicsItem.ItemPositionChange:
            if self.scene() and not self.scene().isInitializing:
                if self.scene().mousePressOnDraggable:
                    self.scene().checkItemDragged(
                        self, variant
                    )  # update compressed move command
            # snap-drag
            if self.draggingMaster is not None:
                pass
            elif self.scene() and self.scene().readOnly():
                # Prevent moving person after double-click and hold when drawer is animating open
                variant = self.pos()
            # Re-enabled to accomodate correcting arrangements from EventForm.
            # elif (
            #     self.scene()
            #     and self.scene().isAnimatingDrawer()
            #     and self.scene().isDraggingSomething()
            # ):
            #     # Prevent moving person after double-click and hold when drawer is animating open
            #     variant = self.pos()
            elif self.scene() and self.scene().canSnapDrag and self.mouseDownPos:
                # snap to people?
                yDelta = self.mouseMovePos.y() - self.mouseDownPos.y()
                yWouldBe = self.mouseDownPos.y() + yDelta
                rectWouldBe = QRectF(self.mouseDownSceneBoundingRect)
                rectWouldBe.setY(self.mouseDownSceneBoundingRect.y() + yDelta)
                otherSceneRect = None
                THRESHOLD = (
                    util.SNAP_THRESHOLD_PERCENT
                    * self.mouseDownSceneBoundingRect.height()
                )
                snapTo = None
                diffs = []
                for other in self.scene().people():
                    if (
                        other is not self
                        and not other.isSelected()
                        and other.isVisible()
                    ):
                        # TODO: don't use Person.boundingRect() because we want to ignore the outer shape when `primary`
                        _otherSceneRect = other.mapToScene(
                            other.boundingRect()
                        ).boundingRect()
                        diff = abs(_otherSceneRect.y() - rectWouldBe.y())
                        diffs.append((other, _otherSceneRect, diff))
                if diffs:
                    diffs = sorted(diffs, key=lambda x: x[2])
                    other, _otherSceneRect, diff = diffs[0]
                    if diff < THRESHOLD:
                        otherSceneRect = _otherSceneRect
                        snapTo = other  # sync frames after pos has changed
                    # stop old snap
                    if self.snappedOther and self.snappedOther is not snapTo:
                        self.scene().onPersonUnsnapped(self)
                        self.snappedOther = None
                    # start or continue snap
                    if snapTo:
                        selfSceneRect = self.mapToScene(
                            self.boundingRect()
                        ).boundingRect()
                        diffY = selfSceneRect.height() * 0.5
                        variant.setY(otherSceneRect.y() + diffY)
                        if snapTo is not self.snappedOther:
                            self.snappedOther = snapTo
                            self.scene().onPersonSnapped(
                                self, self.snappedOther, variant
                            )
                        else:
                            self.scene().onPersonSnapUpdated(
                                self, self.snappedOther, variant
                            )
            if self.mouseDownPersonPos:
                diffX2 = variant.x() - self.mouseDownPersonPos.x()
                diffY2 = variant.y() - self.mouseDownPersonPos.y()
                for person in self.draggingWithMe:
                    person.setPos(
                        person.draggingWithMe_origPos + QPointF(diffX2, diffY2)
                    )
                # else:
                #     variant.setY(yWouldBe)
            self.cachedPosChangeOldPos = self.pos()
        elif change == QGraphicsItem.ItemPositionHasChanged:
            if self.scene():  # None when commands.AddPerson
                for emotion in self.emotions():
                    # update emotions fanned box offsets before updating their geometry
                    if emotion.fannedBox:
                        emotion.fannedBox.updateOffsets()  # double calls when more than one person/emotion moved...
                self.updateDependents()
                posDelta = self.cachedPosChangeOldPos - variant
                for layerItem in self._layerItems:
                    layerItem.setPos(layerItem.pos() - posDelta)
        elif change == QGraphicsItem.ItemSelectedChange:
            self.updatePen()
            # if variant:
            #     self.brush = util.SELECTION_BRUSH
            # else:
            #     self.brush = None
            if self.childOf:
                self.childOf.updatePen()
                self.childOf.updateGeometry()
            if variant is False:
                self.updateAll()  # update after override in shouldShowFor
        return super().itemChange(change, variant)

    ## Paint animations

    def onFadePenTick(self, c):
        super().onFadePenTick(c)
        self.detailsText.setMainTextColor(self.pen().color())

    def onSizeAnimTick(self, x):
        if x != self.scale():
            self.setScale(x)
            self.updateGeometryAndDependents()
            if self.childOf and self.childOf.multipleBirth:
                self.childOf.multipleBirth.updateScale()

    def onSizeAnimFinished(self):
        pass

    def onUpdateAll(self):
        super().onUpdateAll()
        for emotion in self.emotions():
            if emotion.kind() == RelationshipKind.Cutoff:
                emotion.setParentItem(self)
        self.onAgeChanged()

    ## Files

    def __dragEnterEvent(self, e):
        if not e.dropAction() in [Qt.MoveAction, Qt.CopyAction]:
            return
        if e.mimeData().hasUrls():
            for url in e.mimeData().urls():
                if QFileInfo(url.toLocalFile()).isDir():
                    return
        self.here()
        e.acceptProposedAction()

    def __dropEvent(self, e):
        self.here()
        for url in e.mimeData().urls():
            # if QFileInfo(url.toLocalFile()).suffix().lower() in util.DROP_EXTENSIONS:
            self.here(url)
            src = url.toLocalFile()
            dest = os.path.join(self.docsPath(), QFileInfo(src).fileName())
            destDir = QFileInfo(dest).dir()
            if not destDir.exists():
                os.makedirs(destDir.absolutePath())
            if e.dropAction() == Qt.CopyAction:
                self.here("Copied", dest)
                shutil.copyfile(src, dest)
                self.fileAdded.emit(dest)

    def documentsPath(self):
        if self.scene() and self.scene().document():
            documentUrl = self.scene().document().url().toLocalFile()
            return os.path.join(documentUrl, "People", str(self.id))

    ## Actions

    def setVisible(self, on):
        super().setVisible(on)
        self.updateDetails()


from PyQt5.QtQml import qmlRegisterType

qmlRegisterType(Person, "Person", 1, 0, "Person")
