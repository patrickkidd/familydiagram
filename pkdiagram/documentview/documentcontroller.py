import logging
import bisect
import json

import vedana
from _pkdiagram import CUtil
from pkdiagram.pyqt import (
    pyqtSignal,
    Qt,
    QObject,
    QApplication,
    QRect,
    QRectF,
    QActionGroup,
    QAction,
    QQuickWidget,
    QQuickItem,
    QItemSelectionModel,
    QMessageBox,
    QImage,
    QPainter,
    QColor,
    QItemSelection,
    QDialog,
    QJSValue,
    QDateTime,
    QDate,
    QSize,
    QSizeF,
    QPoint,
    QPointF,
)
from pkdiagram import util
from pkdiagram.scene import Property, Person, Emotion, Event, LayerItem, Layer, ChildOf
from pkdiagram.models import selectedEvents
from pkdiagram.widgets import Drawer
from pkdiagram.documentview import RightDrawerView

if not util.IS_IOS:
    import xlsxwriter
    from pkdiagram.pyqt import QPrinter, QPrintDialog


log = logging.getLogger(__name__)


class DocumentController(QObject):
    """
    - Anything that connects actions with scene goes in here.
    - Wrangling views goes in DocumentController.
    """

    uploadToServer = pyqtSignal()

    _ignoreSelectionChanges = False
    _isUpdatingSearchTags = False
    _currentQmlFocusItem = None

    def __init__(self, dv: "DocumentView"):  # type: ignore
        super().__init__(dv)
        self.dv = dv
        self.ui = None
        self.scene = None
        self.view = self.dv.view
        self._isUpdatingLayerActions = False

    def init(self):
        assert self.ui is None
        self.ui = self.dv.ui

        self.dv.caseProps.qmlInitialized.connect(self.onCasePropsInit)

        self.dv.graphicalTimelineView.expandButton.clicked.connect(
            self.onGraphicalTimelineViewExpandedOrContracted
        )

        self.dv.qmlEngine().sceneModel.uploadToServer.connect(self.onUploadToServer)
        self.dv.qmlEngine().sceneModel.showSearch.connect(self.dv.showSearch)

        # File
        self.ui.actionPrint.triggered.connect(self.onPrint)
        # Edit
        self.ui.actionUndo.triggered.connect(self.onUndo)
        self.ui.actionRedo.triggered.connect(self.onRedo)
        self.ui.actionInspect.triggered.connect(self.onInspect)
        self.ui.actionInspect_Item.triggered.connect(self.onInspectItemTab)
        self.ui.actionInspect_Timeline.triggered.connect(self.onInspectTimelineTab)
        self.ui.actionInspect_Notes.triggered.connect(self.onInspectNotesTab)
        self.ui.actionInspect_Meta.triggered.connect(self.onInspectMetaTab)
        # Edit -> Transform
        self.ui.actionNudge_Up.triggered.connect(self.view.nudgeUp)
        self.ui.actionNudge_Down.triggered.connect(self.view.nudgeDown)
        self.ui.actionNudge_Left.triggered.connect(self.view.nudgeLeft)
        self.ui.actionNudge_Right.triggered.connect(self.view.nudgeRight)
        self.ui.actionHard_Nudge_Up.triggered.connect(self.view.hardNudgeUp)
        self.ui.actionHard_Nudge_Down.triggered.connect(self.view.hardNudgeDown)
        self.ui.actionHard_Nudge_Left.triggered.connect(self.view.hardNudgeLeft)
        self.ui.actionHard_Nudge_Right.triggered.connect(self.view.hardNudgeRight)
        self.ui.actionNudge_Up.setEnabled(False)
        self.ui.actionNudge_Down.setEnabled(False)
        self.ui.actionNudge_Left.setEnabled(False)
        self.ui.actionNudge_Right.setEnabled(False)
        self.ui.actionHard_Nudge_Up.setEnabled(False)
        self.ui.actionHard_Nudge_Down.setEnabled(False)
        self.ui.actionHard_Nudge_Left.setEnabled(False)
        self.ui.actionHard_Nudge_Right.setEnabled(False)
        # Insert
        self.itemModeActionGroup = QActionGroup(self)
        self.itemModeActionGroup.addAction(self.ui.actionMale)
        self.itemModeActionGroup.addAction(self.ui.actionFemale)
        self.itemModeActionGroup.addAction(self.ui.actionMarriage)
        self.itemModeActionGroup.addAction(self.ui.actionChild_Of)
        self.itemModeActionGroup.addAction(self.ui.actionConflict)
        self.itemModeActionGroup.addAction(self.ui.actionProjection)
        self.itemModeActionGroup.addAction(self.ui.actionFusion)
        self.itemModeActionGroup.addAction(self.ui.actionPrimary_Cutoff)
        self.itemModeActionGroup.addAction(self.ui.actionDistance)
        self.itemModeActionGroup.addAction(self.ui.actionReciprocity)
        self.itemModeActionGroup.addAction(self.ui.actionAway)
        self.itemModeActionGroup.addAction(self.ui.actionToward)
        self.itemModeActionGroup.addAction(self.ui.actionDefined_Self)
        self.itemModeActionGroup.addAction(self.ui.actionInside)
        self.itemModeActionGroup.addAction(self.ui.actionOutside)
        self.itemModeActionGroup.addAction(self.ui.actionCallout)
        self.itemModeActionGroup.addAction(self.ui.actionPencilStroke)
        self.itemModeActionGroup.triggered[QAction].connect(self.onItemModeAction)
        self.ui.actionMale.setData(util.ITEM_MALE)
        self.ui.actionFemale.setData(util.ITEM_FEMALE)
        self.ui.actionMarriage.setData(util.ITEM_MARRY)
        self.ui.actionChild_Of.setData(util.ITEM_CHILD)
        self.ui.actionParents_to_Selection.triggered.connect(
            self.view.addParentsToSelection
        )
        self.ui.actionConflict.setData(util.ITEM_CONFLICT)
        self.ui.actionProjection.setData(util.ITEM_PROJECTION)
        self.ui.actionFusion.setData(util.ITEM_FUSION)
        self.ui.actionPrimary_Cutoff.setData(util.ITEM_CUTOFF)
        self.ui.actionDistance.setData(util.ITEM_DISTANCE)
        self.ui.actionReciprocity.setData(util.ITEM_RECIPROCITY)
        self.ui.actionAway.setData(util.ITEM_AWAY)
        self.ui.actionToward.setData(util.ITEM_TOWARD)
        self.ui.actionDefined_Self.setData(util.ITEM_DEFINED_SELF)
        self.ui.actionInside.setData(util.ITEM_INSIDE)
        self.ui.actionOutside.setData(util.ITEM_OUTSIDE)
        self.ui.actionCallout.setData(util.ITEM_CALLOUT)
        self.ui.actionPencilStroke.setData(util.ITEM_PENCIL)
        # View
        self.ui.actionDelete.setEnabled(False)
        self.ui.actionDelete.triggered.connect(self.onDelete)
        self.ui.actionNext_Event.triggered.connect(self.onNextEvent)
        self.ui.actionPrevious_Event.triggered.connect(self.onPrevEvent)
        self.dv.graphicalTimelineView.nextTaggedDate.connect(self.onNextEvent)
        self.dv.graphicalTimelineView.prevTaggedDate.connect(self.onPrevEvent)
        #
        self.ui.actionNext_Layer.triggered.connect(self.onNextLayer)
        self.ui.actionPrevious_Layer.triggered.connect(self.onPrevLayer)
        self.ui.actionDeselect_All_Tags.triggered.connect(self.onDeselectAllTags)
        self.ui.actionDeactivate_All_Layers.triggered.connect(
            self.onDeactivateAllLayers
        )
        #
        self.ui.actionAdd_Anything.toggled[bool].connect(self.dv.showEventForm)
        self.ui.actionShow_Diagram.triggered.connect(self.dv.showDiagram)
        self.ui.actionShow_Timeline.toggled[bool].connect(self.dv.showTimeline)
        self.ui.actionShow_Items_with_Notes.toggled.connect(
            self.dv.view.showItemsWithNotes
        )
        self.ui.actionFind.triggered.connect(self.dv.showSearch)
        self.ui.actionShow_Settings.toggled[bool].connect(self.dv.showSettings)
        self.ui.actionShow_Copilot.toggled[bool].connect(self.dv.showCopilot)
        #
        self.ui.actionZoom_In.triggered.connect(self.view.zoomIn)
        self.ui.actionZoom_Out.triggered.connect(self.view.zoomOut)
        self.ui.actionZoom_Fit.triggered.connect(self.onZoomFit)
        self.view.zoomFitDirty[bool].connect(self.onZoomFitDirty)

        ## Views

        self.dv.caseProps.hideRequested.connect(self.onHideCurrentDrawer)
        self.dv.personProps.hideRequested.connect(self.onHideCurrentDrawer)
        self.dv.marriageProps.hideRequested.connect(self.onHideCurrentDrawer)
        self.dv.emotionProps.hideRequested.connect(self.onHideCurrentDrawer)
        self.dv.layerItemProps.hideRequested.connect(self.onHideCurrentDrawer)
        self.dv.eventForm.hideRequested.connect(self.onHideCurrentDrawer)

        self.dv.timelineModel.rowsInserted.connect(self.onTimelineRowsChanged)
        self.dv.timelineModel.rowsRemoved.connect(self.onTimelineRowsChanged)

        self.dv.searchDialog.quit.connect(self.onSearchQuitShortcut)
        self.dv.searchModel.changed.connect(self.onSearchChanged)
        self.dv.searchModel.tagsChanged.connect(self.onSearchTagsChanged)

    def deinit(self):
        self._currentQmlFocusItem = None

    def onCasePropsInit(self):
        self.dv.timelineSelectionModel.selectionChanged[
            QItemSelection, QItemSelection
        ].connect(self.onTimelineSelectionChanged)
        self.dv.caseProps.qml.rootObject().flashTimelineSelection.connect(
            self.onFlashTimelineSelection
        )
        self.dv.caseProps.qml.rootObject().flashTimelineRow.connect(
            self.onFlashTimelineRow
        )
        self.dv.caseProps.qml.rootObject().eventPropertiesTemplateIndexChanged[
            int
        ].connect(self.onEventPropertiesTemplateIndexChanged)

    def setScene(self, scene):
        if self.scene:
            self.dv.searchModel.clear()
            self.scene.propertyChanged[Property].disconnect(self.onSceneProperty)
            self.scene.itemModeChanged.disconnect(self.onSceneItemMode)
            self.scene.itemDoubleClicked.disconnect(self.onItemDoubleClicked)
            self.scene.emotionAdded[Emotion].disconnect(self.onEmotionAdded)
            self.scene.layerAdded[Layer].disconnect(self.onSceneLayersChanged)
            self.scene.layerChanged[Property].disconnect(self.onLayerChanged)
            self.scene.layerRemoved[Layer].disconnect(self.onSceneLayersChanged)
            self.scene.activeLayersChanged.disconnect(self.onActiveLayers)
            self.scene.showNotes.disconnect(self.showNotesFor)
        self.scene = scene
        if self.scene:
            self.scene.propertyChanged[Property].connect(self.onSceneProperty)
            self.scene.itemModeChanged.connect(self.onSceneItemMode)
            self.scene.itemDoubleClicked.connect(self.onItemDoubleClicked)
            self.scene.emotionAdded[Emotion].connect(self.onEmotionAdded)
            self.scene.layerAdded[Layer].connect(self.onSceneLayersChanged)
            self.scene.layerChanged[Property].connect(self.onLayerChanged)
            self.scene.layerRemoved[Layer].connect(self.onSceneLayersChanged)
            self.scene.activeLayersChanged.connect(self.onActiveLayers)
            self.scene.showNotes.connect(self.showNotesFor)
            self.scene.setActiveTags(self.dv.searchModel.tags, skipUpdate=False)
        self.onSceneTagsChanged()
        self.onSceneLayersChanged()

    ## Non-verbal reactive event handlers

    def onEditorMode(self, on):
        self.dv.adjust()
        self.dv.view.onEditorMode(on)
        self.dv.sceneModel.onEditorMode(on)

    def onTimelineRowsChanged(self):
        self.dv.updateTimelineCallout()
        self.updateActions()

    def onSceneProperty(self, prop):
        if prop.name() == "currentDateTime":
            # Canonical way to set event-dependent views.
            if prop.get():
                if (
                    not self.dv.isGraphicalTimelineShown()
                    and not self.scene.hideDateSlider()
                ):
                    self.dv.setShowGraphicalTimeline(True)
                self.dv.caseProps.scrollTimelineToDateTime(prop.get())
            else:
                self.dv.setShowGraphicalTimeline(False)
            self.dv.updateTimelineCallout()
            self.updateActions()

            # Flash timeline items for events when date changes.
            firstRow = self.dv.timelineModel.firstRowForDateTime(prop.get())
            lastRow = self.dv.timelineModel.lastRowForDateTime(prop.get())
            if firstRow > -1 and lastRow > -1:
                for row in range(firstRow, lastRow + 1):
                    event = self.dv.timelineModel.eventForRow(row)
                    if not self.dv.searchModel.shouldHide(event):
                        self.onFlashTimelineRow(row)

        elif prop.name() == "hideDateSlider":
            if (
                prop.get()
                and self.scene.currentDateTime()
                and self.dv.isGraphicalTimelineShown()
            ):
                self.dv.setShowGraphicalTimeline(False)
            elif not prop.get():
                self.dv.setShowGraphicalTimeline(True)

        elif prop.name() == "hideEmotionalProcess":
            if self.dv.searchModel.hideRelationships != prop.get():
                self.dv.searchModel.hideRelationships = prop.get()

        elif prop.name() == "tags":
            self.onSceneTagsChanged()

    def onSceneTagsChanged(self):
        if self.scene:
            sceneTags = self.scene.tags()
        else:
            sceneTags = []
        # Tags Menu
        self.ui.menuTags.clear()
        for tag in sceneTags:
            action = QAction(self)
            action.setText(tag)
            action.setData(tag)
            action.setCheckable(True)
            if tag in self.dv.searchModel.tags:
                action.setChecked(True)
            action.toggled[bool].connect(self.onTagToggled)
            self.ui.menuTags.addAction(action)
        self.ui.menuTags.addSeparator()
        self.ui.menuTags.addAction(self.ui.actionDeselect_All_Tags)

    def onSearchTagsChanged(self, tags):
        self._isUpdatingSearchTags = True
        for action in self.ui.menuTags.actions():
            on = action.data() in tags
            if on != action.isChecked:
                action.setChecked(on)
        self.scene.setActiveTags(tags)
        self._isUpdatingSearchTags = False

    def onTimelineSelectionChanged(
        self, selected: QItemSelection, deselected: QItemSelection
    ):
        if not self.dv.graphicalTimelineView.timeline.canvas.isSelectingEvents():
            return
        selectedRows = list(set([index.row() for index in selected.indexes()]))
        deselectedRows = list(set([index.row() for index in deselected.indexes()]))
        if selectedRows:
            rows = selectedRows
        elif deselectedRows:
            rows = deselectedRows
        else:
            rows = None
        if rows:
            lastChangedDateTime = self.dv.timelineModel.dateTimeForRow(rows[-1])
            self.dv.caseProps.scrollTimelineToDateTime(lastChangedDateTime)

    def onTagToggled(self, on):
        if self._isUpdatingSearchTags:
            return
        action = self.sender()
        tag = action.data()
        tags = list(self.dv.searchModel.tags)
        if on and not tag in tags:
            tags.append(tag)
        elif not on and tag in tags:
            tags.remove(tag)
        self.dv.searchModel.tags = tags

    @util.blocked
    def onActiveLayers(self, activeLayers):
        self.updateActions()
        self._isUpdatingLayerActions = True
        ids = [x.id for x in activeLayers if not x.internal()]
        for action in self.ui.menuLayers.actions():
            on = action.data() in ids
            if on != action.isChecked():
                action.setChecked(on)
        self._isUpdatingLayerActions = False

    @util.blocked
    def onLayerActionToggled(self, on):
        """Exclusive selection."""
        if self._isUpdatingLayerActions:
            return
        action = self.sender()
        id = action.data()
        for layer in self.scene.layers():
            if layer.id == id:
                if on:
                    self.scene.setExclusiveActiveLayerIndex(layer.order())
                else:
                    layer.setActive(False, undo=True)
                return

    def onLayerChanged(self, prop):
        if prop.name() == "active":
            self.onSceneLayersChanged()
        elif prop.name() == "name":
            self.onSceneLayersChanged()

    def onSceneLayersChanged(self):
        self.ui.menuLayers.clear()
        if self.scene:
            for layer in self.scene.layers(includeInternal=False):
                action = QAction(self)
                action.setText(layer.name())
                action.setData(layer.id)
                action.setCheckable(True)
                if layer.active():
                    action.setChecked(True)
                action.toggled[bool].connect(self.onLayerActionToggled)
                self.ui.menuLayers.addAction(action)
        self.ui.menuLayers.addSeparator()
        self.ui.menuLayers.addAction(self.ui.actionDeactivate_All_Layers)
        self.updateActions()

    def onEmotionAdded(self, emotion: Emotion):
        emotion.addTags(self.dv.searchModel.tags)

    def onEventPropertiesTemplateIndexChanged(self, index: int):
        """
        Replace existing timeline variables with template variables.

        TODO: Should move the underlying logic to Scene.setVariablesTemplate()
        """
        if index < 0 or not self.scene:
            return
        propAttrs = [entry["attr"] for entry in self.scene.eventProperties()]
        if self.scene.eventProperties():
            hasPropSet = 0
            for event in self.scene.events():
                for attr in propAttrs:
                    prop = event.dynamicProperty(attr)
                    if prop.get() is not None:
                        hasPropSet += 1
            if hasPropSet:
                btn = QMessageBox.question(
                    QApplication.activeWindow(),
                    "Delete existing timeline variables?",
                    "This will replace the existing timeline variables and their %i values with variables from the template. Are you sure you want to do this?"
                    % hasPropSet,
                )
                if btn == QMessageBox.No:
                    return
        newProps = []
        if index == 0:  # Havstad Model
            newProps = util.HAVSTAD_MODEL
        elif index == 1:  # Papero Model
            newProps = util.PAPERO_MODEL
        elif index == 2:  # Stinson Model
            newProps = util.STINSON_MODEL
        self.scene.replaceEventProperties(newProps, undo=True)
        # for name in [e['name'] for e in self.scene.eventProperties()]:
        #     commands.removeEventProperty(self.scene, name)
        # for name in newProps:
        #     commands.createEventProperty(self.scene, name)

    def onFlashTimelineSelection(self, selectionModel: QItemSelectionModel):
        """Called when case props timeline selection is changed."""
        model = selectionModel.model()
        for index in selectionModel.selectedRows():
            id = model.idForRow(index.row())
            if id is None:
                event = model.eventForRow(index.row())
                log.warning(f"Event selected in timeline has no parent: {event}")
            else:
                item = self.scene.find(id=id)
                item.flash()

    def onFlashTimelineRow(self, row: int):
        if self.scene:
            item = self.dv.timelineModel.itemForRow(row)
            item.flash()

    def onQmlFocusItemChanged(self, item: QQuickItem):
        self._currentQmlFocusItem = item
        # if item:
        #     log.info(
        #         f"DocumentController.onQmlFocusItemChanged: {item.metaObject().className()}#{item.objectName()}"
        #     )
        # else:
        #     log.info(f"DocumentController.onQmlFocusItemChanged: None")
        self.updateActions()

    def updateActions(self):
        """Idempotent"""
        session = self.dv.session
        isReadOnly = self.scene and self.scene.readOnly()

        # License-dependent
        isAdmin = session.user and session.user.hasRoles(vedana.ROLE_ADMIN)

        allActionsEnabled = session.activeFeatures() != []
        for attr, action in self.ui.__dict__.items():
            if isinstance(action, QAction):
                if action not in (self.ui.actionQuit, self.ui.actionShow_Account):
                    action.setEnabled(allActionsEnabled)
        if not allActionsEnabled:
            return
        self.ui.actionOpen.setEnabled(not session.hasFeature(vedana.LICENSE_FREE))
        self.ui.actionImport_Diagram.setEnabled(session.hasFeature(vedana.LICENSE_FREE))
        self.ui.menuOpen_Recent.setEnabled(not session.hasFeature(vedana.LICENSE_FREE))
        self.ui.actionSave.setEnabled(bool(self.scene and not isReadOnly))
        self.ui.actionSave_As.setEnabled(
            bool(
                self.scene
                and not session.hasFeature(vedana.LICENSE_FREE, vedana.LICENSE_CLIENT)
                and (isAdmin or not isReadOnly)
            )
        )
        self.ui.actionSave_Selection_As.setEnabled(
            bool(
                self.scene
                and not session.hasFeature(vedana.LICENSE_FREE, vedana.LICENSE_CLIENT)
                and (self.scene and self.scene.selectedItems() and not isReadOnly)
            )
        )
        self.ui.actionFree_License.setChecked(session.hasFeature(vedana.LICENSE_FREE))
        self.ui.actionProfessional_License.setChecked(
            session.hasFeature(vedana.LICENSE_PROFESSIONAL)
        )
        self.ui.actionResearcher_License.setChecked(
            session.hasFeature(vedana.LICENSE_RESEARCHER)
        )
        self.ui.actionInstall_Update.setEnabled(CUtil.instance().isUpdateAvailable())

        # License + In-view dependent actions

        on = bool(self.scene)
        self.ui.actionClose.setEnabled(
            on and not session.hasFeature(vedana.LICENSE_FREE)
        )

        # In-view actions

        on = bool(self.scene)
        self.ui.actionShow_Tips.setEnabled(on)
        self.ui.actionShow_Local_Files.setEnabled(not on)
        self.ui.actionShow_Server_Files.setEnabled(not on)
        self.ui.menuLayers.setEnabled(on)
        self.ui.menuTags.setEnabled(on)
        self.ui.actionDeselect_All_Layers.setEnabled(on)
        self.ui.actionDeselect_All_Tags.setEnabled(on)
        self.ui.actionReset_All.setEnabled(on)
        self.ui.actionUndo_History.setEnabled(False)  # on)
        self.ui.actionShow_Diagram.setEnabled(on)
        self.ui.actionShow_Timeline.setEnabled(on)
        self.ui.actionShow_Timeline_Search.setEnabled(on)
        self.ui.actionShow_Relationships.setEnabled(on)
        self.ui.actionShow_Items_with_Notes.setEnabled(on)
        self.ui.actionFind.setEnabled(on)
        self.ui.actionShow_Settings.setEnabled(on)
        self.ui.actionJump_to_Now.setEnabled(on)
        self.ui.actionShow_Current_Date.setEnabled(on)
        self.ui.actionShow_Legend.setEnabled(on)
        self.ui.actionAdd_Anything.setEnabled(on)

        canUndo = self.scene.stack().canUndo() if self.scene else False
        self.ui.actionUndo.setEnabled(on and canUndo)
        canRedo = self.scene.stack().canRedo() if self.scene else False
        self.ui.actionRedo.setEnabled(on and canRedo)
        if self.scene:
            numLayers = len(self.scene.layers(includeInternal=False))
            iActiveLayer = self.scene.activeLayer()
        else:
            numLayers = 0
            iActiveLayer = -1

        # In-view + read-only enabled actions

        inViewPlusRW = bool(self.scene)
        self.ui.actionHide_Names.setEnabled(inViewPlusRW)
        self.ui.actionHide_Variables_on_Diagram.setEnabled(inViewPlusRW)
        self.ui.actionHide_Variable_Steady_States.setEnabled(inViewPlusRW)
        self.ui.actionHide_Emotional_Process.setEnabled(inViewPlusRW)
        self.ui.actionHide_Emotion_Colors.setEnabled(inViewPlusRW)
        self.ui.actionHide_ToolBars.setEnabled(inViewPlusRW)
        enableShowAliases = bool(
            inViewPlusRW or (self.scene and self.scene.useRealNames())
        )
        self.ui.actionShow_Aliases.setEnabled(enableShowAliases)
        self.ui.actionDelete.setEnabled(inViewPlusRW)

        # View-focus, read-write dependent actions

        fw = QApplication.focusWidget()
        if (
            (fw not in (self.view, self.view.itemToolBar, self.view.sceneToolBar))
            or (not self.scene)
            or (self.scene and self.scene.readOnly())
        ):
            # added itemToolBar as hack after refactoring as scroll area
            forceOff = True
        else:
            forceOff = False
        on = not forceOff
        self.ui.actionPrint.setEnabled(on)
        self.ui.actionZoom_In.setEnabled(on)
        self.ui.actionZoom_Out.setEnabled(on)
        self.ui.actionZoom_Fit.setEnabled(on)  # and self.view.isZoomFitDirty())
        self.ui.actionMale.setEnabled(on)
        self.ui.actionFemale.setEnabled(on)
        self.ui.actionMarriage.setEnabled(on)
        self.ui.actionChild_Of.setEnabled(on)
        self.ui.actionConflict.setEnabled(on)
        self.ui.actionProjection.setEnabled(on)
        self.ui.actionFusion.setEnabled(on)
        self.ui.actionDistance.setEnabled(on)
        self.ui.actionReciprocity.setEnabled(on)
        self.ui.actionAway.setEnabled(on)
        self.ui.actionToward.setEnabled(on)
        self.ui.actionDefined_Self.setEnabled(on)
        self.ui.actionInside.setEnabled(on)
        self.ui.actionOutside.setEnabled(on)
        self.ui.actionUndo.setEnabled(on)
        self.ui.actionRedo.setEnabled(on)
        self.ui.actionPrimary_Cutoff.setEnabled(on)
        if util.isTextItem(self._currentQmlFocusItem):
            canNextLayer = canPrevLayer = False
        else:
            canNextLayer = numLayers > 0 and (
                iActiveLayer == -1 or iActiveLayer < (numLayers - 1)
            )
            canPrevLayer = numLayers > 0 and (iActiveLayer == -1 or iActiveLayer > 0)
        self.ui.actionNext_Layer.setEnabled(canNextLayer)
        self.ui.actionPrevious_Layer.setEnabled(canPrevLayer)
        if on:
            on = bool(
                self.scene and (not self.scene.layers() or self.scene.activeLayers())
            )
        self.ui.actionPencilStroke.setEnabled(on)  # add default layer now
        self.ui.actionCallout.setEnabled(on)
        # self.view.itemToolBar.pencilButton.setEnabled(on)
        # self.view.itemToolBar.calloutButton.setEnabled(on)
        #

        # Selection-dependent actions

        if self.scene:
            people = self.scene.selectedPeople()
            marriages = self.scene.selectedMarriages()
            emotions = self.scene.selectedEmotions()
            allSelected = self.scene.selectedItems()
        else:
            people = marriages = emotions = allSelected = []

        # Copy/Nudgables (i.e. People & LayerItems)

        rootCopyables = [
            item
            for item in allSelected
            if isinstance(item, Person) or isinstance(item, LayerItem)
        ]
        if not forceOff:
            on = bool(rootCopyables)
        else:
            on = False
        self.ui.actionNudge_Up.setEnabled(on)
        self.ui.actionNudge_Down.setEnabled(on)
        self.ui.actionNudge_Left.setEnabled(on)
        self.ui.actionNudge_Right.setEnabled(on)
        self.ui.actionHard_Nudge_Up.setEnabled(on)
        self.ui.actionHard_Nudge_Down.setEnabled(on)
        self.ui.actionHard_Nudge_Left.setEnabled(on)
        self.ui.actionHard_Nudge_Right.setEnabled(on)

        if util.ENABLE_ITEM_COPY_PASTE:
            self.onSceneClipboard()

        # People-dependent actions

        if not forceOff:
            on = bool(people)
        else:
            on = False
        self.ui.actionParents_to_Selection.setEnabled(on)
        self.ui.actionClear_All_Events.setEnabled(on)
        self.ui.actionDeselect.setEnabled(on)

        # Item-dependent actions

        if not forceOff:
            on = bool(self.scene and self.scene.items() or [])
        self.ui.actionSelect_All.setEnabled(on)
        childOfs = [i for i in allSelected if isinstance(i, ChildOf)]
        if not forceOff:
            on = (len(people) + len(marriages) + len(emotions) + len(childOfs)) > 0

        # Event-dependent actions

        inView = bool(self.scene)
        anyEvents = False if not self.scene else self.dv.timelineModel.rowCount() > 0
        self.ui.actionNext_Event.setEnabled(inView and anyEvents)
        self.ui.actionPrevious_Event.setEnabled(inView and anyEvents)
        self.ui.actionShow_Graphical_Timeline.setEnabled(inView and anyEvents)
        self.ui.actionExpand_Graphical_Timeline.setEnabled(inView and anyEvents)

        # Inspectable|Deletable-dependent action

        self.ui.actionDelete.setEnabled(
            self.canDelete() and (not self.scene or not self.scene.readOnly())
        )
        self.ui.actionInspect.setEnabled(self.canInspect())
        self.ui.actionInspect_Item.setEnabled(bool(allSelected))
        self.ui.actionInspect_Timeline.setEnabled(bool(allSelected))
        self.ui.actionInspect_Notes.setEnabled(bool(allSelected))
        self.ui.actionInspect_Meta.setEnabled(bool(allSelected))

    ## Verbs

    def onZoomFit(self):
        self.view.zoomFit(forLayers=self.scene.activeLayers())

    def onZoomFitDirty(self, on):
        self.ui.actionZoom_Fit.setEnabled(on)

    def onNextEvent(self):
        """Set the current date to the next visible date."""
        if not self.scene:
            return
        nextDateTime = self.dv.timelineModel.nextDateTimeAfter(
            self.scene.currentDateTime()
        )
        if nextDateTime:
            self.scene.setCurrentDateTime(nextDateTime)

    def onPrevEvent(self):
        if not self.scene:
            return
        prevDateTime = self.dv.timelineModel.prevDateTimeBefore(
            self.scene.currentDateTime()
        )
        if prevDateTime:
            self.scene.setCurrentDateTime(prevDateTime)

    def onDeselectAllTags(self):
        for action in self.ui.menuTags.actions():
            if action.isCheckable() and action.isChecked():
                action.blockSignals(True)
                action.setChecked(False)
        else:
            prevDate = events[prevRow].dateTime()
        if prevDate:
            self.scene.setCurrentDateTime(prevDate)

    def onDeselectAllTags(self):
        for action in self.ui.menuTags.actions():
            if action.isCheckable() and action.isChecked():
                action.blockSignals(True)
                action.setChecked(False)
                action.blockSignals(False)
        self.dv.searchModel.reset("tags")

    def onNextLayer(self):
        self.scene.nextActiveLayer()

    def onPrevLayer(self):
        self.scene.prevActiveLayer()

    def onDeactivateAllLayers(self):
        for action in self.ui.menuLayers.actions():
            if action.isCheckable() and action.isChecked():
                action.blockSignals(True)
                action.setChecked(False)
                action.blockSignals(False)
        with self.scene.macro("Deactivate all laters"):
            for layer in self.scene.activeLayers():
                layer.setActive(False, undo=True)

    def onSceneItemMode(self):
        if self.scene.itemMode() is util.ITEM_NONE:
            for action in self.itemModeActionGroup.actions():
                if action.isChecked():
                    action.setChecked(False)

    def onItemModeAction(self, action):
        on = action.isChecked()
        if on:
            itemMode = action.data()
        else:
            itemMode = util.ITEM_NONE
        self.scene.setItemMode(itemMode)

    def onGraphicalTimelineViewExpandedOrContracted(self):
        self.dv.graphicalTimelineCallout.hide()

    def onUndo(self):
        self.scene.undo()
        self.view.onUndo()

    def onRedo(self):
        self.scene.redo()
        self.view.onRedo()

    def onDelete(self):
        fw = QApplication.focusWidget()
        if fw in (self.view, self.view.rightToolBar):
            self.scene.removeSelection()
            self.dv.controller.updateActions()
        elif isinstance(fw, QQuickWidget):
            drawer = fw.parent()
            drawer.removeSelection()
        else:
            log.error(f"Cant handle focuswidget: fw", exc_info=True)

    def canDelete(self):
        fw = QApplication.focusWidget()
        if self.dv.canDeleteSelection():
            return True
        elif isinstance(fw, QQuickWidget):
            ret = fw.parent().rootProp("canRemove")
            if ret is None:
                ret = False
            return ret
        elif (
            fw in (self.view, self.view.rightToolBar)
            and self.scene
            and self.scene.selectedItems()
        ):
            return True
            # people = self.scene.selectedPeople()
            # marriages = self.scene.selectedMarriages()
            # if len(people) > 0:
            #     return True
            # elif not people and len(marriages) == 1:
            #     return True
            # elif self.scene.selectedItems(types=[Emotion, LayerItem]):
            #     return True
            # else:
            #     return False
        else:
            return False

    def canInspect(self):
        """duplicated in onInspect"""
        if not self.scene:
            return False
        fw = QApplication.focusWidget()
        ret = None
        if isinstance(fw, QQuickWidget):
            ret = fw.parent().rootProp("canInspect")
            if ret is None:
                ret = False
        elif fw == self.dv.graphicalTimelineView.timeline:
            events = selectedEvents(
                self.dv.timelineModel, self.dv.timelineSelectionModel
            )
            ret = bool(events)
        else:  # scene
            people = self.scene.selectedPeople()
            marriages = self.scene.selectedMarriages()
            if len(people) > 0:
                ret = True
            elif not people and len(marriages) == 1:
                ret = True
            elif self.scene.selectedItems(types=[Emotion, LayerItem]):
                ret = True
            else:
                ret = False
        return ret

    def onInspect(self, tab=None):
        """duplicated in canInspect"""

        def _inspectEvents(events: list[Event]):
            if isinstance(events, QJSValue):
                events = events.toVariant()
            self.dv.setCurrentDrawer(self.dv.eventForm)
            self.dv.eventForm.editEvents(events)
            self.dv.session.trackView("Edit event(s)")

        fw = QApplication.focusWidget()
        if isinstance(fw, QQuickWidget):
            if (
                fw.parent() == self.dv.caseProps
                and self.dv.caseProps.currentTab() == "timeline"
            ):
                events = self.dv.caseProps.selectedEvents()
                _inspectEvents(events)
            elif hasattr(fw.parent(), "onInspect"):
                fw.parent().onInspect(tab)
        elif fw is self.dv.graphicalTimelineView.timeline:
            events = selectedEvents(
                self.dv.timelineModel, self.dv.timelineSelectionModel
            )
            _inspectEvents(events)
        else:  # scene
            self.dv.inspectSelection(tab=tab)

    def onInspectItemTab(self):
        self.onInspect(tab="item")

    def onInspectTimelineTab(self):
        self.onInspect(tab=RightDrawerView.Timeline.value)

    def onInspectNotesTab(self):
        self.onInspect(tab="notes")

    def onInspectMetaTab(self):
        self.onInspect(tab="meta")

    def onItemDoubleClicked(self, item):
        self.onInspect()

    def onInspectItemById(self, itemId):
        item = self.scene.find(itemId)
        self.dv.inspectSelection(selection=[item])

    def closeTopLevelView(self) -> bool:
        """
        Return True if something was closed, define the priority of closure.
        """
        if self.dv.searchDialog.isShown():
            self.dv.searchDialog.hide()
            return True
        elif self.dv.currentDrawer and self.dv.currentDrawer.isShown():
            return self.onHideCurrentDrawer()
        elif self.dv.graphicalTimelineView.isExpanded():
            self.dv.graphicalTimelineView.setExpanded(False)
            return True

    def onEventFormDoneEditing(self):
        self.dv.setCurrentDrawer(self.dv.caseProps)

    def onHideCurrentDrawer(self):
        if self.dv.currentDrawer:
            self.tryToHideDrawer(self.dv.currentDrawer)

    def tryToHideDrawer(self, drawer: Drawer) -> bool:
        """
        The canonical way to close a drawer on the right toolbar. Ensures
        consistency with action and button states.
        """
        if drawer.canClose():
            if drawer is self.dv.eventForm:
                if self.ui.actionAdd_Anything.isChecked():
                    self.ui.actionAdd_Anything.setChecked(False)
                    return True
            elif drawer is self.dv.caseProps:
                if self.view.ui.actionShow_Timeline.isChecked():
                    self.view.ui.actionShow_Timeline.setChecked(False)
                    return True
                elif self.view.rightToolBar.settingsButton.isChecked():
                    self.view.rightToolBar.settingsButton.setChecked(False)
                    return True
                elif self.view.rightToolBar.copilotButton.isChecked():
                    self.view.rightToolBar.copilotButton.setChecked(False)
                    return True
            else:
                # No button to update
                self.dv.setCurrentDrawer(None)
                return True
        return False

    def onPropertySheetHideRequested(self):
        self.tryToHideDrawer(self.dv.currentDrawer)

    def showNotesFor(self, pathItem):
        self._ignoreSelectionChanges = True
        for item in self.scene.selectedItems():
            if item is not pathItem:
                item.setSelected(False)
        if not pathItem.isSelected():
            pathItem.setSelected(True)
        self._ignoreSelectionChanges = False
        self.dv.inspectSelection(tab="notes")

    def onSearchQuitShortcut(self):
        if self.dv.searchDialog.isShown():
            self.dv.searchDialog.hide()
            self.dv.ui.actionQuit.trigger()

    def onSearchChanged(self):
        if self.scene:
            if self.dv.searchModel.hideRelationships != self.scene.hideEmotionalProcess:
                self.scene.setHideEmotionalProcess(
                    self.dv.searchModel.hideRelationships
                )

            firstDate = self.dv.timelineModel.dateTimeForRow(0)
            if firstDate > self.scene.currentDateTime():
                self.scene.setCurrentDateTime(firstDate)
            elif not self.scene.areActiveLayersChanging():
                self.scene._updateAllItemsForLayersAndTags()
        self.dv.updateTimelineCallout()

    def onUploadToServer(self):
        self.uploadToServer.emit()

    def __writePDF(self, filePath=None, printer=None):
        rect = self.printRect()
        sourceRect = rect.size()
        if printer is None:
            printer = QPrinter()
        printer.setOutputFormat(QPrinter.PdfFormat)
        painter = QPainter()
        painter.begin(printer)
        printerRect = printer.pageRect(QPrinter.Point).toRect()
        if filePath is not None:
            printer.setOutputFileName(filePath)
            # printer.setOrientation(QPrinter.Landscape)
        # elif printer is not None:
        #     # make it fit
        #     sourceRect = image.rect()
        #     if sourceRect.width() > sourceRect.height():
        #         scale = printRect.width() / sourceRect.width()
        #         targetRect = QRect(printRect.x(), printRect.y(),
        #                            sourceRect.width() * scale,
        #                            sourceRect.height() * scale)
        #     else:
        #         scale = printRect.height() / sourceRect.height()
        #         targetRect = QRect(printRect.x(),
        #                            printRect.y(),
        #                            sourceRect.width() * scale,
        #                            sourceRect.height() * scale)
        #     p.drawImage(targetRect, image, sourceRect)
        #     p.end()
        self.render(painter, QRectF(printerRect), self.printRect())
        painter.end()
        painter = None  # control dtor order, before printer

    def writeJPG(self, filePath=None, printer=None):
        rect = self.scene.printRect()
        size = rect.size().toSize() * util.PRINT_DEVICE_PIXEL_RATIO
        image = QImage(size, QImage.Format_RGB32)
        image.setDevicePixelRatio(
            self.scene.view().devicePixelRatio() / util.PRINT_DEVICE_PIXEL_RATIO
        )
        image.fill(QColor("white"))
        painter = QPainter()
        painter.begin(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        self.scene.render(painter, QRectF(0, 0, size.width(), size.height()), rect)
        painter.end()
        if filePath is not None:
            image.save(filePath, "JPEG", 80)
        elif printer is not None:
            p = QPainter()
            p.begin(printer)
            # make it fit
            printRect = printer.pageRect(QPrinter.Point).toRect()
            sourceRect = image.rect()
            if sourceRect.width() > sourceRect.height():
                scale = printRect.width() / sourceRect.width()
                targetRect = QRect(
                    printRect.x(),
                    printRect.y(),
                    int(sourceRect.width() * scale),
                    int(sourceRect.height() * scale),
                )
            else:
                scale = printRect.height() / sourceRect.height()
                targetRect = QRect(
                    printRect.x(),
                    printRect.y(),
                    int(sourceRect.width() * scale),
                    int(sourceRect.height() * scale),
                )
            p.drawImage(targetRect, image, sourceRect)
            p.end()

    def writePNG(self, filePath):
        rect = self.scene.printRect()
        size = rect.size().toSize() * util.PRINT_DEVICE_PIXEL_RATIO
        image = QImage(size, QImage.Format_ARGB32)
        image.setDevicePixelRatio(
            self.scene.view().devicePixelRatio() / util.PRINT_DEVICE_PIXEL_RATIO
        )
        image.fill(Qt.transparent)
        painter = QPainter()
        painter.begin(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        self.scene.render(painter, QRectF(0, 0, size.width(), size.height()), rect)
        image.save(filePath, "PNG", 100)
        painter.end()

    def writeExcel(self, filePath):
        book = xlsxwriter.Workbook(filePath)
        wrap_format = book.add_format({"text_wrap": True})  # doesn't work
        wrap_format.set_text_wrap()  # doesn't work
        ## Events
        sheet = book.add_worksheet("Timeline")
        sheet.set_column(0, 0, 10)  # Date width
        sheet.set_column(1, 1, 35)  # Description width
        sheet.set_column(2, 2, 10)  # Location width
        sheet.set_column(3, 3, 15)  # Person width
        sheet.set_column(4, 4, 10)  # Logged width
        sheet.set_column(5, 5, 100)  # Notes width
        sheet.write(0, 0, "Date")
        sheet.write(0, 1, "Description")
        sheet.write(0, 2, "Location")
        sheet.write(0, 3, "Person")
        sheet.write(0, 4, "Logged")
        sheet.write(0, 5, "Notes", wrap_format)
        for i, entry in enumerate(self.scene.eventProperties()):
            sheet.write(0, 6 + i, entry["name"])

        model = self.dv.timelineModel
        rowDisplay = lambda row, col: model.data(model.index(row, col))
        for row in range(model.rowCount()):
            index = row + 1
            event = model.eventForRow(row)
            sheet.write(index, 0, rowDisplay(row, 1))  # date
            sheet.write(index, 1, rowDisplay(row, 3))  # description
            sheet.write(index, 2, rowDisplay(row, 4))  # location
            sheet.write(index, 3, rowDisplay(row, 5))  # parent
            sheet.write(index, 4, rowDisplay(row, 6))  # logged
            sheet.write(index, 5, event.notes())  # notes

            # sheet.write(index, 1, event.description() and event.description() or '')
            # sheet.write(index, 2, event.location() and event.location() or '')
            # sheet.write(index, 3, event.parentName())
            # sheet.write(index, 4, util.dateString(event.loggedDateTime()))
            # sheet.write(index, 5, event.notes())
            for i, entry in enumerate(self.scene.eventProperties()):
                prop = event.dynamicProperty(entry["attr"])
                if prop:
                    sheet.write(index, 6 + i, prop.get())
        ## People
        sheet = book.add_worksheet("People")
        sheet.write(0, 0, "Birth Date")
        sheet.write(0, 1, "First Name")
        sheet.write(0, 2, "Middle Name")
        sheet.write(0, 3, "Last Name")
        sheet.write(0, 4, "Nick Name")
        sheet.write(0, 5, "Birth Name")
        sheet.write(0, 6, "Sex")
        sheet.write(0, 7, "Deceased")
        sheet.write(0, 8, "Deceased Reason")
        sheet.write(0, 9, "Date of Death")
        sheet.write(0, 10, "Adopted")
        sheet.write(0, 11, "Adoption Date")
        sheet.write(0, 12, "Notes")
        #
        sheet.write(0, 13, "Show Middle Name")
        sheet.write(0, 14, "Show Last Name")
        sheet.write(0, 15, "Show Nick Name")
        sheet.write(0, 16, "Primary")
        sheet.write(0, 17, "Hide Details")
        people = self.scene.find(
            sort="birthDateTime", types=Person, tags=list(self.dv.searchModel.tags)
        )
        for index, person in enumerate(people):
            sheet.write(index + 1, 0, person.birthDateTime(string=True))
            sheet.write(
                index + 1,
                1,
                self.scene.showAliases() and ("[%s]" % person.alias()) or person.name(),
            )
            sheet.write(
                index + 1, 2, self.scene.showAliases() and " " or person.middleName()
            )
            sheet.write(
                index + 1, 3, self.scene.showAliases() and " " or person.lastName()
            )
            sheet.write(
                index + 1, 4, self.scene.showAliases() and " " or person.nickName()
            )
            sheet.write(
                index + 1, 5, self.scene.showAliases() and " " or person.birthName()
            )
            sheet.write(index + 1, 6, person.gender())
            sheet.write(index + 1, 7, person.deceased() and "YES" or "")
            sheet.write(index + 1, 8, person.deceasedReason())
            sheet.write(index + 1, 9, person.deceasedDateTime(string=True))
            sheet.write(index + 1, 10, person.adopted() and "YES" or "")
            sheet.write(index + 1, 11, person.adoptedDateTime(string=True))
            sheet.write(
                index + 1, 12, self.scene.showAliases() and " " or person.notes()
            )
            #
            sheet.write(index + 1, 13, person.showMiddleName() and "YES" or "")
            sheet.write(index + 1, 14, person.showLastName() and "YES" or "")
            sheet.write(index + 1, 15, person.showNickName() and "YES" or "")
            sheet.write(index + 1, 16, person.primary() and "YES" or "")
            sheet.write(index + 1, 17, person.hideDetails() and "YES" or "")
        book.close()

    def writeJSON(self, filePath):
        data = {}
        self.scene.write(data)

        class QtObjectEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, QDateTime):
                    if obj.isNull():
                        return None
                    return obj.toString("yyyy-MM-ddTHH:mm:ss")
                elif isinstance(obj, QDate):
                    if obj.isNull():
                        return None
                    return obj.toString("yyyy-MM-dd")
                elif isinstance(obj, QColor):
                    return obj.name()
                elif isinstance(obj, (QSize, QSizeF)):
                    return {"width": obj.width(), "height": obj.height()}
                elif isinstance(obj, (QPoint, QPointF)):
                    return {"x": obj.x(), "y": obj.y()}
                elif isinstance(obj, (QRect, QRectF)):
                    return {
                        "x": obj.x(),
                        "y": obj.y(),
                        "width": obj.width(),
                        "height": obj.height(),
                    }
                return super().default(obj)

        p_sdata = json.dumps(data, indent=4, cls=QtObjectEncoder)
        log.info(p_sdata)
        with open(filePath, "w") as f:
            f.write(p_sdata)

    def onPrint(self):
        printer = QPrinter()
        printer.setOrientation(QPrinter.Landscape)
        if printer.outputFormat() != QPrinter.NativeFormat:
            QMessageBox.information(
                self.dv,
                "No printers available",
                "You need to set up a printer on your computer before you use this feature.",
            )
            return
        dlg = QPrintDialog(printer, self.dv)
        ret = dlg.exec()
        if ret == QDialog.Accepted:
            _isUIDarkMode = CUtil.instance().isUIDarkMode
            CUtil.instance().isUIDarkMode = lambda: False
            QApplication.instance().paletteChanged.emit(
                QApplication.instance().palette()
            )  # onSystemPaletteChanged()
            self.writeJPG(printer=printer)
            CUtil.instance().isUIDarkMode = _isUIDarkMode
            QApplication.instance().paletteChanged.emit(
                QApplication.instance().palette()
            )  # .onSystemPaletteChanged()
