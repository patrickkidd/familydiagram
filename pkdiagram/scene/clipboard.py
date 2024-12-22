"""
Currently unused but keeping for future.
"""


class CutItems(RemoveItems):
    def __init__(self, scene, items):
        super().__init__(scene, items)
        self.setText("Cut items")


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
            if clone.isPerson and not item.childOf in self.items:
                # Ensure childItem is added to the map even if not selected
                childClone = item.childOf.clone(scene)
                self.map[clone._cloned_childOf_id] = childClone
                clones.append(childClone)
        childOfs = []
        others = []
        people = []
        for clone in clones:
            if clone.isPerson:
                people.append(clone)
            elif clone.isChildOf:
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


class PasteItems(QUndoCommand):
    def __init__(self, scene, items):
        super().__init__("Paste items")
        self.scene = scene
        self.items = {}
        for item in items:
            self.items[item] = {"pos_was": item.pos()}

    def redo(self):
        for item in self.scene.selectedItems():
            item.setSelected(False)
        for item, info in self.items.items():
            if item.scene() != self.scene:  # scene set on copy()
                item.setParentItem(None)
                self.scene.addItem(item)
            if item.isLayerItem:
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


class ImportItems(PasteItems):

    def __init__(self, scene, items):
        super().__init__(scene, items)
        self.setText("Import items")
