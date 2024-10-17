import enum
import logging

from .pyqt import (
    Qt,
    QScrollArea,
    QWidget,
    QPainter,
    QSize,
    QColor,
    QPoint,
    QApplication,
    QImage,
    QPixmap,
    QLabel,
    QTransform,
    QSlider,
    QHBoxLayout,
    QAction,
    QMenu,
    QWidgetAction,
)
from . import util, widgets

_log = logging.getLogger(__name__)


class ItemMixin:

    def __init__(self, objectName: str = None, visible: callable = None):
        self.visible = visible
        self._requestedVisible = True
        if objectName:
            self.setObjectName(objectName)

    @property
    def name(self):
        return self.widget.objectName()

    def requestedVisible(self) -> bool:
        return self._requestedVisible

    def updateVisible(self):
        """
        Update the cache for if this item should be visible:
        """
        visible = True
        if self.visible is not None:
            if callable(self.visible):
                visible = self.visible()
            elif isinstance(self.visible, bool):
                visible = self.visible
        if visible:
            self.show()
        else:
            self.hide()
        self._requestedVisible = visible

    def setToolBar(self, toolbar: "ToolBar"):
        self.setParent(toolbar.widget())


class ButtonItemMixin(ItemMixin):

    def __init__(
        self,
        objectName: str = None,
        autoInvertColor: bool = True,
        ignoreToggle: bool = False,  # don't draw `down` when toggled
        helpPixmap: str = None,
        action: QAction = None,
        visible: callable = None,
    ):
        ItemMixin.__init__(
            self,
            objectName=objectName,
            visible=visible,
        )
        self.action = action
        self.autoInvertColor = autoInvertColor
        self.ignoreToggle = ignoreToggle
        self.helpPixmap = helpPixmap
        self.setObjectName(objectName)
        if self.action:
            self.action.changed.connect(self.onActionChanged)
            self.onActionChanged()
            if self.action.isCheckable():
                if self.ignoreToggle:
                    self.clicked.connect(self.onButtonToggled)
                else:
                    self.toggled[bool].connect(self.onButtonToggled)
            else:
                self.clicked.connect(self.onTriggered)
        if not self.ignoreToggle:
            self.button.setCheckable(self.action.isCheckable())

    def setToolBar(self, toolbar: "ToolBar") -> QLabel:
        """Set the toolbar and create the help tip label."""
        ItemMixin.setToolBar(self, toolbar)
        if self.helpPixmap:
            pixmapPath = util.QRC + "help-tips/" + self.helpPixmap
            image = QImage(pixmapPath)
            image.invertPixels(QImage.InvertRgb)
            pixmap = QPixmap(image)
            pixmap.setDevicePixelRatio(2.0)
            if toolbar.position == Position.North:
                transform = QTransform()
                transform.rotate(80)
                pixmap = pixmap.transformed(transform)
            if hasattr(toolbar, "helpOverlay"):
                helpTipLabel = QLabel(toolbar.helpOverlay)
                helpTipLabel.setPixmap(pixmap)
                helpTipLabel.setObjectName(self.helpPixmap)
                helpTipLabel.adjustSize()
                helpTipLabel._button = self.button
                helpTipLabel._attrs = self.helpPixmap
                return helpTipLabel

    @property
    def button(self):
        return self

    def onTriggered(self, *args):
        self.action.triggered.emit(*args)

    def onButtonToggled(self, on: bool = None):
        if self.ignoreToggle:
            on = not self.action.isChecked()
        if on != self.action.isChecked():
            self.action.setChecked(on)
            if self.action.actionGroup():
                self.action.actionGroup().triggered.emit(self.action)  # qt bug fix?

    def onActionChanged(self):
        if self.action.isEnabled() != self.button.isEnabled():
            self.button.setEnabled(self.action.isEnabled())
        if not self.ignoreToggle and self.action.isChecked() != self.button.isChecked():
            self.button.setChecked(self.action.isChecked())


