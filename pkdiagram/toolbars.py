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


class Separator(QWidget):
    def paintEvent(self, e):
        p = QPainter(self)
        p.setBrush(util.GRID_COLOR)
        p.setPen(util.GRID_COLOR)
        p.drawRect(self.rect())
        p = None


class ToolBar(QScrollArea):

    RESPONSIVE_MARGIN = 30

    # Extra room on the scroll access to prevent 1-2px jigging at full size
    PADDING = 2

    @property
    def mw(self):
        """Only use this in late-stage ui interaction, not setup so these can be unit tested."""
        if util.isInstance(self.parent().mw, "MainWindow"):
            return self.parent().mw

    def __init__(self, parent, ui, position):
        super().__init__(parent)
        self.items = []
        self.position = position
        self.ui = ui
        self.scene = None  # store for interaction with the scene
        self.buttonAttrs = {}
        self.buttons = []
        self.separators = []
        self.shouldShow = []
        self.helpTipLabels = []
        if self.position == "north":
            self.MARGIN_X = util.MARGIN_X
            self.MARGIN_Y = util.MARGIN_Y
        else:
            self.MARGIN_X = util.MARGIN_X
            self.MARGIN_Y = round(util.MARGIN_Y / 2)
        self._lastResponsiveSize = QSize()
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(QWidget())
        # Disable scrolling in the opposing axis altogether
        if self.position == "north":
            self.verticalScrollBar().setEnabled(False)
            self.setViewportMargins(-self.PADDING * 2, 0, -self.PADDING * 2, 0)
        else:
            self.horizontalScrollBar().setEnabled(False)
            self.setViewportMargins(0, -self.PADDING * 2, 0, -self.PADDING * 2)
        QApplication.instance().paletteChanged.connect(self.onApplicationPaletteChanged)
        # self.buttonGroup = widgets.ButtonGroup(self)
        if util.ENABLE_DROP_SHADOWS:
            self.setGraphicsEffect(
                util.makeDropShadow(
                    offset=0, blurRadius=2, color=QColor(100, 100, 100, 70)
                )
            )
        self.onApplicationPaletteChanged()

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
        if self.position == "north":
            ss = (
                ss
                + """
                border-top: 0;
                border-bottom-right-radius: 5px;
                border-bottom-left-radius: 5px;
            """
            )
        elif self.position == "west":
            ss = (
                ss
                + """
                border-left: 0;
                border-bottom-right-radius: 5px;
                border-top-right-radius: 5px;
            """
            )
        elif self.position == "east":
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

    def addItems(self, items):
        for index, (name, attrs) in enumerate(items):
            if attrs and "condition" in attrs and not attrs["condition"]:
                continue
            if attrs and not attrs.get("visible", True):
                continue
            if isinstance(attrs, dict):
                toolbutton = attrs.get("toolbutton")
                invert = attrs.get("autoInvertColor", True)
                if toolbutton:
                    button = widgets.PixmapToolButton(
                        self.widget(),
                        uncheckedPixmapPath=attrs["path"],
                        autoInvertColor=invert,
                    )
                else:
                    # all this does is give a popup delay on click and hold
                    button = widgets.PixmapPushButton(
                        self.widget(),
                        uncheckedPixmapPath=attrs["path"],
                        autoInvertColor=invert,
                    )
                button.setObjectName(name)
                self.buttons.append(button)
                slot = attrs.get("slot", None)
                action = attrs.get("action", None)
                ignoreToggle = attrs.get(
                    "ignoreToggle", False
                )  # don't draw `down` when toggled
                helpTip = attrs.get("help-tip")
                if slot:
                    button.clicked.connect(slot)
                elif action:

                    def makeOnActionChanged(action, button, ignoreToggle):
                        def onActionChanged():
                            if action.isEnabled() != button.isEnabled():
                                button.setEnabled(action.isEnabled())
                            if (
                                not ignoreToggle
                                and action.isChecked() != button.isChecked()
                            ):
                                button.setChecked(action.isChecked())

                        return onActionChanged

                    onActionChanged = makeOnActionChanged(action, button, ignoreToggle)
                    onActionChanged()  # init
                    action.changed.connect(onActionChanged)
                    button.setToolTip(action.toolTip())
                    if not ignoreToggle:
                        button.setCheckable(action.isCheckable())
                    if action.isCheckable():

                        def makeOnButtonToggled(button, action, ignoreToggle):
                            def onButtonToggled(on=None):
                                if ignoreToggle:
                                    on = not action.isChecked()
                                if on != action.isChecked():
                                    action.setChecked(on)
                                    if action.actionGroup():
                                        action.actionGroup().triggered.emit(
                                            action
                                        )  # qt bug fix?

                            return onButtonToggled

                        onButtonToggled = makeOnButtonToggled(
                            button, action, ignoreToggle
                        )
                        if ignoreToggle:
                            button.clicked.connect(onButtonToggled)
                        else:
                            button.toggled[bool].connect(onButtonToggled)
                    else:

                        def makeOnTriggered(button, action):
                            def onTriggered(*args):
                                action.triggered.emit(*args)

                            return onTriggered

                        onTriggered = makeOnTriggered(button, action)
                        button.clicked.connect(onTriggered)
                if helpTip:
                    pixmapPath = util.QRC + "help-tips/" + helpTip["pixmap"]
                    button.__helpTip = helpTip
                    image = QImage(pixmapPath)
                    image.invertPixels(QImage.InvertRgb)
                    pixmap = QPixmap(image)
                    pixmap.setDevicePixelRatio(2.0)
                    if self.position == "north":
                        transform = QTransform()
                        transform.rotate(80)
                        pixmap = pixmap.transformed(transform)
                    if hasattr(self.parent(), "helpOverlay"):
                        helpTipLabel = QLabel(self.parent().helpOverlay)
                        helpTipLabel.setPixmap(pixmap)
                        helpTipLabel.setObjectName(helpTip["pixmap"])
                        helpTipLabel.adjustSize()
                        helpTipLabel._button = button
                        helpTipLabel._attrs = helpTip
                        self.helpTipLabels.append(helpTipLabel)
                setattr(self, name, button)
            else:
                # no spacing for separators
                separator = Separator(self.widget())
                if self.position == "north":
                    separator.setFixedSize(1, util.BUTTON_SIZE)
                elif self.position == "west":
                    separator.setFixedSize(util.BUTTON_SIZE, 1)
                elif self.position == "east":
                    separator.setFixedSize(util.BUTTON_SIZE, 1)
                separator.setObjectName(name)
                self.separators.append(separator)
                setattr(self, name, separator)
            self.buttonAttrs[name] = attrs
            self.shouldShow.append(getattr(self, name))
        self.items += items
        self.adjust()

    def setScene(self, scene):
        self.scene = scene

    def onResponsive(self, size):
        lastInBounds = None
        for index, (name, attrs) in enumerate(self.items):
            if not hasattr(self, name):
                continue
            w = getattr(self, name)
            if w not in self.shouldShow:
                continue
            if self.position == "north":
                inBounds = bool(
                    w.x() + w.width() < size.width() - self.RESPONSIVE_MARGIN * 2
                )
            elif self.position in ("west", "east"):
                inBounds = bool(
                    w.y() + w.height() < size.height() - self.RESPONSIVE_MARGIN * 2
                )
            if inBounds and attrs is not None:
                lastInBounds = w
            # if self.items[index-1][1] is None: # separator just before
            #     sep = getattr(self, name)
            #     sep.setVisible(inBounds)
        if lastInBounds:
            self.show()
            # this assumes that each item is added right at the margin from the previous
            if self.position == "north":
                self.resize(
                    lastInBounds.x() + lastInBounds.width() + self.PADDING,
                    self.height(),
                )
            elif self.position in ("west", "east"):
                self.resize(
                    self.width(),
                    lastInBounds.y() + lastInBounds.height() + self.PADDING,
                )
        else:
            self.hide()

        # Help labels
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
            if self.position == "west":
                viewPosHacked = QPoint(
                    int(self.width() + util.MARGIN_X * 2),
                    int(firstButtonPos.y() + yOff),
                )
            elif self.position == "north":
                viewPosHacked = QPoint(
                    int(firstButtonPos.x() + xOff + 15),
                    int(self.height() + util.MARGIN_Y),
                )
            elif self.position == "east":
                viewPosHacked = QPoint(
                    int(
                        self.parent().width()
                        - self.width()
                        - util.MARGIN_X * 2
                        - label.width()
                    ),
                    int(firstButtonPos.y() + yOff),
                )
            offset = label._attrs.get("offset", QPoint())
            label.move(viewPosHacked + offset)
            if label._button.isVisible() != label.isVisible():
                label.setVisible(label._button.isVisible())

        self._lastResponsiveSize = size

    def adjust(self):
        """Call after showing/hiding a button."""
        if self.position == "north":
            self.cur = self.MARGIN_X
        elif self.position == "west":
            self.cur = self.MARGIN_Y
        elif self.position == "east":
            self.cur = self.MARGIN_Y
        for name, attrs in self.buttonAttrs.items():
            item = getattr(self, name)
            if item not in self.shouldShow:
                continue
            if isinstance(attrs, dict):
                button = item
                if self.position == "north":
                    button.move(self.cur, self.MARGIN_Y)
                    shift = button.width() + self.MARGIN_X
                elif self.position == "west":
                    button.move(self.MARGIN_X, self.cur)
                    shift = button.height() + self.MARGIN_Y
                elif self.position == "east":
                    button.move(self.MARGIN_X, self.cur)
                    shift = button.height() + self.MARGIN_Y
                self.cur += shift
                button.updateGeometry()
            else:
                separator = item
                if self.position == "north":
                    separator.move(self.cur, self.MARGIN_Y)
                    shift = self.MARGIN_X
                elif self.position == "west":
                    separator.move(self.MARGIN_X, self.cur)
                    shift = self.MARGIN_Y
                elif self.position == "east":
                    separator.move(self.MARGIN_X, self.cur)
                    shift = self.MARGIN_Y
                self.cur += shift
        if self.position == "north":
            self.widget().resize(self.cur, util.BUTTON_SIZE + self.MARGIN_Y * 2)
        elif self.position in ("west", "east"):
            self.widget().resize(
                util.BUTTON_SIZE + self.MARGIN_X * 2, self.cur + self.MARGIN_Y
            )
        self.onResponsive(self._lastResponsiveSize)

    def showItem(self, item):
        if item not in self.shouldShow:
            self.shouldShow.append(item)
            item.show()
        self.adjust()

    def hideItem(self, item):
        if item in self.shouldShow:
            self.shouldShow.remove(item)
            item.hide()
        self.adjust()

    def isItemShown(self, item):
        return item in self.shouldShow


