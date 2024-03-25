import os, sys, re, logging
import json
import bisect
from .pyqt import *
from . import version, util, commands, version, compat, slugify
from .objects import *
from .itemgarbage import ItemGarbage
from . import json

if not util.IS_IOS:
    import xlsxwriter


AUTO_PENCIL_MODE = True
MOUSE_PRESSURE = 0.2


log = logging.getLogger(__name__)


import math, time


def mousePressure():
    if True:
        return (1 + (math.sin(time.time() * 2 * math.pi))) * 0.25
    else:
        return MOUSE_PRESSURE


class DragCreateItem(PathItem):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.prop("itemPos").setLayered(False)
        self._animElapsed = QElapsedTimer()
        self._animElapsed.start()
        self._timerId = None
        self.updatePen()

    def timerEvent(self, e):
        self.update()

    def updatePen(self):
        """Animate pen"""
        super().updatePen()
        pen = QPen(util.PEN)
        pen.setDashPattern([4, 2])
        self.setPen(pen)

    def paint(self, painter, option, widget):
        pen = self.pen()
        pen.setDashOffset(self._animElapsed.elapsed() / 70)
        self.setPen(pen)
        super().paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == self.ItemSceneHasChanged:
            if self._timerId:
                self.killTimer(self._timerId)
            if value:
                self._timerId = self.startTimer(util.ANIM_TIMER_MS)
        return super().itemChange(change, value)


