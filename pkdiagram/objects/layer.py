import copy
from .item import Item


class Layer(Item):

    Item.registerProperties(
        (
            {"attr": "name"},
            {"attr": "description"},
            {"attr": "order", "type": int, "default": -1},
            {"attr": "notes"},
            {"attr": "active", "type": bool, "default": False},
            {"attr": "itemProperties", "type": dict},
            {"attr": "storeGeometry", "type": bool, "default": False},
        )
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.isLayer = True
        self._scene = kwargs.get("scene")
        if not "itemProperties" in kwargs:  # avoid shared default value instance
            self.prop("itemProperties").set({}, notify=False)

    def __repr__(self):
        return super().__repr__(exclude="itemProperties")

    def __lt__(self, other):
        if self.name() is not None and other.name() is None:
            return True
        elif self.name() is None and other.name() is not None:
            return False
        elif self.name() is None and other.name() is None:
            return True
        return self.name() < other.name()

    ## Cloning

    def clone(self, scene):
        from .layeritem import LayerItem

        x = super().clone(scene)
        stuff = copy.deepcopy(self.itemProperties())
        x.prop("itemProperties").set(None, notify=False)  # avoid equality check
        x.prop("itemProperties").set(stuff, notify=False)
        for layerItem in scene.find(types=LayerItem):
            if self.id in layerItem.layers():
                layers = list(layerItem.layers())
                layers.append(x.id)
                layerItem.setLayers(layers)
        return x

    def remap(self, map):
        """TODO: Map itemProperties."""
        return False

    ## Properties

    def onProperty(self, prop):
        isChanged = False
        if prop.name() == "storeGeometry" and not prop.get():
            # Setting `storeGeometry` to False clears geometry values
            itemProps = copy.deepcopy(self.itemProperties())
            for itemId, values in itemProps.items():
                if "size" in values:
                    del values["size"]
                    isChanged = True
                if "itemPos" in values:
                    del values["itemPos"]
                    isChanged = True
        super().onProperty(prop)
        if isChanged:
            self.setItemProperties(itemProps)
            if self.scene():
                self.scene().updateActiveLayers(force=True)

    ## Item property storage

    def itemName(self):
        return self.name()

    def setScene(self, scene):
        self._scene = scene

    def scene(self):
        return self._scene

    def getItemProperty(self, itemId, propName):
        # {
        #     id: {
        #         'propName': value,
        #         'propName': value
        #     }
        # }
        values = self.itemProperties().get(itemId)
        if values and propName in values:
            # self.here(self.id, itemId, propName, values[propName])
            return values[propName], True
        else:
            # self.here(self.id, itemId, propName, None)
            return None, False

    def setItemProperty(self, itemId, propName, value):
        props = self.itemProperties()
        if itemId in props:
            values = props[itemId]
        else:
            values = {}
            props[itemId] = values
        values[propName] = value
        self.setItemProperties(props, notify=False)  # noop?
        item = self.scene().find(itemId)

    def resetItemProperty(self, prop):
        """Called from Property.reset."""
        props = self.itemProperties()
        itemProps = props.get(prop.item.id)
        if not itemProps:
            return
        changed = False
        if prop.name() in itemProps:
            del itemProps[prop.name()]
            changed = True
        if not itemProps:
            del props[prop.item.id]
            changed = True
        if changed:
            self.setItemProperties(props, notify=False)

    def resetAllItemProperties(self, notify=True, undo=None):
        for itemId, propValues in list(self.itemProperties().items()):
            item = self.scene().find(itemId)
            for propName in list(propValues.keys()):
                item.prop(propName).reset(notify=notify, undo=undo)
        self.setItemProperties({})
