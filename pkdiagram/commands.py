import os, shutil, logging
import pprint

from .pyqt import QUndoStack, QUndoCommand, QPointF, QApplication
from . import util, objects


# Custom compression ids
CURRENT_DATE_ID = 1
START_ID = 10


log = logging.getLogger(__name__)


class UndoStack(QUndoStack):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lastId = None

    def push(self, cmd: "UndoCommand"):  # type: ignore
        """Track analytics for non-compressed commands."""
        s = None
        if isinstance(cmd.ANALYTICS, str):
            s = "Commands: " + cmd.ANALYTICS
        elif cmd.ANALYTICS is True and (cmd.id() == -1 or cmd.id() != self.lastId):
            s = "Commands: " + cmd.text()
        if s and cmd.logKwargs():
            self.track(s, {k: str(v) for k, v in cmd.logKwargs().items()})
        elif s and not cmd.logKwargs():
            log.warning(f"No logKwargs for command: {cmd}")
            self.track(s)

        logKwargs_s = pprint.pformat(cmd.logKwargs())
        log.debug(f"{cmd.__class__.__name__}: {logKwargs_s}")

        super().push(cmd)
        self.lastId = cmd.id()

    def track(self, eventName, properties={}):
        if not util.prefs() or util.IS_IOS:
            return
        log.info(f"{eventName}, {properties}")
        enableAppUsageAnalytics = util.prefs().value(
            "enableAppUsageAnalytics", defaultValue=True, type=bool
        )
        if enableAppUsageAnalytics:
            return util.CUtil.instance().trackAnalyticsEvent(eventName, properties)


def track(eventName, properties={}):
    return stack().track(eventName, properties)


def trackApp(eventName, properties={}):
    return track("Application: " + eventName, properties)


def trackAction(eventName, properties={}):
    return track("Action: " + eventName, properties)


def trackView(eventName, properties={}):
    return track("View: " + eventName, properties)


_stack = UndoStack()


def stack():
    return _stack


lastId = START_ID


def nextId():
    global lastId
    lastId = lastId + 1
    return lastId


class UndoCommand(QUndoCommand):

    ANALYTICS = True

    def __init__(self, text, id=-1):
        super().__init__(text)
        self._id = id
        self._log_kwargs = None

    def id(self):
        return self._id

    def analyticsProperties(self):
        return {}

    def logKwargs(self):
        return self._log_kwargs

    def debug(self, **kwargs):
        self._log_kwargs = kwargs


class AddPerson(UndoCommand):
    def __init__(self, scene, gender, pos, size, id=-1):
        super().__init__("Add person", id)
        self.scene = scene
        self.person = objects.Person(gender=gender, size=size)
        self.person.setItemPos(pos, notify=False)
        self.debug(gender=gender, pos=pos, size=size, id=id)

    def redo(self):
        self.scene.addItem(self.person)

    def undo(self):
        self.scene.removeItem(self.person)


def addPerson(scene, gender, pos, size, id=-1):
    cmd = AddPerson(scene, gender, pos, size, id=id)
    stack().push(cmd)
    return cmd.person


class AddPeople(UndoCommand):
    def __init__(self, scene, people, id=-1, batch=True):
        super().__init__("Add people", id)
        self.scene = scene
        self.people = people
        self.batch = batch
        self.debug(people=people, id=id, batch=batch)

    def redo(self):
        self.scene.addItems(*self.people, batch=self.batch)

    def undo(self):
        self.scene.removeItems(*self.people, batch=self.batch)


def addPeople(scene, people, id=-1, batch=True):
    cmd = AddPeople(scene, people, id=id, batch=batch)
    stack().push(cmd)


