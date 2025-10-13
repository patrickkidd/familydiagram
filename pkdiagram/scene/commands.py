"""
Undo logic is tightly bound to the data model, i.e. the Scene object. This is
because the data model (Item) and UI (QGraphicsScene) were fused from the start.
Methods with the `undo=` kwarg use the undo api.

If `undo=False`, no UndoCommand is created and the underlying method is called
directly. If `undo=True`, then an UndoCommand is created to store any necessary
state from the object required to undo the underlying api call.
"""

import os, shutil, logging

from pkdiagram.pyqt import QUndoCommand
from pkdiagram.scene import (
    Event,
    Emotion,
    Person,
    Marriage,
    Layer,
    LayerItem,
    MultipleBirth,
)

_log = logging.getLogger(__name__)


class AddItem(QUndoCommand):
    def __init__(self, scene, item):
        super().__init__(f"Add item: {item}")
        self.scene = scene
        self.item = item
        self._layerOrders = self.scene.layers() if item.isLayer else []
        self._calloutParentId = item.parentId() if item.isCallout else None
        self._calloutItemPos = item.itemPos() if item.isCallout else None
        self._eventEmotions = (
            scene.emotionsFor(item) if (item.isEvent and item.relationship()) else []
        )

    def redo(self):
        self.scene._do_addItem(self.item)
        if self.item.isLayer:
            layers = self.scene.layers()
            iOrder = len(self.scene.layers())
            self.item.setOrder(iOrder)  # append
        elif self.item.isCallout:
            self.item.setParentId(self._calloutParentId)
            self.item.setItemPosNow(self._calloutItemPos)
        if self._eventEmotions:
            self.scene.addItems(self._eventEmotions)

    def undo(self):
        self.scene._do_removeItem(self.item)
        if self.item.isLayer:
            for i, layer in enumerate(self._layerOrders):
                layer.setOrder(i, notify=False)
        elif self.item.isCallout and self.item.parentId():
            self.item.setParentId(None)  # disable callbacks in Person.itemChange
        # Emotions may have already been cascade-deleted when event was removed
        for emotion in self._eventEmotions:
            if emotion in self.scene.emotions():
                self.scene.removeItem(emotion)


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

        def mapEvent(item: Event):
            for entry in self._unmapped["events"]:
                if entry["event"] is item:
                    return
            # Store IDs, not object references
            mapping = {
                "event": item,
                "personId": item.person().id if item.person() else None,
                "spouseId": item.spouse().id if item.spouse() else None,
                "childId": item.child().id if item.child() else None,
                "targetIds": [p.id for p in item.relationshipTargets()],
                "triangleIds": [p.id for p in item.relationshipTriangles()],
                "dateTime": item.dateTime(),
            }
            self._unmapped["events"].append(mapping)
            for emotion in self.scene.emotionsFor(item):
                mapEmotion(emotion)

        def mapEmotion(item: Emotion):
            for entry in self._unmapped["emotions"]:
                if entry["emotion"] is item:
                    return
            mapping = {
                "emotion": item,
                "eventId": item.event().id if item.event() else None,
                "targetId": item.target().id if item.target() else None,
            }
            self._unmapped["emotions"].append(mapping)

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
                for emotion in list(scene.emotionsFor(item)):
                    mapEmotion(emotion)
                for event in list(scene.eventsFor(item)):
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
                # Store all items (not just LayerItems) that reference this layer
                itemsWithLayer = []
                for sceneItem in self.scene.itemRegistry.values():
                    if hasattr(sceneItem, "layers") and callable(sceneItem.layers):
                        if item.id in sceneItem.layers():
                            itemsWithLayer.append(sceneItem)
                self._unmapped["layers"].append(
                    {
                        "layer": item,
                        "itemsWithLayer": itemsWithLayer,
                    }
                )

            mapItem(item)

    def redo(self):
        self.scene.removeItems(self.items, undo=False)

    def undo(self):
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
            entry["people"][0].onAddMarriage(entry["marriage"])
            entry["people"][1].onAddMarriage(entry["marriage"])
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
            # Events are restored via scene.addItem - person references will be resolved
            # Just ensure event is in scene
            if not entry["event"].scene():
                self.scene.addItem(entry["event"])
        #
        for entry in self._unmapped["emotions"]:
            # Emotion references are via event, not direct person
            if not entry["emotion"].scene():
                self.scene.addItem(entry["emotion"])
            # Update parent item for non-dyadic emotions
            if (
                not entry["emotion"].isDyadic()
                and entry["emotion"].event()
                and entry["emotion"].event().person()
            ):
                entry["emotion"].setParentItem(entry["emotion"].event().person())
        #
        for entry in self._unmapped["layers"]:  # before layer items
            # Restore layer to all items that had it
            for sceneItem in entry["itemsWithLayer"]:
                layers = sceneItem.layers()
                readd = sceneItem.isLayerItem and not layers
                layers.append(entry["layer"].id)
                sceneItem.setLayers(layers)
                if readd:
                    self.scene.addItem(sceneItem)
            self.scene.addItem(entry["layer"])
        #
        for entry in self._unmapped["layerItems"]:
            self.scene.addItem(entry["item"])
            entry["item"].setParentItem(entry["parent"])
        # again, after others are updated
        for entry in self._unmapped["children"]:
            birthPartners = entry.get("birthPartners", [])
            if birthPartners:
                for child in birthPartners:
                    child.childOf.updateGeometry()

        for item in self.items:
            if item.isPathItem:
                item.flash()
            elif item.isEvent:
                person = item.person()
                if person:
                    person.flash()