class SceneToolBar(ToolBar):

    def __init__(self, parent, ui):
        super().__init__(parent, ui, "north")
        self.setObjectName("sceneToolBar")
        self.addItems(
            [
                # ('newButton', {
                #     'path': 'new-button.png',
                #     'action': self.ui.actionNew
                # }),
                (
                    "homeButton",
                    {
                        "path": "home-button.png",
                        "action": self.ui.actionClose,
                        "help-tip": {
                            "pixmap": "home.png",
                        },
                    },
                ),
                # ('shareButton', {
                #     'path': 'share-button.png',
                #     'action': self.ui.actionSave_As
                # }),
                ("sep1", None),
                (
                    "zoomFitButton",
                    {
                        "path": "zoom-fit-button.png",
                        "action": self.ui.actionZoom_Fit,
                        "help-tip": {
                            "pixmap": "zoom-to-fit.png",
                        },
                    },
                ),
                (
                    "dateSliderButton",
                    {
                        "path": "date-slider-button.png",
                        "action": self.ui.actionShow_Graphical_Timeline,
                        "ignoreToggle": True,
                        "help-tip": {
                            "pixmap": "timeline-slider.png",
                        },
                    },
                ),
                (
                    "hideButton",
                    {
                        "path": "presentation-mode.png",
                        "action": self.ui.actionHide_ToolBars,
                        "help-tip": {
                            "pixmap": "presentation-mode.png",
                        },
                    },
                ),
                (
                    "notesButton",
                    {
                        "path": "paper-clip.png",
                        "action": self.ui.actionShow_Items_with_Notes,
                        "help-tip": {
                            "pixmap": "show-items-with-notes.png",
                        },
                    },
                ),
                ("sep2", None),
                (
                    "prevLayerButton",
                    {
                        "path": "prev-layer-button.png",
                        "action": self.ui.actionPrevious_Layer,
                        "help-tip": {
                            "pixmap": "previous-view.png",
                        },
                    },
                ),
                (
                    "nextLayerButton",
                    {
                        "path": "next-layer-button.png",
                        "action": self.ui.actionNext_Layer,
                        "help-tip": {
                            "pixmap": "next-view.png",
                        },
                    },
                ),
                (
                    "resetAllButton",
                    {
                        "path": "reset-all-button.png",
                        "action": self.ui.actionReset_All,
                        "help-tip": {
                            "pixmap": "reset-diagram.png",
                        },
                    },
                ),
                ("sep3", None),
                (
                    "undoButton",
                    {
                        "path": "undo-button.png",
                        "action": self.ui.actionUndo,
                        "help-tip": {
                            "pixmap": "undo.png",
                        },
                    },
                ),
                (
                    "redoButton",
                    {
                        "path": "redo-button.png",
                        "action": self.ui.actionRedo,
                        "help-tip": {
                            "pixmap": "redo.png",
                        },
                    },
                ),
                (
                    "helpButton",
                    {"path": "help-button.png", "action": self.ui.actionShow_Tips},
                ),
                ("sep0", None),
                (
                    "accountButton",
                    {
                        "path": "cart-button.png",
                        "action": self.ui.actionShow_Account,
                        "autoInvertColor": False,
                        "help-tip": {
                            "pixmap": "show-account.png",
                        },
                    },
                ),
                (
                    "downloadUpdateButton",
                    {
                        "path": "update-available-button.png",
                        "action": self.ui.actionInstall_Update,
                        "autoInvertColor": False,
                    },
                ),
                (
                    "startProfileButton",
                    {
                        "path": "plus-button.png",
                        "action": self.ui.actionStart_Profile,
                        "visible": util.IS_IOS,
                        "help-tip": {
                            "pixmap": "home.png",
                        },
                    },
                ),
                (
                    "stopProfileButton",
                    {
                        "path": "delete-button.png",
                        "action": self.ui.actionStop_Profile,
                        "visible": util.IS_IOS,
                        "help-tip": {
                            "pixmap": "home.png",
                        },
                    },
                ),
            ]
        )