class RemoveItems(UndoCommand):

    def __init__(self, scene, items):
        super().__init__("Remove items")
        self.scene = scene
        if isinstance(items, list):
            self.items = list(items)
        else:
            self.items = [items]
        self.debug(items=items)

        # Keep track of a list of each kind of items at the top level to
        # detach their relationships and then re-attach them after an
        # undo.

        self._unmapped = {
            "marriages": [],
            "children": [],
            "multipleBirths": [],
            "events": [],
            "emotions": [],
            "parents": [],
            "layerItems": [],
            "layers": [],
            "layerProperties": {},
        }

        def mapChildOf(item):
            if item.multipleBirth and item.multipleBirth.isSelected():
                return  # Handled in mapMultipleBirth
            for entry in self._unmapped["children"]:
                if entry["person"] is item.person:
                    return
            item._undo_mapping = {
                "person": item.person,
                "birthPartners": item.multipleBirth
                and [p for p in item.multipleBirth.children() if p.childOf != item]
                or [],
                "parents": item.parents(),
            }
            self._unmapped["children"].append(item._undo_mapping)

        def mapMultipleBirth(item):
            for entry in self._unmapped["multipleBirths"]:
                if entry["multipleBirth"] is item:
                    return
            item._undo_mapping = {
                "multipleBirth": item,
                "parents": item.parents(),
                "children": [child for child in item.children()],
            }
            self._unmapped["multipleBirths"].append(item._undo_mapping)

        def mapMarriage(item):
            for entry in self._unmapped["marriages"]:
                if entry["marriage"] is item:
                    return
            self._unmapped["marriages"].append(
                {"marriage": item, "people": list(item.people)}
            )
            for child in list(item.children):
                mapChildOf(child.childOf)

        def mapEvent(item):
            for entry in self._unmapped["events"]:
                if entry["event"] is item:
                    return
            if item.uniqueId():  # just clear date for built-in events
                parent = None
                dateTime = item.dateTime()
            else:
                parent = item.parent
                dateTime = None
            self._unmapped["events"].append(
                {"event": item, "parent": parent, "dateTime": dateTime}
            )

        def mapEmotion(item):
            for entry in self._unmapped["emotions"]:
                if entry["emotion"] is item:
                    return
            self._unmapped["emotions"].append(
                {
                    "emotion": item,
                    "people": list(item.people),
                }
            )

        def mapItem(item):
            for layer in scene.layers():
                layerEntries = {}
                for prop in item.props:
                    if prop.layered:
                        value, ok = layer.getItemProperty(item.id, prop.name())
                        if ok:
                            if not item.id in layerEntries:
                                layerEntries[item.id] = {}
                            layerEntries[item.id][prop.name()] = {
                                "prop": prop,
                                "was": value,
                            }
                if layerEntries:
                    if not layer in self._unmapped["layerProperties"]:
                        self._unmapped["layerProperties"][layer] = {}
                    self._unmapped["layerProperties"][layer].update(layerEntries)

        # Map anything that will be directly removed or removed as a dependency.
        # Do the mappings first before the data structure is altered
        for item in self.items:
            if item.isPerson:
                for marriage in list(item.marriages):
                    mapMarriage(marriage)
                for emotion in list(item.emotions()):
                    mapEmotion(emotion)
                for event in list(item.events()):
                    mapEvent(event)
                if item.childOf:
                    mapChildOf(item.childOf)
            elif item.isChildOf:
                mapChildOf(item)
            elif item.isMultipleBirth:
                mapMultipleBirth(item)
            elif item.isMarriage:
                mapMarriage(item)
            elif item.isEvent:
                mapEvent(item)
            elif item.isEmotion:
                mapEmotion(item)
            elif item.isLayerItem:
                self._unmapped["layerItems"].append(
                    {"item": item, "parent": item.parentItem()}
                )
            elif item.isLayer:
                self._unmapped["layers"].append(
                    {
                        "layer": item,
                        "layerItems": [
                            li
                            for li in self.scene.layerItems()
                            if item.id in li.layers()
                        ],
                    }
                )

            mapItem(item)

    def redo(self):
        self.scene.setBatchAddingRemovingItems(True)
        for item in self.items:

            if item.isPerson:
                for marriage in list(item.marriages):
                    for child in list(marriage.children):
                        child.setParents(None)
                    for person in list(marriage.people):
                        person._onRemoveMarriage(marriage)
                    self.scene.removeItem(marriage)

                for emotion in list(item.emotions()):
                    for person in list(emotion.people):
                        if person:  # ! dyadic
                            person._onRemoveEmotion(emotion)
                    self.scene.removeItem(emotion)

                if item.childOf:
                    item.setParents(None)

                if self.scene.document():
                    for relativePath in self.scene.document().fileList():
                        personDocPath = item.documentsPath().replace(
                            self.scene.document().url().toLocalFile() + os.sep, ""
                        )
                        for relativePath in self.scene.document().fileList():
                            if relativePath.startswith(personDocPath):
                                self.scene.document().removeFile(relativePath)
                self.scene.removeItem(item)

            elif item.isChildOf:
                if hasattr(item, "_undo_mapping"):
                    item._undo_mapping["person"].setParents(None)

            elif item.isMultipleBirth:
                for child in item._undo_mapping["children"]:
                    child.setParents(None)

            elif item.isMarriage:
                for child in list(item.children):  # after undo setup
                    child.setParents(None)
                for person in list(item.people):
                    person._onRemoveMarriage(item)
                self.scene.removeItem(item)

            elif item.isEvent:
                docsPath = item.documentsPath()
                if docsPath and os.path.isdir(docsPath):  # this cannot be undone
                    shutil.rmtree(docsPath)
                if item.uniqueId() and not item.parent.isMarriage:
                    item.prop("dateTime").reset()
                else:
                    item.setParent(None)

            elif item.isEmotion:
                for person in list(item.people):
                    if person:
                        person._onRemoveEmotion(item)
                        self.scene.removeItem(item)

            elif item.isLayerItem:
                self.scene.removeItem(item)

            elif item.isLayer:
                for layerItem in self.scene.layerItems():
                    if item.id in layerItem.layers():
                        layerItem.layers().remove(item.id)
                    if not layerItem.layers():  # orphaned now
                        self.scene.removeItem(layerItem)
                self.scene.removeItem(item)

        for layer, itemEntries in self._unmapped["layerProperties"].items():
            for itemId, propEntries in itemEntries.items():
                for propName, entry in propEntries.items():
                    layer.resetItemProperty(entry["prop"])

            ## Ignore ItemDetails, SeparationIndicator

        self.scene.setBatchAddingRemovingItems(False)

    def undo(self):
        self.scene.setBatchAddingRemovingItems(True)
        for item in self.items:
            if not item.isChildOf and not item.isMultipleBirth:
                self.scene.addItem(item)
            if not item.isLayer and not item.isEvent:
                item.setSelected(False)
        #
        for layer, itemEntries in self._unmapped["layerProperties"].items():
            for itemId, propEntries in itemEntries.items():
                for propName, entry in propEntries.items():
                    layer.setItemProperty(itemId, entry["prop"].name(), entry["was"])
        #
        for entry in self._unmapped["marriages"]:
            entry["people"][0]._onAddMarriage(entry["marriage"])
            entry["people"][1]._onAddMarriage(entry["marriage"])
            self.scene.addItem(entry["marriage"])
        #
        for entry in self._unmapped["children"]:
            # person.multipleBirth is not None when undeleting one of the
            # birthPartners already remapped this ChildOf.
            if entry["birthPartners"] and not entry["person"].multipleBirth():
                # check if the previous MultipleBirth still exists on two or more birthPartners
                mb = None
                for person in entry["birthPartners"]:
                    if person.multipleBirth():
                        mb = person.multipleBirth()
                        break
                if mb:
                    # Just re-attach to the prior MultipleBirth
                    entry["person"].setParents(mb)
                else:
                    # Map the entire MultipleBirth
                    entry["person"].setParents(entry["parents"])
                    for child in entry["birthPartners"]:
                        child.setParents(entry["person"].childOf)
            elif not entry["birthPartners"]:
                entry["person"].setParents(entry["parents"])
        #
        for entry in self._unmapped["multipleBirths"]:
            entry["children"][0].setParents(entry["parents"])
            for child in entry["children"][1:]:
                child.setParents(entry["children"][0].childOf)
        #
        for entry in self._unmapped["parents"]:
            entry["person"].setParents(entry["parents"])
        #
        for entry in self._unmapped["events"]:
            if entry["dateTime"]:
                entry["event"].setDateTime(entry["dateTime"])
            else:
                entry["event"].setParent(entry["parent"])
        #
        for entry in self._unmapped["emotions"]:
            entry["people"][0]._onAddEmotion(entry["emotion"])
            entry["emotion"].setPersonA(entry["people"][0])
            if entry["people"][1]:  # ! dyadic
                entry["people"][1]._onAddEmotion(entry["emotion"])
                entry["emotion"].setPersonB(entry["people"][1])
            if not entry["emotion"].isDyadic():
                entry["emotion"].setParentItem(entry["people"][0])
            self.scene.addItem(entry["emotion"])
        #
        for entry in self._unmapped["layers"]:  # before layer items
            for layerItem in entry["layerItems"]:
                layers = layerItem.layers()
                readd = not layers
                layers.append(entry["layer"].id)
                layerItem.setLayers(layers)
                if readd:
                    self.scene.addItem(layerItem)
                self.scene.addItem(entry["layer"])
        #
        for entry in self._unmapped["layerItems"]:
            entry["item"].setParentItem(entry["parent"])
        # again, after others are updated
        for entry in self._unmapped["children"]:
            birthPartners = entry.get("birthPartners", [])
            if birthPartners:
                for child in birthPartners:
                    child.childOf.updateGeometry()
        self.scene.setBatchAddingRemovingItems(False)


