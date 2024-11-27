import copy
from .. import commands, util


class Property:
    """Track changes and automatically write to file."""

    _nextId = 0

    @staticmethod
    def sortBy(stuff, attr):
        default = 0
        for item in stuff:
            x = getattr(item, attr)()
            if x is not None:
                default = type(x)()
                break

        def getKey(x):
            y = getattr(x, attr)()
            if y is not None:
                return y
            else:
                return default

        return sorted(stuff, key=getKey)

    def __init__(self, item, **kwargs):
        super().__init__()
        self._kwargs = kwargs
        self._id = Property._nextId
        Property._nextId = Property._nextId + 1
        self.item = item
        self.isDynamic = False
        self.attr = kwargs["attr"]
        self.onset = kwargs.get("onset", None)
        self.default = kwargs.get("default", None)
        if isinstance(self.default, (list, dict)):
            self.default = copy.deepcopy(self.default)
        self.isDynamic = kwargs.get("dynamic", False)
        self._value = None
        self._currentLayerValue = None
        self._usingLayer = False  # updated on activeLayersChanged
        self._activeLayers = []
        self._isResetting = False
        self.strip = kwargs.get("strip", False)
        self.layered = kwargs.get("layered", False)
        self.notify = kwargs.get("notify", True)
        if "type" in kwargs:
            self.type = kwargs["type"]
        else:
            self.type = "default" in kwargs and type(self.default) or str
            kwargs["type"] = self.type

    def __repr__(self):
        s = str(self.get())
        if len(s):
            s = ": " + s
        return "<Property[%i, %s]%s>" % (self.id(), self.name(), s)

    def name(self):
        return self.attr

    def kwargs(self):
        return self._kwargs

    def deinit(self):
        """For circular refs."""
        self.item = None

    def setAttr(self, attr):
        self.attr = attr

    def setLayered(self, on):
        self.layered = on

    def isset(self):
        return self.get() != self.default

    def id(self):
        return self._id

    def scene(self):
        if self.item:
            return self.item.scene()

    def onActiveLayersChanged(self):
        if self.layered:
            # update caches
            self._activeLayers = self.scene().activeLayers()
            if self._activeLayers:
                ok = False
                # last active layer takes precidence
                value, ok = self._activeLayers[-1].getItemProperty(
                    self.item.id, self.name()
                )  # because properties don't have reliable id's. nuts...
                if ok:
                    self._currentLayerValue = value
                    self._usingLayer = True
                else:
                    self._currentLayerValue = None
                    self._usingLayer = False
            else:
                self._currentLayerValue = None
                self._usingLayer = False

    def get(self, forLayers=None):
        """Cache value(s)."""
        ret = None
        if self.layered and forLayers:  # non-cached query
            # last active layer takes precidence
            value, ok = forLayers[-1].getItemProperty(
                self.item.id, self.name()
            )  # because properties don't have reliable id's. nuts...
            if ok:
                ret = value
        # forLayers == [] means force no layer in Item.read()
        elif self.layered and self._usingLayer and forLayers != []:
            ret = self._currentLayerValue
        else:
            if self._value is not None:
                ret = self._value
            elif self.default is not None:
                ret = self.default
            else:
                ret = None
        return ret

    def set(self, x, notify=True, undo=None, forLayers=None, force=False):
        """Return True if value was changed, otherwise False.
        forLayers == None: current visible value
        forLayers == []: non-layer value
        force = True for commands.SetItemProperty so notifications are sent
        """
        if x is None:
            y = None
        else:
            if self.type is type(None):
                y = None
            else:
                y = self.type(x)
        if self.strip and y is not None:
            y = y.strip()
        currentValue = self.get()
        if force or y != currentValue:
            if undo:
                # do this before setting the value so `was` can be extracted from layers
                if undo is True:
                    undo = commands.nextId()
                cmd = commands.SetItemProperty(
                    self, y, layers=self._activeLayers, id=undo
                )
                commands.stack().push(cmd)
            if forLayers is None:
                layers = self._activeLayers
            else:
                layers = forLayers
            if layers and self._kwargs.get("layerIgnoreAttr"):
                layerIgnoreAttr = self._kwargs.get("layerIgnoreAttr")
                layers = [
                    layer for layer in layers if getattr(layer, layerIgnoreAttr)()
                ]
            if self.layered and layers:
                appliesRightNow = False
                for layer in layers:
                    layer.setItemProperty(self.item.id, self.attr, y)
                    if layer in self._activeLayers:
                        appliesRightNow = True
                if appliesRightNow:
                    self._usingLayer = True
                    self._currentLayerValue = y
            else:
                self._value = y
                appliesRightNow = True
            if self.notify and notify and appliesRightNow:
                self.item.onProperty(self)
                if self.onset and hasattr(self.item, self.onset):
                    getattr(self.item, self.onset)()
            return True
        else:
            return False

    def reset(self, notify=True, undo=None):
        if not self.isset():
            return
        self._isResetting = True
        if undo:
            if undo is True:
                undo = commands.nextId()
            cmd = commands.ResetItemProperty(self, layers=self._activeLayers, id=undo)
            commands.stack().push(cmd)
        if self._usingLayer:
            for layer in self._activeLayers:
                layer.resetItemProperty(self)
            self._currentLayerValue = None
            self._usingLayer = False
        else:
            self._value = None
        if self.notify and notify:
            self.item.onProperty(self)
            if self.onset and hasattr(self.item, self.onset):
                getattr(self.item, self.onset)()
        self._isResetting = False

    def isUsingLayer(self):
        """Return True if value is currently being pulled from the layer versus this props's internal value."""
        return self._usingLayer

    def isResetting(self):
        """Item.onProperty can respond differently in some cases, e.g. to animate when resetting itemPos."""
        return self._isResetting