class ItemToolBar(ToolBar):

    def __init__(self, parent, ui):
        super().__init__(parent, ui, "west")
        self.setObjectName("itemToolBar")
        # self.buttonGroup.changed[int].connect(self.onButton)
        self.addItems(
            [
                (
                    "maleButton",
                    {
                        "path": "male-button.png",
                        "action": self.ui.actionMale,
                        "help-tip": {
                            "pixmap": "male.png",
                        },
                    },
                ),
                (
                    "femaleButton",
                    {
                        "path": "female-button.png",
                        "action": self.ui.actionFemale,
                        "help-tip": {
                            "pixmap": "female.png",
                        },
                    },
                ),
                (
                    "marriageButton",
                    {
                        "path": "marriage-button.png",
                        "action": self.ui.actionMarriage,
                        "help-tip": {
                            "pixmap": "pair-bond.png",
                        },
                    },
                ),
                (
                    "childButton",
                    {
                        "path": "child-button.png",
                        "action": self.ui.actionChild_Of,
                        "help-tip": {
                            "pixmap": "child.png",
                        },
                    },
                ),
                (
                    "parentsButton",
                    {
                        "path": "add-parents.png",
                        "action": self.ui.actionParents_to_Selection,
                        "help-tip": {
                            "pixmap": "parents.png",
                        },
                    },
                ),
                ("sep1", None),
                (
                    "distanceButton",
                    {
                        "path": "distance.png",
                        "action": self.ui.actionDistance,
                        "help-tip": {
                            "pixmap": "distance.png",
                        },
                    },
                ),
                (
                    "conflictButton",
                    {
                        "path": "conflict.png",
                        "action": self.ui.actionConflict,
                        "help-tip": {
                            "pixmap": "conflict.png",
                        },
                    },
                ),
                (
                    "reciprocityButton",
                    {
                        "path": "reciprocity.png",
                        "action": self.ui.actionReciprocity,
                        "help-tip": {
                            "pixmap": "reciprocity.png",
                        },
                    },
                ),
                (
                    "projectionButton",
                    {
                        "path": "projection.png",
                        "action": self.ui.actionProjection,
                        "help-tip": {
                            "pixmap": "projection.png",
                        },
                    },
                ),
                ("sep2", None),
                (
                    "cutoffButton",
                    {
                        "path": "cutoff.png",
                        "action": self.ui.actionPrimary_Cutoff,
                        "help-tip": {
                            "pixmap": "cutoff.png",
                        },
                    },
                ),
                (
                    "fusionButton",
                    {
                        "path": "fusion.png",
                        "action": self.ui.actionFusion,
                        "help-tip": {
                            "pixmap": "fusion.png",
                        },
                    },
                ),
                (
                    "insideButton",
                    {
                        "path": "inside.png",
                        "action": self.ui.actionInside,
                        "help-tip": {
                            "pixmap": "inside.png",
                        },
                    },
                ),
                (
                    "outsideButton",
                    {
                        "path": "outside.png",
                        "action": self.ui.actionOutside,
                        "help-tip": {
                            "pixmap": "outside.png",
                        },
                    },
                ),
                ("sep3", None),
                (
                    "towardButton",
                    {
                        "path": "toward.png",
                        "action": self.ui.actionToward,
                        "help-tip": {
                            "pixmap": "toward.png",
                        },
                    },
                ),
                (
                    "awayButton",
                    {
                        "path": "away.png",
                        "action": self.ui.actionAway,
                        "help-tip": {
                            "pixmap": "away.png",
                        },
                    },
                ),
                (
                    "definedSelfButton",
                    {
                        "path": "defined-self.png",
                        "action": self.ui.actionDefined_Self,
                        "help-tip": {
                            "pixmap": "defined-self.png",
                        },
                    },
                ),
                ("sep4", None),
                (
                    "calloutButton",
                    {
                        "path": "callout.png",
                        "action": self.ui.actionCallout,
                        "help-tip": {
                            "pixmap": "text-callout.png",
                        },
                    },
                ),
                (
                    "pencilButton",
                    {
                        "path": "pencil-button.png",
                        "action": self.ui.actionPencilStroke,
                        "toolbutton": True,
                        "help-tip": {
                            "pixmap": "pencil-drawing.png",
                        },
                    },
                ),
                # ('eraserButton', {
                #     'path': 'eraser-button.png',
                #     'id': util.ITEM_ERASER
                # })
            ]
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
        super().__init__(parent, ui, "east")
        self.setObjectName("toolToolBar")
        # self.buttonGroup.changed[int].connect(self.onButton)
        self.addItems(
            [
                (
                    "timelineButton",
                    {
                        "path": "timeline-button.png",
                        "action": self.ui.actionShow_Timeline,
                        "help-tip": {
                            "pixmap": "family-timeline.png",
                        },
                    },
                ),
                (
                    "searchButton",
                    {
                        "path": "search-button.png",
                        "action": self.ui.actionShow_Search,
                        "help-tip": {
                            "pixmap": "search.png",
                        },
                    },
                ),
                (
                    "settingsButton",
                    {
                        "path": "settings-button.png",
                        "action": self.ui.actionShow_Settings,
                        "help-tip": {
                            "pixmap": "diagram-settings.png",
                        },
                    },
                ),
                ("sep", None),
                (
                    "detailsButton",
                    {
                        "path": "details-button.png",
                        "action": self.ui.actionInspect,
                        "help-tip": {
                            "pixmap": "inspect-selection.png",
                        },
                    },
                ),
                (
                    "deleteButton",
                    {
                        "path": "delete-button.png",
                        "action": self.ui.actionDelete,
                        "help-tip": {
                            "pixmap": "delete-item.png",
                        },
                    },
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
            ]
        )