def removeItems(*args):
    stack().push(RemoveItems(*args))


class MoveItems(UndoCommand):

    ANALYTICS = False

    def __init__(self, item, pos, id):
        super().__init__("Move items", id)
        if isinstance(item, objects.Callout):
            calloutPoints = item.mouseMovePoints
            calloutPoints_was = item.mousePressPoints
        else:
            calloutPoints = None
            calloutPoints_was = None
        self.data = {
            item: {
                "pos": pos,  # latest
                "pos_was": item.pos(),
                "calloutPoints": calloutPoints,  # latest
                "calloutPoints_was": calloutPoints_was,
            }
        }
        self.scene = item.scene()
        self.firstRun = True
        # self.debug(item=item, pos=pos, id=id)

    def redo(self):
        if self.firstRun:
            # Items are already in place; don't move until true 'redo.'
            self.firstRun = False
        else:
            for item, entry in self.data.items():
                item.setPos(entry["pos"])
                if isinstance(item, objects.Callout) and entry["calloutPoints"]:
                    item.setPoints(entry["calloutPoints"])
            # after set pos
            for item, entry in self.data.items():
                if hasattr(item, "updateGeometry"):  # needed?
                    item.updateGeometry()

    def undo(self):
        for item, entry in self.data.items():
            item.setPos(entry["pos_was"])
            if isinstance(item, objects.Callout) and entry["calloutPoints_was"]:
                item.setPoints(entry["calloutPoints_was"])
        # after
        for item, entry in self.data.items():
            if hasattr(item, "updateGeometry"):  # needed?
                item.updateGeometry()

    def mergeWith(self, other):
        for item, entry in other.data.items():
            if item in self.data:
                self.data[item].update(
                    {"pos": entry["pos"], "calloutPoints": entry["calloutPoints"]}
                )
            else:
                self.data[item] = {
                    "pos": entry["pos"],
                    "pos_was": entry["pos_was"],
                    "calloutPoints": entry["calloutPoints"],
                    "calloutPoints_was": entry["calloutPoints_was"],
                }
        return True


