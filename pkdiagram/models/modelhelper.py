from pkdiagram.pyqt import pyqtSlot
from pkdiagram import util
from .qobjecthelper import QObjectHelper
from pkdiagram.scene import Scene, Property


class ModelHelper(QObjectHelper):
    """
    Handle properties for a list of like Item's.
    calls refreshAllProperties() when items and/or scene changed.
    """

    QObjectHelper.registerQtProperties(
        [
            {"attr": "items", "type": list},
            {"attr": "scene", "type": Scene, "default": None},
            {
                "attr": "dirty",
                "type": bool,
                "default": False,
            },  # set automatically, reset manually
            {
                "attr": "resetter",
                "type": bool,
            },  # alternates when modelReset is called for bindings
        ]
    )

    def initModelHelper(self, storage=False):
        self._ModelHelperInitializing = True
        self._dirty = False
        self._items = []
        self._scene = None
        self._resetter = False
        self.itemsChanged.connect(self.onItemsChanged)
        self.sceneChanged.connect(self.onSceneChanged)
        if hasattr(self, "modelReset"):

            def onModelReset():
                if not self._ModelHelperInitializing:
                    self.resetter = not self._resetter

            self.modelReset.connect(onModelReset)
        self.initQObjectHelper(storage=storage)
        self._ModelHelperInitializing = False

    def onItemProperty(self, prop):
        """Properties come upstream through here upon undo."""
        # Now that one of the many values for this property has changed,
        # recalcuate the qml-level value from the set of values for this
        # prop name from subclasses before comparing to the cache and emitting
        # a value changed signal
        if not self.refreshingAttr() == prop.name():
            # blocked from set() when this is called back from onItemProperty()
            self.refreshProperty(prop.name())

    def onSceneProperty(self, prop):
        """Virtual"""
        if prop.name() == "showAliases":
            self.refreshAllProperties()

    def onItemsChanged(self, items):
        """For stack trace in test."""
        self.refreshAllProperties()

    def onSceneChanged(self, items):
        """For stack trace in test."""
        self.refreshAllProperties()

    def sameOf(self, attr, getter):
        ret = None
        if self._items:
            ret = util.sameOf(self._items, getter)
        if ret is None:
            ret = self.defaultFor(attr)
        return ret

    def same(self, attr):
        """Return: - the set value if all are the same, or None."""
        if self._items and self._items[0].prop(attr):
            return self.sameOf(attr, lambda item: getattr(item, attr)())

    @pyqtSlot(str, result=bool)
    def any(self, attr):
        """Return True if the property is set for any of the items, otherwise False."""
        if not self._items:
            return False
        numSet = 0
        for item in self._items:
            if item.prop(attr).get() is not None:
                numSet += 1
        return bool(numSet > 0)

    def get(self, attr):
        """Return the value. Default behavior is to return the same(attr).
        If value is a bool then convert it to a check state.
        """
        if attr == "items":
            return self._items
        elif attr == "scene":
            return self._scene
        elif attr == "dirty":
            return self._dirty
        elif attr == "resetter":
            return self._resetter
        #
        foundItemProp = False
        for item in self._items:
            if item.prop(attr) is not None:
                foundItemProp = True
                break
        if foundItemProp:
            value = self.same(attr)
        else:
            value = super().get(attr)
        value = self.getterConvertTo(attr, value)
        if value is None:  # Handle conversion to default when not matching or not set.
            value = self.defaultFor(attr)
        return value

    def set(self, attr, value):
        """Set the value on the models from qml; Default behavior is to set the properties or reset if x is the default.
        If value is a bool then convert it from a check state.
        """
        if self.propAttrsFor(attr) is None:
            raise AttributeError("%s has no property named `%s`" % (self, attr))
        if not self._dirty and attr != "dirty":
            self._dirty = True
            self.refreshProperty("dirty")
        if attr == "items":
            if self._items:
                for item in self._items:
                    item.removePropertyListener(self)
                self._items = []
            if value not in (None, [None]):
                if not isinstance(value, list):
                    value = [value]
                self._items = value
                for item in self._items:
                    item.addPropertyListener(self)
            self.refreshProperty("items")
            return
        elif attr == "scene":
            if self._scene:
                self._scene.propertyChanged[Property].disconnect(self.onSceneProperty)
            self._scene = value
            if self._scene:
                self._scene.propertyChanged[Property].connect(self.onSceneProperty)
            self.refreshProperty("scene")
            return
        elif attr == "dirty":
            self._dirty = value
        elif attr == "resetter":
            self._resetter = value
            self.refreshProperty("resetter")
        #
        x = self.setterConvertTo(attr, value)
        # set on property
        undo = attr != "resetter"
        foundItemProp = False
        if self._scene and self._items:
            with self._scene.macro(
                f"Set attribute '{attr}' on model class '{self.__class__.__name__}'",
                undo=undo,
            ):
                for item in self._items:
                    # if the item has not been set yet then leave it alone
                    prop = item.prop(attr)
                    if prop is not None:
                        foundItemProp = True
                        y = prop.get()
                        if y != x:
                            prop.set(x, undo=undo)
                            # if x == prop.default:
                            #     prop.reset(notify=notify, undo=undo)
                            # else:
                            #     prop.set(x, notify=notify, undo=undo)
        if not foundItemProp:
            super().set(attr, value)

    def reset(self, attr):
        if attr == "items":
            self.set("items", [])
            return
        elif attr == "scene":
            self.set("scene", [])
            return
        elif attr == "dirty":
            self.set("dirty", False)
        undo = attr != "resetter"
        with self._scene.macro(
            f"Reset attribute '{attr}' on model class '{self.__class__.__name__}'"
        ):
            for item in self._items:
                prop = item.prop(attr)
                if prop:
                    item.prop(attr).reset(undo=undo)
