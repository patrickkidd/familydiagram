import logging

from pkdiagram.pyqt import (
    pyqtSignal,
    QWidget,
    QSizePolicy,
    QApplication,
    QVariantAnimation,
    QTimer,
    QRect,
    QRectF,
    QPoint,
    QPointF,
    QMainWindow,
)
from pkdiagram import util
from pkdiagram.scene import Person, Marriage, Emotion, Event, LayerItem
from pkdiagram.widgets import TimelineCallout, Drawer
from pkdiagram.views import EventForm, SearchDialog, QmlDrawer, CaseProperties
from pkdiagram.documentview import (
    View,
    QmlEngine,
    GraphicalTimelineView,
    RightDrawerView,
    DocumentController,
)


log = logging.getLogger(__name__)


class DocumentView(QWidget):
    """
    Contains the View and drawers to edit a document.
    - Anything having to do with wrangling views and drawers goes in here.
    - Anything about actions, verbs, and connecting components goes in DocumentController

    Would be a single document window in a multi-document editor.
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
        self._settingCurrentDrawer = False

        self._qmlEngine = QmlEngine(session, parent)
        self.sceneModel = self._qmlEngine.sceneModel
        self.searchModel = self._qmlEngine.searchModel
        self.timelineModel = self._qmlEngine.timelineModel
        self.peopleModel = self._qmlEngine.peopleModel
        self.accessRightsModel = self._qmlEngine.accessRightsModel
        self.eventSelectionModel = self._qmlEngine.eventSelectionModel

        self.view = View(self, parent.ui)

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

        # Property sheets

        self.caseProps = CaseProperties(
            self._qmlEngine,
            "qml/CaseProperties.qml",
            parent=self,
            objectName="caseProps",
        )
        self.caseProps.qmlInitialized.connect(self.onCasePropsInit)
        self.personProps = QmlDrawer(
            self._qmlEngine,
            "qml/PersonProperties.qml",
            parent=self,
            propSheetModel="personModel",
            objectName="personProps",
        )
        self.marriageProps = QmlDrawer(
            self._qmlEngine,
            "qml/MarriageProperties.qml",
            parent=self,
            propSheetModel="marriageModel",
            objectName="marriageProps",
        )
        self.emotionProps = QmlDrawer(
            self._qmlEngine,
            "qml/EmotionProperties.qml",
            parent=self,
            resizable=False,
            propSheetModel="emotionModel",
            objectName="emotionProps",
        )
        self.layerItemProps = QmlDrawer(
            self._qmlEngine,
            "qml/LayerItemProperties.qml",
            parent=self,
            propSheetModel="layerItemModel",
            objectName="layerItemProps",
            resizable=False,
        )
        #
        self.ignoreDrawerAnim = False
        self.currentDrawer = None
        self.eventForm = EventForm(self._qmlEngine, self)
        QWidget.hide(self.caseProps)
        QWidget.hide(self.personProps)
        QWidget.hide(self.marriageProps)
        QWidget.hide(self.emotionProps)
        QWidget.hide(self.layerItemProps)
        self.drawers = [
            self.eventForm,
            self.caseProps,
            self.personProps,
            self.marriageProps,
            self.emotionProps,
            self.layerItemProps,
        ]
        for drawer in self.drawers:
            drawer.canInspectChanged.connect(self.qmlSelectionChanged.emit)
            drawer.manuallyResized.connect(self.onDrawerManuallyResized)
            drawer.qmlFocusItemChanged.connect(self.controller.onQmlFocusItemChanged)

        def _init_personProps():
            self.personProps.qml.rootObject().editBirthEvent.connect(
                self.onEditPersonBirthEvent
            )
            self.personProps.qml.rootObject().editDeathEvent.connect(
                self.onEditPersonDeathEvent
            )

        self.personProps.qmlInitialized.connect(_init_personProps)
        self.emotionProps.qmlInitialized.connect(
            lambda: self.emotionProps.qml.rootObject().editEvent.connect(
                self.onEditEmotionEvent
            )
        )
        self.eventForm.doneEditing.connect(self.controller.onEventFormDoneEditing)
        self._forceSceneUpdate = False  # fix for scene update bug

        # This one shows/hides it all together.
        # The timeline itself manages expansion/contraction
        self.graphicalTimelineShim = QWidget(
            self
        )  # allow hiding with blind effect without changing height of GTL'
        self.graphicalTimelineShim.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        self.graphicalTimelineShim.setObjectName("graphicalTimelineShim")
        self.graphicalTimelineShim.setFixedHeight(0)
        # show over the graphicalTimelineShim just like the drawers to allow expanding to fuull screen
        self.graphicalTimelineView = GraphicalTimelineView(
            self.searchModel, self.eventSelectionModel, self
        )
        self.graphicalTimelineView.expandedChanged.connect(
            self.graphicalTimelineExpanded
        )
        self.graphicalTimelineView.searchButton.clicked.connect(
            self.ui.actionFind.trigger
        )
        self.graphicalTimelineView.inspectButton.clicked.connect(
            self.ui.actionInspect.trigger
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

        self.graphicalTimelineCallout = TimelineCallout(self)
        self.graphicalTimelineCallout.clicked.connect(self.onShowDateTimeOnTimeline)

        self.searchDialog = SearchDialog(self._qmlEngine, self.dialogParent())
        self.searchDialog.setObjectName("searchDialog")

        # Init

        # # delay-init qml widgets
        # # self._nextQmlInit = 0
        # # if util.QML_LAZY_DELAY_INTERVAL_MS:
        # #     QTimer.singleShot(util.QML_LAZY_DELAY_INTERVAL_MS * 2, self._nextDelayedQmlInit) # after view animation
        # for w in self.drawers:
        #     w.checkInitQml()

        self.graphicalTimelineShim.lower()
        self.drawerShim.lower()
        self.onApplicationPaletteChanged()
        QApplication.instance().paletteChanged.connect(self.onApplicationPaletteChanged)
        self._isInitializing = False

    # def _nextDelayedQmlInit(self):
    #     """ Stagger lazy init of qml widgets over time. """
    #     if self._nextQmlInit < len(self.drawers) and not self.isAnimating():
    #         drawer = self.drawers[self._nextQmlInit]
    #         drawer.checkInitQml()
    #         self.here(drawer._qmlSource)
    #         self._nextQmlInit += 1
    #     if self._nextQmlInit < len(self.drawers):
    #         QTimer.singleShot(util.QML_LAZY_DELAY_INTERVAL_MS, self._nextDelayedQmlInit)

    def init(self):
        self.controller.init()
        self.controller.updateActions()

    def deinit(self):
        self.controller.deinit()
        self.caseProps.deinit()
        self.personProps.deinit()
        self.marriageProps.deinit()
        self.emotionProps.deinit()
        self.layerItemProps.deinit()
        self.eventForm.deinit()
        self.searchDialog.deinit()
        self._qmlEngine.deinit()

    def onCasePropsInit(self):
        self.timelineSelectionModel = self.caseProps.rootProp("timelineView").property(
            "selectionModel"
        )
        self.caseProps.findItem("stack").currentIndexChanged.connect(
            self.onCasePropsTabChanged
        )

    def qmlEngine(self):
        return self._qmlEngine

    def dialogParent(self) -> QWidget:
        w = self
        while w.parent():
            w = w.parent()
        return w

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
        self.graphicalTimelineView.setScene(scene)
        QWidget.hide(self.caseProps)
        QWidget.hide(self.personProps)
        QWidget.hide(self.marriageProps)
        QWidget.hide(self.emotionProps)
        QWidget.hide(self.layerItemProps)
        self.eventForm.hide(animate=False)
        self.currentDrawer = None
        self.controller.setScene(None)
        if self.scene:
            self.scene.selectionChanged.disconnect(self.onSceneSelectionChanged)
            self.sceneModel.inspectItem[int].disconnect(
                self.controller.onInspectItemById
            )
        self.scene = scene
        self._qmlEngine.setScene(scene)
        if scene:
            self.scene.selectionChanged.connect(self.onSceneSelectionChanged)
            self.sceneModel.inspectItem[int].connect(self.controller.onInspectItemById)
            if self.scene.hideDateSlider() or self.timelineModel.rowCount() == 0:
                self.graphicalTimelineShim.setFixedHeight(0)
            else:
                self.graphicalTimelineShim.setFixedHeight(
                    util.GRAPHICAL_TIMELINE_SLIDER_HEIGHT
                )
            self.drawerShim.setFixedWidth(0)
        self.view.setScene(scene)
        self.eventForm.setScene(scene)
        self.caseProps.setScene(scene)
        self.personProps.setScene(scene)
        self.emotionProps.setScene(scene)
        self.layerItemProps.setScene(scene)
        self.marriageProps.setScene(scene)
        self.updateSceneStopOnAllEvents()
        self.session.refreshAllProperties()
        self.adjust()
        self.controller.setScene(scene)
        self._isInitializing = False

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
        self.updateTimelineCallout()
        if not self.isAnimatingDrawer:
            for drawer in self.drawers:
                drawer.adjust()

    def isGraphicalTimelineShown(self):
        return (
            self.graphicalTimelineShim.height() == util.GRAPHICAL_TIMELINE_SLIDER_HEIGHT
        )

    def updateTimelineCallout(self):
        if not self.scene:
            self.graphicalTimelineCallout.hide()
            return
        elif not self.scene.currentDateTime():
            self.graphicalTimelineCallout.hide()
            return
        elif not self.isGraphicalTimelineShown():
            self.graphicalTimelineCallout.hide()
            return
        events = self.timelineModel.eventsAt(self.scene.currentDateTime())
        self.graphicalTimelineCallout.setEvents(events)
        canvas = self.graphicalTimelineView.timeline.canvas
        if events and canvas.isSlider():
            cursorRect_local = canvas.currentDateTimeIndicatorRect()
            cursorPos = self.mapTo(
                self,
                cursorRect_local.toRect().center(),
                # + QPoint(0, int(cursorRect_local.height() * -0.5)),
            )
            self.graphicalTimelineCallout.move(
                QPoint(
                    int(
                        cursorPos.x()
                        - self.graphicalTimelineCallout.width() * 0.25
                        - util.CURRENT_DATE_INDICATOR_WIDTH
                    ),
                    int(
                        self.height()
                        - self.graphicalTimelineView.height()
                        - self.graphicalTimelineCallout.height()
                    ),
                )
            )
            # self.graphicalTimelineCallout.setZIndex()
            self.graphicalTimelineCallout.show()
        else:
            self.graphicalTimelineCallout.hide()

    def onShowDateTimeOnTimeline(self):
        self.showTimeline(dateTime=self.scene.currentDateTime())

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

        # To basically implement an exclusive QActionGroup for the actions below
        if self._settingCurrentDrawer:
            return
        self._settingCurrentDrawer = True

        if drawer != self.eventForm and self.view.ui.actionAdd_Anything.isChecked():
            self.view.ui.actionAdd_Anything.setChecked(False)

        if self.view.ui.actionShow_Timeline.isChecked() and (
            drawer != self.caseProps
            or kwargs.get("tab") != RightDrawerView.Timeline.value
        ):
            self.view.ui.actionShow_Timeline.setChecked(False)

        if self.view.ui.actionShow_Settings.isChecked() and (
            drawer != self.caseProps
            or kwargs.get("tab") != RightDrawerView.Settings.value
        ):
            self.view.ui.actionShow_Settings.setChecked(False)

        if self.view.ui.actionShow_Copilot.isChecked() and (
            drawer != self.caseProps
            or kwargs.get("tab") != RightDrawerView.Copilot.value
        ):
            self.view.ui.actionShow_Copilot.setChecked(False)

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
            elif was is drawer and tab != drawer.currentTab():
                drawer.setCurrentTab(tab)
            else:
                if not "tab" in kwargs:
                    kwargs["tab"] = drawer.currentTab()
                self.ignoreDrawerAnim = True
                was.hide(callback=lambda: drawer.show(**kwargs), swapping=True)
        elif was is not drawer and was and drawer:  # new drawer
            self.ignoreDrawerAnim = True
            # was.hide(callback=lambda: drawer.show(**kwargs))
            if not "tab" in kwargs:
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
        self._settingCurrentDrawer = False

    def inspectSelection(self, selection=None, tab=None):
        """Can only inspect what is visible. `tab` is only passed for MW tab-shortcuts."""
        if selection is None:
            selection = [i for i in self.scene.selectedItems() if i.isVisible()]
        people = [i for i in selection if isinstance(i, Person)]
        marriages = [i for i in selection if isinstance(i, Marriage)]
        emotions = [i for i in selection if isinstance(i, Emotion)]
        layerItems = [i for i in selection if isinstance(i, LayerItem)]
        if people:
            if tab is None and self.currentDrawer is self.personProps:
                tab = self.personProps.currentTab()
            self.setCurrentDrawer(self.personProps, items=people, tab=tab)
            self.session.trackView("Edit person")
        elif len(marriages) == 1:
            if tab is None and self.currentDrawer is self.marriageProps:
                tab = self.marriageProps.currentTab()
            self.setCurrentDrawer(self.marriageProps, items=marriages, tab=tab)
            self.session.trackView("Edit marriage")
        elif emotions:
            if tab is None and self.currentDrawer is self.emotionProps:
                tab = self.emotionProps.currentTab()
            self.setCurrentDrawer(self.emotionProps, items=emotions, tab=tab)
            self.session.trackView("Edit emotion")
        elif layerItems:
            if tab is None and self.currentDrawer is self.layerItemProps:
                tab = self.layerItemProps.currentTab()
            self.setCurrentDrawer(self.layerItemProps, items=layerItems, tab=tab)
            self.session.trackView("Edit layer item")

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
            self.setCurrentDrawer(None)

    def onCasePropsTabChanged(self):
        self.updateSceneStopOnAllEvents()

    def updateSceneStopOnAllEvents(self):
        if self.scene:  # redundnant?
            if (
                self.currentDrawer is self.caseProps
                and self.caseProps.currentTab() == RightDrawerView.Timeline.value
            ):
                isTimelineShown = True
            else:
                isTimelineShown = False
            self.scene.setStopOnAllEvents(isTimelineShown)
            self.graphicalTimelineView.update()

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
            QRect(0, 0, self.width() - Drawer.WIDTH, self.height())
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
            self.session.trackView("Show Graphical Timeline")
        else:
            self.session.trackView("Hide Graphical Timeline")

    def onShowGraphicalTimelineTick(self, height):
        # if self.graphicalTimelineAnimation.state() == QAbstractAnimation.Running:
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

    ## Actions (TODO: Move to controller)

    def showDiagram(self):
        count = 0
        while self.controller.closeTopLevelView() and count < 4:
            count += 1
        if self.scene:
            self.scene.update()

    def showEventForm(self, on: bool):
        if on:
            self.setCurrentDrawer(self.eventForm)
            self.eventForm.addEvent(self.scene.selectedItems())
        else:
            self.setCurrentDrawer(None)

    def showTimeline(self, on=True, dateTime=None, **kwargs):
        if on or dateTime is not None:
            self.setCurrentDrawer(
                self.caseProps, tab=RightDrawerView.Timeline.value, **kwargs
            )
            if dateTime is not None:
                self.caseProps.scrollTimelineToDateTime(dateTime)
        else:
            self.setCurrentDrawer(None, **kwargs)

    def showSettings(self, on=True):
        if on:
            self.setCurrentDrawer(self.caseProps, tab=RightDrawerView.Settings.value)
        else:
            self.setCurrentDrawer(None)

    def showCopilot(self, on=True):
        if on:
            self.setCurrentDrawer(self.caseProps, tab=RightDrawerView.Copilot.value)
        else:
            self.setCurrentDrawer(None)

    def showSearch(self):
        if not self.searchDialog.isShown():
            self.searchDialog.show()

    def showUndoHistory(self):
        pass

    def setExpandGraphicalTimeline(self, on):
        self.graphicalTimelineView.setExpanded(on)