def moveItem(item, pos, id):
    stack().push(MoveItems(item, pos, id))


class AddMarriage(UndoCommand):
    def __init__(self, scene, item1, item2, id=-1):
        super().__init__("Add marriage", id)
        self.scene = scene
        self.item1 = item1
        self.item2 = item2
        self.marriage = objects.Marriage(self.item1, self.item2)
        self.debug(item1=item1, item2=item2, id=id)

    def redo(self):
        self.item1._onAddMarriage(self.marriage)
        self.item2._onAddMarriage(self.marriage)
        self.scene.addItem(self.marriage)
        self.marriage.updateGeometry()

    def undo(self):
        self.item1._onRemoveMarriage(self.marriage)
        self.item2._onRemoveMarriage(self.marriage)
        self.scene.removeItem(self.marriage)


def addMarriage(scene, a, b, id=-1):
    cmd = AddMarriage(scene, a, b, id=id)
    stack().push(cmd)
    return cmd.marriage


class SetItemProperty(UndoCommand):
    """Only called from Property.set()."""

    ANALYTICS = "SetItemProperty"

    def __init__(self, prop, value, layers=[], id=-1):
        if layers:
            super().__init__("Set %s on layers" % prop.name(), id)
        else:
            super().__init__("Set %s" % prop.name(), id)
        self.data = {}

        def _addEntry(layer, prop, value, was):
            if not layer in self.data:
                self.data[layer] = {}
            if not prop.item.id in self.data[layer]:
                self.data[layer][prop.item.id] = {}
            self.data[layer][prop.item.id][prop.name()] = {"value": value, "prop": prop}
            self.data[layer][prop.item.id][prop.name()]["wasSet"] = prop.isset()
            if not was is None:
                self.data[layer][prop.item.id][prop.name()]["was"] = was

        if layers:
            for layer in layers:
                was, ok = layer.getItemProperty(prop.item.id, prop.name())
                _addEntry(layer, prop, value, was)
        else:
            _addEntry(None, prop, value, prop.get())
        self.firstTime = True  # yep
        self.debug(
            name=prop.name(), value=value, layers=[x.name() for x in layers], id=id
        )

    def redo(self):
        if self.firstTime:
            self.firstTime = False
            return
        for layer, itemData in self.data.items():
            for itemId, props in itemData.items():
                for propName, data in props.items():
                    if layer:
                        layer.setItemProperty(itemId, propName, data["value"])
                        data["prop"].onActiveLayersChanged()
                    else:
                        data["prop"].set(data["value"], force=True)

    def undo(self):
        for layer, itemData in self.data.items():
            for itemId, props in itemData.items():
                for propName, data in props.items():
                    if layer:
                        if data["wasSet"] and "was" in data:
                            layer.setItemProperty(itemId, propName, data["was"])
                        else:
                            layer.resetItemProperty(data["prop"])
                        data["prop"].onActiveLayersChanged()
                    else:
                        if data["wasSet"] and "was" in data:
                            data["prop"].set(data["was"], force=True)
                        else:
                            data["prop"].reset()

    def mergeWith(self, other):
        util.deepMerge(self.data, other.data, ignore="was")
        return True


class ResetItemProperty(UndoCommand):
    """Only used from Property.reset(."""

    def __init__(self, prop, layers=[], id=-1):
        item = prop.item
        super().__init__("Reset %s" % prop.name(), id)
        self.data = {}
        if prop.layered:
            # only take `was` values stored on selected layers
            for layer in layers:
                self.data[layer] = {}
                x, ok = layer.getItemProperty(prop.item.id, prop.name())
                if ok:
                    self.data[layer] = {prop: x}
        else:
            self.data[None] = {prop: prop.get()}
        self.firstTime = True
        self.debug(prop=prop, layers=layers, id=id)

    def redo(self):
        if self.firstTime:
            self.firstTime = False
            return
        for layer, propEntry in self.data.items():
            for prop, was in propEntry.items():
                if layer:
                    layer.resetItemProperty(prop)
                else:
                    prop.reset()
        self.firstTime = False

    def undo(self):
        for layer, propEntry in self.data.items():
            for prop, was in propEntry.items():
                if layer:
                    layer.setItemProperty(prop.item.id, prop.name(), was)
                else:
                    prop.set(was)

    def mergeWith(self, other):
        util.deepMerge(self.data, other.data, ignore="was")
        return True