class PushButton(widgets.PixmapPushButton, ButtonItemMixin):
    def __init__(
        self,
        objectName: str,
        pixmap: str = None,
        helpPixmap: str = None,
        action: QAction = None,
        visible: callable = None,
        ignoreToggle: bool = False,
        autoInvertColor: bool = True,
    ):
        widgets.PixmapPushButton.__init__(
            self,
            uncheckedPixmapPath=pixmap,
            autoInvertColor=autoInvertColor,
        )
        ButtonItemMixin.__init__(
            self,
            objectName=objectName,
            action=action,
            helpPixmap=helpPixmap,
            visible=visible,
            ignoreToggle=ignoreToggle,
        )


class ToolButton(widgets.PixmapToolButton, ButtonItemMixin):
    def __init__(
        self,
        objectName: str,
        pixmap: str = None,
        helpPixmap: str = None,
        action: QAction = None,
        visible: callable = None,
        ignoreToggle: bool = False,
        autoInvertColor: bool = True,
    ):
        widgets.PixmapToolButton.__init__(
            self,
            uncheckedPixmapPath=pixmap,
            autoInvertColor=autoInvertColor,
        )
        ButtonItemMixin.__init__(
            self,
            objectName=objectName,
            action=action,
            helpPixmap=helpPixmap,
            visible=visible,
            ignoreToggle=ignoreToggle,
        )


class Separator(QWidget, ItemMixin):

    def __init__(self, parent=None, objectName: str = None, visible: callable = None):
        QWidget.__init__(self, parent=parent)
        ItemMixin.__init__(self, objectName=objectName, visible=visible)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setBrush(util.GRID_COLOR)
        p.setPen(util.GRID_COLOR)
        p.drawRect(self.rect())
        p = None


class Position(enum.Enum):
    North = "north"
    West = "west"
    East = "east"


