from .pyqt import QObject, QTime, QLineF, QPointF, QCursor
from . import util, commands


class PanZoomer(QObject):
    """ For the View. """
    
    ZOOM_THRESHOLD = 15.0
    PAN_THRESHOLD = 25
    ANIM_DURATION_MS = 200
    
    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.catchUpStartTime = QTime()
        self._reset()

    def _reset(self):
        self.crossedThreshold = False
        self.crossedPanThreshold = False
        self.crossedZoomThreshold = False
        self._animTimer = None
        self._beganTest = False
        # self.view.setInteractive(True)

    def begun(self):
        return self._animTimer is not None

    def test(self, touchPoints, zoomSceneStartScale, panSceneStartCenter):
        if not self._beganTest: # init
            self._beganTest = True
            self.firstTwoTouchIds = touchPoints[0].id(), touchPoints[1].id()
            self.firstTwoTouchPoints = touchPoints[0], touchPoints[1]
            a = touchPoints[0].scenePos()
            b = touchPoints[1].scenePos()
            self.zoomTouchStartDistance = QLineF(a, b).length()
            self.zoomSceneStartScale = zoomSceneStartScale
            self.panTouchStartCenter = QLineF(a, b).center()
            self.panSceneStartCenter = panSceneStartCenter
            self.startSceneCenter = self.view.sceneCenter()
            self.startMouseScenePos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
            self.crossedThreshold = False
            #
            self.finishedCatchUp = False
        if not self.begun() and not self.crossedThreshold: # test
            a = touchPoints[0].scenePos()
            b = touchPoints[1].scenePos()
            point0Distance = QLineF(self.firstTwoTouchPoints[0].scenePos(), a).length()
            point1Distance = QLineF(self.firstTwoTouchPoints[1].scenePos(), b).length()
            # zoom
            zoomTouchDistance = QLineF(a, b).length()
            zoomTouchScale = zoomTouchDistance / self.zoomTouchStartDistance
            self.zoomSceneScaleFactor = self.zoomSceneStartScale * zoomTouchScale
            zoomTouchDelta = abs(zoomTouchDistance - self.zoomTouchStartDistance)
            # pan
            panTouchCenter = QLineF(a, b).center()
            panTouchDelta = QLineF(self.panTouchStartCenter, panTouchCenter).length()
            if not self.crossedPanThreshold:
                self.crossedPanThreshold = panTouchDelta >= self.PAN_THRESHOLD
            if not self.crossedZoomThreshold:
                self.crossedZoomThreshold = zoomTouchDelta >= self.ZOOM_THRESHOLD
            crossed = False
            if not util.ENABLE_PINCH_PAN_ZOOM:
                if not self.crossedPanThreshold: # prioritize wheel-panning by preventing every starting if panning
                    crossed = self.crossedZoomThreshold
            else:
                crossed = (point0Distance >= self.ZOOM_THRESHOLD and point1Distance >= self.ZOOM_THRESHOLD) and \
                           (self.crossedZoomThreshold or self.crossedPanThreshold)
            return crossed
        return True

    def begin(self, touchPoints, zoomSceneStartScale, panSceneStartCenter):
        if self.begun():
            self.cancel()
        if self.test(touchPoints, zoomSceneStartScale, panSceneStartCenter):
            self._animTimer = self.startTimer(util.ANIM_TIMER_MS)
            self.catchUpStartTime.start()
            self.crossedThreshold = True
        # self.view.setInteractive(False)
        return self.crossedThreshold
    
    def update(self, touchPoints):
        if not self.begun():
            return
        elif self.firstTwoTouchIds != (touchPoints[0].id(), touchPoints[1].id()):
            self.cancel()
            return
        a = touchPoints[0].scenePos()
        b = touchPoints[1].scenePos()
        point0Distance = QLineF(self.firstTwoTouchPoints[0].scenePos(), a).length()
        point1Distance = QLineF(self.firstTwoTouchPoints[1].scenePos(), b).length()
        # zoom
        zoomTouchDistance = QLineF(a, b).length()
        zoomTouchScale = zoomTouchDistance / self.zoomTouchStartDistance
        self.zoomSceneScaleFactor = self.zoomSceneStartScale * zoomTouchScale
        zoomTouchDelta = abs(zoomTouchDistance - self.zoomTouchStartDistance)
        # pan
        panTouchCenter = QLineF(a, b).center()
        panTouchDelta = QLineF(self.panTouchStartCenter, panTouchCenter).length()
        if util.IS_IOS:
            panSpeed = 1.3
        else:
            panSpeed = 4.0
        panXScale = ((panTouchCenter.x() - self.panTouchStartCenter.x()) * panSpeed) / self.view.scene().scaleFactor()
        panYScale = ((panTouchCenter.y() - self.panTouchStartCenter.y()) * panSpeed) / self.view.scene().scaleFactor()
        self.panSceneCenter = QPointF(self.panSceneStartCenter.x() - panXScale,
                                      self.panSceneStartCenter.y() - panYScale)
        if self._animTimer is None:
            self.view.zoomAbsolute(self.zoomSceneScaleFactor)
            self.doPan()
        # # test threshold
        # if self.crossedThreshold is False and \
        #    (point0Distance >= self.ZOOM_THRESHOLD and point1Distance >= self.ZOOM_THRESHOLD) and \
        #    (zoomTouchDelta >= self.ZOOM_THRESHOLD or panTouchDelta >= self.PAN_THRESHOLD):
        #     self.catchUpStartTime.start()
        #     self.crossedThreshold = True
        # elif self.crossedThreshold and self._animTimer is None:
        #     self.view.zoomAbsolute(self.zoomSceneScaleFactor)
        #     self.doPan()
        # else:
        #     pass # animation timer is running

    def doPan(self, sceneCenter=None):
        if util.ENABLE_PINCH_PAN_ZOOM: # TODO: rename to ENABLE_PINCH_PAN_ZOOM
            if sceneCenter is None:
                sceneCenter = self.panSceneCenter
            self.view.panAbsolute(sceneCenter)
        else:
            # zoom to cursor
            currentSceneCenter = self.view.sceneCenter()
            currentMouseScenePos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
            sceneMouseDiff = self.startMouseScenePos - currentMouseScenePos
            newSceneCenter = currentSceneCenter + sceneMouseDiff
            self.view.centerOn(newSceneCenter)
        
    def timerEvent(self, e):
        """ Catch up animated. """
        if self.crossedThreshold and not self.finishedCatchUp:
            elapsed = self.catchUpStartTime.elapsed()
            if elapsed < self.ANIM_DURATION_MS:
                # catch-up animation
                keyFrameCoeff = elapsed / self.ANIM_DURATION_MS
                # scale
                zoomScaleDeltaTotal = self.zoomSceneScaleFactor - self.zoomSceneStartScale
                scale = self.zoomSceneStartScale + zoomScaleDeltaTotal * keyFrameCoeff
                self.view.zoomAbsolute(scale)
                # pan
                panSceneDeltaTotal = self.panSceneCenter - self.panSceneStartCenter
                panSceneCenter = self.panSceneStartCenter + panSceneDeltaTotal * keyFrameCoeff
                self.doPan(sceneCenter=panSceneCenter)
            else:
                self.finishedCatchUp = True
        if self.crossedThreshold and self.finishedCatchUp:
            self.view.zoomAbsolute(self.zoomSceneScaleFactor)
            self.doPan()

    def end(self):
        if self.begun():
            self.killTimer(self._animTimer)
            self.doPan()
            self.view.zoomAbsolute(self.zoomSceneScaleFactor)
        self._reset()
    
    def cancel(self):
        if self.begun():
            self.killTimer(self._animTimer)
        self._reset()
