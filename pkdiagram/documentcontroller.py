import logging
import vedana
from pkdiagram.pyqt import (
    QObject,
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
    QKeySequence,
    QJSValue,
)
from pkdiagram import (
    util,
    CUtil,
    commands,
    Property,
    Person,
    Marriage,
    Emotion,
    Event,
    LayerItem,
    Layer,
    ChildOf,
)


log = logging.getLogger(__name__)


class DocumentController(QObject):
    """
    - Anything that connects actions with objects goes in here.
    - Wrangling views goes in DocumentController.
    """

    @property
    def dv(self):
        return self.parent()

    @property
    def view(self):
        return self.dv.view

    ui = None
    scene = None
    _ignoreSelectionChanges = False
    _isUpdatingSearchTags = False

    def init(self):
        assert self.ui is None
        self.ui = self.dv.ui

        # Edit
        self.ui.actionUndo.triggered.connect(self.view.onUndo)
        self.ui.actionRedo.triggered.connect(self.view.onRedo)
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
        self.ui.actionAdd_Event.triggered.connect(self.dv.onAddEvent)
        self.ui.actionAdd_Relationship.triggered.connect(self.dv.onAddEmotion)
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
        self.ui.actionParents_to_Selection.triggered.connect(
            self.view.addParentsToSelection
        )
        self.ui.actionMale.setData(util.ITEM_MALE)
        self.ui.actionFemale.setData(util.ITEM_FEMALE)
        self.ui.actionMarriage.setData(util.ITEM_MARRY)
        self.ui.actionChild_Of.setData(util.ITEM_CHILD)
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
        self.ui.actionShow_Diagram.triggered.connect(self.dv.showDiagram)
        self.ui.actionShow_Timeline.triggered.connect(self.dv.showTimeline)
        self.ui.actionShow_Items_with_Notes.toggled.connect(
            self.dv.view.showItemsWithNotes
        )
        self.ui.actionShow_Search.triggered.connect(self.dv.showSearch)
        self.ui.actionShow_Search.setShortcuts(
            [self.ui.actionShow_Search.shortcuts()[0], QKeySequence("Shift+Ctrl+f")]
        )
        self.ui.actionShow_Settings.triggered.connect(self.dv.showSettings)
        #
        self.ui.actionZoom_In.triggered.connect(self.view.zoomIn)
        self.ui.actionZoom_Out.triggered.connect(self.view.zoomOut)
        self.ui.actionZoom_Fit.triggered.connect(self.onZoomFit)
        self.view.zoomFitDirty[bool].connect(self.onZoomFitDirty)

    def setScene(self, scene):
        if self.scene:
            self.scene.searchModel.clear()
            self.scene.searchModel.tagsChanged.disconnect(self.onSearchTagsChanged)
            self.scene.propertyChanged[Property].disconnect(self.onSceneProperty)
            self.scene.itemModeChanged.disconnect(self.onSceneItemMode)
            self.scene.itemDoubleClicked.disconnect(self.onItemDoubleClicked)
            self.scene.layerAdded[Layer].disconnect(self.onSceneLayersChanged)
            self.scene.layerChanged[Property].disconnect(self.onLayerChanged)
            self.scene.layerRemoved[Layer].disconnect(self.onSceneLayersChanged)
            self.scene.activeLayersChanged.disconnect(self.onActiveLayers)
            self.scene.showNotes.disconnect(self.showNotesFor)
        self.scene = scene
        if self.scene:
            self.scene.propertyChanged[Property].connect(self.onSceneProperty)
            self.scene.searchModel.tagsChanged.connect(self.onSearchTagsChanged)
            self.scene.itemModeChanged.connect(self.onSceneItemMode)
            self.scene.itemDoubleClicked.connect(self.onItemDoubleClicked)
            self.scene.layerAdded[Layer].connect(self.onSceneLayersChanged)
            self.scene.layerChanged[Property].connect(self.onLayerChanged)
            self.scene.layerRemoved[Layer].connect(self.onSceneLayersChanged)
            self.scene.activeLayersChanged.connect(self.onActiveLayers)
            self.scene.showNotes.connect(self.showNotesFor)
        self.onSceneTagsChanged()
        self.onSceneLayersChanged()

    ## Non-verbal reactive event handlers

    def onSceneProperty(self, prop):
        if prop.name() == "tags":
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
            if tag in self.scene.searchModel.tags:
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
        self._isUpdatingSearchTags = False

    def onTagToggled(self, on):
        if self._isUpdatingSearchTags:
            return
        action = self.sender()
        tag = action.data()
        tags = list(self.scene.searchModel.tags)
        if on and not tag in tags:
            tags.append(tag)
        elif not on and tag in tags:
            tags.remove(tag)
        self.scene.searchModel.tags = tags

    @util.blocked
    def onActiveLayers(self, activeLayers):
        self.updateActions()
        ids = [layer.id for layer in activeLayers]
        for action in self.ui.menuLayers.actions():
            on = action.data() in ids
            if on != action.isChecked:
                action.setChecked(on)

    @util.blocked
    def onLayerActionToggled(self, on):
        """Exclusive selection."""
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
            sceneLayers = self.scene.layers()
            activeLayers = [layer for layer in self.scene.layers() if layer.active()]
            for layer in sceneLayers:
                action = QAction(self)
                action.setText(layer.name())
                action.setData(layer.id)
                action.setCheckable(True)
                if layer in activeLayers:
                    action.setChecked(True)
                action.toggled[bool].connect(self.onLayerActionToggled)
                self.ui.menuLayers.addAction(action)
        self.ui.menuLayers.addSeparator()
        self.ui.menuLayers.addAction(self.ui.actionDeactivate_All_Layers)
        self.updateActions()

    def updateActions(self):
        """Idempotent"""
        session = self.dv.session
        isReadOnly = self.scene and self.scene.readOnly()
        # License-dependent
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
                and not isReadOnly
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
        self.ui.actionShow_Search.setEnabled(on)
        self.ui.actionShow_Settings.setEnabled(on)
        self.ui.actionHide_Layers.setEnabled(on)
        self.ui.actionJump_to_Now.setEnabled(on)
        self.ui.actionShow_Current_Date.setEnabled(on)
        self.ui.actionShow_Legend.setEnabled(on)
        self.ui.actionShow_Graphical_Timeline.setEnabled(on)
        self.ui.actionExpand_Graphical_Timeline.setEnabled(on)
        self.ui.actionNext_Event.setEnabled(on)
        self.ui.actionPrevious_Event.setEnabled(on)
        self.ui.actionAdd_Event.setEnabled(on)
        self.ui.actionAdd_Relationship.setEnabled(on)
        self.ui.actionUndo.setEnabled(on and commands.stack().canUndo())
        self.ui.actionRedo.setEnabled(on and commands.stack().canRedo())
        if self.scene:
            numLayers = len(self.scene.layers())
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

    def onPrevEvent(self):
        """Set the current date to the next visible date."""
        # w = QApplication.focusWidget()
        # if isinstance(w, QQuickWidget):
        #     w.parent().prevTab()
        #     return
        if self.scene:
            self.scene.prevTaggedDateTime()

    def onNextEvent(self):
        """Set the current date to the next visible date."""
        # w = QApplication.focusWidget()
        # if isinstance(w, QQuickWidget):
        #     w.parent().nextTab()
        #     return
        if self.scene:
            self.scene.nextTaggedDateTime()

    def onDeselectAllTags(self):
        for action in self.ui.menuTags.actions():
            if action.isCheckable() and action.isChecked():
                action.blockSignals(True)
                action.setChecked(False)
                action.blockSignals(False)
        self.scene.searchModel.reset("tags")

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
        id = commands.nextId()
        for layer in self.scene.activeLayers():
            layer.setActive(False, undo=id)

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
        fw = QApplication.focusWidget()
        if isinstance(fw, QQuickWidget):
            if hasattr(fw.parent(), "onInspect"):
                fw.parent().onInspect(tab)
        else:  # scene
            self.dv.inspectSelection(tab=tab)

    def onInspectItemTab(self):
        self.onInspect(tab="item")

    def onInspectTimelineTab(self):
        self.onInspect(tab="timeline")

    def onInspectNotesTab(self):
        self.onInspect(tab="notes")

    def onInspectMetaTab(self):
        self.onInspect(tab="meta")

    def onItemDoubleClicked(self, item):
        self.onInspect()

    def onInspectItemById(self, itemId):
        item = self.scene.find(itemId)
        self.dv.inspectSelection(selection=[item])

    def onClearSearch(self):
        self.scene.searchModel.clear()
        self.scene.clearActiveLayers()

    def showNotesFor(self, pathItem):
        self._ignoreSelectionChanges = True
        for item in self.scene.selectedItems():
            if item is not pathItem:
                item.setSelected(False)
        if not pathItem.isSelected():
            pathItem.setSelected(True)
        self._ignoreSelectionChanges = False
        self.dv.inspectSelection(tab="notes")