class ToolBar(QScrollArea):

    RESPONSIVE_MARGIN = 30

    # Extra room on the scroll access to prevent 1-2px jigging at full size
    PADDING = 2

    @property
    def mw(self):
        """Only use this in late-stage ui interaction, not setup so these can be unit tested."""
        if util.isInstance(self.parent(), "View"):
            return self.parent().parent().mw

    def view(self):
        return self.parent()

    def __init__(self, parent, ui, position: Position):
        super().__init__(parent)
        self.position = position
        self.ui = ui
        self.scene = None  # store for interaction with the scene
        self.items = []
        self.buttons = []
        self.helpTipLabels = []
        self._isInEditorMode = False
        self._isAppUpdateAvailable = False
        self._isNotReadOnly = True
        if self.position == Position.North:
            self.MARGIN_X = util.MARGIN_X
            self.MARGIN_Y = util.MARGIN_Y
        else:
            self.MARGIN_X = util.MARGIN_X
            self.MARGIN_Y = round(util.MARGIN_Y / 2)
        self._lastViewSize = QSize()
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(QWidget())
        # Disable scrolling in the opposing axis altogether
        if self.position == Position.North:
            self.verticalScrollBar().setEnabled(False)
            self.setViewportMargins(-self.PADDING * 2, 0, -self.PADDING * 2, 0)
        else:
            self.horizontalScrollBar().setEnabled(False)
            self.setViewportMargins(0, -self.PADDING * 2, 0, -self.PADDING * 2)
        QApplication.instance().paletteChanged.connect(self.onApplicationPaletteChanged)
        self.ui.actionEditor_Mode.toggled[bool].connect(
            lambda: self.onItemsVisibilityChanged()
        )
        # self.buttonGroup = widgets.ButtonGroup(self)
        if util.ENABLE_DROP_SHADOWS:
            self.setGraphicsEffect(
                util.makeDropShadow(
                    offset=0, blurRadius=2, color=QColor(100, 100, 100, 70)
                )
            )
        self.onApplicationPaletteChanged()
        self.onItemsVisibilityChanged()

    def onApplicationPaletteChanged(self):
        ss = ""
        # background
        if util.IS_IOS and not util.IS_UI_DARK_MODE:
            ss = (
                ss
                + """
                background-color: white;
            """
            )
        elif util.IS_UI_DARK_MODE:
            ss = (
                ss
                + """
                background-color: rgba(75, 75, 82, .8);
            """
            )
        else:
            ss = (
                ss
                + """
                background-color: rgba(255, 255, 255, .8);
            """
            )
        # border
        if util.IS_IOS and not util.IS_UI_DARK_MODE:
            ss = (
                ss
                + """
                border: 1px solid #ccc;
            """
            )
        elif util.IS_UI_DARK_MODE:
            ss = (
                ss
                + """
                border: 1px solid #545358;
            """
            )
        else:
            ss = (
                ss
                + """
                border: 1px solid #d8d8d8;
            """
            )
        if self.position == Position.North:
            ss = (
                ss
                + """
                border-top: 0;
                border-bottom-right-radius: 5px;
                border-bottom-left-radius: 5px;
            """
            )
        elif self.position == Position.West:
            ss = (
                ss
                + """
                border-left: 0;
                border-bottom-right-radius: 5px;
                border-top-right-radius: 5px;
            """
            )
        elif self.position == Position.East:
            ss = (
                ss
                + """
                border-right: 0;
                border-bottom-left-radius: 5px;
                border-top-left-radius: 5px;
            """
            )
        self.setStyleSheet("ToolBar { %s }" % ss)
        self.widget().setStyleSheet("QWidget { background-color: transparent; }")
        # debugging
        # self.widget().setStyleSheet("""
        #     background-color: #f00;
        # """)

        for child in self.findChildren(widgets.PixmapButtonHelper):
            if isinstance(child, widgets.PixmapButtonHelper):
                child.onApplicationPaletteChanged()

    def setScene(self, scene):
        self.scene = scene

    def addItems(self, *items: list[ItemMixin]):
        for item in items:
            item.setToolBar(self)
            if isinstance(item, (PushButton, ToolButton)):
                self.buttons.append(item)
            if isinstance(item, Separator):
                # no spacing for separators
                if self.position == Position.North:
                    item.setFixedSize(1, util.BUTTON_SIZE)
                elif self.position == Position.West:
                    item.setFixedSize(util.BUTTON_SIZE, 1)
                elif self.position == Position.East:
                    item.setFixedSize(util.BUTTON_SIZE, 1)
            setattr(self, item.objectName(), item)
            item.updateVisible()
            self.items.append(item)

    def isInBounds(self, w: QWidget, size=None) -> bool:
        size = size or self.size()
        if self.position == Position.North:
            return w.x() + w.width() < size.width() - self.RESPONSIVE_MARGIN * 2
        elif self.position in (Position.West, Position.East):
            return w.y() + w.height() < size.height() - self.RESPONSIVE_MARGIN * 2

    def onlyShownInEditorMode(self) -> bool:
        return False

    def adjust(self, viewSize: QSize = None):
        """
        Adjust item size and visibility, scrollable viewport size.
        """
        if viewSize is None:
            viewSize = self._lastViewSize
        else:
            self._lastViewSize = viewSize

        ## Item Positions

        if self.position == Position.North:
            self.cur = self.MARGIN_X
        elif self.position == Position.West:
            self.cur = self.MARGIN_Y
        elif self.position == Position.East:
            self.cur = self.MARGIN_Y
        toUpdate = [x for x in self.items if x.requestedVisible()]
        for item in toUpdate:
            if item:
                if self.position == Position.North:
                    item.move(self.cur, self.MARGIN_Y)
                    shift = item.width() + self.MARGIN_X
                elif self.position == Position.West:
                    item.move(self.MARGIN_X, self.cur)
                    shift = item.height() + self.MARGIN_Y
                elif self.position == Position.East:
                    item.move(self.MARGIN_X, self.cur)
                    shift = item.height() + self.MARGIN_Y
                self.cur += shift
                item.updateGeometry()
            else:
                # Separators
                if self.position == Position.North:
                    item.move(self.cur, self.MARGIN_Y)
                    shift = self.MARGIN_X
                elif self.position == Position.West:
                    item.move(self.MARGIN_X, self.cur)
                    shift = self.MARGIN_Y
                elif self.position == Position.East:
                    item.move(self.MARGIN_X, self.cur)
                    shift = self.MARGIN_Y
                self.cur += shift
        if self.position == Position.North:
            self.widget().resize(self.cur, util.BUTTON_SIZE + self.MARGIN_Y * 2)
        elif self.position in (Position.West, Position.East):
            self.widget().resize(
                util.BUTTON_SIZE + self.MARGIN_X * 2, self.cur + self.MARGIN_Y
            )

        ## Responsive size, hide if all buttons out of bounds.

        lastInBounds = None
        for item in self.items:
            inBounds = self.isInBounds(item, viewSize)
            if inBounds and item and item.requestedVisible():
                lastInBounds = item
            # if self.items[index-1][1] is None: # separator just before
            #     sep = getattr(self, name)
            #     sep.setVisible(inBounds)
        if lastInBounds:
            self.setVisible(True)
            # this assumes that each item is added right at the margin from the previous
            if self.position == Position.North:
                self.resize(
                    lastInBounds.x() + lastInBounds.width() + self.PADDING,
                    self.height(),
                )
            elif self.position in (Position.West, Position.East):
                self.resize(
                    self.width(),
                    lastInBounds.y() + lastInBounds.height() + self.PADDING,
                )

        if not self.isInEditorMode() and self.onlyShownInEditorMode():
            self.setVisible(False)
        else:
            if lastInBounds:
                self.setVisible(True)
            elif not lastInBounds:
                self.setVisible(False)

        if not self.buttons:
            return

        ## Help labels

        firstButtonPos = self.mapTo(self.parent(), self.buttons[0].pos())
        # dpr = self.devicePixelRatio()
        dpr = 2  # hack; no idea
        for label in self.helpTipLabels:
            viewPos = label._button.mapTo(
                self.parent(), label._button.pos()
            )  # helpOverlay coordinates are the same as view coordinates
            yOff = (viewPos.y() - firstButtonPos.y()) / dpr
            xOff = (viewPos.x() - firstButtonPos.x()) / dpr
            # QWidget.mapTo() semes to have a bug in it where it is using different devicePixelRatio values
            # between this toolbar and the View. Strangely, the first button appears to have the right mapped pos.
            # So the hack is to use view's devicePixelRatio up to this toolbar postion (actually the first button's position),
            # then use this toolbar's devicePixelRatio for the relative offset for subsequent buttons
            if self.position == Position.West:
                viewPosHacked = QPoint(
                    int(self.width() + util.MARGIN_X * 2),
                    int(firstButtonPos.y() + yOff),
                )
            elif self.position == Position.North:
                viewPosHacked = QPoint(
                    int(firstButtonPos.x() + xOff + 15),
                    int(self.height() + util.MARGIN_Y),
                )
            elif self.position == Position.East:
                viewPosHacked = QPoint(
                    int(
                        self.parent().width()
                        - self.width()
                        - util.MARGIN_X * 2
                        - label.width()
                    ),
                    int(firstButtonPos.y() + yOff),
                )
            label.move(viewPosHacked)
            if label._button.isVisible() != label.isVisible():
                label.setVisible(label._button.isVisible())

    # Visibility helpers

    def onItemsVisibilityChanged(self):
        """
        Update + cache the callback values, then update all items accordingly.
        """
        self._isInEditorMode = self.ui.actionEditor_Mode.isChecked()
        self._isAppUpdateAvailable = self.ui.actionInstall_Update.isEnabled()
        if self.view() and self.view().scene():
            self._isNotReadOnly = not self.view().scene().readOnly()
        else:
            self._isNotReadOnly = True
        for item in self.items:
            item.updateVisible()
        self.adjust()

    def isInEditorMode(self) -> bool:
        return self._isInEditorMode

    def isAppUpdateAvailable(self) -> bool:
        return self._isAppUpdateAvailable

    def isNotReadOnly(self) -> bool:
        return self._isNotReadOnly


