import logging
from .pyqt import (
    QWidget,
    pyqtSignal,
    QSizePolicy,
    QApplication,
    QVariant,
    QVariantAnimation,
    QAbstractAnimation,
    QTimer,
    QRect,
    QRectF,
    QPoint,
    QPointF,
    QActionGroup,
    QAction,
    QQuickWidget,
    QJSValue,
    QMainWindow,
    Qt,
)
from .view import View
from . import util, objects, commands, Person, Marriage, Emotion, Event, LayerItem
from . import addeventdialog, addemotiondialog
from .addanythingdialog import AddAnythingDialog
from .graphicaltimelineview import GraphicalTimelineView
from .widgets.drawer import Drawer
from .models import SceneModel
from .qmldrawer import QmlDrawer


log = logging.getLogger(__name__)


class CaseProperties(QmlDrawer):
    QmlDrawer.registerQmlMethods(
        [
            {"name": "clearSearch"},
            {"name": "inspectEvents"},
            {"name": "scrollSettingsToBottom"},
        ]
    )

    def show(self, items=[], tab=None, **kwargs):
        if items and items[0].isEvent:
            self.inspectEvents(items)
            items = []
        super().show(items, tab, **kwargs)


class DocumentView(QWidget):
    """
    Contains the View and drawers to edit a document.
    - Anything having to do with wrangling views and drawers goes in here.
    - Anything about actions, verbs, and connecting components goes in DocumentController
    """

    graphicalTimelineExpanded = pyqtSignal(bool)
    qmlSelectionChanged = pyqtSignal()

    def __init__(self, parent: QMainWindow, session):
        super().__init__(parent.centralWidget())
        self.session = session
        self.ui = parent.ui
        self.scene = None
        self.isAnimatingDrawer = False
        self._isInitializing = True
        self._isReloadingCurrentDiagram = False

        self.view = View(self, parent.ui)
        self.view.escape.connect(self.onEscape)

        # This one shows/hides it all together.
        # The timeline itself manages expansion/contraction
        self.graphicalTimelineShim = QWidget(
            self
        )  # allow hiding with blind effect without changing height of GTL'
        self.graphicalTimelineShim.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        self.graphicalTimelineShim.setObjectName("graphicalTimelineShim")
        # show over the graphicalTimelineShim just like the drawers to allow expanding to fuull screen
        self.graphicalTimelineView = GraphicalTimelineView(self)
        self.graphicalTimelineView.expandedChanged.connect(
            self.graphicalTimelineExpanded
        )
        self.graphicalTimelineView.searchButton.clicked.connect(
            self.ui.actionShow_Search.trigger
        )
        self.graphicalTimelineAnimation = QVariantAnimation(self)
        self.graphicalTimelineAnimation.setDuration(util.ANIM_DURATION_MS)
        self.graphicalTimelineAnimation.setEasingCurve(util.ANIM_EASING)
        self.graphicalTimelineAnimation.valueChanged.connect(
            self.onShowGraphicalTimelineTick
        )
        self.graphicalTimelineAnimation.finished.connect(
            self.onShowGraphicalTimelineFinished
        )

        from pkdiagram.documentcontroller import DocumentController

        self.controller = DocumentController(self)

        ## Just sits under the drawer to move the view over.
        ## Allows the drawer to be parented to the DocumentView
        ## while still appearing to be a sibling of the View
        self.drawerShim = QWidget(self)
        self.drawerShim.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.drawerShim.setObjectName("drawerShim")
        # self.drawerShimAnimation = QVariantAnimation(self)
        # self.drawerShimAnimation.setDuration(util.ANIM_DURATION_MS)
        # self.drawerShimAnimation.setEasingCurve(util.ANIM_EASING)
        # self.drawerShimAnimation.valueChanged.connect(self.onDrawerAnimationTick)
        # self.drawerShimAnimation.finished.connect(self.onDrawerAnimationFinished)

        # property sheets
        self.sceneModel = SceneModel(self, session=session)
        self.sceneModel.setObjectName("documentView_sceneModel")
        self.caseProps = CaseProperties(
            "qml/CaseProperties.qml",
            parent=self,
            objectName="caseProps",
            sceneModel=self.sceneModel,
        )
        self.caseProps.findItem("stack").currentIndexChanged.connect(
            self.onCasePropsTabChanged
        )
        self.personProps = QmlDrawer(
            "qml/PersonProperties.qml",
            parent=self,
            propSheetModel="personModel",
            objectName="personProps",
            sceneModel=self.sceneModel,
        )
        self.marriageProps = QmlDrawer(
            "qml/MarriageProperties.qml",
            parent=self,
            propSheetModel="marriageModel",
            objectName="marriageProps",
            sceneModel=self.sceneModel,
        )
        self.emotionProps = QmlDrawer(
            "qml/EmotionPropertiesDrawer.qml",
            parent=self,
            resizable=False,
            propSheetModel="emotionModel",
            objectName="emotionProps",
            sceneModel=self.sceneModel,
        )
        self.layerItemProps = QmlDrawer(
            "qml/LayerItemProperties.qml",
            parent=self,
            propSheetModel="layerItemModel",
            objectName="layerItemProps",
            sceneModel=self.sceneModel,
            resizable=False,
        )
        #
        self.ignoreDrawerAnim = False
        self.currentDrawer = None
        self.caseProps.qml.rootObject().clearSearch.connect(
            self.controller.onClearSearch
        )
        self.addAnythingDialog = AddAnythingDialog(
            parent=self, sceneModel=self.sceneModel
        )
        self.addEventDialog = addeventdialog.AddEventDialog(
            self, sceneModel=self.sceneModel
        )
        self.addEventDialog.hide(animate=False)
        self.addEmotionDialog = addemotiondialog.AddEmotionDialog(
            self, sceneModel=self.sceneModel
        )
        self.addEmotionDialog.hide(animate=False)
        self.emotionProps.stackUnder(self.addEventDialog)
        self.emotionProps.stackUnder(self.addEmotionDialog)
        self.personProps.hide(animate=False)
        self.marriageProps.hide(animate=False)
        self.emotionProps.hide(animate=False)
        self.layerItemProps.hide(animate=False)
        self.drawers = [
            self.addAnythingDialog,
            self.caseProps,
            self.personProps,
            self.marriageProps,
            self.emotionProps,
            self.layerItemProps,
            self.addEventDialog,
            self.addEmotionDialog,
        ]
        for drawer in self.drawers:
            drawer.canInspectChanged.connect(self.qmlSelectionChanged.emit)
            drawer.manuallyResized.connect(self.onDrawerManuallyResized)
        self._forceSceneUpdate = False  # fix for scene update bug

        self.addAnythingDialog.submitted.connect(self.controller.onAddAnythingSubmitted)

        self.graphicalTimelineShim.lower()
        self.drawerShim.lower()
        self.onApplicationPaletteChanged()
        QApplication.instance().paletteChanged.connect(self.onApplicationPaletteChanged)
        self._isInitializing = False

    def init(self):
        self.controller.init()
        self.controller.updateActions()

    def onApplicationPaletteChanged(self):
        self.drawerShim.setStyleSheet("background-color: %s " % util.QML_CONTROL_BG)

    def setReloadingCurrentDiagram(self, on):
        """Not currently used, but saved for later."""
        self._isReloadingCurrentDiagram = on

    def isReloadingCurrentDiagram(self):
        """Not currently used, but saved for later."""
        return self._isReloadingCurrentDiagram

    def setScene(self, scene):
        self._isInitializing = True
        self.sceneModel.scene = scene
        self.graphicalTimelineView.setScene(scene)
        self.emotionProps.hide(animate=False)
        self.layerItemProps.hide(animate=False)
        self.marriageProps.hide(animate=False)
        self.personProps.hide(animate=False)
        self.caseProps.hide(animate=False)
        self.addAnythingDialog.hide(animate=False)
        self.currentDrawer = None
        self.controller.setScene(scene)
        if self.scene:
            self.scene.propertyChanged[objects.Property].disconnect(
                self.onSceneProperty
            )
            self.scene.selectionChanged.disconnect(self.onSceneSelectionChanged)
            self.sceneModel.addEvent[QVariant, QVariant].disconnect(self.onAddEvent)
            self.sceneModel.addEmotion.disconnect(self.onAddEmotion)
            self.sceneModel.addEmotion[QVariant].disconnect(self.onAddEmotion)
            self.sceneModel.inspectItem[int].disconnect(
                self.controller.onInspectItemById
            )
        self.scene = scene
        if scene:
            self.scene.propertyChanged[objects.Property].connect(self.onSceneProperty)
            self.scene.selectionChanged.connect(self.onSceneSelectionChanged)
            self.sceneModel.addEvent[QVariant, QVariant].connect(self.onAddEvent)
            self.sceneModel.addEmotion.connect(self.onAddEmotion)
            self.sceneModel.addEmotion[QVariant].connect(self.onAddEmotion)
            self.sceneModel.inspectItem[int].connect(self.controller.onInspectItemById)
            if self.scene.hideDateSlider():
                self.graphicalTimelineShim.setFixedHeight(0)
            else:
                self.graphicalTimelineShim.setFixedHeight(
                    util.GRAPHICAL_TIMELINE_SLIDER_HEIGHT
                )
            self.drawerShim.setFixedWidth(0)
        self.view.setScene(scene)
        self.addAnythingDialog.setScene(scene)
        self.caseProps.setScene(scene)
        self.addEventDialog.setScene(scene)
        self.addEmotionDialog.setScene(scene)
        self.personProps.setScene(scene)
        self.emotionProps.setScene(scene)
        self.layerItemProps.setScene(scene)
        self.marriageProps.setScene(scene)
        self.updateSceneStopOnAllEvents()
        self.session.refreshAllProperties()
        self.adjust()
        self._isInitializing = False

    def onSceneProperty(self, prop):
        if prop.name() == "hideDateSlider":
            self.setShowGraphicalTimeline(not prop.get())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.adjust()
        self._forceSceneUpdate = True

    def adjust(self, drawerAnimating=False):
        self.view.resize(
            self.width() - self.drawerShim.width(),
            self.height() - self.graphicalTimelineShim.height(),
        )
        self.drawerShim.setGeometry(
            self.width() - self.drawerShim.width(),
            0,
            self.drawerShim.width(),
            self.height(),
        )
        self.graphicalTimelineShim.setGeometry(
            0,
            self.graphicalTimelineShim.height(),
            self.view.width(),
            self.graphicalTimelineShim.height(),
        )
        if self.graphicalTimelineView.state == self.graphicalTimelineView.CONTRACTED:
            self.graphicalTimelineView.setGeometry(
                0,
                self.height() - self.graphicalTimelineShim.height(),
                self.graphicalTimelineShim.width(),
                self.graphicalTimelineShim.height(),
            )
        elif self.graphicalTimelineView.state == self.graphicalTimelineView.EXPANDED:
            self.graphicalTimelineView.setGeometry(
                0, 0, self.graphicalTimelineShim.width(), self.height()
            )
        self.graphicalTimelineView.adjust(freezeScroll=drawerAnimating)
        self.view.adjust()
        if not self.isAnimatingDrawer:
            for drawer in self.drawers:
                drawer.adjust()

    ## Non-Verbal Internal Events

    def lockEditor(self):
        self.setEnabled(False)

    def unlockEditor(self):
        self.setEnabled(True)

    ## Drawers

    def setCurrentDrawer(self, drawer, **kwargs):
        """Might cancel"""
        # for d in self.drawers: # close all secondary drawers
        #     if d.isOverDrawer:
        #         d.hide()
        if self.currentDrawer and not self.currentDrawer.canClose():
            return
        was = self.currentDrawer
        self.currentDrawer = drawer
        if was is drawer and was is not None:  # same drawer, new data
            items = kwargs.get("items", None)
            tab = kwargs.get("tab", None)
            if (
                items is not None
                and tab is not None
                and was.propSheetModel
                and was.rootProp(was.propSheetModel).items == items
            ):
                # same drawer new data
                was.setCurrentTab(tab)
            else:
                if not "tab" in kwargs:
                    kwargs["tab"] = drawer.currentTab()
                self.ignoreDrawerAnim = True
                was.hide(callback=lambda: drawer.show(**kwargs), swapping=True)
        elif was is not drawer and was and drawer:  # new drawer
            self.ignoreDrawerAnim = True
            # was.hide(callback=lambda: drawer.show(**kwargs))
            if not "tab" in kwargs and not drawer in (
                self.addEventDialog,
                self.addEmotionDialog,
            ):
                kwargs["tab"] = drawer.currentTab()
            was.hide()
            drawer.show(**kwargs)
        elif was and drawer is None:  # just closing drawer
            was.hide()
        elif drawer is not None:  # just opening drawer
            drawer.show(**kwargs)
        if self.currentDrawer is None:
            self.ignoreDrawerAnim = False
        # Attempt to fix a bug where scene wouldn't update when hiding drawer.
        self.updateSceneStopOnAllEvents()

        def doSceneUpdate():
            if self.scene:
                self.scene.update()

        QTimer.singleShot(1, doSceneUpdate)

    def inspectSelection(self, selection=None, tab=None):
        """Can only inspect what is visible. `tab` is only passed for MW tab-shortcuts."""
        if selection is None:
            selection = [i for i in self.scene.selectedItems() if i.isVisible()]
        people = [i for i in selection if isinstance(i, Person)]
        marriages = [i for i in selection if isinstance(i, Marriage)]
        emotions = [i for i in selection if isinstance(i, Emotion)]
        events = [i for i in selection if isinstance(i, Event)]
        layerItems = [i for i in selection if isinstance(i, LayerItem)]
        if people:
            if tab is None and self.currentDrawer is self.personProps:
                tab = self.personProps.currentTab()
            self.setCurrentDrawer(self.personProps, items=people, tab=tab)
            commands.trackView("Edit person")
        elif len(marriages) == 1:
            if tab is None and self.currentDrawer is self.marriageProps:
                tab = self.marriageProps.currentTab()
            self.setCurrentDrawer(self.marriageProps, items=marriages, tab=tab)
            commands.trackView("Edit marriage")
        elif emotions:
            if tab is None and self.currentDrawer is self.emotionProps:
                tab = self.emotionProps.currentTab()
            self.setCurrentDrawer(self.emotionProps, items=emotions, tab=tab)
            commands.trackView("Edit emotion")
        elif events:
            if tab is None and self.currentDrawer is self.caseProps:
                tab = self.eventProps.currentTab()
            self.setCurrentDrawer(self.caseProps, items=events, tab="timeline")
            commands.trackView("Edit event")
        elif layerItems:
            if tab is None and self.currentDrawer is self.layerItemProps:
                tab = self.layerItemProps.currentTab()
            self.setCurrentDrawer(self.layerItemProps, items=layerItems, tab=tab)
            commands.trackView("Edit layer item")

    def onAddAnything(self):
        if self.currentDrawer == self.addAnythingDialog:
            self.setCurrentDrawer(None)
        else:
            self.addAnythingDialog.clear()
            self.addAnythingDialog.setExistingPeopleA(self.scene.selectedPeople())
            self.setCurrentDrawer(self.addAnythingDialog)

    def onAddEvent(self, parent=None, rootItem=None):
        if isinstance(parent, QJSValue):
            parent = parent.toVariant()[0]
            if parent.isScene:
                parent = None
        if parent and self.currentDrawer:
            if self.currentDrawer is self.caseProps:
                returnTo = (self.currentDrawer, None)
            elif self.currentDrawer.propSheetModel:
                returnTo = (
                    self.currentDrawer,
                    self.currentDrawer.rootProp(
                        self.currentDrawer.propSheetModel
                    ).items,
                )
        elif not parent and rootItem:
            returnTo = (self.currentDrawer, None)
        else:
            returnTo = None

        if not parent:  # add to current [single] selection
            selection = self.scene.selectedItems()
            people = []
            marriages = []
            for item in selection:
                if isinstance(item, Person):
                    people.append(item)
                elif isinstance(item, Marriage):
                    marriages.append(item)
            if len(people) == 1:
                parent = people[0]
            elif len(marriages) == 1:
                parent = marriages[0]
        self.setCurrentDrawer(self.addEventDialog, parent=parent, returnTo=returnTo)

    def onAddEmotion(self, parent=None):
        if parent and self.currentDrawer:
            if self.currentDrawer is self.caseProps:
                returnTo = (self.currentDrawer, None)
            elif self.currentDrawer.propSheetModel:
                returnTo = (
                    self.currentDrawer,
                    self.currentDrawer.rootProp(
                        self.currentDrawer.propSheetModel
                    ).items,
                )
        else:
            returnTo = None
        personA = None
        personB = None
        if not util.isInstance(
            parent, "Scene"
        ):  # don't init people when scene passed (from TLView)
            people = self.scene.selectedPeople()
            if personA is False:
                personA = None
            personB = None
            if not personA and len(people) in [1, 2]:
                personA = people[0]
            if not personB and len(people) == 2:
                personB = people[1]
        self.setCurrentDrawer(
            self.addEmotionDialog, personA=personA, personB=personB, returnTo=returnTo
        )

    def onSceneSelectionChanged(self):
        if (
            self.currentDrawer is self.caseProps or self.view.dontInspect
        ):  # dontInspect: edge cases
            return
        if self.controller._ignoreSelectionChanges:
            return
        selection = [item for item in self.scene.selectedItems() if item.isVisible()]
        if self.currentDrawer and selection:
            self.inspectSelection(selection)
        elif self.currentDrawer:
            if not self.currentDrawer in [self.addEventDialog, self.addEmotionDialog]:
                self.setCurrentDrawer(None)

    def onCasePropsTabChanged(self):
        self.updateSceneStopOnAllEvents()

    def updateSceneStopOnAllEvents(self):
        if self.scene:  # redundnant?
            if (
                self.currentDrawer is self.caseProps
                and self.caseProps.currentTab() == "timeline"
            ):
                isTimelineShown = True
            else:
                isTimelineShown = False
            self.scene.setStopOnAllEvents(isTimelineShown)
            self.graphicalTimelineView.update()

    def onEscape(self):
        if self.currentDrawer:
            for (
                drawer
            ) in (
                self.drawers
            ):  # cycle through them as a stack to catch secondary-drawers
                if drawer.isVisible():
                    self.setCurrentDrawer(None)
                    return True
        elif self.graphicalTimelineView.isExpanded():
            self.graphicalTimelineView.setExpanded(False)

    def adjustDrawerShim(self, drawer, progress):
        if not self.ignoreDrawerAnim:
            if drawer.showing:
                width = drawer.WIDTH * progress
            elif drawer.hiding:
                width = drawer.WIDTH * (1 - progress)
            else:
                return
            self.drawerShim.setFixedWidth(round(width))
            # uncommenting this will force the toolbar to stay put, which hides it when the drawer is shown.
            # I didn't like this so I disabled this to make the move with the drawer.
            # self.view.forceRightRBOffRightEdge_x = self.drawerShim.width()
            self.adjust(drawerAnimating=True)

    def onDrawerAnimationStart(self, drawer, action, progress):
        """action == 'showing' | 'hiding'"""
        if self._isInitializing:
            return
        self.isAnimatingDrawer = True
        self.adjustDrawerShim(drawer, progress)
        self._forceSceneUpdate = True

    def onDrawerAnimationTick(self, drawer, progress):
        if self._isInitializing:
            return
        self.adjustDrawerShim(drawer, progress)
        if (
            self.scene and drawer.shrinking
        ):  # scene wasn't updating when going from expanded -> shrinking
            self.scene.update()

    def onDrawerAnimationFinished(self, drawer, progress):
        if self._isInitializing:
            return
        self.adjustDrawerShim(drawer, progress)
        if not self.currentDrawer:
            self.view.forceRightRBOffRightEdge_x = None
        self.isAnimatingDrawer = False

    def onDrawerManuallyResized(self):
        """Attempt to fix bug where scene wouldn't fully update when
        expanded drawer was shown and then manually shrunk. So just
        update the scene on the first manual resize frame."""
        if self.scene and self._forceSceneUpdate:
            self._forceSceneUpdate = False
            self.scene.update()

    def ___zoomToItem(self, item=None, items=None):
        """Center on one or more items
        Kind of a cool idea, so leaving here for now.
        """
        self.origSceneRect = self.sceneRect()
        newViewableRect = self.mapToScene(
            QRect(0, 0, self.width() - widgets.Drawer.WIDTH, self.height())
        ).boundingRect()
        newViewableCenter = newViewableRect.center()
        xOffset = self.origSceneRect.center().x() - newViewableRect.center().x()
        if item:  # center on item
            allBoundingRect = item.boundingRect() | item.childrenBoundingRect()
            newCenter = item.mapToScene(allBoundingRect.center())
            newSceneRect = QRectF(self.origSceneRect)
            newSceneRect.moveCenter(QPointF(newCenter.x() + xOffset, newCenter.y()))
        elif items:
            rect = QRectF()
            for item in items:
                rect |= item.sceneBoundingRect()
            newCenter = rect.center()
            newSceneRect = QRectF(self.origSceneRect)
            newSceneRect.moveCenter(QPointF(newCenter.x() + xOffset, newCenter.y()))
        else:  # center on entire screen
            newSceneRect = self.scene.itemsBoundingRect()
            log.debug(newSceneRect)
            log.debug(self.origSceneRect)
        self.zoomFit(newSceneRect)

    ## Graphical Timeline

    def setShowGraphicalTimeline(self, on):
        self.graphicalTimelineAnimation.stop()
        if on:
            self.graphicalTimelineAnimation.setStartValue(0)
            self.graphicalTimelineAnimation.setEndValue(
                util.GRAPHICAL_TIMELINE_SLIDER_HEIGHT
            )
        else:
            self.graphicalTimelineAnimation.setStartValue(
                util.GRAPHICAL_TIMELINE_SLIDER_HEIGHT
            )
            self.graphicalTimelineAnimation.setEndValue(0)
        self.graphicalTimelineAnimation.start()
        if on:
            commands.trackView("Show Graphical Timeline")
        else:
            commands.trackView("Hide Graphical Timeline")

    def onShowGraphicalTimelineTick(self, height):
        if self.graphicalTimelineAnimation.state() == QAbstractAnimation.Running:
            self.graphicalTimelineShim.setFixedHeight(height)
            self.adjust()

    def onShowGraphicalTimelineFinished(self):
        pass

    def canDeleteSelection(self):
        return (
            QApplication.focusWidget() is self
            and (self.scene and self.scene.selectedItems())
            and (self.currentDrawer is None or self.currentDrawer is self.caseProps)
        )

    ## Actions

    def showDiagram(self):
        count = 0
        while self.onEscape() and count < 4:
            count += 1
        if self.scene:
            self.scene.update()

    def showTimeline(self):
        """Set current tab, otherwise toggle."""
        if self.currentDrawer == self.caseProps:
            if self.caseProps.currentTab() == "timeline":
                self.setCurrentDrawer(None)
            else:
                self.caseProps.setCurrentTab("timeline")
        else:
            self.setCurrentDrawer(self.caseProps, tab="timeline")

    def showSearch(self):
        if self.currentDrawer == self.caseProps:
            if self.caseProps.currentTab() == "search":
                self.setCurrentDrawer(None)
            else:
                self.caseProps.setCurrentTab("search")
                self.caseProps.setFocus(Qt.MouseFocusReason)
                self.caseProps.findItem("descriptionEdit").forceActiveFocus()
        else:
            self.setCurrentDrawer(self.caseProps, tab="search")

    def showSettings(self):
        if self.currentDrawer == self.caseProps:
            if self.caseProps.currentTab() == "settings":
                self.setCurrentDrawer(None)
            else:
                self.caseProps.setCurrentTab("settings")
        else:
            self.setCurrentDrawer(self.caseProps, tab="settings")

    def showUndoHistory(self):
        pass

    def setExpandGraphicalTimeline(self, on):
        self.graphicalTimelineView.setExpanded(on)