class AddEvent(UndoCommand):
    def __init__(self, parent, event=None):
        super().__init__("Add event to %s" % parent.__class__.__name__)
        self.parent = parent
        self.event = event
        self.debug(parent=parent, event=event)

    def redo(self):
        self.event.setParent(self.parent)

    def undo(self):
        self.event.setParent(None)


def addEvent(parent, event):
    cmd = AddEvent(parent, event)
    stack().push(cmd)
    return cmd.event


class SetParents(UndoCommand):
    def __init__(self, person, target, id=-1):
        super().__init__("Set child", id=id)
        #
        if target is None:
            data = {"state": None}
        elif target.isMarriage:
            data = {"state": "marriage", "parents": target}
        elif target.isChildOf and target.multipleBirth is None:
            data = {
                "state": "multipleBirth.person",
                "parents": target.parents(),
                "otherPerson": target.person,
            }
        elif target.isChildOf and target.multipleBirth:
            data = {
                "state": "multipleBirth.children",
                "parents": target.parents(),
                "people": list(target.multipleBirth.children()),
            }
        elif target.isMultipleBirth:
            data = {
                "state": "multipleBirth.children",
                "parents": target.parents(),
                "people": list(target.children()),
            }
        # was
        if person.multipleBirth():
            was_data = {
                "was_state": "multipleBirth.children",
                "was_parents": person.parents(),
                "was_people": list(person.multipleBirth().children()),
            }
        elif person.parents():
            was_data = {"was_state": "marriage", "was_parents": person.parents()}
        else:
            was_data = {"was_state": None}
        #
        data.update(was_data)
        self.data = {person: data}
        self.debug(person=person, target=target, id=id)

    def redo(self):
        for person, data in self.data.items():
            if data["state"] == "marriage":
                person.setParents(data["parents"])
            elif data["state"] == "multipleBirth.children":
                data["people"][0].setParents(data["parents"])
                for child in data["people"][1:]:
                    child.setParents(data["people"][0].childOf)
                person.setParents(data["people"][0].childOf)
            elif data["state"] == "multipleBirth.person":
                data["otherPerson"].setParents(data["parents"])
                person.setParents(data["otherPerson"].childOf)
            elif data["state"] is None:
                person.setParents(None)

    def undo(self):
        for person, data in self.data.items():
            if data["was_state"] == "marriage":
                person.setParents(data["was_parents"])
            elif data["was_state"] == "multipleBirth.children":
                data["was_people"][0].setParents(data["was_parents"])
                for person in data["was_people"][1:]:
                    person.setParents(data["was_people"][0].childOf)
            elif data["was_state"] is None:
                person.setParents(None)

    def mergeWith(self, other):
        util.deepMerge(self.data, other.data)
        return True


def setParents(person, target, id=-1):
    cmd = SetParents(person, target, id=id)
    stack().push(cmd)


def setMultipleBirth(person, target, id=-1):
    cmd = SetParents(person, target, id=id)
    stack().push(cmd)


class AddEmotion(UndoCommand):
    def __init__(self, scene, emotion, id=-1):
        super().__init__("Add " + emotion.__class__.__name__, id)
        self.scene = scene
        self.emotion = emotion
        self.personA = emotion.personA()
        self.personB = emotion.personB()
        self.firstRun = True
        self.debug(emotion=emotion, id=id)

    def redo(self):
        if not self.firstRun:
            self.personA._onAddEmotion(self.emotion)
            if self.personB:
                self.personB._onAddEmotion(self.emotion)
        self.firstRun = False
        self.scene.addItem(self.emotion)
        self.scene.setCurrentDateTime(self.emotion.startDateTime())

    def undo(self):
        self.personA._onRemoveEmotion(self.emotion)
        if self.personB:
            self.personB._onRemoveEmotion(self.emotion)
        self.scene.removeItem(self.emotion)


def addEmotion(scene, emotion, id=-1):
    cmd = AddEmotion(scene, emotion, id=id)
    stack().push(cmd)


class AddPencilStroke(UndoCommand):
    def __init__(self, scene, item):
        super().__init__("Pencil stroke")
        self.scene = scene
        self.item = item
        self.item.setLayers([layer.id for layer in self.scene.activeLayers()])
        self.debug(item=item)

    def redo(self):
        self.scene.addItem(self.item)
        self.item.setItemPos(QPointF(0, 0))

    def undo(self):
        self.scene.removeItem(self.item)


def addPencilStroke(*args, **kwargs):
    cmd = AddPencilStroke(*args, **kwargs)
    stack().push(cmd)


class ErasePencilStroke(UndoCommand):
    def __init__(self, scene, item):
        super().__init__("Erase pencil stroke")
        self.scene = scene
        self.item = item
        self.debug(item=item)

    def redo(self):
        self.scene.removeItem(self.item)

    def undo(self):
        self.scene.addItem(self.item)


class CutItems(RemoveItems):
    def __init__(self, scene, items):
        super().__init__(scene, items)
        self.setText("Cut items")


def cutItems(*args):
    stack().push(CutItems(*args))