class SetItemPos(QUndoCommand):
    def __init__(self, item, value):
        super().__init__("Set item pos")
        self.was_value = item.itemPos()
        self.item = item
        self.value = value
        if item.isCallout:
            self.calloutPoints = item.mouseMovePoints
            self.was_calloutPoints = item.mousePressPoints

    def redo(self):
        self.item.setItemPosNow(self.value)
        if self.item.isCallout and self.calloutPoints:
            self.item.setPoints(self.calloutPoints)
        self.item.updateGeometry()

    def undo(self):
        self.item.setItemPosNow(self.was_value)
        if self.item.isCallout:
            self.item.setPoints(self.was_calloutPoints)
        self.item.updateGeometry()


class SetProperty(QUndoCommand):
    def __init__(self, prop, value, forLayers=[]):
        if forLayers:
            layerNames = ",".join([layer.name() for layer in forLayers])
            super().__init__(
                f"Set property '{prop.name()}' on {prop.item.__class__.__name__} for layers {layerNames}"
            )
        else:
            super().__init__(
                f"Set property '{prop.name()}' on {prop.item.__class__.__name__}"
            )
        self.forLayers = forLayers
        if forLayers:
            self.was_values = {
                layer.id: layer.getItemProperty(prop.item.id, prop.name())
                for layer in forLayers
                if layer.getItemProperty(prop.item.id, prop.name())[0]
            }
        else:
            self.was_set = prop.isset()
            self.was_value = prop.get()
        self.value = value
        self.prop = prop

    def redo(self):
        if self.forLayers:
            for layer in self.forLayers:
                layer.setItemProperty(self.item.id, self.prop.name(), self.value)
            self.prop.onActiveLayersChanged()
        else:
            self.prop._do_set(self.value, force=True)

    def undo(self):
        if self.forLayers:
            for layer in self.forLayers:
                if layer.id in self.was_values:
                    was = self.was_values[layer.id]
                    layer.setItemValue(self.prop.item.id, self.prop.name(), was)
                else:
                    layer.resetItemProperty(self.prop)
            self.prop.onActiveLayersChanged()
        else:
            if self.was_set:
                self.prop._do_set(self.was_value, force=True)
            else:
                self.prop._do_reset()