class SceneToolBar(ToolBar):

    def __init__(self, parent, ui):
        super().__init__(parent, ui, Position.North)
        self.setObjectName("sceneToolBar")
        self.addItems(
            # ('newButton', {
            #     'path': 'new-button.png',
            #     'action': self.ui.actionNew
            # }),
            PushButton(
                objectName="homeButton",
                pixmap="home-button.png",
                action=self.ui.actionClose,
                helpPixmap="home.png",
            ),
            # ('shareButton', {
            #     'path': 'share-button.png',
            #     'action': self.ui.actionSave_As
            # }),
            Separator(objectName="sep1", visible=self.isInEditorMode),
            PushButton(
                objectName="zoomFitButton",
                pixmap="zoom-fit-button.png",
                action=self.ui.actionZoom_Fit,
                helpPixmap="zoom-to-fit.png",
                visible=self.isInEditorMode,
            ),
            PushButton(
                objectName="dateSliderButton",
                pixmap="date-slider-button.png",
                action=self.ui.actionShow_Graphical_Timeline,
                ignoreToggle=True,
                helpPixmap="timeline-slider.png",
                visible=self.isInEditorMode,
            ),
            PushButton(
                objectName="hideButton",
                pixmap="presentation-mode.png",
                action=self.ui.actionHide_ToolBars,
                helpPixmap="presentation-mode.png",
                visible=self.isInEditorMode,
            ),
            PushButton(
                objectName="notesButton",
                pixmap="paper-clip.png",
                action=self.ui.actionShow_Items_with_Notes,
                helpPixmap="show-items-with-notes.png",
                visible=self.isInEditorMode,
            ),
            Separator(objectName="sep2", visible=self.isInEditorMode),
            PushButton(
                objectName="prevLayerButton",
                pixmap="prev-layer-button.png",
                action=self.ui.actionPrevious_Layer,
                helpPixmap="previous-view.png",
                visible=self.isInEditorMode,
            ),
            PushButton(
                objectName="nextLayerButton",
                pixmap="next-layer-button.png",
                action=self.ui.actionNext_Layer,
                helpPixmap="next-view.png",
                visible=self.isInEditorMode,
            ),
            PushButton(
                objectName="resetAllButton",
                pixmap="reset-all-button.png",
                action=self.ui.actionReset_All,
                helpPixmap="reset-diagram.png",
            ),
            Separator(objectName="sep3", visible=self.isInEditorMode),
            PushButton(
                objectName="undoButton",
                pixmap="undo-button.png",
                action=self.ui.actionUndo,
                helpPixmap="undo.png",
                visible=self.isInEditorMode,
            ),
            PushButton(
                objectName="redoButton",
                pixmap="redo-button.png",
                action=self.ui.actionRedo,
                helpPixmap="redo.png",
                visible=self.isInEditorMode,
            ),
            PushButton(
                objectName="helpButton",
                pixmap="help-button.png",
                action=self.ui.actionShow_Tips,
                visible=self.isInEditorMode,
            ),
            Separator(objectName="sep4", visible=self.isInEditorMode),
            PushButton(
                objectName="accountButton",
                pixmap="cart-button.png",
                action=self.ui.actionShow_Account,
                autoInvertColor=False,
                helpPixmap="show-account.png",
            ),
            PushButton(
                objectName="downloadUpdateButton",
                pixmap="update-available-button.png",
                action=self.ui.actionInstall_Update,
                autoInvertColor=False,
                visible=self.isAppUpdateAvailable,
            ),
            # PushButton(
            #     objectName="startProfileButton",
            #     pixmap="plus-button.png",
            #     action=self.ui.actionStart_Profile,
            #     visible=util.IS_IOS,
            #     helpPixmap="home.png",
            # ),
            # PushButton(
            #     objectName="stopProfileButton",
            #     pixmap="delete-button.png",
            #     action=self.ui.actionStop_Profile,
            #     visible=util.IS_IOS,
            #     helpPixmap="home.png",
            # ),
        )