class Scene(QGraphicsScene, Item):

    loaded = pyqtSignal()
    diagramReset = pyqtSignal()
    propertyChanged = pyqtSignal(Property)
    clipboardChanged = pyqtSignal()
    printRectChanged = pyqtSignal()
    itemModeChanged = pyqtSignal()
    itemDragged = pyqtSignal(object)
    itemAdded = pyqtSignal(Item)
    itemRemoved = pyqtSignal(Item)
    eventAdded = pyqtSignal(Event)
    eventChanged = pyqtSignal(Property)
    eventRemoved = pyqtSignal(Event)
    emotionAdded = pyqtSignal(Emotion)
    emotionChanged = pyqtSignal(Property)
    emotionRemoved = pyqtSignal(Emotion)
    layerAdded = pyqtSignal(Layer)
    layerChanged = pyqtSignal(Property)
    layerRemoved = pyqtSignal(Layer)
    activeLayersChanged = pyqtSignal(list)
    layerOrderChanged = pyqtSignal()
    layerItemAdded = pyqtSignal(LayerItem)
    layerItemChanged = pyqtSignal(Property)
    layerItemRemoved = pyqtSignal(LayerItem)
    personAdded = pyqtSignal(Person)
    personChanged = pyqtSignal(Property)
    personRemoved = pyqtSignal(Person)
    marriageAdded = pyqtSignal(Marriage)
    marriageChanged = pyqtSignal(Property)
    marriageRemoved = pyqtSignal(Marriage)
    showNotes = pyqtSignal(PathItem)
    itemDoubleClicked = pyqtSignal(PathItem)

    Item.registerProperties(
        (
            {"attr": "uuid"},
            {"attr": "masterKey"},
            {"attr": "alias"},
            {"attr": "readOnly", "type": bool},
            {"attr": "lastItemId", "default": -1, "notify": False},
            {"attr": "contributeToResearch", "default": False},
            {"attr": "useRealNames", "default": False},
            {"attr": "password", "default": util.newPassword()},
            {"attr": "requirePasswordForRealNames", "default": False},
            {"attr": "showAliases", "default": False, "onset": "onShowAliases"},
            {"attr": "hideNames", "default": False},
            {"attr": "hideToolBars", "default": False},
            {"attr": "hideEmotionalProcess", "default": False},
            {"attr": "hideEmotionColors", "default": False},
            {"attr": "hideLayers", "default": False},
            {"attr": "hideDateSlider", "type": bool, "default": False},
            {
                "attr": "hideVariablesOnDiagram",
                "type": bool,
                "default": False,
            },
            {
                "attr": "hideVariableSteadyStates",
                "type": bool,
                "default": False,
            },
            {"attr": "exclusiveLayerSelection", "type": bool, "default": True},
            {
                "attr": "storePositionsInLayers",
                "type": bool,
                "default": False,
            },  # obsolete
            {"attr": "currentDateTime", "default": QDateTime.currentDateTime()},
            {"attr": "scaleFactor", "type": float, "default": util.DEFAULT_SCENE_SCALE},
            {"attr": "pencilColor", "default": util.PEN.color()},
            {
                "attr": "eventProperties",
                "default": [],
            },  # { 'attr': 'symptom', 'name': '𝚫 Symptom' }
            {
                "attr": "legendData",
                "default": {
                    "shown": False,
                    "size": util.DEFAULT_LEGEND_SIZE,
                    "anchor": "south-east",
                },
            },
        )
    )

    def __init__(self, parent=None, document=None, **kwargs):
        super().__init__(parent)
        _items = kwargs.pop("items", None)
        self.isScene = True
        self._hasRead = False
        self._document = (
            document  # for self.name() (windowTitle) and item.documentsPath
        )
        self._itemMode = util.ITEM_NONE
        self._stopOnAllEvents = True
        self._showNotesIcons = False
        self._serverDiagram = None
        self.lastLoadData = {}
        self.futureItems = []  # retain items not yet supported in this version
        self.initialized = False
        self.isDeinitializing = False
        self.isInitializing = True
        self._batchAddRemoveStackLevel = 0
        self._updatingAll = (
            False  # indicates a static update is occuring, i.e. no animations, etc
        )
        self._areActiveLayersChanging = False
        self._isResettingSomeLayerProps = False
        self._isAddingLayerItem = False
        self.dragStartItem = None
        self.dragCreateItem = None
        self.mouseElapsedTimer = QElapsedTimer()
        self.hoverItem = None
        self.mouseCursorItem = QGraphicsPathItem()
        self.mouseCursorPosition = QGraphicsTextItem()
        self.layerAnimationGroup = QParallelAnimationGroup(self)
        self.layerAnimationGroup.finished.connect(self.onLayerAnimationFinished)
        # items
        self.itemRegistry = {}
        self._people = []
        self._events = []
        self._marriages = []
        self._emotions = []
        self._layerItems = []
        self._itemDetails = []
        self._layers = []
        self._activeLayers = []
        self.nowEvent = Event(
            None,
            uniqueId="now",
            dateTime=QDateTime.currentDateTime(),
            description="Now",
            parentName="",
        )
        self.nowEvent.parent = self
        self.addItem(self.nowEvent)
        self.mousePressOnDraggable = None  # item move undo compression
        self._isNudgingSomething = False
        self._isDraggingSomething = False
        self.clipboard = None
        self._printRect = QRectF()

        # This is contained here because many TimelineModels (person, marriage,
        # graphical timeline) use the same SearchModel.
        from .models import SearchModel

        self.searchModel = SearchModel(self)
        self.searchModel.setObjectName("Scene.searchModel")
        self.searchModel.scene = self
        self.searchModel.changed.connect(self.onSearchChanged)

        from .models import TimelineModel

        self.timelineModel = TimelineModel(self)
        self.timelineModel.setObjectName("Scene.timelineModel")
        self.timelineModel.scene = self
        self.timelineModel.items = [self]

        from .models import PeopleModel

        self.peopleModel = PeopleModel(self)
        self.peopleModel.setObjectName("Scene.peopleModel")
        self.peopleModel.scene = self

        from .models import AccessRightsModel

        self.accessRightsModel = AccessRightsModel(self)
        self.accessRightsModel.setObjectName("Scene.accessRightsModel")
        self.accessRightsModel.scene = self

        # snap
        self.canSnapDrag = False
        self.snapItem = QGraphicsLineItem()
        self.setProperties(**kwargs)

        # pencil
        self.pencilCanvas = PencilStroke.Canvas()
        self.pencilCanvas.setPos(QPointF(0, 0))
        self.pencilParent = None
        self.calloutParent = None
        # debug
        self.centerItem = util.Center()
        self.viewSceneRectItem = QGraphicsRectItem()
        self.viewSceneRectItem.setPen(QColor("green"))
        self.printRectItem = QGraphicsRectItem()
        self.printRectItem.setPen(QColor("red"))

        self.isInitializing = False
        self.initialized = True
        self.startTimer(60 * 1000)  # update the now event periodically
        if _items:
            if not isinstance(_items, list):
                _items = [_items]
            self.addItems(*tuple(_items))

    def __repr__(self):
        props = {}
        for prop in self.props:
            props[prop.attr] = prop.get()
        s = util.pretty(props, exclude="id")
        if s:
            s = ": " + s
        return "<%s[%s]%s>" % (self.__class__.__name__, id(self), s)

    def deinit(self, garbage=None):
        if garbage is None:
            garbage = ItemGarbage(_async=False)
        self.isDeinitializing = True
        garbage.dump(self.itemRegistry)
        self.itemRegistry = {}
        self.isDeinitializing = False
        super().deinit()

    def isDeinitializing(self):
        return self.isDeinitializing

    def setSession(self, session):
        self.accessRightsModel.setSession(session)

    def setServerDiagram(self, diagram):
        self._serverDiagram = diagram
        self.accessRightsModel.setServerDiagram(diagram)

    def serverDiagram(self):
        return self._serverDiagram

    def isAnimatingDrawer(self):
        view = self.view()
        if view:
            return view.parent().isAnimatingDrawer
        else:
            return False

    def setScaleFactor(self, *args, **kwargs):
        self.prop("scaleFactor").set(*args, **kwargs)

    def addItem(self, item, register=True):
        if (
            isinstance(item, QGraphicsItem) or isinstance(item, QGraphicsObject)
        ) and not item.scene() is self:
            super().addItem(item)
        if not isinstance(item, Item):
            return
        if register:
            if item.id is None:
                item.id = self.nextId()
            elif item.id > self.lastItemId():
                self.setLastItemId(item.id)  # bump
            elif self.itemRegistry.get(item.id, None) is item:  # already registered
                return
            self.itemRegistry[item.id] = item
        ## Signals
        if item.isPathItem:
            if not self.isBatchAddingRemovingItems():
                item.beginUpdateFrame()
                item.updateAll()
                item.endUpdateFrame()
        if item.isPerson:
            self._people.append(item)
            item.eventAdded[Event].connect(self.eventAdded)
            item.eventRemoved[Event].connect(self.eventRemoved)
            if not self.isBatchAddingRemovingItems():
                item.setLayers([x.id for x in self.activeLayers()])
                if self.activeLayers():
                    # Added because person remained hidden because
                    # they weren't updated after setting tags.
                    item.updateAll()
                self.personAdded[Person].emit(item)
        elif item.isMarriage:
            self._marriages.append(item)
            item.eventAdded[Event].connect(self.eventAdded)
            item.eventRemoved[Event].connect(self.eventRemoved)
            if not self.isBatchAddingRemovingItems():
                self.marriageAdded[Marriage].emit(item)
        elif item.isEvent:
            self._events.append(item)
            for entry in self.eventProperties():
                if item.dynamicProperty(entry["attr"]) is None:
                    item.addDynamicProperty(entry["attr"])
            if not self.isBatchAddingRemovingItems():
                self.eventAdded.emit(item)
        elif item.isEmotion:
            self._emotions.append(item)
            if not self.isBatchAddingRemovingItems():
                item.addTags(self.searchModel.tags)
                self.emotionAdded.emit(item)
        elif item.isLayer:
            self._layers.append(item)
            item.setScene(self)
            if not self.isBatchAddingRemovingItems():
                self.tidyLayerOrder()
            self.layerAdded.emit(item)
            if not self.isBatchAddingRemovingItems():
                if item.active():
                    self.updateActiveLayers()
        elif item.isLayerItem:
            self._isAddingLayerItem = True
            self._layerItems.append(item)
            if not self.isInitializing:
                if not self.layers():
                    layer = Layer(name="View 1", active=True)
                    self.addItem(layer)
                if not item.layers():
                    layerIds = [layer.id for layer in self.activeLayers()]
                    if not layerIds:
                        raise RuntimeError(
                            "Cannot add a LayerItem if there are no active layers."
                        )
                    item.setLayers(layerIds)
                self.layerItemAdded.emit(item)
            self._isAddingLayerItem = False
        elif item.isItemDetails:
            self._itemDetails.append(item)
        item.addPropertyListener(self)
        item.onRegistered(self)
        if item.isPathItem:  # after geometries are updated.
            if not self.isBatchAddingRemovingItems():
                self.checkPrintRectChanged()
        if self.isBatchAddingRemovingItems() and not item in self._batchAddedItems:
            self._batchAddedItems.append(item)
        self.itemAdded.emit(item)
        return item

    def addItems(self, *args):
        self.setBatchAddingRemovingItems(True)
        for item in args:
            self.addItem(item)
        self.setBatchAddingRemovingItems(False)

    def isAddingLayerItem(self):
        return self._isAddingLayerItem

    def isBatchAddingRemovingItems(self):
        return self._batchAddRemoveStackLevel > 0

    def setBatchAddingRemovingItems(self, on):
        if on:
            self._batchAddRemoveStackLevel += 1
            self._batchAddedItems = []
            self._batchRemovedItems = []
        else:
            self._batchAddRemoveStackLevel -= 1
            assert self._batchAddRemoveStackLevel >= 0
            if self._batchAddRemoveStackLevel == 0:
                if (
                    len(
                        [
                            x
                            for x in (self._batchAddedItems + self._batchRemovedItems)
                            if isinstance(x, Layer)
                        ]
                    )
                    > 0
                ):
                    self.tidyLayerOrder()
                self.updateAll()
                self.checkPrintRectChanged()
                # maybe move these into updateAll()
                for item in self._batchAddedItems + self._batchRemovedItems:
                    if item.isEmotion:
                        item.updateFannedBox()
                self.timelineModel.cleanupBatchAddingRemovingItems(
                    self._batchAddedItems, self._batchRemovedItems
                )
                self.peopleModel.cleanupBatchAddingRemovingItems(
                    self._batchAddedItems, self._batchRemovedItems
                )
                self._batchAddedItems = []
                self._batchRemovedItems = []

    def removeItem(self, item):
        if isinstance(item, QGraphicsItem) and item.scene() is self:
            super().removeItem(item)
        if not isinstance(item, Item):
            return
        # deregister
        if not item.id in self.itemRegistry:
            return
        del self.itemRegistry[item.id]
        item.onDeregistered(self)
        item.removePropertyListener(self)
        # I think it's ok to skip signals when deinitializing
        if self.isDeinitializing:
            return
        ## Signals
        if item.isPerson:
            self._people.remove(item)
            self.personRemoved.emit(item)
            item.eventAdded[Event].disconnect(self.eventAdded)
            item.eventRemoved[Event].disconnect(self.eventRemoved)
        elif item.isMarriage:
            self._marriages.remove(item)
            self.marriageRemoved.emit(item)
            item.eventAdded[Event].disconnect(self.eventAdded)
            item.eventRemoved[Event].disconnect(self.eventRemoved)
        elif item.isEvent:
            self._events.remove(item)
            self.eventRemoved.emit(item)
        elif item.isEmotion:
            self._emotions.remove(item)
            self.emotionRemoved.emit(item)
        elif item.isLayer:
            self._layers.remove(item)
            self.tidyLayerOrder()
            self.layerRemoved.emit(item)
        elif item.isLayerItem:
            self._layerItems.remove(item)
        elif item.isItemDetails:
            self._itemDetails.remove(item)
        if item.isPathItem:  # so far only for details/sep items
            if not self.isBatchAddingRemovingItems():
                self.checkPrintRectChanged()
        if self.isBatchAddingRemovingItems() and not item in self._batchRemovedItems:
            self._batchRemovedItems.append(item)
        self.itemRemoved.emit(item)

    def resortLayersFromOrder(self):
        # re-sort iternal layer list.
        was = list(self._layers)

        def layerOrder(layer):
            if layer.order() is layer.prop("order").default:
                return sys.maxsize - 1
            else:
                return layer.order()

        self._layers = sorted(self.layers(), key=layerOrder)
        if self._layers != was:
            self.layerOrderChanged.emit()

    def tidyLayerOrder(self):
        """Set Layer.order based on order of self._layers."""
        was = list(self._layers)
        for i, layer in enumerate(self.layers()):
            layer.setOrder(i, notify=False)
        if self._layers != was:
            self.layerOrderChanged.emit()

    def view(self):
        views = self.views()
        if len(views) == 0:
            return None
        return views[0]

    def onItemDoubleClicked(self, item):
        self.itemDoubleClicked.emit(item)

    def newPersonScale(self):
        size = self.newPersonSize()
        return util.scaleForPersonSize(size)

    def newPersonSize(self):
        scaleFactor = self.scaleFactor()
        if scaleFactor <= 0.5:
            size = 5
        elif scaleFactor > 0.5 and scaleFactor <= 0.8:
            size = 4
        elif scaleFactor > 0.8 and scaleFactor <= 1.5:
            size = 3
        elif scaleFactor > 1.5 and scaleFactor <= 2.7:
            size = 2
        elif scaleFactor > 2.7:
            size = 1
        return size

    def centerAllItems(self):
        """Called from MainWindow.setDocument."""
        delta = self.getPrintRect().center()
        for item in self.items():
            if not isinstance(item, Item):
                continue
            if item.isPerson or (item.isLayerItem and not item.parentItem()):
                newPos = item.pos() - delta
                if item.isPerson:
                    item.nudging = True
                item.setPos(newPos)
                if item.isPerson:
                    item.nudging = False
        self.checkPrintRectChanged()

    def prune(self, data):
        """Delete any references to items containing stale references.
        Returns any chunks that were removed, otherwise None.
        """
        if not data.get("items"):
            return
        by_ids = {}
        for chunk in data["items"]:
            by_ids[chunk["id"]] = chunk

        pruned = []
        for chunk in list(data["items"]):
            if chunk["kind"] == "Marriage":
                for eventChunk in list(chunk["events"]):
                    dateTime = eventChunk.get("dateTime", eventChunk.get("date"))
                    if not dateTime:
                        chunk["events"].remove(eventChunk)
                        pruned.append(eventChunk)
            elif chunk["kind"] == "MultipleBirth":
                for childId in chunk["children"]:
                    if not childId in by_ids:
                        log.warning(
                            f"Removing MultipleBirth with stale ref to child {childId}"
                        )
                        data["items"].remove(chunk)
                        pruned.append(chunk)
                        break
        if pruned:
            return pruned
        else:
            return None

    ## Files

    def read(self, data, byId=None):
        """Read in a python dict, return an error string on failure."""
        if self._hasRead:
            raise RuntimeError("Can only read data into a Scene once.")
        ver = data.get("versionCompat")
        if ver and version.greaterThan(ver, version.VERSION_COMPAT):
            return (
                "This file cannot be opened because it was saved with a future version of this app (%s)."
                % ver
            )
        self.isInitializing = True
        if not util.validate_uuid4(data.get("uuid")):
            # self.here('RESETTING UUID:', data.get('uuid'))
            data["uuid"] = None
        self._hasRead = True
        self.timelineModel.reset("scene")
        self.timelineModel.reset("items")
        self.peopleModel.reset("scene")
        # TODO: copy this forward, sort of like future items...
        self.lastLoadData = dict(((p.name(), p.get()) for p in self.props))
        self.lastLoadData["name"] = data.get("name")
        self.prune(data)
        try:
            compat.update_data(data)
            super().read(data, None)
            self.addItem(self.nowEvent)  # super().read() sets lastItemId to -1
            ## Set 'em up
            itemChunks = []
            self.futureItems = []
            items = []
            for chunk in data.get("items", []):
                if chunk["kind"] == "Person":
                    item = Person()
                elif chunk["kind"] == "Marriage":
                    item = Marriage()
                elif chunk["kind"] == "MultipleBirth":
                    item = MultipleBirth()
                elif chunk["kind"] == "PencilStroke":
                    item = PencilStroke()
                elif chunk["kind"] == "Layer":
                    item = Layer()
                elif chunk["kind"] == "Callout":
                    item = Callout()
                elif chunk["kind"] in Emotion.kindSlugs():
                    kind = Emotion.kindForKindSlug(chunk["kind"])
                    item = Emotion(kind=kind)
                else:
                    log.warning(f"Retaining future item: {chunk}")
                    self.futureItems.append(chunk)
                    continue
                item.id = chunk["id"]
                items.append(item)
                itemChunks.append((item, chunk))
            if util.ENABLE_DUPLICATES_CHECK:  # check for duplicates
                check = {}
                for item, chunk in itemChunks:
                    if not item.id in check:
                        check[item.id] = []
                    check[item.id].append(item)
                for k, v in check.items():
                    x = check[k]
                    if len(x) > 1:
                        log.warning(f"Found duplicate items with id: {k}")
                        for item in x:
                            log.warning(f"    {item}")
            ## Knock 'em down
            itemMap = {}
            for item, chunk in itemChunks:
                itemMap[item.id] = item
            # read w/ error checking
            erroredOut = []
            for item, chunk in list(itemChunks):
                if (
                    item.read(chunk, itemMap.get) == False
                ):  # have to read in ids before addItem()
                    erroredOut.append(item)
            self.setBatchAddingRemovingItems(True)
            for item in items:
                if item.isEmotion and item.personA() is None:
                    log.warning(f"Emotion {item} has no personA, skipping loading...")
                    continue
                self.addItem(
                    item
                )  # don't use addItems() to avoid calling updateAll() until layer
            for itemId, item in self.itemRegistry.items():
                if itemId is None:
                    raise ValueError("Found Item object stored without id!" + item)
            # add event dynamic properties
            for e in self.events():
                if e.uniqueId() != "now":
                    for entry in self.eventProperties():
                        if e.dynamicProperty(entry["attr"]) is None:
                            e.addDynamicProperty(entry["attr"])
            self.pencilCanvas.setColor(self.pencilColor())
            compat.update_scene(self, data)
            self.resortLayersFromOrder()
            self.setBatchAddingRemovingItems(False)
        except Exception as e:
            import traceback

            traceback.print_exc()
            return "This file is currupt and cannot be opened"
        finally:
            self.isInitializing = False
        # models
        self.timelineModel.scene = self
        self.timelineModel.items = [self]
        self.peopleModel.scene = self

    def write(self, data, selectionOnly=False):
        super().write(data)
        data["version"] = version.VERSION
        data["versionCompat"] = (
            version.VERSION_COMPAT
        )  # oldest version this scene can be opened in
        data["items"] = []
        data["name"] = self.name()
        items = []
        for id, item in self.itemRegistry.items():
            if selectionOnly and item.isPathItem and not item.isSelected():
                continue
            else:
                items.append(item)
        for item in items:
            chunk = {}
            if item.isPerson:
                chunk["kind"] = "Person"
            elif item.isMarriage:
                chunk["kind"] = "Marriage"
            elif item.isPencilStroke:
                chunk["kind"] = "PencilStroke"
            elif item.isLayer:
                chunk["kind"] = "Layer"
            elif item.isCallout:
                chunk["kind"] = "Callout"
            elif item.isEmotion:
                chunk["kind"] = item.kind()
            elif item.isMultipleBirth:
                chunk["kind"] = "MultipleBirth"
            else:
                continue
            item.write(chunk)
            data["items"].append(chunk)
        # forward-compatibility
        for chunk in self.futureItems:
            data["items"].append(chunk)
            log.warning(f"Retained future item: {chunk}")

    def data(self, selectionOnly=False):
        data = {}
        self.write(data, selectionOnly=selectionOnly)
        return data

    def getPrintRect(self, forLayers=None, forTags=None):
        rect = QRectF()
        if forTags is not None:
            pass
        elif forLayers:
            m = set()
            for layer in forLayers:
                for t in layer.tags():
                    m = m | {t}
            forTags = list(m)
        else:
            forTags = []
        currentDateTime = self.currentDateTime()
        for item in self.find(types=[Person, LayerItem]):
            if item.isLayerItem and item.shouldShowForLayers(forLayers):
                itemRect = item.layeredSceneBoundingRect(
                    forLayers=forLayers, forTags=forTags
                )
            elif item.shouldShowFor(currentDateTime, forTags, forLayers):
                itemRect = item.layeredSceneBoundingRect(
                    forLayers=forLayers, forTags=forTags
                )
            else:
                continue
            rect |= itemRect
        m = util.PRINT_MARGIN
        return rect.marginsAdded(QMarginsF(m, m, m, m))  # fit it all in...

    def checkPrintRectChanged(self):
        activeLayers = self.activeLayers()
        if activeLayers:
            forLayers = activeLayers
        else:
            forLayers = None
        newPrintRect = self.getPrintRect(forLayers=forLayers)
        if newPrintRect != self._printRect:
            self._printRect = newPrintRect
            self.printRectItem.setRect(self.printRect())
            self.printRectChanged.emit()

    def printRect(self, forLayers=None):
        if forLayers:
            return self.getPrintRect(forLayers=forLayers)
        else:
            return self._printRect

    def __writePDF(self, filePath=None, printer=None):
        rect = self.printRect()
        sourceRect = rect.size()
        if printer is None:
            printer = QPrinter()
        printer.setOutputFormat(QPrinter.PdfFormat)
        painter = QPainter()
        painter.begin(printer)
        printerRect = printer.pageRect(QPrinter.Point).toRect()
        if filePath is not None:
            printer.setOutputFileName(filePath)
            # printer.setOrientation(QPrinter.Landscape)
        # elif printer is not None:
        #     # make it fit
        #     sourceRect = image.rect()
        #     if sourceRect.width() > sourceRect.height():
        #         scale = printRect.width() / sourceRect.width()
        #         targetRect = QRect(printRect.x(), printRect.y(),
        #                            sourceRect.width() * scale,
        #                            sourceRect.height() * scale)
        #     else:
        #         scale = printRect.height() / sourceRect.height()
        #         targetRect = QRect(printRect.x(),
        #                            printRect.y(),
        #                            sourceRect.width() * scale,
        #                            sourceRect.height() * scale)
        #     p.drawImage(targetRect, image, sourceRect)
        #     p.end()
        self.render(painter, QRectF(printerRect), self.printRect())
        painter.end()
        painter = None  # control dtor order, before printer

    def writeJPG(self, filePath=None, printer=None):
        rect = self.printRect()
        size = rect.size().toSize() * util.PRINT_DEVICE_PIXEL_RATIO
        image = QImage(size, QImage.Format_RGB32)
        image.setDevicePixelRatio(
            self.view().devicePixelRatio() / util.PRINT_DEVICE_PIXEL_RATIO
        )
        image.fill(QColor("white"))
        painter = QPainter()
        painter.begin(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        self.render(painter, QRectF(0, 0, size.width(), size.height()), rect)
        painter.end()
        if filePath is not None:
            image.save(filePath, "JPEG", 80)
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

    def writePNG(self, filePath):
        rect = self.printRect()
        size = rect.size().toSize() * util.PRINT_DEVICE_PIXEL_RATIO
        image = QImage(size, QImage.Format_ARGB32)
        image.setDevicePixelRatio(
            self.view().devicePixelRatio() / util.PRINT_DEVICE_PIXEL_RATIO
        )
        image.fill(Qt.transparent)
        painter = QPainter()
        painter.begin(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        self.render(painter, QRectF(0, 0, size.width(), size.height()), rect)
        image.save(filePath, "PNG", 100)
        painter.end()

    def writeExcel(self, filePath):
        book = xlsxwriter.Workbook(filePath)
        wrap_format = book.add_format({"text_wrap": True})  # doesn't work
        wrap_format.set_text_wrap()  # doesn't work
        ## Events
        sheet = book.add_worksheet("Timeline")
        sheet.set_column(0, 0, 10)  # Date width
        sheet.set_column(1, 1, 35)  # Description width
        sheet.set_column(2, 2, 10)  # Location width
        sheet.set_column(3, 3, 15)  # Person width
        sheet.set_column(4, 4, 10)  # Logged width
        sheet.set_column(5, 5, 100)  # Notes width
        sheet.write(0, 0, "Date")
        sheet.write(0, 1, "Description")
        sheet.write(0, 2, "Location")
        sheet.write(0, 3, "Person")
        sheet.write(0, 4, "Logged")
        sheet.write(0, 5, "Notes", wrap_format)
        for i, entry in enumerate(self.eventProperties()):
            sheet.write(0, 6 + i, entry["name"])

        model = self.timelineModel
        rowDisplay = lambda row, col: model.data(model.index(row, col))
        for row in range(model.rowCount()):
            index = row + 1
            event = model.eventForRow(row)
            sheet.write(index, 0, rowDisplay(row, 1))  # date
            sheet.write(index, 1, rowDisplay(row, 3))  # description
            sheet.write(index, 2, rowDisplay(row, 4))  # location
            sheet.write(index, 3, rowDisplay(row, 5))  # parent
            sheet.write(index, 4, rowDisplay(row, 6))  # logged
            sheet.write(index, 5, event.notes())  # notes

            # sheet.write(index, 1, event.description() and event.description() or '')
            # sheet.write(index, 2, event.location() and event.location() or '')
            # sheet.write(index, 3, event.parentName())
            # sheet.write(index, 4, util.dateString(event.loggedDateTime()))
            # sheet.write(index, 5, event.notes())
            for i, entry in enumerate(self.eventProperties()):
                prop = item.dynamicProperty(entry["attr"])
                if prop:
                    sheet.write(index, 6 + i, prop.get())
        ## People
        sheet = book.add_worksheet("People")
        sheet.write(0, 0, "Birth Date")
        sheet.write(0, 1, "First Name")
        sheet.write(0, 2, "Middle Name")
        sheet.write(0, 3, "Last Name")
        sheet.write(0, 4, "Nick Name")
        sheet.write(0, 5, "Birth Name")
        sheet.write(0, 6, "Sex")
        sheet.write(0, 7, "Deceased")
        sheet.write(0, 8, "Deceased Reason")
        sheet.write(0, 9, "Date of Death")
        sheet.write(0, 10, "Adopted")
        sheet.write(0, 11, "Adoption Date")
        sheet.write(0, 12, "Notes")
        #
        sheet.write(0, 13, "Show Middle Name")
        sheet.write(0, 14, "Show Last Name")
        sheet.write(0, 15, "Show Nick Name")
        sheet.write(0, 16, "Primary")
        sheet.write(0, 17, "Hide Details")
        people = self.find(
            sort="birthDateTime", types=Person, tags=list(self.searchModel.tags)
        )
        for index, person in enumerate(people):
            sheet.write(index + 1, 0, person.birthDateTime(string=True))
            sheet.write(
                index + 1,
                1,
                self.showAliases() and ("[%s]" % person.alias()) or person.name(),
            )
            sheet.write(index + 1, 2, self.showAliases() and " " or person.middleName())
            sheet.write(index + 1, 3, self.showAliases() and " " or person.lastName())
            sheet.write(index + 1, 4, self.showAliases() and " " or person.nickName())
            sheet.write(index + 1, 5, self.showAliases() and " " or person.birthName())
            sheet.write(index + 1, 6, person.gender())
            sheet.write(index + 1, 7, person.deceased() and "YES" or "")
            sheet.write(index + 1, 8, person.deceasedReason())
            sheet.write(index + 1, 9, person.deceasedDateTime(string=True))
            sheet.write(index + 1, 10, person.adopted() and "YES" or "")
            sheet.write(index + 1, 11, person.adoptedDateTime(string=True))
            sheet.write(index + 1, 12, self.showAliases() and " " or person.notes())
            #
            sheet.write(index + 1, 13, person.showMiddleName() and "YES" or "")
            sheet.write(index + 1, 14, person.showLastName() and "YES" or "")
            sheet.write(index + 1, 15, person.showNickName() and "YES" or "")
            sheet.write(index + 1, 16, person.primary() and "YES" or "")
            sheet.write(index + 1, 17, person.hideDetails() and "YES" or "")
        book.close()

    def writeJSON(self, filePath):
        data = {}
        self.write(data)

        import pprint

        p_sdata = pprint.pformat(data, indent=4)
        log.info(p_sdata)
        with open(filePath, "w") as f:
            f.write(p_sdata)

        # sdata = json.dumps(data, indent=4)
        # with open(filePath, 'w') as f:
        #     f.write(sdata)

    ## Events

    def timerEvent(self, e):
        if (
            QDateTime.currentDateTime().date().day()
            != self.nowEvent.dateTime().date().day()
        ):
            self.nowEvent.setDateTime(QDateTime.currentDateTime(), notify=False)

    def pencilEvent(self, e, pos, pressure):
        """Shared by touch events and mouse events."""
        if self.itemMode() != util.ITEM_PENCIL:
            if AUTO_PENCIL_MODE:
                self.setItemMode(util.ITEM_PENCIL)
            else:
                e.ignore()
                return False
        e.accept()
        kind = None
        if isinstance(e, QApplePencilEvent):
            kind = e.state()
            pos = self.view().mapToScene(pos)
        else:
            kind = e.type()
        if kind in [
            QEvent.TouchBegin,
            QEvent.GraphicsSceneMousePress,
            Qt.TouchPointPressed,
        ]:
            log.debug(f"PENCIL BEGIN: {pos}, {pressure}")
            parent = None
            people = self.selectedItems(type=PathItem)
            if len(people) == 1:
                parent = people[0]
            # init pencil
            self.pencilParent = parent
            self.addItem(self.pencilCanvas)
            self.pencilCanvas.start(pos, pressure, parentItem=parent)
            # if 0 and hasattr(e, 'coalesced'):
            #     i = 0
            #     for point in e.coalesced():
            #         # viewPos = self.view().mapFromGlobal(point.point)
            #         # scenePos = self.view().mapToScene(viewPos)
            #         scenePos = self.view().mapToScene(point.point())
            #         if util.DEBUG_PENCIL:
            #             self.here('    coalesced:', scenePos, point.pressure())
            #         if i == 0:
            #             self.pencilCanvas.start(scenePos, point.pressure())
            #         else:
            #             self.pencilCanvas.drawTo(scenePos, point.pressure())
            #     self.pencilCanvas.update(dirty=True)
            # else:
            #     self.pencilCanvas.start(pos, pressure)
        elif kind in [
            QEvent.TouchUpdate,
            QEvent.GraphicsSceneMouseMove,
            Qt.TouchPointMoved,
        ]:
            log.debug(f"PENCIL UPDATE: {pos}")
            self.pencilCanvas.drawTo(e.scenePos(), mousePressure())
            # coalesced = []
            # if 0 and hasattr(e, 'coalesced'):
            #     for point in e.coalesced():
            #         #viewPos = self.view().mapFromGlobal(point.point)
            #         #scenePos = self.view().mapToScene(viewPos)
            #         scenePos = self.view().mapToScene(point.point())
            #         if util.DEBUG_PENCIL:
            #             self.here('    coalesced:', scenePos, point.pressure())
            #         self.pencilCanvas.drawTo(scenePos, point.pressure())
            # else:
            #     self.pencilCanvas.drawTo(pos, pressure)
            # if hasattr(e, 'predicted'):
            #     predicted = []
            #     for point in e.predicted():
            #         # viewPos = self.view().mapFromGlobal(point.point)
            #         # scenePos = self.view().mapToScene(viewPos)
            #         scenePos = self.view().mapToScene(point.point())
            #         predicted.append((scenePos, point.pressure()))
            #         if util.DEBUG_PENCIL:
            #             self.here('    predicted:', scenePos, point.pressure())
            #     self.pencilCanvas.update(dirty=True, predicted=predicted)
            # else:
            #     self.pencilCanvas.update(dirty=True)
        elif kind in [
            QEvent.TouchEnd,
            QEvent.TouchCancel,
            QEvent.GraphicsSceneMouseRelease,
            Qt.TouchPointReleased,
        ]:
            log.debug(f"PENCIL END|CANCEL: {pressure}")
            pencilStroke = self.pencilCanvas.finish()
            self.removeItem(self.pencilCanvas)
            if pencilStroke:
                commands.addPencilStroke(self, pencilStroke)
            self.pencilParent = None
        return True

    def __event(self, e):
        """touch.pressure() == NaN when not pencil"""
        if e.type() in [
            QEvent.TouchBegin,
            QEvent.TouchUpdate,
            QEvent.TouchEnd,
            QEvent.TouchCancel,
        ]:
            touch = e.touchPoints()[0]
            if self.itemMode() == util.ITEM_PENCIL:
                if e.type() == QEvent.TouchBegin:
                    return self.pencilEvent(e, touch.scenePos(), pressure)
                elif e.type() == QEvent.TouchUpdate:
                    return self.pencilEvent(e, touch.scenePos(), pressure)
                elif e.type() in [QEvent.TouchEnd, QEvent.TouchCancel]:
                    return self.pencilEvent(e, touch.scenePos(), pressure)
            else:
                return super().event(e)
        else:
            return super().event(e)

    ## This can work around a bug where a scene won't track mouse
    ## events until an item has been added. Very annoying, no idea why.
    ## I worked around this 'cleaner' by adding and removing a dummy item in setFD
    # def event(self, e):
    #     if e.type() == QEvent.TouchUpdate and self.itemMode != util.ITEM_NONE:
    #         self.updateMouseCursorItem() # bug fix where mouse move events don't get sent before adding a person.
    #     return super().event(e)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        self.mouseElapsedTimer.restart()
        item = None
        for _item in self.items(e.scenePos()):
            if isinstance(
                _item, (QGraphicsSimpleTextItem, QGraphicsTextItem)
            ) and isinstance(_item.parentItem(), Person):
                continue
            item = _item
            break
        # item = next(iter(self.items(e.scenePos())), None)
        if self.itemMode() in [util.ITEM_MALE, util.ITEM_FEMALE, util.ITEM_CALLOUT]:
            if (
                item
                and not isinstance(item, Marriage)
                and not isinstance(item, QGraphicsPathItem)
            ):
                e.accept()
                self.setItemMode(util.ITEM_NONE)
            if self.itemMode() == util.ITEM_CALLOUT:
                people = self.selectedItems(type=Person)
                if len(people) == 1:
                    self.calloutParent = people[0]
                else:
                    self.calloutParent = None
        elif self.itemMode() in [
            util.ITEM_MARRY,
            util.ITEM_CHILD,
            util.ITEM_CONFLICT,
            util.ITEM_PROJECTION,
            util.ITEM_FUSION,
            util.ITEM_DISTANCE,
            util.ITEM_AWAY,
            util.ITEM_TOWARD,
            util.ITEM_DEFINED_SELF,
            util.ITEM_RECIPROCITY,
            util.ITEM_INSIDE,
            util.ITEM_OUTSIDE,
        ]:
            e.accept()
            if isinstance(item, Person):
                self.dragStartItem = item
                self.dragStartItem.setHover(True)
                self.dragCreateItem = DragCreateItem()
                self.addItem(self.dragCreateItem)
                # self.dragCreateItem.setPen(self.dragStartItem.pen())
            else:
                self.setItemMode(util.ITEM_NONE)
        elif self.itemMode() == util.ITEM_PENCIL:
            self.pencilEvent(e, e.scenePos(), mousePressure())
        else:
            if self.draggableUnder(e.scenePos()):  # drag-moving?
                self.mousePressOnDraggable = commands.nextId()
                self._isDraggingSomething = True
            e.ignore()
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        elapsed = self.mouseElapsedTimer.elapsed()
        if self.mouseCursorPosition.scene() == self:
            s = "(%.2f, %.2f)" % (e.scenePos().x(), e.scenePos().y())
            self.mouseCursorPosition.setPlainText(s)
            self.mouseCursorPosition.setScale(1 / self.scaleFactor())
            self.mouseCursorPosition.setPos(e.scenePos())
        if self.dragStartItem:
            e.accept()
            hoverMe = None
            if self.itemMode() is util.ITEM_MARRY:
                path = Marriage.pathFor(self.dragStartItem, pos=e.scenePos())
                hoverMe = self.personUnder(e.scenePos())
            elif self.itemMode() is util.ITEM_CHILD:
                path = ChildOf.pathFor(self.dragStartItem, endPos=e.scenePos())
                hoverMe = self.marriageUnder(e.scenePos())
                if not hoverMe:
                    hoverMe = self.childOfUnder(e.scenePos())
                    if not hoverMe:
                        hoverMe = self.multipleBirthUnder(e.scenePos())
            elif self.itemMode() in Emotion.kinds():
                hoverMe = self.personUnder(e.scenePos())
                path = Emotion.pathFor(
                    kind=self.itemMode(),
                    personA=self.dragStartItem,
                    pointB=e.scenePos(),
                    hoverPerson=hoverMe,
                )
            scale = self.newPersonScale()
            self.dragCreateItem.setScale(scale)
            path = self.dragCreateItem.mapFromScene(path)
            self.dragCreateItem.setPath(path)
            if hoverMe != self.hoverItem and self.hoverItem:
                self.hoverItem.setHover(False)
            if hoverMe and hoverMe != self.dragStartItem:
                hoverMe.setHover(True)
                self.hoverItem = hoverMe
        elif self.mouseCursorItem.scene() == self:
            self.mouseCursorItem.setPos(e.scenePos())
            hoverMe = self.personUnder(e.scenePos())
            if hoverMe != self.hoverItem and self.hoverItem:
                self.hoverItem.setHover(False)
            if hoverMe and hoverMe != self.dragStartItem:
                hoverMe.setHover(True)
                self.hoverItem = hoverMe
        elif self.itemMode() == util.ITEM_PENCIL and self.pencilCanvas.isDrawing():
            self.pencilEvent(e, e.scenePos(), mousePressure())
        elif self.mousePressOnDraggable:  # dragging item; handle kb modifiers
            if e.modifiers() & Qt.ShiftModifier:
                self.canSnapDrag = True
                if self.snapItem.scene() is not self:
                    self.addItem(self.snapItem)
            else:
                self.canSnapDrag = False
                if self.snapItem.scene() is self:
                    self.removeItem(self.snapItem)
            super().mouseMoveEvent(e)
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if self.itemMode() == util.ITEM_MALE:
            e.accept()
            commands.addPerson(self, "male", e.scenePos(), self.newPersonSize())
            self.setItemMode(util.ITEM_NONE)
        elif self.itemMode() == util.ITEM_FEMALE:
            e.accept()
            commands.addPerson(self, "female", e.scenePos(), self.newPersonSize())
            self.setItemMode(util.ITEM_NONE)
        elif self.itemMode() in [util.ITEM_MARRY, util.ITEM_CHILD] + Emotion.kinds():
            e.accept()
            success = False
            if self.itemMode() is util.ITEM_MARRY:
                person = self.personUnder(e.scenePos())
                if person and person is not self.dragStartItem:
                    commands.addMarriage(self, self.dragStartItem, person)
                    success = True
            elif self.itemMode() is util.ITEM_CHILD:
                parentItem = self.itemUnder(
                    e.scenePos(), types=[Marriage, ChildOf, MultipleBirth]
                )
                if parentItem:
                    commands.setParents(self.dragStartItem, parentItem)
                    success = True
            elif self.itemMode() in Emotion.kinds():
                person = self.personUnder(e.scenePos())
                if self.itemMode() == util.ITEM_CUTOFF:  # monadic
                    emotion = Emotion(kind=self.itemMode(), personA=person)
                elif person and person is not self.dragStartItem:  # dyadic
                    emotion = Emotion(
                        kind=self.itemMode(), personA=self.dragStartItem, personB=person
                    )
                else:
                    emotion = None
                if emotion:
                    emotion.isCreating = True
                    commands.addEmotion(self, emotion)
                    emotion.isCreating = False
                success = emotion is not None
            if self.dragCreateItem:
                self.removeItem(self.dragCreateItem)
            self.dragCreateItem = None
            if self.dragStartItem:
                self.dragStartItem.setHover(False)
                self.dragStartItem = None
            if self.hoverItem:
                self.hoverItem.setHover(False)
                self.hoverItem = None
            if success:
                self.setItemMode(util.ITEM_NONE)
        elif self.itemMode() == util.ITEM_CALLOUT:
            e.accept()
            callout = commands.addCallout(
                self, e.scenePos(), parentPerson=self.calloutParent
            )
            callout.setSelected(True)
            self.setItemMode(util.ITEM_NONE)
            self.calloutParent = None
        elif self.itemMode() is util.ITEM_PENCIL:
            self.pencilEvent(e, e.scenePos(), 0)
            self.setItemMode(util.ITEM_NONE)
        if self.mousePressOnDraggable:
            self.checkPrintRectChanged()
            self.mousePressOnDraggable = None  # for self.checkItemDragged()
        if self.snapItem.scene() is self:
            self.removeItem(self.snapItem)
        if self._isDraggingSomething:
            self._isDraggingSomething = False
        super().mouseReleaseEvent(e)

    ## Data

    def document(self):
        return self._document

    def updateMouseCursorItem(self):
        scale = None
        if self.itemMode() not in [
            util.ITEM_MALE,
            util.ITEM_FEMALE,
            util.ITEM_CUTOFF,
            util.ITEM_CALLOUT,
        ]:
            return
        if self.itemMode() is util.ITEM_MALE:
            path = Person.pathFor("male", pos=QPointF(0, 0))
            scale = self.newPersonScale()
        elif self.itemMode() is util.ITEM_FEMALE:
            path = Person.pathFor("female", pos=QPointF(0, 0))
            scale = self.newPersonScale()
        elif self.itemMode() == util.ITEM_CUTOFF:
            path = Emotion.pathFor(util.ITEM_CUTOFF, personA=QPointF(0, 0))
            scale = (1 / self.scaleFactor()) * 0.6
        elif self.itemMode() == util.ITEM_CALLOUT:
            path = Callout(scale=self.newPersonScale()).path()
        if scale is not None and scale != self.mouseCursorItem.scale():
            self.mouseCursorItem.setScale(scale)
        if path != self.mouseCursorItem.path():
            self.mouseCursorItem.setPath(path)
        pos = self.view().mapFromGlobal(QCursor.pos())
        scenePos = self.view().mapToScene(pos)
        if pos != self.mouseCursorItem.pos():
            self.mouseCursorItem.setPos(scenePos)

    def itemMode(self):
        return self._itemMode

    def setItemMode(self, mode):
        if mode == self.itemMode():  # block signal loops
            return
        self._itemMode = mode
        if self.itemMode() in [
            util.ITEM_MALE,
            util.ITEM_FEMALE,
            util.ITEM_CUTOFF,
            util.ITEM_CALLOUT,
        ]:
            self.mouseCursorItem.setPen(util.HOVER_PEN)
            if self.mouseCursorItem.scene() is not self:
                self.addItem(self.mouseCursorItem)
            self.updateMouseCursorItem()
        elif self.mouseCursorItem:
            if self.mouseCursorItem.scene() is self:
                self.removeItem(self.mouseCursorItem)
        self.itemModeChanged.emit()

    def checkItemDragged(self, item, pos):
        """Called every mouse move on draggable.
        Update undo compressed move command if necessary.
        Also implicitly cancel any pinch events in the view.
        """
        if self.mousePressOnDraggable:
            commands.moveItem(item, pos, id=self.mousePressOnDraggable)
            self.itemDragged.emit(item)

    def isDraggingSomething(self):
        return self._isDraggingSomething

    def isNudgingSomething(self):
        return self._isNudgingSomething

    def isMovingSomething(self):
        return self.isDraggingSomething() or self.isNudgingSomething()

    def nudgeSelection(self, delta):
        self._isNudgingSomething = True
        id = commands.nextId()
        selection = self.selectedStuff()
        for item in selection:
            if not item.parentItem() in selection:
                newPos = item.pos() + delta
                if isinstance(item, Person):
                    item.nudging = True
                commands.moveItem(item, newPos, id)
                item.setPos(newPos)
                if isinstance(item, Person):
                    item.nudging = False
        self._isNudgingSomething = False

    def setPencilColor(self, name):
        self.prop("pencilColor").set(name)
        self.pencilCanvas.setColor(name)

    def pencilScale(self):
        return self.pencilCanvas.scale()

    def setPencilScale(self, x):
        self.pencilCanvas.setScale(x)

    def onPersonSnapped(self, person, other, newPersonPos):
        pen = util.SNAP_PEN
        pen.setWidthF(person.pen().widthF() / 2.0)
        self.snapItem.setPen(pen)
        self.addItem(self.snapItem)
        self.onPersonSnapUpdated(person, other, newPersonPos)

    def onPersonSnapUpdated(self, person, other, newPersonPos):
        x1 = min(newPersonPos.x(), other.x())
        x2 = max(newPersonPos.x(), other.x())
        # use the other because the pos for person has not been changed yet (called from ItemPositionChange)
        y = other.sceneBoundingRect().y()
        self.snapItem.setScale(1 / self.scaleFactor())
        p1 = self.snapItem.mapFromScene(QPoint(int(x1), int(y)))
        p2 = self.snapItem.mapFromScene(QPoint(int(x2), int(y)))
        self.snapItem.setLine(QLineF(p1.x(), p1.y(), p2.x(), p2.y()))

    def onPersonUnsnapped(self, person):
        self.removeItem(self.snapItem)

    def nextId(self):
        self.setLastItemId(self.lastItemId() + 1)
        return self.lastItemId()

    def query(self, **kwargs):
        """Query based on property value."""
        ret = []
        for id, item in self.itemRegistry.items():
            for k, v in kwargs.items():
                prop = item.prop(k)
                if prop and item.prop(k).get() == v:
                    ret.append(item)
        return ret

    def query1(self, **kwargs):
        ret = self.query(**kwargs)
        if ret:
            return ret[0]

    def find(self, id=None, tags=None, types=None, sort=None):
        """Match is AND."""
        if id is not None:  # exclusive; most common use case
            ret = self.itemRegistry.get(id, None)
        else:
            if types is not None:
                if isinstance(types, list):
                    types = tuple(types)
                elif not isinstance(types, tuple):
                    types = (types,)
            if tags is not None:
                if not isinstance(tags, list):
                    tags = [tags]
            ret = []
            for id, item in self.itemRegistry.items():
                if types is not None and not isinstance(item, types):
                    continue
                if tags is not None and not item.hasTags(tags):
                    continue
                ret.append(item)
        if sort:
            return Property.sortBy(ret, sort)
        else:
            return ret

    def findById(self, id):
        if id is not None:
            return self.find(id=id)

    def itemsWithTags(self, tags=[], kind=Item):
        ret = []
        for id, item in self.itemRegistry.items():
            if isinstance(item, kind) and item.hasTags(tags):
                ret.append(item)
        return sorted(ret)

    def people(self, sort=None, name=None):
        if name is not None:
            ret = [p for id, p in self._people if i.name() == name]
        else:
            ret = list(self._people)
        if sort:
            return Property.sortBy(ret, sort)
        else:
            return ret

    def marriages(self):
        return list(self._marriages)

    def itemDetails(self):
        return list(self._itemDetails)

    def events(self, tags=[]):
        if not tags:
            return list(self._events)
        else:
            return [e for e in self._events if e.hasTags(tags)]

    def emotions(self):
        return list(self._emotions)

    def layers(self, tags=[], name=None):
        if not tags and name is None:
            layers = list(self._layers)
        if tags and name is not None:
            layers = [l for l in self._layers if l.hasTags(tags) and l.name() == name]
        elif not tags and name is not None:
            layers = [l for l in self._layers if l.name() == name]
        elif tags and name is None:
            layers = [l for l in self._layers if l.hasTags(tags)]
        else:
            layers = list(self._layers)
        # ret = sorted(layers, key=lambda l: l.order() > -1 and l.order() or sys.maxsize)
        return layers

    def layerItems(self):
        return list(self._layerItems)

    def layersForPerson(self, person):
        return [self.find(id=layerId) for layerId in person.layers()]

    def draggableUnder(self, pos):
        for item in self.items(pos):
            if item.flags() & QGraphicsItem.ItemIsMovable:
                return item

    def selectableUnder(self, pos):
        for item in self.items(pos):
            if item.flags() & QGraphicsItem.ItemIsSelectable:
                return item

    def itemUnder(self, pos, type=None, types=None):
        if type is not None:
            types = (type,)
        else:
            types = tuple(types)
        for item in self.items(pos):
            if isinstance(item, types):
                return item

    def personUnder(self, pos):
        for item in self.items(pos):
            if isinstance(item, Person):
                return item

    def marriageUnder(self, pos):
        for item in self.items(pos):
            if isinstance(item, Marriage):
                return item

    def childOfUnder(self, pos):
        for item in self.items(pos):
            if isinstance(item, ChildOf):
                return item

    def multipleBirthUnder(self, pos):
        for item in self.items(pos):
            if isinstance(item, MultipleBirth):
                return item

    def selectedPeople(self):
        return [i for i in self.selectedItems() if isinstance(i, Person)]

    def selectedMarriages(self):
        return [i for i in self.selectedItems() if isinstance(i, Marriage)]

    def selectedEmotions(self):
        return [i for i in self.selectedItems() if isinstance(i, Emotion)]

    def selectedItems(self, type=None, types=[]):
        if type:
            return [i for i in super().selectedItems() if isinstance(i, type)]
        elif types:
            ret = []
            for item in super().selectedItems():
                for type in types:
                    if isinstance(item, type):
                        ret.append(item)
                        break
            return ret
        else:
            return super().selectedItems()

    def selectedStuff(self, type=None):
        """stuff that can be moved (no marriages, child items)"""
        return [
            i
            for i in self.selectedItems()
            if isinstance(i, Person) or isinstance(i, LayerItem)
        ]

    def anonymize(self, s):
        if self.isInitializing:
            return None
        for person in self.people():
            name = person.name()
            if name:
                nameRE = re.compile(re.escape(name), re.IGNORECASE)
                s = nameRE.sub("[%s]" % person.alias(), s)
            nickName = person.nickName()
            if nickName:
                nickNameRE = re.compile(re.escape(nickName), re.IGNORECASE)
                s = nickNameRE.sub("[%s]" % person.alias(), s)
        return s

    def onProperty(self, prop):
        if prop.name() == "scaleFactor":
            self.updateMouseCursorItem()
        elif prop.name() == "currentDateTime":
            # TODO: Figure out why this is calling being and end update frame.
            # Is this just a synonym for updateAll()?
            updateGraph = self.getUpdateGraph()
            for item in updateGraph:
                item.beginUpdateFrame()
            for item in updateGraph:
                item.onCurrentDateTime()
            for item in updateGraph:
                item.endUpdateFrame()
        elif prop.name() == "useRealNames":
            if not prop.get():
                self.setRequirePasswordForRealNames(False)
        elif prop.name() == "hideNames":
            for person in self.people():
                person.updateDetails()
        elif prop.name() in ("hideEmotionalProcess", "hideEmotionColors"):
            for item in self.emotions():
                item.updateAll()
            if prop.name() == "hideEmotionalProcess":
                if self.searchModel.hideRelationships != prop.get():
                    self.searchModel.hideRelationships = prop.get()
        elif prop.name() == "hideVariablesOnDiagram":
            for person in self.people():
                person.onHideVariablesOnDiagram()
        elif prop.name() == "hideVariableSteadyStates":
            for person in self.people():
                person.onHideVariableSteadyStates()
        elif prop.name() == "hideLayers":
            if prop.get():
                activeLayers = []
            else:
                activeLayers = self.activeLayers()
        if prop.name() not in ["lastItemId"]:
            self.propertyChanged.emit(prop)
        super().onProperty(prop)  # update listeners after searchModel.tags updates data

    def onItemProperty(self, prop):
        item = prop.item
        if item.isEvent:
            self.eventChanged.emit(prop)
        elif item.isPerson:
            self.personChanged.emit(prop)
        elif item.isMarriage:
            self.marriageChanged.emit(prop)
        elif item.isLayerItem:
            self.layerItemChanged.emit(prop)
        elif item.isLayer:
            if prop.name() == "active":
                if self.itemMode() in [util.ITEM_CALLOUT, util.ITEM_PENCIL]:
                    self.setItemMode(util.ITEM_NONE)
                self.updateActiveLayers()
            self.layerChanged.emit(prop)
        elif item.isEvent:
            self.eventChanged.emit(prop)
        elif item.isEmotion:
            self.emotionChanged.emit(prop)
        if prop.name() == "notes":
            if self._showNotesIcons and not item.isEvent:
                item.setShowNotesIcon(prop.isset())

    def onEventProperty(self, prop):
        pass

    def onSearchChanged(self):
        firstDate = self.timelineModel.dateTimeForRow(0)
        if firstDate > self.currentDateTime():
            self.setCurrentDateTime(firstDate)
        elif not self._areActiveLayersChanging:
            self._updateAllItemsForLayersAndTags()

    def setShowNotesIcons(self, on):
        self._showNotesIcons = on
        for item in self.find(types=PathItem):
            notesProp = item.prop("notes")
            if notesProp and notesProp.isset():
                item.setShowNotesIcon(on)

    def onNotesIconClicked(self, pathItem):
        self.showNotes.emit(pathItem)

    def _updateAllItemsForLayersAndTags(self):
        # Tell the items to add their animations to the group if a layered property has changed.
        # TODO: Rename Item.onActiveLayersChanged to something more appropriate since
        # this sometimes just runs when tags are changed.
        super().onActiveLayersChanged()
        #
        updateGraph = self.getUpdateGraph()
        for item in updateGraph:
            item.beginUpdateFrame()
        #
        for id, item in self.itemRegistry.items():
            if isinstance(item, Item):
                item.onActiveLayersChanged()
        #
        for item in updateGraph:
            item.endUpdateFrame()

    def setResettingSomeLayerProps(self, on):
        self._isResettingSomeLayerProps = on
        if not on:
            self.layerAnimationGroup.start()  # start all added animations on all items that have changed

    def isResettingSomeLayerProps(self):
        return self._isResettingSomeLayerProps

    def areActiveLayersChanging(self):
        return self._areActiveLayersChanging

    def updateActiveLayers(self, force=False):
        """Can trigger animations while updateAll forces changes immediately."""
        _activeLayers = [layer for layer in self.layers() if layer.active()]
        if set(_activeLayers) == set(self._activeLayers) and not force:
            return
        self._areActiveLayersChanging = True
        if self.layerAnimationGroup.state() == QAbstractAnimation.Running:
            self.onLayerAnimationFinished()
        self._activeLayers = list(_activeLayers)
        if not self.isUpdatingAll():
            self._updateAllItemsForLayersAndTags()
            self.checkPrintRectChanged()
        self.activeLayersChanged.emit(self._activeLayers)
        self.layerAnimationGroup.start()  # start all added animations on all items that have changed
        self._areActiveLayersChanging = False

    def startLayerAnimation(self, animation):
        if self.layerAnimationGroup.indexOfAnimation(animation) == -1:
            self.layerAnimationGroup.addAnimation(animation)

    def isLayerAnimationRunning(self):
        return self.layerAnimationGroup.state() == QAbstractAnimation.Running

    def onLayerAnimationFinished(self):
        if (
            util.ANIM_DURATION_MS == 0
            or self.layerAnimationGroup.currentTime()
            < self.layerAnimationGroup.duration()
        ):
            util.test_finish_group(self.layerAnimationGroup)
        while self.layerAnimationGroup.animationCount():
            animation = self.layerAnimationGroup.animationAt(0)
            self.layerAnimationGroup.removeAnimation(animation)

    def activeLayers(self):
        return self._activeLayers

    @pyqtProperty(bool, notify=activeLayersChanged)
    def hasActiveLayers(self):
        return bool(self.activeLayers())

    def activeLayer(self):
        iActiveLayer = -1
        for layer in self.layers():
            if layer.active():
                iActiveLayer = layer.order()
                break  # get first
        return iActiveLayer

    def nextActiveLayer(self):
        iActiveLayer = self.activeLayer() + 1
        if iActiveLayer < len(self.layers()):
            self.setExclusiveActiveLayerIndex(iActiveLayer)

    def prevActiveLayer(self):
        iActiveLayer = self.activeLayer() - 1
        if iActiveLayer < 0 and len(self.layers()):
            iActiveLayer = len(self.layers()) - 1
        if iActiveLayer >= 0:
            self.setExclusiveActiveLayerIndex(iActiveLayer)

    def setExclusiveActiveLayerIndex(self, iLayer):
        """Put in batch job so zoomFit can run after all items are shown|hidden."""
        id = commands.nextId()
        activeLayers = []
        changedLayers = []
        for layer in self.layers():
            if layer.order() == iLayer:
                if layer.active() is not True:
                    changedLayers.append(layer)
                layer.setActive(True, undo=id, notify=False)
                activeLayers.append(layer)
            else:
                if layer.active() is not False:
                    changedLayers.append(layer)
                layer.setActive(False, undo=id, notify=False)
        for layer in changedLayers:
            self.layerChanged.emit(layer.prop("active"))
        self.updateActiveLayers()

    def clearActiveLayers(self):
        for layer in self._layers:
            layer.setActive(False)

    ## Actions

    def selectAll(self):
        for item in self.items():
            if (
                isinstance(item, PathItem)
                and item.isVisible()
                and item.flags() & QGraphicsItem.ItemIsSelectable
            ):
                item.setSelected(True)
            else:
                item.setSelected(False)

    def clear(self):
        self.selectAll()
        self.removeSelection()

    def removeSelection(self):
        iPeople = 0
        iFiles = 0
        iEvents = 0
        for item in self.selectedItems():
            if item.isPerson and item.documentsPath():
                docsPath = item.documentsPath()
                personDocPath = item.documentsPath().replace(
                    self.document().url().toLocalFile() + os.sep, ""
                )
                for relativePath in self.document().fileList():
                    if relativePath.startswith(personDocPath):
                        iFiles = iFiles + 1
                iPeople = iPeople + 1
            if item.isPerson or item.isMarriage:
                iEvents += len(item.events())
        if iFiles > 0:
            btn = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                "Are you sure you want to delete %i people, their %i events, and %i files? If you undo this the files will still be deleted."
                % (iPeople, iEvents, iFiles),
            )
        elif iEvents > 0:
            btn = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                "Are you sure you want to delete %i people and their %i events?"
                % (iPeople, iEvents),
            )
        elif iPeople > 0:
            btn = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                "Are you sure you want to delete %i people?" % iPeople,
            )
        else:
            btn = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                "Are you sure you want to delete %i items?" % len(self.selectedItems()),
            )

        if btn == QMessageBox.Yes:
            commands.removeItems(self, self.selectedItems())

    def copy(self):
        self.clipboard = commands.Clipboard(self.selectedItems())
        self.clipboardChanged.emit()

    def cut(self):
        items = self.selectedItems()
        self.clipboard = commands.Clipboard(items)
        commands.cutItems(self, items)
        self.clipboardChanged.emit()

    def paste(self):
        for item in self.selectedItems():
            item.setSelected(False)
        items = self.clipboard.copy(scene=self)
        commands.pasteItems(self, items)
        for item in items:
            item.setSelected(True)
        return items

    def __clearAllEvents(self):
        nFiles = 0
        events = []
        for person in self.selectedPeople():
            for event in person.events():
                if event.uniqueId() is not None:
                    events.append(event)
                    docsPath = event.documentsPath()
                    if docsPath:
                        eventDocPath = docsPath.replace(
                            self.document().url().toLocalFile() + os.sep, ""
                        )
                        for relativePath in self.document().fileList():
                            if relativePath.startswith(eventDocPath):
                                nFiles = nFiles + 1
        btn = QMessageBox.question(
            self.view().mw,
            "Are you sure?",
            "Are you sure you want to delete %i events and their %i files? If you undo this the files will still be deleted."
            % (len(events), nFiles),
        )
        if btn == QMessageBox.No:
            return
        commands.removeItems(self, events)

    def removeEvent(self, event):
        """Accomodate scene as dummy parent for new events."""
        pass

    def setStopOnAllEvents(self, on):
        self._stopOnAllEvents = on

    def itemShownOnDiagram(self, item):
        """Return False for any events that should be deemphasized
        in the timeline and skipped when moving through time."""
        if self._stopOnAllEvents:
            return True
        else:
            if item.parent.isEmotion:
                return True
            elif item.isEvent:
                if item.anyDynamicPropertiesSet():
                    return True
                elif item.uniqueId():
                    return True
                elif item.includeOnDiagram():
                    return True
            return False

    def nextTaggedDateTime(self):
        events = self.timelineModel.events()
        dummy = Event(dateTime=self.currentDateTime())
        nextRow = bisect.bisect_right(events, dummy)
        if nextRow == len(events):  # end
            nextDate = events[-1].dateTime()
        else:
            nextDate = events[nextRow].dateTime()
        self.setCurrentDateTime(nextDate)

    def prevTaggedDateTime(self):
        events = self.timelineModel.events()
        dummy = Event(dateTime=self.currentDateTime())
        prevRow = bisect.bisect_left(events, dummy) - 1
        if prevRow <= 0:
            prevDate = events[0].dateTime()
        else:
            prevDate = events[prevRow].dateTime()
        self.setCurrentDateTime(prevDate)

    ## Properties

    def itemName(self):
        return self.name()

    def name(self):
        title = ""
        filePath = ""
        if self.shouldShowAliases() and self.alias():
            title = "[%s]" % self.alias()
        elif self._serverDiagram:
            title = self._serverDiagram.name if self._serverDiagram.name else ""
        elif self.readOnly() and self.useRealNames() and self.lastLoadData.get("name"):
            title = self.lastLoadData["name"]
        elif not self.showAliases():
            if self.document():
                filePath = self.document().url().toLocalFile()
                if filePath[len(filePath) - 1 :] == os.path.sep:
                    filePath = filePath[:-1]  # sometimes has '/' at end
                title = QFileInfo(filePath).completeBaseName()
            else:
                filePath = ""
        else:
            title = "Family Diagram"
        return title

    def shouldShowAliases(self):
        """The core logic for the whole app."""
        if self.showAliases():
            return True
        elif (
            self.readOnly()
            and self.useRealNames()
            and self.requirePasswordForRealNames()
        ):
            return True
        elif self.useRealNames():
            return False
        else:
            return False

    def getUpdateGraph(self):
        """Return all PathItems in the order they should be updated."""
        people = []
        marriages = []
        emotions = []
        childs = []
        multipleBirths = []
        for id, item in self.itemRegistry.items():
            if isinstance(item, Person):
                people.append(item)
            elif isinstance(item, Marriage):
                marriages.append(item)
            elif isinstance(item, Emotion):
                emotions.append(item)
            elif isinstance(item, ChildOf):
                childs.append(item)
            elif isinstance(item, MultipleBirth):
                multipleBirths.append(item)
        # - People are the only items that change position on their own,
        # so they go first. Marriages and Emotions are next and their
        # order doesn't matter. ChildOf's need to go after emotions.
        # - This only works because each call only updates that specific
        # item and doesn't call the children.
        # - Position changes are handled similarly in Person.itemChange().
        return people + emotions + marriages + childs + multipleBirths

    def updateAll(self):
        """The main call to visually update everything visual instantly, i.e. w/o animations."""
        self._updatingAll = True
        updateGraph = self.getUpdateGraph()
        for item in updateGraph:
            item.beginUpdateFrame()
        #
        self.updateActiveLayers()
        #
        for item in self.find(types=[PathItem]):
            item.updateAll()
        #
        for item in updateGraph:
            item.endUpdateFrame()
        self.checkPrintRectChanged()
        self._updatingAll = False

    def isUpdatingAll(self):
        return self._updatingAll

    def onShowAliases(self):
        for person in self.people():
            person.onShowAliases()
        for marriage in self.marriages():
            marriage.onShowAliases()
        for event in self.events():
            event.onShowAliases()
        for emotion in self.emotions():
            emotion.onShowAliases()

    def toggleShowSceneCenter(self, on):
        if on:
            self.addItem(self.centerItem)
        else:
            self.removeItem(self.centerItem)

    def toggleShowViewSceneRect(self, on):
        if on:
            self.addItem(self.viewSceneRectItem)
        else:
            self.removeItem(self.viewSceneRectItem)

    def toggleShowPrintRect(self, on):
        if on:
            self.addItem(self.printRectItem)
        else:
            self.removeItem(self.printRectItem)

    def toggleCursorPosition(self, on):
        if on:
            self.addItem(self.mouseCursorPosition)
        else:
            self.removeItem(self.mouseCursorPosition)

    def toggleShowPathItemShapes(self, on):
        for item in self.find(types=PathItem):
            item.dev_setShowPathItemShapes(on)
        # self.update()

    def jumpToNow(self):
        self.setCurrentDateTime(self.nowEvent.dateTime(), undo=True)

    def resetAll(self):
        id = commands.nextId()
        for layer in self.activeLayers():
            layer.setActive(False, undo=id, notify=False)
        self.updateActiveLayers()
        self.searchModel.clear()
        self.setCurrentDateTime(self.nowEvent.dateTime(), undo=True)
        self.diagramReset.emit()

    def addTag(self, tag, notify=True):
        self.setTag(tag, notify, undo=None)

    def removeTag(self, tag, notify=True):
        self.unsetTag(tag, notify=notify, undo=None)

    def renameTag(self, old, new):
        if old in self.tags():
            self.removeTag(old, notify=False)
            self.addTag(new, notify=False)
            for item in self.find(tags=old):
                item.onTagRenamed(old, new)
            self.onProperty(self.prop("tags"))

    ## Event properties

    def addEventProperty(self, propName, index=None):
        names = [entry["name"] for entry in self.eventProperties()]
        if not propName in names:
            x = list(self.eventProperties())
            attr = slugify.slugify(propName)
            entry = {"name": propName, "attr": attr}
            if index is None:
                x.append(entry)
            else:
                x.insert(index, entry)
            self.prop("eventProperties").set(x)
            for event in self.events():
                event.addDynamicProperty(attr)

    def removeEventProperty(self, propName):
        newEntries = []
        entry = None
        for e in self.eventProperties():
            if e["name"] == propName:
                entry = e
            else:
                newEntries.append(e)
        if entry:
            self.prop("eventProperties").set(newEntries)
            for event in self.events():
                event.removeDynamicProperty(entry["attr"])

    def renameEventProperty(self, oldName, newName):
        entry = None
        for e in self.eventProperties():
            if e["name"] == oldName:
                entry = e
                break
        oldSlug = entry["attr"]
        entry["attr"] = slugify.slugify(newName)
        entry["name"] = newName
        for event in self.events():  # must occur before self.onProperty()
            event.renameDynamicProperty(oldSlug, entry["attr"])
        self.onProperty(self.prop("eventProperties"))  # hack force

    def replaceEventProperties(self, newPropNames):
        """So that there is only one notification."""
        oldAttrs = [entry["attr"] for entry in self.eventProperties()]
        for event in self.events():
            for attr in oldAttrs:
                event.removeDynamicProperty(attr)
        newEntries = []
        for propName in newPropNames:
            attr = slugify.slugify(propName)
            entry = {"name": propName, "attr": attr}
            newEntries.append(entry)
            for event in self.events():
                event.addDynamicProperty(attr)
        self.prop("eventProperties").set(newEntries)


from .pyqt import qmlRegisterUncreatableType

qmlRegisterUncreatableType(Scene, "PK.Models", 1, 0, "Scene", "Cannot create Scene")
