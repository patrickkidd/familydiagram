from pkdiagram.pyqt import Qt, QGraphicsItem, QRectF, QColor, QPen, QAbstractAnimation
from pkdiagram import util
from .pathitem import PathItem


# TODO: Really should be PersonLayerItem or something, since these can have parents.
class LayerItem(PathItem):

    PathItem.registerProperties(
        (
            {"attr": "layers", "default": []},  # [id, id, id]
            {"attr": "parentId", "type": int},
            {"attr": "scale", "default": 1.0},
            {"attr": "color"},
        )
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.isLayerItem = True
        self.setZValue(util.LAYERITEM_Z)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self._parentPerson = None

    def read(self, chunk, byId):
        super().read(chunk, byId)
        if chunk.get("parentId") is not None:
            self._parentPerson = byId(chunk["parentId"])
            if self._parentPerson:
                self._parentPerson._onAddLayerItem(self)
        # clean out stale ids for load file
        layerIds = [id for id in self.layers() if byId(id)]
        self.prop("layers").set(
            layerIds, notify=False
        )  # avoid .setLayers for cleanliness
        self.onProperty(self.prop("scale"))

    def write(self, chunk):
        super().write(chunk)

    def clone(self, scene):
        x = super().clone(scene)
        if self.parentId():
            self._parentId = self.parentId()
        else:
            self._parentId = None
        x.onProperty(x.prop("scale"))
        return x

    def remap(self, map):
        super().remap(map)
        self._parentPerson = map.find(self._parentId)
        delattr(self, "_parentId")

    def onProperty(self, prop):
        if prop.name() == "scale":
            super().setScale(self.prop("scale").get())
        elif prop.name() == "parentId":
            if self._parentPerson:
                self._parentPerson._onRemoveLayerItem(self)
            if prop.get() is None:
                self._parentPerson = None
            else:
                self._parentPerson = self.scene().find(id=prop.get())
                self._parentPerson._onAddLayerItem(self)
        elif prop.name() == "itemPos":
            # Ignore itemPos when no layers set.
            # Prevents animating to QPointF(0, 0) when disabling active layers.
            if not self.scene().activeLayers() and not self.isUpdatingAll():
                return
        elif prop.name() == "color":
            # old
            oldPenColor = self.pen().color()
            if self.itemAnimationGroup.state() == QAbstractAnimation.Running:
                oldBrushColor = self.brushAnimation.currentValue()
                self.itemAnimationGroup.stop()
            else:
                oldBrushColor = self.brush().color()
            # new
            if prop.isset():
                newPenColor = QColor(prop.get())
                # newBrushColor = QColor(newPenColor)
                # newBrushColor.setAlpha(100)
            else:
                newPenColor = QColor(util.PEN.color())
                # newBrushColor = QColor(Qt.transparent)
            newBrushColor = QColor(Qt.transparent)
            self.penAnimation.setStartValue(oldPenColor)
            self.penAnimation.setEndValue(newPenColor)
            self.brushAnimation.setStartValue(oldBrushColor)
            self.brushAnimation.setEndValue(newBrushColor)
            self.scaleAnimation.setStartValue(None)
            self.scaleAnimation.setEndValue(None)
            self.startLayerAnimation(self.itemAnimationGroup)
        super().onProperty(prop)

    def parentPerson(self):
        return self._parentPerson

    def setLayers(self, x, **kwargs):
        if x:  # always must have >= 1 layer
            self.prop("layers").set(x, **kwargs)
        if self.scene():
            self.onActiveLayersChanged()

    def shouldShowForLayers(self, forLayers):
        if (
            self.isSelected()
        ):  # sort of an override to prevent prop sheets disappearing, updated in ItemSelectedChange
            return True
        if forLayers is None:
            return False
        for layer in forLayers:
            for layerId in self.layers():
                if layerId == layer.id:
                    return True
        return False

    def layeredSceneBoundingRect(self, forLayers, forTags):
        if not self.shouldShowForLayers(forLayers):
            return QRectF()
        else:
            return super().layeredSceneBoundingRect(forLayers, forTags)

    def onActiveLayersChanged(self):
        super().onActiveLayersChanged()
        visible = self.shouldShowForLayers(self.scene().activeLayers())
        if visible:
            opacity = 1.0
        else:
            opacity = 0.0
        if not self.isUpdatingAll():
            self.fadeToOpacity(opacity)
        else:
            self.setOpacity(opacity)
            if opacity == 0:
                self.hide()
            else:
                self.show()

    def updatePen(self):
        super().updatePen()
        if self.hover:
            pen = QPen(util.HOVER_PEN)
        else:
            pen = QPen(util.PEN)
        pen.setCapStyle(self.penCapStyle)
        self.setPen(pen)
