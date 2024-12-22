"""
Undo logic is tightly bound to the data model, i.e. the Scene object. The Scene
and its child Item's have the basic logic needed to perform a change. Any
UndoCommand contains the logic to *undo* that basic change.

*However*, UndoCommand's are also only ever created by the Scene and Item API's
when undo=True is passed to a basic api method, e.g. Scene.addItem(). This means
that the api method needs to call a secondary method like Scene._addItem() that
contains the actual logic for the basic change and not creating the UndoCommand.
This is not ideal, but accomodates the existing QGraphicsScene and
QGraphicsItem-based data model.
"""

import os, shutil, logging
import pprint

from pkdiagram.pyqt import QUndoStack, QUndoCommand, QPointF
from pkdiagram import util
from pkdiagram.scene import Callout


_log = logging.getLogger(__name__)


class AddItem(QUndoCommand):
    def __init__(self, scene, item):
        super().__init__(f"Add item: {item}")
        self.scene = scene
        self.item = item
        self._layerOrders = self.scene.layers() if item.isLayer else None
        self._calloutParentId = item.parentId() if item.isCallout else None

    def redo(self):
        self.scene._addItem(self.item)
        if self.item.isLayer:
            layers = self.scene.layers()
            iOrder = len(self.scene.layers())
            self.item.setOrder(iOrder)  # append
        elif self.item.isCallout and self.calloutParentId:
            self.item.setParentId(self._calloutParentId)

    def undo(self):
        self.scene._removeItem(self.item)
        if self.item.isLayer:
            for i, layer in enumerate(self._layerOrders):
                layer.setOrder(i, notify=False)
        elif self.item.isCallout and self.item.parentId():
            self.item.setParentId(None)  # disable callbacks in Person.itemChange


class RemoveItems(QUndoCommand):

    def __init__(self, scene, items):
        super().__init__("Remove items")
        self.scene = scene
        if isinstance(items, list):
            self.items = list(items)
        else:
            self.items = [items]

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


class SetPos(QUndoCommand):

    def __init__(self, item, pos, id):
        super().__init__("Move items", id)

        if item.isCallout:
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

    def redo(self):
        if self.firstRun:
            # Items are already in place; don't move until true 'redo.'
            self.firstRun = False
        else:
            for item, entry in self.data.items():
                item.setPos(entry["pos"])
                if item.isCallout and entry["calloutPoints"]:
                    item.setPoints(entry["calloutPoints"])
            # after set pos
            for item, entry in self.data.items():
                if hasattr(item, "updateGeometry"):  # needed?
                    item.updateGeometry()

    def undo(self):
        for item, entry in self.data.items():
            item.setPos(entry["pos_was"])
            if item.isCallout and entry["calloutPoints_was"]:
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


class SetItemProperty(QUndoCommand):
    """Only called from Property.set()."""

    ANALYTICS = False  # "SetItemProperty"

    def __init__(self, prop, value, layers=[]):
        if layers:
            super().__init__("Set %s on layers" % prop.name())
        else:
            super().__init__("Set %s" % prop.name())
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


class ResetItemProperty(QUndoCommand):
    """Only used from Property.reset(."""

    def __init__(self, prop, layers=[]):
        item = prop.item
        super().__init__("Reset %s" % prop.name())
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


class SetParents(QUndoCommand):
    def __init__(self, person, target):
        super().__init__("Set child")
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


class AddEventProperty(QUndoCommand):

    ANALYTICS = "Create event property"

    def __init__(self, scene, propName, index=None):
        super().__init__('Create event property "%s"' % propName)
        self.scene = scene
        self.propName = propName
        self.index = index

    def redo(self):
        self.scene._addEventProperty(self.propName, self.index)

    def undo(self):
        self.scene._removeEventProperty(self.propName)


class RemoveEventProperty(QUndoCommand):

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

    def redo(self):
        self.scene.removeEventProperty(self.propName)

    def undo(self):
        self.scene.addEventProperty(self.propName, index=self.propIndex)
        self.writeValueCache(self.scene, self.valueCache, onlyAttr=self.attr)


class RenameEventProperty(QUndoCommand):

    def __init__(self, scene, old, new):
        super().__init__('Rename event property "%s" to "%s"' % (old, new))
        self.scene = scene
        self.old = old
        self.new = new

    def redo(self):
        self.scene.renameEventProperty(self.old, self.new)

    def undo(self):
        self.scene.renameEventProperty(self.new, self.old)


class ReplaceEventProperties(QUndoCommand):

    ANALYTICS = "Replace event properties"

    def __init__(self, scene, newPropNames):
        super().__init__('Create event properties with "%s"' % newPropNames)
        self.scene = scene
        self.oldPropNames = [entry["name"] for entry in scene.eventProperties()]
        self.newPropNames = newPropNames
        self.valueCache = RemoveEventProperty.readValueCache(scene)

    def redo(self):
        self.scene.replaceEventProperties(self.newPropNames)

    def undo(self):
        self.scene.replaceEventProperties(self.oldPropNames)
        RemoveEventProperty.writeValueCache(self.scene, self.valueCache)


class SetEmotionPerson(QUndoCommand):

    ANALYTICS = "Set emotion person"

    def __init__(self, emotion, personA=None, personB=None):
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
        self.emotion = emotion
        self.personA = personA
        self.personB = personB
        self.was_personA = emotion.personA()
        self.was_personB = emotion.personB()
        if personA == was_personB and personB == was_personA:
            self.swap = True
        else:
            self.swap = False

    def redo(self):
        if self.swap:
            emotion.swapPeople()
        else:
            if self.personA:
                emotion.setPersonA(self.personA)
            if self.personB:
                emotion.setPersonB(self.personB)

    def undo(self):
        if self.swap:
            emotion.swapPeople()
        else:
            if self.was_personA != emotion.personA():
                emotion.setPersonA(self.was_personA)
            if self.was_personB != emotion.personB():
                emotion.setPersonB(self.was_personB)


class SetEventParent(QUndoCommand):

    ANALYTICS = "Set event parent"

    def __init__(self, event, parent):
        super().__init__("Add <%s> to <%s>" % (event.itemName(), parent.itemName()))
        self.was = event.parent
        self.event = event
        self.parent = parent

    def redo(self):
        self.event.setParent(self.parent)

    def undo(self):
        self.event.setParent(self.was)


class SetLayerOrder(QUndoCommand):

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


class SetLayerItemParent(QUndoCommand):

    ANALYTICS = "Set LayerItem parent"

    def __init__(self, item, parent):
        parentName = parent and parent.itemName() or None
        super().__init__("Reparent %s parent to <%s>" % (item.itemName(), parentName))
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
