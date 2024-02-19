from .pyqt import (
    QGraphicsView,
    QTimeLine,
    QObject,
    QVariantAnimation,
    QGraphicsRectItem,
    Qt,
    QRectF,
    QGraphicsItem,
)
from . import util


class WheelZoomer(QObject):

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self._begun = False
        self.currentScale = None

    def begun(self):
        return self._begun

    def begin(self, e):
        if self.begun():
            self.cancel()
        self._begun = True
        self.startSceneScale = self.view.scene().scaleFactor()
        self.currentScale = self.view.scene().scaleFactor()
        # zoom to cursor
        self.startSceneCenter = self.view.sceneCenter()
        self.startMouseScenePos = self.view.mapToScene(e.pos())

    def update(self, e):
        if util.IS_WINDOWS:
            delta = e.angleDelta().x()
        else:
            delta = e.pixelDelta().y()
        if not delta:
            return
        FACTOR = 0.999
        if delta < 0:  # zoom out
            coeff = pow(FACTOR, abs(delta))
            self.currentScale = self.currentScale * coeff
        else:  # zoom in
            coeff = pow(1 / FACTOR, abs(delta))
            self.currentScale = self.currentScale * coeff
        self.view.zoomAbsolute(self.currentScale)
        # zoom to cursor
        currentSceneCenter = self.view.sceneCenter()
        currentMouseScenePos = self.view.mapToScene(e.pos())
        sceneMouseDiff = self.startMouseScenePos - currentMouseScenePos
        newSceneCenter = currentSceneCenter + sceneMouseDiff
        self.view.centerOn(newSceneCenter)

    def end(self):
        if not self.begun():
            return
        self.view.panAbsolute(self.view.sceneCenter())
        self.view.zoomAbsolute(self.currentScale)
        self._begun = False
        self.currentScale = None

    def cancel(self):
        if not self.begun():
            return
        self.currentScale = None
        self._begun = False
