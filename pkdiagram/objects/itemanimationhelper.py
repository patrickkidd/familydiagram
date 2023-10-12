
from ..pyqt import QAbstractAnimation, QVariantAnimation, QParallelAnimationGroup, QBrush, QPen, Qt
from .. import util



class ItemAnimationHelper:
    """
    TODO: move Person.posAnimation and Person.opacityAnimation here too.
    """

    def initItemAnimationHelper(self):
        self._flashAnimData = {}
        self.penAnimation = QVariantAnimation()
        self.penAnimation.setDuration(util.LAYER_ANIM_DURATION_MS)
        self.penAnimation.valueChanged.connect(self.onFlashPenTick)
        self.brushAnimation = QVariantAnimation()
        self.brushAnimation.setDuration(self.penAnimation.duration())
        self.brushAnimation.valueChanged.connect(self.onFlashBrushTick)
        self.scaleAnimation = QVariantAnimation()
        self.scaleAnimation.setDuration(self.penAnimation.duration())
        self.scaleAnimation.valueChanged.connect(self.onFlashScaleTick)
        self.itemAnimationGroup = QParallelAnimationGroup()
        self.itemAnimationGroup.finished.connect(self.onFlashColorFinished)
        self.itemAnimationGroup.addAnimation(self.penAnimation)
        self.itemAnimationGroup.addAnimation(self.brushAnimation)
        self.itemAnimationGroup.addAnimation(self.scaleAnimation)

    def flash(self):
        """ flash a color to draw attention. """
        if self.itemAnimationGroup.state() == QAbstractAnimation.Running:
            self.itemAnimationGroup.stop() # premature
            # self.onAnimatedPenColorChanged(self._flashAnimData['orig_pen'])
            # self.onAnimatedBrushColorChanged(self._flashAnimData['orig_brush'])
            self.setScale(self._flashAnimData['orig_scale'])
        self._flashAnimData = {
            # 'orig_pen': self.pen().color(),
            # 'orig_brush': self.brush().color(),
            'orig_scale': self.scale(),
        }
        # self.penAnimation.setStartValue(util.FLASH_COLOR)
        self.penAnimation.setStartValue(self.pen().color()) # noop
        self.penAnimation.setEndValue(self.pen().color())
        # self.brushAnimation.setStartValue(util.FLASH_COLOR.lighter(110))
        self.brushAnimation.setStartValue(self.brush().color()) # noop
        self.brushAnimation.setEndValue(self.brush().color())
        self.scaleAnimation.setStartValue(self.scale() * util.FLASH_SCALE_DELTA)
        self.scaleAnimation.setEndValue(self.scale())
        self.itemAnimationGroup.start()

    def onAnimatedPenColorChanged(self, c):
        pass

    def onAnimatedBrushColorChanged(self, c):
        pass

    def onFlashScaleTick(self, x):
        if x is not None:
            self.setScale(x)

    def onFlashPenTick(self, c):
        pen = self.pen()
        pen.setColor(c)
        self.setPen(pen)
        self.update()

    def onFlashBrushTick(self, c):
        self.setBrush(c)
        self.update()

    def onFlashColorFinished(self):
        pass