class ResetProperty(QUndoCommand):
    def __init__(self, prop, forLayers=[]):
        if forLayers:
            super().__init__(f"Reset '{prop.name()}' on layers")
        else:
            super().__init__(f"Reset '{prop.name()}' on item")

        self.was_values = {}
        if prop.layered:
            # only take `was` values stored on selected layers
            for layer in forLayers:
                self.was_values[layer] = {}
                x, ok = layer.getItemProperty(prop.item.id, prop.name())
                if ok:
                    self.was_values[layer] = {prop: x}
        else:
            self.was_values[None] = {prop: prop.get()}
        self.prop = prop

    def redo(self):
        self.prop._do_reset()

    def undo(self):
        for layer, propEntry in self.was_values.items():
            for prop, was in propEntry.items():
                if layer:
                    layer.setItemProperty(prop.item.id, prop.name(), was)
                else:
                    prop.set(was)
                prop.onActiveLayersChanged()


class SetEventPerson(QUndoCommand):

    def __init__(self, event, person):
        super().__init__(f"Set event {event.itemName()} person to {person.itemName()}")
        self.was_person = event.person()
        self.event = event
        self.person = person

    def redo(self):
        self.event._do_setPerson(self.person)

    def undo(self):
        self.event._do_setPerson(self.was_person)


# class SetEventKind(QUndoCommand):

#     def __init__(self, events, kind: EventKind):
#         super().__init__(f"Set event(s) to {kind.name}")
#         self.was_kinds
#         self.event = event
#         self.parent = parent

#     def redo(self):
#         self.event._do_setParent(self.parent)

#     def undo(self):
#         self.event._do_setParent(self.was_parent)


class SetParents(QUndoCommand):
    def __init__(self, person, target):
        """
        target is either a Marriage, ChildOf, or MultipleBirth.
        """
        super().__init__("Set parents")
        #
        if target is None:
            data = {"state": None}
        elif target.isMarriage:
            data = {"state": "marriage", "parents": target}
        elif target.isChildOf:
            if target.multipleBirth:
                data = {
                    "state": "multipleBirth.children",
                    "parents": target.parents(),
                    "people": list(target.multipleBirth.children()),
                }
            else:
                data = {
                    "state": "multipleBirth.person",
                    "parents": target.parents(),
                    "otherPerson": target.person,
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


class AddEventProperty(QUndoCommand):

    def __init__(self, scene, propName, index=None):
        super().__init__("Create event property")
        self.scene = scene
        self.propName = propName
        self.index = index

    def redo(self):
        self.scene._do_addEventProperty(self.propName, self.index)

    def undo(self):
        self.scene._do_removeEventProperty(self.propName)


class RemoveEventProperty(QUndoCommand):

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
        super().__init__(f"Remove event property '{propName}'")
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
        self.scene.removeEventPropertyByName(self.propName)

    def undo(self):
        self.scene.addEventProperty(self.propName, index=self.propIndex)
        self.writeValueCache(self.scene, self.valueCache, onlyAttr=self.attr)


class RenameEventProperty(QUndoCommand):

    def __init__(self, scene, old, new):
        super().__init__("Rename event property")
        self.scene = scene
        self.old = old
        self.new = new

    def redo(self):
        self.scene.renameEventProperty(self.old, self.new)

    def undo(self):
        self.scene.renameEventProperty(self.new, self.old)


class ReplaceEventProperties(QUndoCommand):

    def __init__(self, scene, newPropNames):
        super().__init__(f"Replace event properties")
        self.scene = scene
        self.oldPropNames = [entry["name"] for entry in scene.eventProperties()]
        self.newPropNames = newPropNames
        self.valueCache = RemoveEventProperty.readValueCache(scene)

    def redo(self):
        self.scene.replaceEventProperties(self.newPropNames)

    def undo(self):
        self.scene.replaceEventProperties(self.oldPropNames)
        RemoveEventProperty.writeValueCache(self.scene, self.valueCache)


class SetLayerOrder(QUndoCommand):

    def __init__(self, scene, layers):
        super().__init__("Set layer order")
        self.scene = scene
        self.was_layers = scene.layers()  # sorted
        self.layers = list(layers)  # new sorted

    def redo(self):
        self.scene._do_setLayerOrder(self.layers)

    def undo(self):
        self.scene._do_setLayerOrder(self.was_layers)
