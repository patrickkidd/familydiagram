"""
Undo logic is tightly bound to the data model, i.e. the Scene object. The Scene
and its child Item's have the basic logic needed to perform a change. Any
UndoCommand contains the logic to *undo* that basic change.

*However*, UndoCommand's are also only ever created by the Scene and Item API's
when undo=True is passed to a basic api method, e.g. Scene.addItem(). This means
that the api method needs to call a secondary method like Scene._do_addItem() that
contains the actual logic for the basic change and not creating the UndoCommand.
This is not ideal, but accomodates the existing QGraphicsScene and
QGraphicsItem-based data model.
"""

import os, shutil, logging

from pkdiagram.pyqt import QUndoCommand


_log = logging.getLogger(__name__)


class AddItem(QUndoCommand):
    def __init__(self, scene, item):
        super().__init__(f"Add item: {item}")
        self.scene = scene
        self.item = item
        self._layerOrders = self.scene.layers() if item.isLayer else None
        self._calloutParentId = item.parentId() if item.isCallout else None

    def redo(self):
        self.scene._do_addItem(self.item)
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
    def __init__(self, item, pos):
        super().__init__("Set pos")
        self.was_pos = item.pos()
        self.item = item
        self.pos = pos
        if item.isCallout:
            self.calloutPoints = item.mouseMovePoints
            self.was_calloutPoints = item.mousePressPoints

    def redo(self):
        self.item.setPos(self.pos)
        if self.item.isCallout and self.calloutPoints:
            self.item.setPoints(self.calloutPoints)
        self.item.updateGeometry()

    def undo(self):
        self.item.setPos(self.was_pos)
        if self.item.isCallout:
            self.item.setPoints(self.was_calloutPoints)
        self.item.updateGeometry()


class SetProperty(QUndoCommand):
    def __init__(self, prop, value, forLayers=[]):
        if forLayers:
            super().__init__(f"Set '{prop.name()}' on layers")
        else:
            super().__init__(f"Set '{prop.name()}' on item")
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
        if self.forlayers:
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
        self.prop = prop

    def redo(self):
        if self.forlayers:
            for layer in self.forLayers:
                if layer.id in self.was_values:
                    layer.resetItemProperty(self.prop)
            self.prop.onActiveLayersChanged()
        elif self.was_set:
            self.prop._do_reset()

    def undo(self):
        if self.forlayers:
            for layer in self.forLayers:
                if layer.id in self.was_values:
                    was = self.was_values[layer.id]
                    layer.setItemValue(self.prop.item.id, self.prop.name(), was)
            self.prop.onActiveLayersChanged()
        elif self.was_set:
            self.prop._do_set(self.was_value, force=True)


class SetEmotionPerson(QUndoCommand):

    def __init__(self, emotion, personA=None, personB=None):
        super().__init__("Set emotion person")
        self.emotion = emotion
        self.personA = personA
        self.personB = personB
        self.was_personA = emotion.personA()
        self.was_personB = emotion.personB()
        if personA == self.was_personB and personB == self.was_personA:
            self.swap = True
        else:
            self.swap = False

    def redo(self):
        if self.swap:
            self.emotion.swapPeople()
        else:
            if self.personA:
                self.emotion.setPersonA(self.personA)
            if self.personB:
                self.emotion.setPersonB(self.personB)

    def undo(self):
        if self.swap:
            self.emotion.swapPeople()
        else:
            if self.was_personA != self.emotion.personA():
                self.emotion.setPersonA(self.was_personA)
            if self.was_personB != self.emotion.personB():
                self.emotion.setPersonB(self.was_personB)


class SetEventParent(QUndoCommand):

    def __init__(self, event, parent):
        super().__init__(f"Set event {event.itemName()} parent to {parent.itemName()}")
        self.was_parent = event.parent
        self.event = event
        self.parent = parent

    def redo(self):
        self.event.setParent(self.parent, notify=True)

    def undo(self):
        self.event.setParent(self.was_parent, notify=True)


class SetParents(QUndoCommand):
    def __init__(self, person, target):
        super().__init__("Set parents")
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
        self.scene.removeEventProperty(self.propName)

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
