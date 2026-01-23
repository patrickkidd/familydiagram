from pkdiagram.pyqt import QGraphicsSimpleTextItem, QPen
from pkdiagram import util
from pkdiagram.scene import LayerItem


class LayerLabel(LayerItem):
    def __init__(self, text="", **kwargs):
        super().__init__(**kwargs)
        self.isLayerLabel = True
        self.setShapeMargin(0)
        self.setZValue(util.DETAILS_Z)
        self._textItem = QGraphicsSimpleTextItem(self)
        self._textItem.setPen(util.PEN)
        self._textItem.setFont(util.DETAILS_BIG_FONT)
        if text:
            self.setText(text)

    def updatePen(self):
        super().updatePen()
        if self.hover:
            pen = QPen(util.HOVER_PEN)
        else:
            pen = QPen(util.PEN)
        pen.setCapStyle(self.penCapStyle)
        self.setPen(pen)
        self._textItem.setPen(pen)

    def text(self):
        return self._textItem.text()

    def setText(self, text):
        self._textItem.setText(text)
        self.updatePathItemData()

    def setFont(self, font):
        self._textItem.setFont(font)
        self.updatePathItemData()