class ItemToolBar(ToolBar):

    def __init__(self, parent, ui):
        super().__init__(parent, ui, Position.West)
        self.setObjectName("itemToolBar")
        # self.buttonGroup.changed[int].connect(self.onButton)
        self.addItems(
            PushButton(
                objectName="maleButton",
                pixmap="male-button.png",
                action=self.ui.actionMale,
                helpPixmap="male.png",
            ),
            PushButton(
                objectName="femaleButton",
                pixmap="female-button.png",
                action=self.ui.actionFemale,
                helpPixmap="female.png",
            ),
            PushButton(
                objectName="marriageButton",
                pixmap="marriage-button.png",
                action=self.ui.actionMarriage,
                helpPixmap="pair-bond.png",
            ),
            PushButton(
                objectName="childButton",
                pixmap="child-button.png",
                action=self.ui.actionChild_Of,
                helpPixmap="child.png",
            ),
            PushButton(
                objectName="parentsButton",
                pixmap="add-parents.png",
                action=self.ui.actionParents_to_Selection,
                helpPixmap="parents.png",
            ),
            Separator(
                objectName="sep1",
                visible=self.isInEditorMode,
            ),
            PushButton(
                objectName="distanceButton",
                pixmap="distance.png",
                action=self.ui.actionDistance,
                visible=self.isInEditorMode,
                helpPixmap="distance.png",
            ),
            PushButton(
                objectName="conflictButton",
                pixmap="conflict.png",
                action=self.ui.actionConflict,
                visible=self.isInEditorMode,
                helpPixmap="conflict.png",
            ),
            PushButton(
                objectName="reciprocityButton",
                pixmap="reciprocity.png",
                action=self.ui.actionReciprocity,
                visible=self.isInEditorMode,
                helpPixmap="reciprocity.png",
            ),
            PushButton(
                objectName="projectionButton",
                pixmap="projection.png",
                action=self.ui.actionProjection,
                visible=self.isInEditorMode,
                helpPixmap="projection.png",
            ),
            Separator(
                objectName="sep2",
                visible=self.isInEditorMode,
            ),
            PushButton(
                objectName="cutoffButton",
                pixmap="cutoff.png",
                action=self.ui.actionPrimary_Cutoff,
                visible=self.isInEditorMode,
                helpPixmap="cutoff.png",
            ),
            PushButton(
                objectName="fusionButton",
                pixmap="fusion.png",
                action=self.ui.actionFusion,
                visible=self.isInEditorMode,
                helpPixmap="fusion.png",
            ),
            PushButton(
                objectName="insideButton",
                pixmap="inside.png",
                action=self.ui.actionInside,
                visible=self.isInEditorMode,
                helpPixmap="inside.png",
            ),
            PushButton(
                objectName="outsideButton",
                pixmap="outside.png",
                action=self.ui.actionOutside,
                visible=self.isInEditorMode,
                helpPixmap="outside.png",
            ),
            Separator(
                objectName="sep3",
                visible=self.isInEditorMode,
            ),
            PushButton(
                objectName="towardButton",
                pixmap="toward.png",
                action=self.ui.actionToward,
                visible=self.isInEditorMode,
                helpPixmap="toward.png",
            ),
            PushButton(
                objectName="awayButton",
                pixmap="away.png",
                action=self.ui.actionAway,
                visible=self.isInEditorMode,
                helpPixmap="away.png",
            ),
            PushButton(
                objectName="definedSelfButton",
                pixmap="defined-self.png",
                action=self.ui.actionDefined_Self,
                visible=self.isInEditorMode,
                helpPixmap="defined-self.png",
            ),
            Separator(
                objectName="sep4",
                visible=self.isInEditorMode,
            ),
            PushButton(
                objectName="calloutButton",
                pixmap="callout.png",
                action=self.ui.actionCallout,
                visible=self.isInEditorMode,
                helpPixmap="text-callout.png",
            ),
            ToolButton(
                objectName="pencilButton",
                pixmap="pencil-button.png",
                action=self.ui.actionPencilStroke,
                visible=self.isInEditorMode,
                helpPixmap="pencil-drawing.png",
            ),
            # ('eraserButton', {
            #     'path': 'eraser-button.png',
            #     'id': util.ITEM_ERASER
            # })
        )

        # pencil width slider
        self.pencilPopup = QWidget()
        self.pencilPopup.setFixedWidth(200)
        self.pencilSlider = QSlider(Qt.Horizontal, self.pencilPopup)
        self.pencilSlider.setMinimum(10)
        self.pencilSlider.setMaximum(250)
        self.pencilSlider.setFixedWidth(
            80
        )  # avoid jitter from label changing width with value.
        self.pencilSlider.valueChanged[int].connect(self.onPencilSlider)
        self.pencilLabel = QLabel(self.pencilPopup)
        self.pencilColorBox = widgets.ColorBox(self.pencilPopup)
        self.pencilColorBox.currentColorChanged[QColor].connect(self.onPencilColor)
        PencilLayout = QHBoxLayout(self.pencilPopup)
        PencilLayout.setSpacing(12)
        PencilLayout.addWidget(self.pencilSlider)
        PencilLayout.addWidget(self.pencilLabel)
        PencilLayout.addWidget(self.pencilColorBox)
        self.pencilMenu = QMenu()
        self.pencilButton.setMenu(self.pencilMenu)
        self.pencilAction = QWidgetAction(self.pencilMenu)
        self.pencilAction.setDefaultWidget(self.pencilPopup)
        self.pencilMenu.addAction(self.pencilAction)
        self.pencilMenu.aboutToShow.connect(self.onPencilShow)
        self.pencilMenu.aboutToHide.connect(self.onPencilHide)

    def onPencilShow(self):
        if self.scene:
            self.pencilSlider.setValue(self.scene.pencilScale() * 100)  # trigger signal
            self.pencilColorBox.setCurrentColor(self.scene.pencilColor())

    def onPencilHide(self):
        self.pencilButton.setChecked(True)  # button is auto unchecked on hide menu

    def onPencilSlider(self, x):
        if self.scene:
            scale = x / 100
            self.scene.setPencilScale(scale)
            self.pencilLabel.setText("%.2f" % (scale * 10))

    def onPencilColor(self, color):
        if self.scene:
            if color != self.scene.pencilColor():
                self.scene.setPencilColor(color)


