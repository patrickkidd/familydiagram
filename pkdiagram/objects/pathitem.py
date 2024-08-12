import logging
import math
from ..pyqt import *
from .. import util
from .item import Item
from .itemanimationhelper import ItemAnimationHelper


_log = logging.getLogger(__name__)


class NotesIcon(QGraphicsPixmapItem):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPixmap(QPixmap(util.QRC + "notes-indicator.png"))
        self.setScale(0.5)

    def mousePressEvent(self, e):
        e.accept()

    def mouseDoubleClickEvent(self, e):
        e.accept()
        self.scene().onNotesIconClicked(self.parentItem())


class PathItem(util.PathItemBase, Item, ItemAnimationHelper):

    # ITEM_Z = 0

    Item.registerProperties(
        (
            {
                "attr": "itemPos",
                "type": QPointF,
                "default": QPointF(),
                "layered": True,
                "layerIgnoreAttr": "storeGeometry",
            },
        )
    )

    def __init__(self, parent=None, **kwargs):
        if "pos" in kwargs:
            kwargs["itemPos"] = kwargs["pos"]
        super().__init__(parent, **kwargs)
        self.isPathItem = True
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setPen(util.PEN)
        # self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        # self.setCacheMode(QGraphicsItem.ItemCoordinateCache)
        self.hover = False
        self._boundingRect = QRectF()
        self._isUpdatingAll = False
        self._isPathItemVisible = (
            True  # central pathway for show|hide; forces fade in|out
        )
        self._shouldShowForDateLayersAndTags = False
        # Set in the past to avoid false positives in tests
        self.lastMouseRelease = QTime.currentTime().addSecs(-60)
        self.penCapStyle = Qt.RoundCap
        self.dirtyGeometry = False
        self.boundingRectDirty = False
        self.emitDoubleClick = True
        self.initItemAnimationHelper()
        self.opacityAnimation = QPropertyAnimation(self, b"opacity")
        self.opacityAnimation.setDuration(util.LAYER_ANIM_DURATION_MS)
        self.opacityAnimation.finished.connect(self.onOpacityAnimationFinished)
        # pos
        self.posAnimation = QPropertyAnimation(self, b"pos")
        self.posAnimation.setDuration(util.LAYER_ANIM_DURATION_MS)
        # note icon
        self._notesIcon = NotesIcon(self)
        self._notesIcon.setVisible(False)
        self._notesIcon.setPos(self.notesIconPos())
        self._notesIcon.setZValue(util.NOTE_Z)
        # debug
        self._n_updateAll = 0
        self._n_onUpdateAll = 0
        self._n_updateGeometry = 0
        self._n_updatePen = 0
        self._n_updateDetails = 0

        self.installEventFilter(self)

    def eventFilter(self, o, event):
        """
        Hack only because I can't figure out what is calling deleteLater() for
        marriages (or anything for that matter?). This should work assuming that
        there should never be a deferred delete on a QGraphicsObject.
        """
        if event.type() == QEvent.DeferredDelete:
            QMessageBox.warning(None, "DeferredDelete", f"DeferredDelete event for {o}")
            _log.warning(f"DeferredDelete event for {o}")
            return True
        return super().eventFilter(o, event)

    def view(self):
        if self.scene():
            return self.scene().view()

    ## Paint animations

    def onAnimatedPenColorChanged(self, c):
        ItemAnimationHelper.onAnimatedPenColorChanged(self, c)
        self.setPenColor(c)

    def onAnimatedBrushColorChanged(self, c):
        ItemAnimationHelper.onAnimatedBrushColorChanged(self, c)
        self.setBrushColor(c)

    def startLayerAnimation(self, anim):
        """Placeholder for when scene() is None."""
        if self.scene() and (
            self.scene().isResettingSomeLayerProps()
            or (self.scene()._areActiveLayersChanging and not self.isUpdatingAll())
        ):
            self.scene().startLayerAnimation(anim)
        else:
            if isinstance(anim, QParallelAnimationGroup):
                util.test_finish_group(anim)
            elif isinstance(anim, QVariantAnimation):
                util.test_finish_anim(anim)

    def fadeToOpacity(self, x):
        if self.opacityAnimation.group():
            self.opacityAnimation.group().removeAnimation(self.opacityAnimation)
        if self.opacityAnimation.state() != self.opacityAnimation.Stopped:
            self.opacityAnimation.stop()
        if self.opacity() != x:
            self.opacityAnimation.setStartValue(self.opacity())
            self.opacityAnimation.setEndValue(x)
            if (
                not self.scene()
                or self.scene().isUpdatingAll()
                or self.isUpdatingAll()
                or util.IS_TEST
            ):
                self.onOpacityAnimationFinished()
            elif self.scene().areActiveLayersChanging():
                self.startLayerAnimation(self.opacityAnimation)
            else:
                self.opacityAnimation.start()
        if x > 0.0 and not self.isVisible():
            super().setVisible(True)

    def onOpacityAnimationFinished(self):
        if self.opacity() != self.opacityAnimation.endValue():
            # wasn't force setting for updateAll()
            self.setOpacity(self.opacityAnimation.endValue())
        if self.opacity() == 0:
            super().setVisible(False)

    def onFlashColorFinished(self):
        self.updatePen()

    def onProperty(self, prop):
        if prop.name() == "itemPos" and prop.layered and prop.get() != self.pos():
            if self.isUpdatingAll() or util.ANIM_DURATION_MS == 0:  # test
                self.setPos(prop.get())
            else:
                self.posAnimation.setStartValue(self.pos())
                self.posAnimation.setEndValue(prop.get())
                self.startLayerAnimation(self.posAnimation)
        super().onProperty(prop)

    def setItemPosNow(self, pos: QPointF):
        """
        To get around `if self.isUpdatingAll()` and set the position in the
        current layer now.

        Currently only used for AddAnythingDialog since it is the only way that
        people are added other than manually with the left toolbar.
        """
        self.setItemPos(pos)
        self.setPos(pos)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            if (
                self.scene()
                and self.scene().isMovingSomething()
                and not self.scene().areActiveLayersChanging()
            ):
                self.setItemPos(value, notify=True)
            # if self.posAnimation.state() == QAbstractAnimation.Running or \
            #     (self.scene() and (self.scene().isInitializing or self.scene().isUpdatingAll())) or \
            #     not self._useItemPos:
            #     pass
            # else:
            #     # should only be when dragging.
            #     self.setItemPos(value, notify=False)
            #     self.here(value)
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            # Disabled for performance
            # if value:
            #     dropShadow = QGraphicsDropShadowEffect(self)
            #     dropShadow.setColor(QColor(100, 100, 100, 70))
            #     dropShadow.setBlurRadius(7)
            #     dropShadow.setOffset(1)
            #     self.setGraphicsEffect(dropShadow)
            # else:
            #     self.setGraphicsEffect(None)
            self.updatePen()
            # if value:
            #     self.setZValue(self.ITEM_Z + util.SELECTED_Z_DELTA)
            # else:
            #     self.setZValue(self.ITEM_Z)
        return super().itemChange(change, value)

    ## Internal Data

    def notesIconPos(self):
        return QPointF(0, self._notesIcon.boundingRect().height() * -0.5)

    def clone(self, scene):
        ret = super().clone(scene)
        ret.setPos(self.pos())
        return ret

    @pyqtSlot(result=str)
    def itemName(self):
        return super().itemName()

    @pyqtSlot(str, result=QVariant)
    def itemProp(self, attr):
        return self.prop(attr).get()

    @pyqtSlot(result=int)
    def itemId(self):
        return self.id

    def layeredSceneBoundingRect(self, forLayers, forTags):
        ret = super().sceneBoundingRect()
        offset = None
        itemPos = self.prop("itemPos")
        if itemPos.layered:
            itemPos = itemPos.get(forLayers=forLayers)
            if itemPos is not None and self.hasTags(forTags):
                origPos = self.pos()
                ret.moveCenter(itemPos)
                offset = itemPos - origPos
        for child in self.childItems():
            if isinstance(child, PathItem) and child.isChildOf:  # hack
                continue
            childRect = child.sceneBoundingRect()
            if offset is not None:
                childRect.moveCenter(childRect.center() + offset)
            ret2 = ret | childRect
            ret = ret2
        return ret

    def shouldShowFor(self, dateTime, tags=[], layers=[]):
        """virtual"""
        return True

    def shouldShowRightNow(self):
        scene = self.scene()
        if scene:
            return self.shouldShowFor(
                scene.currentDateTime(),
                tags=scene.searchModel.tags,
                layers=scene.activeLayers(),
            )
        else:
            return False

    def updateGeometry(self):
        self._n_updateGeometry += 1

    def beginUpdateFrame(self):
        super().beginUpdateFrame()
        self._n_updateAll = 0
        self._n_onUpdateAll = 0
        self._n_updateGeometry = 0
        self._n_updatePen = 0
        self._n_updateDetails = 0

    def onUpdateAll(self):
        """Virtual"""
        self._n_onUpdateAll += 1
        self.onActiveLayersChanged()
        self.updateGeometry()
        for prop in self.props:
            if prop.layered:
                self.onProperty(prop)

    def updateAll(self):
        self._n_updateAll += 1
        if not self.scene():
            return
        self._isUpdatingAll = True
        self.onUpdateAll()
        self._isUpdatingAll = False

    def isUpdatingAll(self):
        return self._isUpdatingAll

    def onActiveLayersChanged(self):
        """Update selected state and visible state for date + tags if necessary."""
        super().onActiveLayersChanged()
        on = self.shouldShowRightNow()
        self._shouldShowForDateLayersAndTags = on
        # Don't change selection status if updating all,
        # because updateAll() should be a read-only change.
        if not self.isUpdatingAll() and (not self.isInspecting and self.isSelected()):
            self.setSelected(False)
        self.updatePathItemVisible()

    def shouldShowForDateAndLayerTags(self):
        return self._shouldShowForDateLayersAndTags

    def updatePathItemVisible(self):
        """Virtual - Final endpoint for fading to show/hide."""
        if self.shouldShowForDateAndLayerTags():
            self.setPathItemVisible(True)
        else:
            self.setPathItemVisible(False)

    def setPathItemVisible(self, on, opacity=None):
        """A show|hide replacement that fades. Should be the only way to show and hide a PathItem.
        Prevents restarting animation many times (at least) in zooms.
        """
        if on != self._isPathItemVisible or (on and opacity is not None):
            self._isPathItemVisible = on
            if on:
                if opacity is None:
                    opacity = 1.0
                self.fadeToOpacity(opacity)
            else:
                self.fadeToOpacity(0.0)

    def onCurrentDateTime(self):
        """Virtual. How is this different from onUpdateAll() ?"""
        if not self.scene():
            return
        on = self.shouldShowRightNow()
        self._shouldShowForDateLayersAndTags = on
        if self.isSelected():
            self.setSelected(False)
        self.updatePathItemVisible()
        self.updateGeometry()

    def updateDetails(self):
        """Virtual"""
        self._n_updateDetails = 0

    def updatePen(self):
        """Virtual"""
        self._n_updatePen = 0

    def mouseReleaseEvent(self, e):
        """double click edit"""
        super().mouseReleaseEvent(e)
        diff = self.lastMouseRelease.elapsed()
        self.lastMouseRelease.start()
        if self.emitDoubleClick and diff < QApplication.doubleClickInterval():
            if hasattr(self.scene(), "onItemDoubleClicked"):
                self.scene().onItemDoubleClicked(self)

    def setHover(self, on):
        if on != self.hover:
            self.hover = on
            # self.updateGeometry()
            self.updatePen()
            self.update()

    def setEmitDoubleClick(self, on):
        self.emitDoubleClick = bool(on)

    def setShowNotesIcon(self, on):
        if on != self._notesIcon.isVisible():
            self._notesIcon.setVisible(on)