class Clipboard:
    """Represents a remaped hiarchy of Items in the clipboard.
    Seperates out the copy action from UndoCommand."""

    def __init__(self, items):
        """Clone them in memory only, so they are all set up to register.
        That way PasteItems() can clone the clones over and over again
        even if the original items have been deleted. Hence `Clipboard`."""
        self.map = {}
        self.items = list(items)
        for item in self.items:
            item._cloned_was_selected = True  # just leave the attribute there...
            assert item.isSelected()

    def copy(self, scene):
        self.map = {}
        clones = []
        for item in self.items:
            clone = item.clone(scene)
            self.map[item.id] = clone
            clones.append(clone)
            if isinstance(clone, objects.Person) and not item.childOf in self.items:
                # Ensure childItem is added to the map even if not selected
                childClone = item.childOf.clone(scene)
                self.map[clone._cloned_childOf_id] = childClone
                clones.append(childClone)
        childOfs = []
        others = []
        people = []
        for clone in clones:
            if isinstance(clone, objects.Person):
                people.append(clone)
            elif isinstance(clone, objects.ChildOf):
                childOfs.append(clone)
            else:
                others.append(clone)
        # First remap non-people to weed out incomplete emotions|marriages,
        # ChildOfs after marriages.
        for clone in others + childOfs:
            if clone.remap(self) is False:
                clones.remove(clone)  # when emotions|marriage can't find a person
                scene.removeItem(
                    clone
                )  # this is messy, maybe clone(scene) shouldn't call register() if it won't be used?
                for k, v in dict(self.map).items():
                    if v == clone:
                        del self.map[k]
        # then remap people with accurate list of emotions|marriages
        for clone in people:
            clone.remap(self)
        # hack-messy, but preoccupied
        for childOf in childOfs:
            if childOf.parents():
                childOf.parents().onAddChild(childOf.person)
        return clones

    def find(self, id):
        """'item' will be the original object, and self.map has the clone."""
        if id is not None:
            return self.map.get(id)


class PasteItems(UndoCommand):
    def __init__(self, scene, items):
        super().__init__("Paste items")
        self.scene = scene
        self.items = {}
        for item in items:
            self.items[item] = {"pos_was": item.pos()}
        self.debug(items=items)

    def redo(self):
        for item in self.scene.selectedItems():
            item.setSelected(False)
        for item, info in self.items.items():
            if item.scene() != self.scene:  # scene set on copy()
                item.setParentItem(None)
                self.scene.addItem(item)
            if isinstance(item, objects.LayerItem):
                item.setLayers([layer.id for layer in self.scene.activeLayers()])
            pos = info["pos_was"]
            item.setPos(pos.x() + util.PASTE_OFFSET, pos.y() + util.PASTE_OFFSET)
            item.updateGeometry()
            item.updateDetails()
        # Do it again for dependents.
        # Still required after optimizing Person.updateDependents?
        for item, info in self.items.items():
            item.updateGeometry()
            item.updateDetails()
            item.setSelected(True)

    def undo(self):
        for item in self.items:
            self.scene.removeItem(item)


def pasteItems(*args):
    stack().push(PasteItems(*args))


class ImportItems(PasteItems):

    def __init__(self, scene, items):
        super().__init__(scene, items)
        self.setText("Import items")
        self.debug(items=items)


def importItems(*args):
    stack().push(ImportItems(*args))


class CreateTag(UndoCommand):

    ANALYTICS = "Create tag"

    def __init__(self, scene, tag):
        super().__init__('Create tag "%s"' % tag)
        self.scene = scene
        self.tag = tag
        self.debug(tag=tag)

    def redo(self):
        self.scene.addTag(self.tag)

    def undo(self):
        self.scene.removeTag(self.tag)


def createTag(*args):
    stack().push(CreateTag(*args))


class DeleteTag(UndoCommand):

    ANALYTICS = "Delete tag"

    def __init__(self, scene, tag):
        super().__init__('Delete tag "%s"' % tag)
        self.scene = scene
        self.tag = tag
        self.items = []
        self.debug(tag=tag)

    def redo(self):
        self.items = self.scene.find(tags=self.tag)
        self.scene.removeTag(self.tag)
        for item in self.items:
            item.unsetTag(self.tag)

    def undo(self):
        self.scene.addTag(self.tag)
        for item in self.items:
            item.setTag(self.tag)


def deleteTag(*args):
    stack().push(DeleteTag(*args))


class RenameTag(UndoCommand):

    ANALYTICS = "Rename tag"

    def __init__(self, scene, old, new):
        super().__init__('Rename tag "%s" to "%s"' % (old, new))
        self.scene = scene
        self.old = old
        self.new = new
        self.debug(old=old, new=new)

    def redo(self):
        self.scene.renameTag(self.old, self.new)

    def undo(self):
        self.scene.renameTag(self.new, self.old)


def renameTag(*args):
    stack().push(RenameTag(*args))


class SetTag(UndoCommand):

    ANALYTICS = "Set tag"

    def __init__(self, item, tag):
        super().__init__('Set tag "%s" on <%s>' % (tag, item.itemName()))
        self.item = item
        self.tag = tag
        self.debug(item=item, tag=tag)

    def redo(self):
        self.item.setTag(self.tag)

    def undo(self):
        self.item.unsetTag(self.tag)