class RightToolBar(ToolBar):

    def __init__(self, parent, ui):
        super().__init__(parent, ui, Position.East)
        self.setObjectName("rightToolBar")
        # self.buttonGroup.changed[int].connect(self.onButton)
        self.addItems(
            PushButton(
                objectName="addAnythingButton",
                pixmap="plus-button-green.png",
                action=self.ui.actionAdd_Anything,
                autoInvertColor=False,
                visible=self.isNotReadOnly(),
                # "help-tip": {
                #     "pixmap": "family-timeline.png",
                # },
            ),
            Separator(objectName="sep1"),
            PushButton(
                objectName="timelineButton",
                pixmap="timeline-button.png",
                action=self.ui.actionShow_Timeline,
                helpPixmap="family-timeline.png",
            ),
            PushButton(
                objectName="searchButton",
                pixmap="search-button.png",
                action=self.ui.actionShow_Search,
                helpPixmap="search.png",
            ),
            PushButton(
                objectName="settingsButton",
                pixmap="settings-button.png",
                action=self.ui.actionShow_Settings,
                helpPixmap="diagram-settings.png",
                visible=self.isInEditorMode,
            ),
            Separator(objectName="sep2", visible=self.isInEditorMode),
            PushButton(
                objectName="detailsButton",
                pixmap="details-button.png",
                action=self.ui.actionInspect,
                helpPixmap="inspect-selection.png",
                visible=self.isInEditorMode,
            ),
            PushButton(
                objectName="deleteButton",
                pixmap="delete-button.png",
                action=self.ui.actionDelete,
                helpPixmap="delete-item.png",
            ),
            # ('addEventButton', {
            #     'path': 'add-event-button.png',
            #     'action': self.ui.actionAdd_Event,
            #     'help-tip': {
            #         'pixmap': 'add-event.png',
            #     }
            # }),
            # ('addEmotionButton', {
            #     'path': 'add-emotion-button.png',
            #     'action': self.ui.actionAdd_Relationship,
            #     'help-tip': {
            #         'pixmap': 'add-relationship.png',
            #     }
            # }),
        )