def setTag(*args):
    stack().push(SetTag(*args))


class UnsetTag(UndoCommand):

    ANALYTICS = "Unset tag"

    def __init__(self, item, tag):
        super().__init__('Unset tag "%s" on <%s>' % (tag, item.itemName()))
        self.item = item
        self.tag = tag
        self.debug(item=item, tag=tag)

    def redo(self):
        self.item.unsetTag(self.tag)

    def undo(self):
        self.item.setTag(self.tag)


def unsetTag(*args):
    stack().push(UnsetTag(*args))


class CreateEventProperty(UndoCommand):

    ANALYTICS = "Create event property"

    def __init__(self, scene, propName):
        super().__init__('Create event property "%s"' % propName)
        self.scene = scene
        self.propName = propName
        self.debug(propName=propName)

    def redo(self):
        self.scene.addEventProperty(self.propName)

    def undo(self):
        self.scene.removeEventProperty(self.propName)


def createEventProperty(*args):
    stack().push(CreateEventProperty(*args))


class RemoveEventProperty(UndoCommand):

    ANALYTICS = "Remove event property"

    @staticmethod
    def readValueCache(scene, onlyAttr=None):
        """Returns cache of attrs in order of variable listing."""
        ret = []
        for entry in scene.eventProperties():
            attr = entry["attr"]
            if onlyAttr is not None and attr != onlyAttr:
                continue
            attrEntries = {}
            for event in scene.events():
                if event.uniqueId() != "now":
                    attrEntries[event.id] = {
                        "value": event.dynamicProperty(attr).get(),
                        "event": event,
                    }
            ret.append((attr, attrEntries))
        return ret

    @staticmethod
    def writeValueCache(scene, cache, onlyAttr=None):
        for attr, attrEntries in cache:
            if onlyAttr is not None and attr != onlyAttr:
                continue
            for id, entry in attrEntries.items():
                if entry["value"] is not None:
                    entry["event"].dynamicProperty(attr).set(
                        entry["value"], notify=False
                    )

    def __init__(self, scene, propName):
        super().__init__('Remove event property "%s"' % propName)
        self.scene = scene
        self.propName = propName
        self.attr = None
        self.propIndex = None
        for i, entry in enumerate(self.scene.eventProperties()):
            if entry["name"] == self.propName:
                self.attr = entry["attr"]
                self.propIndex = i
                break
        self.valueCache = self.readValueCache(scene, onlyAttr=self.attr)
        self.debug(propName=propName)

    def redo(self):
        self.scene.removeEventProperty(self.propName)

    def undo(self):
        self.scene.addEventProperty(self.propName, index=self.propIndex)
        self.writeValueCache(self.scene, self.valueCache, onlyAttr=self.attr)


def removeEventProperty(*args):
    stack().push(RemoveEventProperty(*args))


class RenameEventProperty(UndoCommand):

    ANALYTICS = "Rename event property"

    def __init__(self, scene, old, new):
        super().__init__('Rename event property "%s" to "%s"' % (old, new))
        self.scene = scene
        self.old = old
        self.new = new
        self.debug(old=old, new=new)

    def redo(self):
        self.scene.renameEventProperty(self.old, self.new)

    def undo(self):
        self.scene.renameEventProperty(self.new, self.old)


def renameEventProperty(*args):
    stack().push(RenameEventProperty(*args))


class ReplaceEventProperties(UndoCommand):

    ANALYTICS = "Replace event properties"

    def __init__(self, scene, newPropNames):
        super().__init__('Create event properties with "%s"' % newPropNames)
        self.scene = scene
        self.oldPropNames = [entry["name"] for entry in scene.eventProperties()]
        self.newPropNames = newPropNames
        self.valueCache = RemoveEventProperty.readValueCache(scene)
        self.debug(newPropNames=newPropNames)

    def redo(self):
        self.scene.replaceEventProperties(self.newPropNames)

    def undo(self):
        self.scene.replaceEventProperties(self.oldPropNames)
        RemoveEventProperty.writeValueCache(self.scene, self.valueCache)


def replaceEventProperties(*args):
    stack().push(ReplaceEventProperties(*args))


class SetEmotionPerson(UndoCommand):

    ANALYTICS = "Set emotion person"

    def __init__(self, emotion, personA=None, personB=None, id=-1):
        if personA and personB:
            super().__init__(
                "Set %s on <%s> and <%s>"
                % (emotion.__class__.__name__, personA.itemName(), personB.itemName()),
                id,
            )
        elif personA:
            super().__init__(
                "Set person A on %s on <%s>"
                % (emotion.__class__.__name__, personA.itemName()),
                id,
            )
        elif personB:
            super().__init__(
                "Set person B on %s on <%s>"
                % (emotion.__class__.__name__, personB.itemName()),
                id,
            )
        if personA == emotion.personB() and personB == emotion.personA():
            swap = True
        else:
            swap = False
        self.data = {
            emotion: {
                "swap": swap,
                "personA": personA,
                "personB": personB,
                "personA_was": emotion.personA(),
                "personB_was": emotion.personB(),
            }
        }
        self.debug(emotion=emotion, personA=personA, personB=personB, id=id)

    def redo(self):
        for emotion, entry in self.data.items():
            if entry["swap"]:
                emotion.swapPeople()
            else:
                if entry["personA"]:
                    emotion.setPersonA(entry["personA"])
                if entry["personB"]:
                    emotion.setPersonB(entry["personB"])

    def undo(self):
        for emotion, entry in self.data.items():
            if entry["swap"]:
                emotion.swapPeople()
            else:
                emotion.setPersonA(entry["personA_was"])
                emotion.setPersonB(entry["personB_was"])

    def mergeWith(self, other):
        self.data.update(other.data)
        return True


def setEmotionPerson(*args, **kwargs):
    stack().push(SetEmotionPerson(*args, **kwargs))


class SetEventParent(UndoCommand):

    ANALYTICS = "Set event parent"

    def __init__(self, event, parent, id=-1):
        super().__init__("Add <%s> to <%s>" % (event.itemName(), parent.itemName()), id)
        self.events = {
            event: {
                "parent_was": event.parent,
                "parent": parent,
            }
        }

    def redo(self):
        for event, entry in self.events.items():
            if entry["parent"]:
                event.setParent(entry["parent"])

    def undo(self):
        for event, entry in self.events.items():
            event.setParent(entry["parent_was"])

    def mergeWith(self, cmd):
        if cmd.id() != self.id():
            log.info(f"{self.id()} != {cmd.id()} !!!")
            return False
        self.events.update(cmd.events)
        return True


def setEventParent(event, parent, undo=-1):
    stack().push(SetEventParent(event, parent, id=undo))


class AddLayer(UndoCommand):

    ANALYTICS = "Add layer"

    def __init__(self, scene, layer):
        super().__init__("Add layer %s" % layer.itemName())
        self.scene = scene
        self.layer = layer

    def redo(self):
        layers = self.scene.layers()
        iOrder = len(self.scene.layers())
        self.layer.setOrder(iOrder)  # append
        self.scene.addItem(self.layer)

    def undo(self):
        self.scene.removeItem(self.layer)
        for i, layer in enumerate(self.scene.layers()):
            self.layer.setOrder(i, notify=False)


def addLayer(scene, layer):
    cmd = AddLayer(scene, layer)
    stack().push(cmd)
    return cmd.layer


class SetLayerOrder(UndoCommand):

    ANALYTICS = "Set layer order"

    def __init__(self, scene, layers):
        super().__init__("Set layer order")
        self.scene = scene
        self.oldLayers = scene.layers()  # sorted
        self.newLayers = layers  # new sorted

    def redo(self):
        for i, layer in enumerate(self.newLayers):
            layer.setOrder(i)
        self.scene.resortLayersFromOrder()

    def undo(self):
        for i, layer in enumerate(self.oldLayers):  # re-init order
            layer.setOrder(i)
        self.scene.resortLayersFromOrder()


def setLayerOrder(scene, layers):
    stack().push(SetLayerOrder(scene, layers))


class AddCallout(UndoCommand):
    def __init__(self, scene, mouseScenePos, parentPerson=None):
        super().__init__("Add callout")
        self.scene = scene
        self.callout = objects.Callout()
        self.parentPerson = parentPerson
        self.mouseScenePos = mouseScenePos

    def redo(self):
        self.scene.addItem(self.callout)
        self.callout.setPos(self.mouseScenePos)
        self.callout.setItemPos(self.mouseScenePos)
        if self.parentPerson:
            self.callout.setParentId(
                self.parentPerson.id
            )  # handles position translation

    def undo(self):
        self.scene.removeItem(self.callout)
        self.callout.setParentId(None)  # disable callbacks in Person.itemChange


def addCallout(*args, **kwargs):
    cmd = AddCallout(*args, **kwargs)
    stack().push(cmd)
    return cmd.callout


class SetLayerItemParent(UndoCommand):

    ANALYTICS = "Set LayerItem parent"

    def __init__(self, item, parent, id=-1):
        parentName = parent and parent.itemName() or None
        super().__init__(
            "Reparent %s parent to <%s>" % (item.itemName(), parentName), id
        )
        self.data = {item: {"parent": parent, "parent_was": item.parentPerson()}}

    def redo(self):
        for item, data in self.data.items():
            if data["parent"]:
                parentId = data["parent"]
            else:
                parentId = None
            item.setParentId(parentId)

    def undo(self):
        for item, data in self.data.items():
            if data["parent_was"]:
                parentId = data["parent_was"]
            else:
                parentId = None
            item.setParentId(parentId)

    def mergeWith(self, other):
        util.deepMerge(self.data, other.data, ignore="parent_was")
        return True


def setLayerItemParent(*args, **kwargs):
    cmd = SetLayerItemParent(*args, **kwargs)
    stack().push(cmd)
