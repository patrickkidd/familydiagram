import os.path, sys, datetime, shutil, logging, atexit
import pickle

from PyQt5.QtCore import QT_VERSION_STR

import vedana
from _pkdiagram import CUtil, FDDocument
from pkdiagram.pyqt import (
    pyqtSignal,
    tr,
    Qt,
    QAction,
    QAbstractAnimation,
    QAbstractButton,
    QApplication,
    QCheckBox,
    QCoreApplication,
    QDateTime,
    QDesktopServices,
    QDialog,
    QDir,
    QFile,
    QFileDialog,
    QFileInfo,
    QHBoxLayout,
    QIcon,
    QInputDialog,
    QIODevice,
    QKeyEvent,
    QLineEdit,
    QMainWindow,
    QMargins,
    QMessageBox,
    QNetworkAccessManager,
    QPalette,
    QPixmap,
    QPoint,
    QPrinter,
    QPrintDialog,
    QPropertyAnimation,
    QStandardPaths,
    QTimer,
    QTextEdit,
    QPushButton,
    QUndoView,
    QUrl,
    QVBoxLayout,
    QSize,
    QEasingCurve,
    QEvent,
    QKeyEvent,
    QQuickWidget,
)
from pkdiagram import version, util
from pkdiagram.server_types import Diagram, HTTPError
from pkdiagram.scene import ItemGarbage, Property, Scene
from pkdiagram.scene.clipboard import Clipboard, ImportItems
from pkdiagram.views import AccountDialog
from pkdiagram.documentview import DocumentView
from pkdiagram.mainwindow import FileManager, Preferences, Welcome
from pkdiagram.mainwindow.mainwindow_form import Ui_MainWindow


log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    The main application window that manages the menus and any document-agnostic
    dialogs, etc.
    """

    S_DIAGRAM_UPDATED_FROM_SERVER = "This diagram has been updated from the newer version on the server. If this is unexpected, you may find it useful to plan updates with other users that share access to this diagram, as it will always auotmatically update to the newest version saved from any computer."

    S_NO_FREE_DIAGRAM_NO_SERVER = (
        "You must be connected to the internet to use the free diagram."
    )

    S_FAILED_TO_SAVE_SERVER_FILE = "Could not save file to server. Either there is a problem with your internet connection or the server is down. Another attempt to save it to the server will be made the next time you save the diagram."

    S_IMPORTING_TO_FREE_DIAGRAM = "Importing a diagram will overwrite all of the data in your one free diagram. You must purchase the full version of Family Diagram to edit more than one diagram.\n\nAre you sure want to continue?"
    S_CONFIRM_SAVE_CHANGES = "Do you want to save your changes?"

    S_CONFIRM_UPLOAD_DIAGRAM = "Are you sure you want to upload this diagram to the server? This is required to share the diagram with others."
    S_CONFIRM_DELETE_LOCAL_COPY_OF_UPLOADED_DIAGRAM = "This diagram was copied to the server.\n\nDo you want to delete the local copy of this file?"

    OPEN_DIAGRAM_SYNC_MS = (
        1000 * 60 * 30
    )  # 30 minutes; just enough for infrequent updates

    documentChanged = pyqtSignal(FDDocument, FDDocument)
    closed = pyqtSignal()  # for app.py

    def __init__(self, appConfig, session):
        super().__init__()  # None, Qt.MaximizeUsingFullscreenGeometryHint)

        if hasattr(Qt, "WA_ContentsMarginsRespectsSafeArea"):
            self.setAttribute(Qt.WA_ContentsMarginsRespectsSafeArea, False)

        MainWindow._instance = self
        self._profile = None
        self.prefs = QApplication.instance().prefs()
        self.session = session
        self.appConfig = appConfig
        self.eula = None
        self.isInitialized = False
        self.isInitializing = False
        self._blocked = False
        self._savingServerFile = False
        self._isOpeningDiagram = False
        self._isImportingToFreeDiagram = False
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        if QApplication.platformName() != "offscreen":
            self.setUnifiedTitleAndToolBarOnMac(True)  # crash

        #
        _translate = QCoreApplication.translate
        self.ui.actionMarriage.setShortcuts(
            [
                _translate("MainWindow", "Ctrl+Shift+P"),
                _translate("MainWindow", "Ctrl+Shift+D"),
            ]
        )
        #
        self._windowIcon = None  # cached to speed up f.ex. timeline scrolling
        self.fileStatuses = {}

        if util.ENABLE_OPENGL:  # ios should already be OpenGL
            from pkdiagram.pyqt import QOpenGLWidget, QSurfaceFormat

            self.ui.centralWidget = QOpenGLWidget(self)
            fmt = QSurfaceFormat.defaultFormat()
            fmt.setSamples(util.OPENGL_SAMPLES)
            self.ui.centralWidget.setFormat(fmt)
            self.ui.centralWidget.setObjectName("centralWidget")
            self.ui.horizontalLayout = QHBoxLayout(self.ui.centralWidget)
            self.ui.horizontalLayout.setContentsMargins(0, 0, 0, 0)
            self.ui.horizontalLayout.setSpacing(6)
            self.ui.horizontalLayout.setObjectName("horizontalLayout")
            self.setCentralWidget(self.ui.centralWidget)

        self.ui.actionUndo.setEnabled(False)
        self.ui.actionRedo.setEnabled(False)

        self.profiler = None

        self.scene = None
        self.document = None
        self.serverFileModel = None
        self.updateReply = None
        self.diagramShown = False
        self.savePending = False
        self.qnam = QNetworkAccessManager(self)
        self._isOpeningServerDiagram = None
        # self.manualView = None
        self.itemGarbage = ItemGarbage(self)
        self.closeDiagramPending = False
        self.deferedShowHomeDialog = QMessageBox(self)
        self.deferedShowHomeDialog.setText("Syncing to server...")
        self.deferedShowHomeDialog.setStandardButtons(QMessageBox.NoButton)

        # Goes before documentView which is initialized based on this
        self.ui.actionInstall_Update.setEnabled(False)

        # DEBUG: UndoStackView
        self.undoView = QUndoView()
        self.undoView.hide()
        self.ui.actionShow_Undo_View.toggled.connect(self.onShowUndoView)

        # Document View

        self.documentView = DocumentView(self, self.session)
        self.documentView.controller.uploadToServer.connect(self.onUploadToServer)
        self.view = self.documentView.view
        self.qmlWidgets = list(self.documentView.drawers)
        self.view.filePathDropped.connect(self.onFilePathDroppedOnView)
        self.view.showToolBarButton.clicked.connect(self.ui.actionHide_ToolBars.trigger)
        self.viewAnimation = QPropertyAnimation(self.documentView, b"pos")
        self.viewAnimation.setDuration(util.ANIM_DURATION_MS)
        self.viewAnimation.setEasingCurve(QEasingCurve.OutQuad)
        self.viewAnimation.finished.connect(self.onViewAnimationDone)
        self.documentView.graphicalTimelineExpanded[bool].connect(
            self.onGraphicalTimelineExpanded
        )
        self.documentView.qmlSelectionChanged.connect(self.onQmlSelectionChanged)
        self.documentView.move(self.width(), 0)

        self.accountDialog = AccountDialog(self.documentView.qmlEngine(), self)
        self.accountDialog.init()

        ## File Manager

        self.fileManager = FileManager(self.documentView.qmlEngine(), self)
        self.fileManager.localFileClicked[str].connect(self.onLocalFileClicked)
        self.fileManager.serverFileClicked[str, Diagram].connect(
            self.onServerFileClicked
        )
        self.fileManager.newButtonClicked.connect(self.new)
        self.fileManager.localFilesShownChanged[bool].connect(
            self.onLocalFilesShownChanged
        )
        self.fileManager.serverFileModel.dataChanged.connect(
            self.onServerFileModelDataChanged
        )
        self.ui.centralWidget.layout().addWidget(self.fileManager)
        self.prefsDialog = None
        self.documentView.raise_()

        # Welcome
        self.welcomeDialog = Welcome(self)
        self.welcomeDialog.hidden.connect(self.onWelcomeHidden)

        # Analytics
        for action in self.findChildren(QAction):
            if action not in (self.ui.actionUndo, self.ui.actionRedo):
                action.triggered.connect(
                    lambda x: self.session.trackAction(self.sender().text())
                )

        # Signals

        # Family Diagram
        self.ui.actionQuit.triggered.connect(
            self.onQuit, Qt.QueuedConnection
        )  # as per Qt docs; wasn't quitting
        self.ui.actionShow_Welcome.triggered.connect(self.showWelcome)
        self.ui.actionShow_Account.triggered.connect(self.showAccount)
        self.ui.actionShow_License_Agreement.triggered.connect(self.showEULA)
        sep = QAction(self)
        sep.setSeparator(True)
        sep.setMenuRole(QAction.ApplicationSpecificRole)
        self.ui.actionPreferences.triggered.connect(self.showPreferences)
        # View
        self.ui.actionInspect.setEnabled(False)
        self.ui.actionInspect_Item.setEnabled(False)
        self.ui.actionInspect_Timeline.setEnabled(False)
        self.ui.actionInspect_Notes.setEnabled(False)
        self.ui.actionInspect_Meta.setEnabled(False)
        # File
        self.ui.actionNew.triggered.connect(self.new)
        self.ui.actionOpen.triggered.connect(self.open)
        self.ui.actionClear_Recent_Menu.triggered.connect(self.onClearRecentFiles)
        self.ui.actionSave.triggered.connect(self.save)
        self.ui.actionSave_As.triggered.connect(self.saveAs)
        self.ui.actionAbout.triggered.connect(self.showAbout)
        self.ui.actionPrint.triggered.connect(self.onPrint)
        self.ui.actionView_Diagram.triggered.connect(self.showDiagram)
        self.ui.actionDocuments_Folder.triggered.connect(self.openDocumentsFolder)
        # Edit
        self.ui.actionCopy.triggered.connect(self.onCopy)
        self.ui.actionCut.triggered.connect(self.onCut)
        self.ui.actionPaste.triggered.connect(self.onPaste)
        # self.ui.actionOpen_Server_Folder.triggered.connect(self.openServerFolder)
        # View
        self.ui.actionShow_Aliases.toggled[bool].connect(self.onShowAliases)
        self.ui.actionShow_Current_Date.toggled.connect(self.onShowCurrentDateTime)
        self.ui.actionShow_Legend.toggled.connect(self.onShowLegend)
        self.ui.actionShow_Graphical_Timeline.toggled.connect(self.onGraphicalTimeline)
        self.ui.actionExpand_Graphical_Timeline.toggled.connect(
            self.onExpandGraphicalTimeline
        )
        self.ui.actionUndo_History.triggered.connect(self.documentView.showUndoHistory)
        self.ui.actionClear_All_Events.triggered.connect(self.clearAllEvents)
        self.ui.actionHide_Names.toggled[bool].connect(self.onHideNames)
        self.ui.actionHide_Variables_on_Diagram.toggled[bool].connect(
            self.onHideVariablesOnDiagram
        )
        self.ui.actionHide_Variable_Steady_States.toggled[bool].connect(
            self.onHideVariableSteadyStates
        )
        self.ui.actionHide_Emotional_Process.toggled.connect(
            self.onHideEmotionalProcess
        )
        self.ui.actionHide_Emotion_Colors.toggled.connect(self.onHideEmotionColors)
        self.ui.actionHide_ToolBars.toggled.connect(self.onHideToolBars)
        self.ui.actionImport_Diagram.triggered.connect(self.onImportDiagram)
        self.ui.actionSave_Selection_As.triggered.connect(self.saveSelectionAs)
        self.ui.actionClose.triggered.connect(self.closeDocument)
        self.ui.actionSupport.triggered.connect(self.onSupport)
        self.ui.actionShow_Tips.toggled[bool].connect(self.onShowHelpTips)
        self.ui.actionUser_Manual.triggered.connect(self.onShowManual)
        self.ui.actionUser_Manual_Latest_Version.triggered.connect(
            self.onShowManualLatest
        )
        self.ui.actionDiscussion_Forum.triggered.connect(self.onShowDiscussionForom)
        self.ui.actionCrash.triggered.connect(self.onTriggerCrash)
        self.ui.actionRaise_Python_Exception.triggered.connect(self.onTriggerException)
        self.ui.actionExport_Scene_dict.triggered.connect(self.onExportSceneDict)
        self.ui.actionCheck_for_Updates.triggered.connect(self.onCheckForUpdates)
        self.ui.actionInstall_Update.triggered.connect(self.onCheckForUpdates)
        # Insert
        self.ui.actionParents_to_Selection.triggered.connect(
            self.view.addParentsToSelection
        )
        #
        self.ui.actionJump_to_Now.triggered.connect(self.onJumpToNow)
        self.ui.actionReset_All.triggered.connect(self.onResetAll)
        self.ui.actionEditor_Mode.toggled[bool].connect(self.onEditorMode)
        self.ui.actionStart_Profile.triggered.connect(self.onStartProfile)
        self.ui.actionStop_Profile.triggered.connect(self.onStopProfile)
        self.ui.actionRefresh_Server.triggered.connect(self.onServerRefresh)
        self.ui.actionReload_Server.triggered.connect(self.onServerReload)
        self.ui.actionShow_Local_Files.toggled[bool].connect(self.onShowLocalFiles)
        self.ui.actionShow_Server_Files.toggled[bool].connect(self.onShowServerFiles)
        self.ui.actionClear_Preferences.triggered.connect(self.onClearPreferences)
        self.ui.actionSave_Scene_as_JSON.triggered.connect(self.onSaveSceneAsJSON)
        self.alreadyResetFreeDiagramOnce = (
            False  # cancel the second time to avoid loop.
        )

        # Hide actions for now
        self.ui.actionUser_Manual_Latest_Version.setVisible(False)
        self.ui.actionShow_Legend.setVisible(False)
        # self.ui.actionShow_Welcome.setVisible(False)

        # delay-init qml widgets
        # self._nextQmlInit = 0
        # if util.QML_LAZY_DELAY_INTERVAL_MS:
        #     QTimer.singleShot(util.QML_LAZY_DELAY_INTERVAL_MS * 2, self._nextDelayedQmlInit) # after view animation
        for w in self.qmlWidgets:
            w.checkInitQml()

    # def _nextDelayedQmlInit(self):
    #     """ Stagger lazy init of qml widgets over time. """
    #     if self._nextQmlInit < len(self.qmlWidgets) and not self.isAnimating():
    #         drawer = self.qmlWidgets[self._nextQmlInit]
    #         drawer.checkInitQml()
    #         self.here(drawer._qmlSource)
    #         self._nextQmlInit += 1
    #     if self._nextQmlInit < len(self.qmlWidgets):
    #         QTimer.singleShot(util.QML_LAZY_DELAY_INTERVAL_MS, self._nextDelayedQmlInit)

    def init(self):
        """Called after CUtil is initialized."""
        self.isInitializing = True
        log.debug(f"init {version.VERSION}")

        ## Document View

        self.documentView.init()

        ## File Manager View

        self.fileManager.init()
        self.serverFileModel = self.fileManager.serverFileModel
        self.serverPollTimer = QTimer(self)
        self.serverPollTimer.setInterval(self.OPEN_DIAGRAM_SYNC_MS)
        self.serverPollTimer.timeout.connect(self.onServerPollTimer)

        QApplication.instance().focusChanged.connect(self.onFocusChanged)
        QApplication.instance().paletteChanged.connect(self.onApplicationPaletteChanged)

        CUtil.instance().fileOpened[FDDocument].connect(self.setDocument)
        CUtil.instance().safeAreaMarginsChanged[QMargins].connect(
            self.onSafeAreaMarginsChanged
        )
        CUtil.instance().screenOrientationChanged.connect(
            self.onScreenOrientationChanged
        )
        CUtil.instance().fileAdded.connect(self.onFileAdded)
        CUtil.instance().fileStatusChanged.connect(self.onFileStatusChanged)
        CUtil.instance().fileRemoved.connect(self.onFileRemoved)
        for url in CUtil.instance().fileList():
            status = CUtil.instance().fileStatusForUrl(url)
            self.onFileAdded(url, status)
        CUtil.instance().updateIsAvailable.connect(self.onAppUpdateIsAvailable)
        CUtil.instance().updateIsNotAvailable.connect(self.onAppUpdateIsNotAvailable)
        # self.documentView.sceneModel.selectionChanged.connect(self.onSceneModelSelectionChanged)
        self.documentView.sceneModel.trySetShowAliases[bool].connect(self.onShowAliases)
        #

        if not util.ENABLE_COPY_PASTE:
            self.ui.actionCopy.setEnabled(False)
            self.ui.actionCut.setEnabled(False)
            self.ui.actionPaste.setEnabled(False)
            self.ui.menuEdit.removeAction(self.ui.actionCopy)
            self.ui.menuEdit.removeAction(self.ui.actionCut)
            self.ui.menuEdit.removeAction(self.ui.actionPaste)

        QApplication.clipboard().changed.connect(self.onClipboardChanged)

        # Things that are disabled for any beta users.
        if not util.IS_DEV or CUtil.dev_amIBeingDebugged():
            self.ui.menuTags.setTitle("Tags")

        was = self._blocked  # remove and retest
        self._blocked = True
        self.ui.actionShow_Local_Files.setChecked(
            self.fileManager.rootProp("localFilesShown")
        )
        self._blocked = was

        self.updateRecentFilesMenu()
        self.adjust()
        self.statusBar().hide()
        if util.IS_IOS:
            self.menuWidget().hide()
        self.removeToolBar(self.ui.mainToolBar)
        if util.IS_IOS:
            self.setGeometry(CUtil.instance().screenSize())
        self.documentView.setScene(None)
        #
        self.welcomeDialog.init()
        self.setDocument(None)
        if (
            CUtil.dev_amIBeingDebugged()
            or sys.gettrace()
            or (not util.IS_BUNDLE)
            or version.IS_BETA
        ):
            self.ui.menuDebug.menuAction().setVisible(True)
        else:
            self.ui.menuDebug.menuAction().setVisible(False)
        self.ui.actionUndo_History.setVisible(False)
        self.ui.actionClear_All_Events.setVisible(False)
        self.documentView.controller.updateActions()
        self.isInitializing = False
        self.isInitialized = True

    # def delayedInit(self):
    #     """ Anything that needs to be run after the widget is shown. """
    #     CUtil.instance().onScreenOrientationChanged()

    def deinit(self):
        if not self.isInitialized:
            return
        log.debug(f"deinit {version.VERSION}")

        QApplication.clipboard().changed.disconnect(self.onClipboardChanged)
        QApplication.instance().focusChanged.disconnect(self.onFocusChanged)
        CUtil.instance().fileOpened[FDDocument].disconnect(self.setDocument)
        CUtil.instance().fileAdded.disconnect(self.onFileAdded)
        CUtil.instance().fileStatusChanged.disconnect(self.onFileStatusChanged)
        CUtil.instance().fileRemoved.disconnect(self.onFileRemoved)
        # self.documentView.sceneModel.selectionChanged.disconnect(self.onSceneModelSelectionChanged)
        self.documentView.sceneModel.trySetShowAliases[bool].disconnect(
            self.onShowAliases
        )
        self.setDocument(None)
        self.documentView.deinit()
        self.fileManager.deinit()
        self.accountDialog.deinit()
        self.welcomeDialog.deinit()
        self.view.setViewport(None)  # prevent segfault on destructing OpenGLWidget
        # self.view = None # avoid QApplication::style() assertion on shutdown
        self.isInitialized = False

    def showEvent(self, e):
        super().showEvent(e)
        self.documentView.adjust()  # adjust again after geometry is received

    def isAnimating(self):
        return self.viewAnimation.state() == QAbstractAnimation.Running

    @util.fblocked
    def onEditorMode(self, on: bool):
        editorMode = self.prefs.value("editorMode", defaultValue=False, type=bool)
        if editorMode != on:
            self.prefs.setValue("editorMode", on)
        self.ui.actionEditor_Mode.setChecked(on)
        self.documentView.controller.onEditorMode(on)

    def isInEditorMode(self) -> bool:
        return self.prefs.value("editorMode", defaultValue=False, type=bool)

    def onAppUpdateIsAvailable(self):
        self.ui.actionInstall_Update.setEnabled(True)
        self.view.sceneToolBar.onItemsVisibilityChanged()
        self.view.adjustToolBars()

    def onAppUpdateIsNotAvailable(self):
        self.ui.actionInstall_Update.setEnabled(False)
        self.view.sceneToolBar.onItemsVisibilityChanged()
        self.view.adjustToolBars()

    def onServerFileModelDataChanged(self, fromIndex, toIndex, roles):
        if not self.scene:
            return

        if self._savingServerFile:
            return

        # Warn that current loaded file was updated from server
        diagram = self.scene.serverDiagram()
        if not diagram:
            return

        # # Check if alias of scene should be updated.
        # row = self.serverFileModel.rowForDiagramId(diagram.id)
        # alias = self.serverFileModel.index(row, 0).data(self.serverFileModel.AliasRole)
        # if alias and alias != self.scene.alias():
        #     self.scene.setAlias(alias)
        #     self.updateWindowTitle()

        if (
            diagram
            and self.serverFileModel.DiagramDataRole in roles
            and not self._isImportingToFreeDiagram
        ):
            model = self.fileManager.serverFileModel
            loadedRow = model.rowForDiagramId(diagram.id)
            if loadedRow in list(range(fromIndex.row(), toIndex.row() + 1)):
                if not self.prefs.value(
                    "dontShowServerFileUpdated", type=bool, defaultValue=False
                ):
                    box = QMessageBox(
                        QMessageBox.Information,
                        "Diagram updated from server",
                        self.S_DIAGRAM_UPDATED_FROM_SERVER,
                        QMessageBox.Ok,
                    )
                    cb = QCheckBox(
                        "Don't show this any more."
                    )  # segfault on accessing box.checkBox()
                    box.setCheckBox(cb)
                    box.exec()
                    self.prefs.setValue("dontShowServerFileUpdated", cb.isChecked())
                filePath = self.serverFileModel.localPathForID(diagram.id)
                self.documentView.setReloadingCurrentDiagram(True)
                self.onServerFileClicked(filePath, diagram)
                self.documentView.setReloadingCurrentDiagram(False)

    def onShowUndoView(self, on):
        if on:
            self.undoView.setStack(self.scene.stack())
        self.undoView.setVisible(on)

    def clearWindowIcon(self):
        p = QPixmap(1, 1)
        p.fill(Qt.transparent)
        self.setWindowIcon(QIcon(p))
        self._windowIcon = None

    def updateWindowTitle(self):
        if self.document is None:
            self.setWindowTitle("Family Diagram")
            self.clearWindowIcon()
        else:
            if self.scene.readOnly() or self.documentView.sceneModel.isOnServer:
                self.clearWindowIcon()
            elif self._windowIcon is None:
                self._windowIcon = QIcon(QPixmap(util.QRC + "PKDiagram.png"))
                self.setWindowIcon(self._windowIcon)
            if self.session.hasFeature(vedana.LICENSE_FREE):
                title = "Family Diagram"
            else:
                title = self.scene.name()
            try:
                isClean = self.scene.stack().isClean()
            except RuntimeError as e:
                isClean = True  # shutting down, so doesn't matter.
            if not isClean:
                title = title + " *"
            dateTime = self.scene.currentDateTime()
            if self.scene.readOnly() and self.scene.serverDiagram():
                title += " (Server, Read-Only)"
            elif self.scene.serverDiagram():
                title += " (Server)"
            elif self.scene.readOnly():
                title += " (Read-Only)"
            if not dateTime.isNull():
                if dateTime.date().year() == QDateTime.currentDateTime().date().year():
                    tmpl = "MMM dd yyyy"
                else:
                    tmpl = "MMM dd yyyy"
                if title:
                    title += " | "
                x = dateTime.toString(tmpl)
                title += "Showing: " + x
            layerNames = ", ".join(
                [
                    layer.name()
                    for layer in self.scene.activeLayers(includeInternal=False)
                ]
            )
            if layerNames:
                title += " | " + layerNames
            if (
                self.scene.readOnly()
                or self.session.hasFeature(vedana.LICENSE_FREE)
                or self.documentView.sceneModel.isOnServer
            ):
                self.setWindowFilePath(" ")
            else:
                if self.document:
                    filePath = self.document.url().toLocalFile()
                else:
                    filePath = ""
                self.setWindowFilePath(filePath)
            self.setWindowTitle(title)

    ## Files

    def onFileAdded(self, url, status):
        if url in self.fileStatuses:
            raise KeyError("Duplicate file status for:", url.toLocalFile())
        self.fileStatuses[url] = status

    def onFileStatusChanged(self, url, status):
        if url not in self.fileStatuses:
            raise KeyError(
                "File modified recieved before file added for:", url.toLocalFile()
            )
        self.fileStatuses[url] = status

    def onFileRemoved(self, url):
        if url not in self.fileStatuses:
            raise KeyError("No file status for:", url.toLocalFile())
        del self.fileStatuses[url]

    def fileStatusExists(self, url):
        return QUrl.fromLocalFile(url) in self.fileStatuses

    def confirmSave(self):
        if not util.CONFIRM_SAVE:
            return True
        if self.scene and not self.scene.stack().isClean():
            ret = QMessageBox.question(
                self,
                "Save changes?",
                self.S_CONFIRM_SAVE_CHANGES,
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if ret == QMessageBox.Yes:
                self.save()
                return True
            elif ret == QMessageBox.Cancel:
                return False
        return True

    def onQuit(self):
        if not self.atHome() and not self.confirmSave():
            return
        self.hide()
        QApplication.quit()

    def closeEvent(self, e):
        self.closed.emit()

    def onUndoCleanChanged(self, on):
        if not self.scene:
            return
        if not self.isInitialized:
            return
        if self.scene.readOnly():
            self.scene.stack().setClean()
        else:
            self.updateWindowTitle()
            self.ui.actionSave.setEnabled(not on)

    def clear(self):
        self.scene.clear()

    def createNewFile(self):

        ## MOVE TO MainWindow

        # dString = datetime.datetime.now().strftime('%a %B %d, %I:%M%p').replace('AM', 'am').replace('PM', 'pm')
        # _fpath = os.path.join(util.DATA_PATH, 'New Case - %s' % dString)
        # fpath = _fpath + '.' + util.EXTENSION
        # if QFile(fpath).exists():
        #     tmpl = '%s %i.' + util.EXTENSION
        #     for i in range(1, 100):
        #         fpath = tmpl % (_fpath, i)
        #         if not QFile(fpath).exists():
        #             break
        dString = (
            datetime.datetime.now()
            .strftime("%a %B %d, %I:%M%p")
            .replace("AM", "am")
            .replace("PM", "pm")
        )
        fileName = ("New Case - " + dString).replace(":", "-").replace(",", "")
        docRoot = CUtil.instance().documentsFolderPath()
        bump = 1
        dupeTmpl = fileName + " %i"
        filePath = os.path.join(docRoot, fileName + util.DOT_EXTENSION)
        while self.fileStatusExists(filePath) or QFile(filePath).exists():
            bump = bump + 1
            fileName = dupeTmpl % bump
            filePath = os.path.join(docRoot, fileName + "." + util.EXTENSION)
        util.touchFD(filePath)
        return filePath

    def new(self):
        if self.session.hasFeature(vedana.LICENSE_FREE):
            btn = QMessageBox.question(
                self,
                "Clear diagram?",
                "The free version of this app only allows editing a single diagram. Do you want to delete all of your work and start over with a new diagram?",
            )
            if btn == QMessageBox.Yes:
                self.scene.clear()
                self.save()
        else:
            if not self.confirmSave():
                return
            fpath = self.createNewFile()
            self.open(fpath)

    ## File Handling

    def save(self, latent=False):
        """`latent` is True when this is being called after a delay to write the response from the server."""
        if not self.scene or self.scene.readOnly():
            return

        data = self.scene.data()

        # Write to disk
        bdata = pickle.dumps(data)
        self.document.updateDiagramData(bdata)

        # Write to server
        if self.scene.serverDiagram():
            self._savingServerFile = True
            row = self.serverFileModel.rowForDiagramId(self.scene.serverDiagram().id)
            index = self.serverFileModel.index(row, 0)
            try:
                self.serverFileModel.setData(
                    index, bdata, self.serverFileModel.DiagramDataRole
                )
            except HTTPError as e:
                log.error(e, exc_info=True)
                QMessageBox.critical(
                    self,
                    "Could not save file to server",
                    self.S_FAILED_TO_SAVE_SERVER_FILE,
                )
            self._savingServerFile = False
        else:
            self.document.save(quietly=latent)  # emits 'saved'; calls onDocumentSaved()
        self.scene.stack().setClean()

    # def onDocumentSaved(self):
    #     """ Called from CUtils. """
    #     commands.stack().setClean()

    def saveAs(self, selectionOnly=False, as_json=False):
        import os.path

        lastFileSavePath = self.prefs.value(
            "lastFileSavePath",
            type=str,
            defaultValue=CUtil.instance().documentsFolderPath(),
        )

        # Save folder
        if QFileInfo(lastFileSavePath).isFile() or util.isDocumentPackage(
            lastFileSavePath
        ):
            dirPath = QFileInfo(lastFileSavePath).dir().absolutePath()
        elif os.path.isdir(lastFileSavePath):
            dirPath = lastFileSavePath
        else:
            dirPath = CUtil.instance().documentsFolderPath()

        # Save file name
        if self.scene.shouldShowAliases():
            fileName = "[%s]" % self.scene.alias
        else:
            fileName = QFileInfo(self.document.url().toLocalFile()).fileName()

        # Add json type?
        if as_json:
            saveFileTypes = "JSON (*.json)"
        else:
            saveFileTypes = util.SAVE_FILE_TYPES

        filePath = os.path.join(dirPath, QFileInfo(fileName).baseName())
        filePath, types = QFileDialog.getSaveFileName(
            self, "Save File", filePath, saveFileTypes
        )
        if not filePath:
            return False
        selectedItems = self.scene.selectedItems()
        self.scene.clearSelection()
        ext = filePath.rsplit(".")[1].lower()
        if ext in ["jpg", "jpeg"]:
            format = "JPG"
        elif ext in ["png"]:
            format = "PNG"
        elif ext in ["pdf"]:
            format = "PDF"
        elif ext in ["xlsx"]:
            format = "XLSX"
        elif ext in ["json"]:
            format = "JSON"
        else:
            format = "FD"
        if selectionOnly:
            if format == "FD":
                if QFileInfo(filePath).exists():
                    if not QDir(filePath).removeRecursively():
                        QMessageBox.critical(
                            self,
                            "Could not overwrite",
                            "Could not overwrite %s" % filePath,
                        )
                        return
                packageDir = QDir(filePath)
                os.makedirs(filePath)
                picklePath = os.path.join(filePath, "diagram.pickle")
                with open(picklePath, "wb") as f:
                    data = self.scene.data(selectionOnly=True)
                    bdata = pickle.dumps(data)
                    f.write(bdata)
                    log.info(f"Created {picklePath}")
        else:
            if not filePath:
                lastFileReadPath = self.prefs.value("lastFileReadPath", type=str)
                lastFileSavePath = self.prefs.value("lastFileSavePath", type=str)
                if lastFileSavePath is None:
                    filePath = lastFileReadPath
                else:
                    filePath = lastFileSavePath
            if not filePath:
                self.saveAs()
            else:
                if format == "FD":
                    data = self.scene.data()
                    bdata = pickle.dumps(data)
                    self.document.updateDiagramData(bdata)
                    self.document.saveAs(QUrl.fromLocalFile(filePath))
                    self.prefs.setValue("lastFileSavePath", filePath)
                    self.updateWindowTitle()
                # elif format == "PDF":
                #     self.documentView.controller.writePDF(filePath)
                elif format == "JPG":
                    self.documentView.controller.writeJPG(filePath)
                elif format == "PNG":
                    self.documentView.controller.writePNG(filePath)
                elif format == "XLSX":
                    self.documentView.controller.writeExcel(
                        filePath, self.documentView.searchModel
                    )
                elif format == "JSON":
                    self.documentView.controller.writeJSON(filePath)
        for item in selectedItems:
            item.setSelected(True)
        return True

    def saveSelectionAs(self):
        self.saveAs(selectionOnly=True)

    ## File Manager

    @util.blocked
    def onLocalFilesShownChanged(self, on):
        self.ui.actionShow_Local_Files.setChecked(on)
        self.ui.actionShow_Server_Files.setChecked(not on)

    @util.blocked
    def onShowLocalFiles(self, on):
        self.ui.actionShow_Server_Files.setChecked(not on)
        self.fileManager.showLocalFiles(on)

    @util.blocked
    def onShowServerFiles(self, on):
        self.ui.actionShow_Local_Files.setChecked(not on)
        self.fileManager.showLocalFiles(not on)

    def onLocalFileClicked(self, fpath):
        self.session.trackApp("Open local file from file manager")
        self.fileManager.setEnabled(False)
        self.open(filePath=fpath)
        # def doOpen():
        #     self.fileClicked.emit(item.fpath)
        #     self.localCaseList.clearSelection()
        # QTimer.singleShot(10, doOpen) # repaint with disabled state

    def onServerFileClicked(self, fpath, diagram):
        self.session.trackApp("Open server file from file manager")
        self.fileManager.setEnabled(False)
        self._isOpeningServerDiagram = diagram  # just to set Scene.readOnly
        self.open(filePath=fpath)
        self.documentView.qmlEngine().setServerDiagram(diagram)
        self.updateWindowTitle()
        self._isOpeningServerDiagram = None
        # def doOpen():
        #     self.fileClicked.emit(item.fpath)
        # QTimer.singleShot(10, doOpen) # repaint with disabled state

    ## File Management

    def onImportDiagram(self):
        self.open(importing=True)

    def onFilePathDroppedOnView(self, filePath):
        self.mw.open(filePath, importing=True)

    def open(self, filePath=None, importing=False):
        usedDialog = False

        if not filePath:
            desktopPath = QStandardPaths.writableLocation(
                QStandardPaths.DesktopLocation
            )
            filePath = self.prefs.value(
                "lastFileOpenPath", type=str, defaultValue=desktopPath
            )
            if filePath and QFileInfo(filePath).isFile():
                filePath = QFileInfo(filePath).absolutePath()
            filePath = CUtil.instance().getOpenFileName()
            if filePath:
                usedDialog = True

        if not filePath:
            return

        if not importing and not self.confirmSave():
            return
        if filePath.endswith("/"):
            filePath = filePath[:-1]
        if (
            not QFileInfo(filePath).isDir()
            or QFileInfo(filePath).suffix() != util.EXTENSION
        ):
            # QMessageBox.warning(self, 'Error opening file', 'You can only open Family Diagram files: %s' % filePath)
            return

        if importing:
            if self.session.hasFeature(vedana.LICENSE_FREE):
                btn = QMessageBox.question(
                    self, "Overwrite free diagram?", self.S_IMPORTING_TO_FREE_DIAGRAM
                )
                if btn != QMessageBox.Yes:
                    return
            if QFileInfo(filePath).isDir() and util.suffix(filePath) == util.EXTENSION:
                filePath = os.path.join(filePath, "diagram.pickle")
                if QFileInfo(filePath).isFile():
                    with open(filePath, "rb") as f:
                        # read in the data to check for errors first
                        newScene = Scene()
                        bdata = f.read()
                        data = pickle.loads(bdata)
                        ret = newScene.read(data)
                        if ret:
                            self.onOpenFileError(ret)

                        if self.session.hasFeature(vedana.LICENSE_FREE):

                            self._isImportingToFreeDiagram = True
                            diagram = self.scene.serverDiagram()
                            row = self.serverFileModel.rowForDiagramId(diagram.id)
                            self.serverFileModel.setData(
                                self.serverFileModel.index(row, 0),
                                bdata,
                                role=self.serverFileModel.DiagramDataRole,
                            )
                            self._isImportingToFreeDiagram = False

                        else:
                            newScene.selectAll()
                            items = Clipboard(newScene.selectedItems()).copy(self.scene)
                            self.scene.push(ImportItems(items))
        else:
            CUtil.instance().openExistingFile(
                QUrl.fromLocalFile(filePath)
            )  # calls FileManager.onFileOpened, then -> mw.setDocument

    def openFreeLicenseDiagram(self):
        if self.session.hasFeature(vedana.LICENSE_FREE):
            diagram = self.serverFileModel.findDiagram(
                self.session.user.free_diagram_id
            )
            if diagram:
                row = self.serverFileModel.rowForDiagramId(diagram.id)
                fpath = self.serverFileModel.pathForDiagram(diagram)
                self.onServerFileClicked(fpath, diagram)
            elif not diagram:
                QMessageBox.information(
                    self,
                    "Must connect to internet and log in",
                    self.S_NO_FREE_DIAGRAM_NO_SERVER,
                )

    def openLastFile(self):
        lastFileWasOpen = self.prefs.value(
            "lastFileWasOpen", type=bool, defaultValue=False
        )
        if lastFileWasOpen and not self.session.hasFeature(vedana.LICENSE_FREE):
            lastFileReadPath = self.prefs.value("lastFileReadPath", type=str)
            if QFileInfo(lastFileReadPath).exists():
                diagram = self.serverFileModel.serverDiagramForPath(lastFileReadPath)
                if diagram:
                    self.onServerFileClicked(lastFileReadPath, diagram)
                else:
                    self.open(filePath=lastFileReadPath)

    def onOpenFileError(self, x):
        QMessageBox.warning(self, "Error opening file", x)

    def setDocument(self, document):
        """Called from CUtil.openExistingFile() async open."""
        newScene = None
        self._isOpeningDiagram = True

        if document:  # see if scene loads successfully first
            if not self.session.hasFeature(vedana.LICENSE_FREE):
                self.prefs.setValue("lastFileReadPath", document.url().toLocalFile())
            filePath = document.url().toLocalFile()

            bdata = bytes(document.diagramData())

            # readOnly = QFileInfo(document.url().toLocalFile()).absolutePath() == self.serverFileModel.dataPath
            readOnly = None
            if self._isOpeningServerDiagram:
                # Check access rights against cache, even when offline
                if self.session.user:  # if logged in
                    user_id = self.session.user.id
                    if self._isOpeningServerDiagram.check_access(
                        user_id, vedana.ACCESS_READ_WRITE
                    ):
                        readOnly = False
                    elif self._isOpeningServerDiagram.check_access(
                        user_id, vedana.ACCESS_READ_ONLY
                    ):
                        readOnly = True
                    else:
                        raise RuntimeError("Not access at all? Is that possible??")
                else:
                    raise RuntimeError(
                        "user should always be logged in if reaching here"
                    )

                # Check if free diagram data then check if it is tampered with
                try:
                    bdata = util.readWithHash(os.path.join(filePath, "diagram.pickle"))
                except util.FileTamperedWithError:
                    QMessageBox.warning(
                        self,
                        "Error opening file",
                        "The local copy of this diagram stored on the server has been tampered with. This occurs because of an attempt to crack the app's license, by transfering the app's internal files to another computer/device, or by somehow altering the operating system.\n\nThe last version saved under your account on the server will be pulled down so that you may begin using it.",
                    )
                    document = None

            newScene = Scene(document=document)

            ret = None
            if bdata:

                try:
                    data = pickle.loads(bdata)
                except:
                    ret = "This file is currupt and cannot be opened"
                    import traceback

                    traceback.print_exc()
            else:
                data = {}

            if not ret:
                ret = newScene.read(data)
                if readOnly is not None:
                    newScene.setReadOnly(readOnly)

            # Error loading scene
            if ret:
                self.onOpenFileError(ret)
                self.fileManager.setEnabled(True)
                self._isOpeningDiagram = False
                return

            #
            # if not newScene.activeLayers():
            #     newScene.isInitializing = True # hack, but no biggie since this is set at end of Scene.read()
            #     newScene.centerAllItems()
            #     newScene.isInitializing = False
            # Ensure scene has latest alias from server in strange case of mismatch
            serverEntry = self.serverFileModel.findDiagram(newScene.uuid())
            if serverEntry and serverEntry.get("alias") != newScene.alias():
                newScene.setAlias(serverEntry["alias"], notify=False)

            # Update recent files list.
            if not util.IS_TEST and not self.session.hasFeature(vedana.LICENSE_FREE):
                recentFiles = []
                size = self.prefs.beginReadArray("recentFiles")
                for i in range(size):
                    self.prefs.setArrayIndex(i)
                    recentFiles.append(
                        {
                            "filePath": self.prefs.value("filePath"),
                            "fileName": self.prefs.value("fileName"),
                        }
                    )
                self.prefs.endArray()
                if len(recentFiles) == util.MAX_RECENT_FILES:
                    recentFiles.remove(recentFiles[-1])
                for entry in list(recentFiles):
                    if entry["filePath"] == filePath:
                        recentFiles.remove(entry)
                recentFiles.insert(
                    0, {"filePath": filePath, "fileName": newScene.name()}
                )
                self.prefs.beginWriteArray("recentFiles")
                self.prefs.setValue("size", len(recentFiles))
                for i, entry in enumerate(recentFiles):
                    self.prefs.setArrayIndex(i)
                    self.prefs.setValue("filePath", entry["filePath"])
                    self.prefs.setValue("fileName", entry["fileName"])
                self.prefs.endArray()
                self.prefs.sync()
                self.updateRecentFilesMenu()

        if self.document:
            # deinit document
            self.scene.stack().cleanChanged[bool].disconnect(self.onUndoCleanChanged)
            # self.document.saved.disconnect(self.onDocumentSaved)
            self.document.fileAdded.disconnect(self.onDocumentFileAdded)
            self.document.fileRemoved.disconnect(self.onDocumentFileRemoved)
            self.document.close()
            # deinit scene
            self.ui.actionSelect_All.triggered.disconnect(self.scene.selectAll)
            self.ui.actionDeselect.triggered.disconnect(self.scene.clearSelection)
            self.scene.clipboardChanged.disconnect(self.onSceneClipboard)
            self.scene.selectionChanged.disconnect(self.onSceneSelectionChanged)
            self.scene.propertyChanged[Property].disconnect(self.onSceneProperty)
            self.scene.layerAnimationGroup.finished.disconnect(
                self.onLayerAnimationFinished
            )
            self.ui.actionShow_Scene_Center.toggled[bool].disconnect(
                self.scene.toggleShowSceneCenter
            )
            self.ui.actionShow_Print_Rect.toggled[bool].disconnect(
                self.scene.toggleShowPrintRect
            )
            self.ui.actionShow_View_Scene_Rect.toggled[bool].disconnect(
                self.scene.toggleShowViewSceneRect
            )
            self.ui.actionShow_Cursor_Position.toggled[bool].disconnect(
                self.scene.toggleCursorPosition
            )
            self.ui.actionPathItem_Shapes.toggled[bool].disconnect(
                self.scene.toggleShowPathItemShapes
            )
            self.scene.loaded.disconnect(self.showDiagram)
            self.scene.stack().clear()
            self.scene.deinit(self.itemGarbage)  # hopefully it gets deleted now

        self.ui.actionShow_Scene_Center.setChecked(False)
        self.ui.actionShow_Print_Rect.setChecked(False)
        self.ui.actionShow_View_Scene_Rect.setChecked(False)

        oldDoc, newDoc = self.document, document
        self.document = document
        self.scene = newScene
        self.documentView.setScene(None)  # close all drawers/sheets, deinit all models
        if self.document:
            self.scene.stack().cleanChanged[bool].connect(self.onUndoCleanChanged)
            # self.document.saved.connect(self.onDocumentSaved)
            self.document.fileAdded.connect(self.onDocumentFileAdded)
            self.document.fileRemoved.connect(self.onDocumentFileRemoved)
            self.ui.actionShow_Aliases.setChecked(self.scene.showAliases())
            self.ui.actionHide_Names.setChecked(self.scene.hideNames())
            self.ui.actionHide_Variables_on_Diagram.setChecked(
                self.scene.hideVariablesOnDiagram()
            )
            self.ui.actionHide_Variable_Steady_States.setChecked(
                self.scene.hideVariableSteadyStates()
            )
            self.ui.actionHide_Emotional_Process.setChecked(
                self.scene.hideEmotionalProcess()
            )
            self.ui.actionHide_Emotion_Colors.setChecked(self.scene.hideEmotionColors())
            self.ui.actionShow_Graphical_Timeline.setChecked(
                not self.scene.hideDateSlider()
            )
            self.ui.actionExpand_Graphical_Timeline.setChecked(
                self.documentView.graphicalTimelineView.isExpanded()
            )
            self.ui.actionSelect_All.triggered.connect(self.scene.selectAll)
            self.ui.actionDeselect.triggered.connect(self.scene.clearSelection)
            self.scene.stack().canUndoChanged.connect(self.ui.actionUndo.setEnabled)
            self.scene.stack().canRedoChanged.connect(self.ui.actionRedo.setEnabled)
            self.scene.clipboardChanged.connect(self.onSceneClipboard)
            self.scene.selectionChanged.connect(self.onSceneSelectionChanged)
            self.scene.propertyChanged[Property].connect(self.onSceneProperty)
            self.scene.loaded.connect(self.showDiagram)
            self.scene.layerAnimationGroup.finished.connect(
                self.onLayerAnimationFinished
            )
            self.ui.actionShow_Scene_Center.toggled[bool].connect(
                self.scene.toggleShowSceneCenter
            )
            self.ui.actionShow_Print_Rect.toggled[bool].connect(
                self.scene.toggleShowPrintRect
            )
            self.ui.actionShow_View_Scene_Rect.toggled[bool].connect(
                self.scene.toggleShowViewSceneRect
            )
            self.ui.actionShow_Cursor_Position.toggled[bool].connect(
                self.scene.toggleCursorPosition
            )
            self.ui.actionPathItem_Shapes.toggled[bool].connect(
                self.scene.toggleShowPathItemShapes
            )
            self.ui.actionPaste.setEnabled(False)
            self.ui.actionSave.setEnabled(not readOnly)
            self.ui.actionSave_As.setEnabled(True)
            self.ui.actionSave_Selection_As.setEnabled(True)
            self.ui.actionImport_Diagram.setEnabled(not readOnly)
            self.ui.actionClose.setEnabled(True)
            if (
                self.scene.readOnly
                and self.scene.useRealNames()
                and self.scene.requirePasswordForRealNames()
            ):
                self.scene.setShowAliases(True)
            #
            self._blocked = (
                True  # too tired to debug setting util.blocked on &.setScene
            )
            self.ui.actionShow_Legend.setChecked(self.scene.legendData()["shown"])
            self._blocked = False
            self.scene.stack().clear()
            self.documentView.setScene(self.scene)
            # various scenarios for delaying the view animation for aesthetics
            if self.isInitializing:  # loading last opened file stored in prefs
                if not self.fileManager.localFileModel.isLoaded:
                    self.fileManager.localFileModel.loaded.connect(
                        lambda: self.showDiagram()
                    )
                else:
                    QTimer.singleShot(
                        900, lambda: self.showDiagram()
                    )  # just delayed for aesthetics
            else:
                self.showDiagram()
            if self._isOpeningServerDiagram:
                self.serverPollTimer.start()
        else:
            self.ui.actionSave.setEnabled(False)
            self.ui.actionSave_As.setEnabled(False)
            self.ui.actionSave_Selection_As.setEnabled(False)
            self.ui.actionImport_Diagram.setEnabled(False)
            self.ui.actionClose.setEnabled(False)
            self.serverPollTimer.stop()
        self.updateWindowTitle()
        self.documentView.controller.updateActions()
        if oldDoc or newDoc:
            self.documentChanged.emit(oldDoc, newDoc)
        self._isOpeningDiagram = False

    def onServerPollTimer(self):
        if self.scene:
            diagram = self.scene.serverDiagram()
            if diagram:
                self.serverFileModel.syncDiagramFromServer(diagram.id)

    def onDocumentFileAdded(self, relativePath):
        self.scene.stack().resetClean()

    def onDocumentFileRemoved(self, relativePath):
        self.scene.stack().resetClean()

    def onFileLocked(self, url):
        if url == self.document.url():
            self.documentView.lockEditor()

    def onFileUnlocked(self, url):
        if url == self.document.url():
            s = Scene(document=self.document)
            bdata = self.document.diagramData()
            data = pickle.loads(bdata)
            s.read(data)
            name = (
                QFileInfo(url.toLocalFile())
                .dir()
                .dirName()
                .replace("." + util.EXTENSION, "")
            )
            s.setName(name)
            self.setScene(s)
            self.documentView.unlockEditor()

    ## Actions

    def showEULA(self):
        if not self.eula:
            f = QFile(util.QRC + "Family-Diagram-User-License-Agreement.txt")
            if not f.open(QIODevice.ReadOnly):
                log.error("Could not open EULA file.", exc_info=True)
                return
            bdata = bytes(f.readAll())
            text = bdata.decode("utf-8")
            self.eula = QDialog(self)
            self.eula.resize(640, 480)
            self.eula.textEdit = QTextEdit(self.eula)
            self.eula.textEdit.setReadOnly(True)
            self.eula.textEdit.setPlainText(text)
            self.eula.acceptButton = QPushButton("Accept")
            self.eula.acceptButton.clicked.connect(self.eula.accept)
            self.eula.acceptButton.setDefault(True)
            self.eula.rejectButton = QPushButton("Reject")
            self.eula.rejectButton.clicked.connect(self.eula.reject)
            Layout = QVBoxLayout(self.eula)
            Layout.addWidget(self.eula.textEdit)
            HLayout = QHBoxLayout()
            HLayout.addSpacing(10)
            HLayout.addWidget(self.eula.rejectButton)
            HLayout.addWidget(self.eula.acceptButton)
            Layout.addLayout(HLayout)
        self.eula.move(400, 200)
        code = self.eula.exec()
        if code == QDialog.Accepted:
            self.prefs.setValue("acceptedEULA", True)
            return True
        else:
            return False

    def showAbout(self):
        QMessageBox.about(
            self,
            tr("About Family Diagram"),
            tr(
                """<center>
<p><h1>Family Diagram %s</h1></p>
<p style="font-weight: normal; text-align: justify">
    <span style="font-style: italic">Family Diagram</span>
        is a research and assessment tool designed around Bowen theory, which
        views the human family as a natural system. Information on Bowen
        theory can be found at <a href="http://thebowencenter.org">The Bowen
        Center for the Study of the Family</a>.
</p>
<p> &nbsp; </p>
<p> <h2>Produced by:</h2> </p>
  <p><a href="https://alaskafamilysystems.com">Alaska Family Systems</a></p>
<p> &nbsp;</p>
<p> <h2>Licensing</h2> </p>
<p> LGPLv3 (<a href="https://vedanamedia.com/products/Family-Diagram/Licensing/Licensing-Info.txt">More information</a>) </p>
<p> Qt-%s (<a href="https://vedanamedia.com/products/Family-Diagram/Licensing/qt-everywhere-src-5.15.1.tar.xz">Source Code</a>)</p>
<p> Family Diagram-%s (<a href="https://vedanamedia.com/products/Family-Diagram/Licensing/family-diagram-1.1.0.tar.gz">Source Code</a>)</p>
<p> </p>
</center>"""
                % (version.VERSION, QT_VERSION_STR, version.VERSION)
            ),
        )

    def showAccount(self):
        if self.welcomeDialog.isShown():
            return
        if not self.accountDialog.isShown():
            if not self.session.isLoggedIn():
                lastSessionData = self.appConfig.get(
                    "lastSessionData", {}, pickled=True
                )
                if lastSessionData:
                    self.session.login(token=lastSessionData["session"]["token"])
            self.accountDialog.show()
            # if self.accountDialog._forcedQuit:
            #     QApplication.quit()

    def onCheckForUpdates(self):
        CUtil.instance().checkForUpdates()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not self.isInitialized:
            return
        self.adjust()

    def adjust(self):
        self.documentView.resize(self.documentView.parent().size())
        if self.documentView.x() != 0:
            self.documentView.move(
                self.documentView.parent().width(), 0
            )  # slide-in window
        #
        s = QSize(self.welcomeDialog.sizeHint())
        if self.width() < s.width():
            s.setWidth(self.width())
        if self.height() < s.height():
            s.setHeight(self.height())
        self.welcomeDialog.resize(s)
        #
        s = QSize(self.accountDialog.sizeHint())
        if self.width() < s.width():
            s.setWidth(self.width())
        if self.height() < s.height():
            s.setHeight(self.height())
        self.accountDialog.resize(s)

    def showPreferences(self):
        if self.prefsDialog is None:
            self.prefsDialog = Preferences(self)
            self.prefsDialog.init(self.prefs)
            self.prefsDialog.exec()
            self.prefsDialog.deinit()
            self.prefsDialog = None

    def showDiagram(self, animated=True):
        if (
            self.documentView.x() == 0
        ):  # or self.viewAnimation.state() == self.viewAnimation.Running:
            return
        self.documentView.show()
        self.documentView.adjust()
        self.diagramShown = True

        def doUpdateScene():
            if self.scene:
                self.scene.update()

        QTimer.singleShot(100, doUpdateScene)  # was showing a blank on load
        if animated:
            self.viewAnimation.setStartValue(QPoint(self.documentView.x(), 0))
            self.viewAnimation.setEndValue(QPoint(0, 0))
            self.viewAnimation.start()
        else:
            self.documentView.move(0, 0)
            self.onViewAnimationDone()

    def closeDocument(self, dummy=None, animated=True):
        if (
            self.atHome()
        ):  # or self.viewAnimation.state() == self.viewAnimation.Running:
            return
        if not self.confirmSave():
            return
        self.session.trackApp("Close document")
        self.diagramShown = False
        self.setDocument(None)
        self.documentView.showDiagram()
        self.fileManager.show()
        self.fileManager.onFileClosed()
        if animated:
            self.viewAnimation.setStartValue(QPoint(self.documentView.x(), 0))
            self.viewAnimation.setEndValue(QPoint(self.width(), 0))
            self.viewAnimation.start()
        else:
            self.documentView.move(self.width(), 0)
            self.onViewAnimationDone()
        self.updateWindowTitle()
        if self.scene:
            self.scene.stack().clear()

    def onViewAnimationDone(self):
        if self.documentView.x() == self.width():  # at home
            self.documentView.hide()
            self.ui.actionImport_Diagram.setEnabled(False)
            self.fileManager.updateModTimes()
            self.documentView.controller.updateActions()
            if self.session.activeFeatures() and not self.session.hasFeature(
                vedana.LICENSE_FREE
            ):
                self.fileManager.setEnabled(True)
        else:
            self.fileManager.hide()
            if self.scene:
                self.scene.update()  # on first doc load on iPad (Qt bug where scene doesn't update when QGV is covered/off screen)
                self.ui.actionImport_Diagram.setEnabled(not self.scene.readOnly())
            self.documentView.controller.updateActions()
            self.view.setFocus()

    def atHome(self):
        return not self.diagramShown

    def onSceneSelectionChanged(self):
        self.documentView.controller.updateActions()

    def onSceneModelSelectionChanged(self):
        self.documentView.controller.updateActions()

    def updateRecentFilesMenu(self):
        # clear
        self.ui.menuOpen_Recent.clear()
        # for action in list(self.ui.menuOpen_Recent.findChildren(QAction)):
        #     self.ui.menuOpen_Recent.removeAction(action)
        # self.here(len(self.ui.menuOpen_Recent.actions()))
        # init
        size = self.prefs.beginReadArray("recentFiles")
        for i in range(size):
            self.prefs.setArrayIndex(i)
            filePath = self.prefs.value("filePath")
            fileName = self.prefs.value("fileName")
            action = QAction(self)
            action.setText(fileName)
            action.setData(filePath)
            action.triggered.connect(self.onOpenRecentFile)
            self.ui.menuOpen_Recent.addAction(action)
        self.prefs.endArray()
        self.ui.menuOpen_Recent.addSeparator()
        self.ui.menuOpen_Recent.addAction(self.ui.actionClear_Recent_Menu)
        on = bool(size)
        self.ui.menuOpen_Recent.setEnabled(on)
        self.ui.actionClear_Recent_Menu.setEnabled(on)

    def onClearRecentFiles(self):
        self.prefs.beginWriteArray("recentFiles")
        self.prefs.setValue("size", 0)
        self.prefs.endArray()
        self.updateRecentFilesMenu()

    def onOpenRecentFile(self):
        filePath = self.sender().data()
        self.open(filePath)

    def onSceneClipboard(self):
        on = False
        if QApplication.focusWidget() != self.view or self.atHome():
            on = False
        elif self.scene:
            if self.scene.clipboard:
                on = True
        self.ui.actionPaste.setEnabled(on)

    def onClipboardChanged(self, mode):
        return
        text = QApplication.clipboard().text()
        if text:
            self.ui.actionPaste.setEnabled(True)
        else:
            self.ui.actionPaste.setEnabled(False)
            # self.ui.actionCut.setEnabled(on)
            # self.ui.actionCopy.setEnabled(on)

    def onCut(self):
        pass

    def onCopy(self):
        pass

    @util.fblocked
    def onPaste(self, x=None):
        log.debug(QApplication.clipboard().text())
        press = QKeyEvent(QEvent.KeyPress, Qt.Key_V, Qt.ControlModifier)
        release = QKeyEvent(QEvent.KeyRelease, Qt.Key_V, Qt.ControlModifier)
        QApplication.instance().sendEvent(QApplication.activeWindow(), press)
        QApplication.instance().sendEvent(QApplication.activeWindow(), release)

    def onPrint(self):
        printer = QPrinter()
        printer.setOrientation(QPrinter.Landscape)
        if printer.outputFormat() != QPrinter.NativeFormat:
            QMessageBox.information(
                self,
                "No printers available",
                "You need to set up a printer on your computer before you use this feature.",
            )
            return
        dlg = QPrintDialog(printer, self)
        ret = dlg.exec()
        if ret == QDialog.Accepted:
            _isUIDarkMode = CUtil.instance().isUIDarkMode
            CUtil.instance().isUIDarkMode = lambda: False
            QApplication.instance().paletteChanged.emit(
                QApplication.instance().palette()
            )  # onSystemPaletteChanged()
            self.scene.writeJPG(printer=printer)
            CUtil.instance().isUIDarkMode = _isUIDarkMode
            QApplication.instance().paletteChanged.emit(
                QApplication.instance().palette()
            )  # .onSystemPaletteChanged()

    def openDocumentsFolder(self):
        s = CUtil.instance().documentsFolderPath()
        import os, sys

        if sys.platform == "win32":
            s = os.path.abspath(s)
            os.system('explorer "%s"' % s)
        elif os.path.isdir(s):
            os.system('open "%s"' % s)

    def openServerFolder(self):
        import os, sys

        if sys.platform == "win32":
            os.system('explorer "%s"' % self.fileManager.serverDataPath)
        else:
            os.system('open "%s"' % self.fileManager.serverDataPath)

    def clearAllEvents(self):
        self.scene.clearAllEvents()

    def onSupport(self):
        QDesktopServices.openUrl(
            QUrl("https://vedanamedia.com/our-products/family-diagram/support/")
        )
        # if (version.IS_ALPHA or version.IS_BETA):
        #     QDesktopServices.openUrl(QUrl('mailto:patrick@vedanamedia.com?subject=Family%20Diagram%20Support'))
        #     # CUtil.instance().showFeedbackWindow()
        # else:
        #     QDesktopServices.openUrl(QUrl('https://vedanamedia.com/forum/'))

    def onTriggerCrash(self):
        CUtil.instance().dev_crash()

    def onTriggerException(self):
        here = there  # type: ignore

    def onFocusChanged(self, old, new):
        if isinstance(new, QQuickWidget):
            _objectName = new.parent().objectName()
        elif new:
            _objectName = new.objectName()
        else:
            _objectName = None
        # log.info(f"onFocusChanged: {new}[{_objectName}]")
        if not self.scene:
            return
        if not isinstance(new, QAbstractButton):
            # some selections anre't made until after focus is set
            def go():
                self.documentView.controller.updateActions()

            QTimer.singleShot(0, go)

    def onApplicationPaletteChanged(self):
        p = self.palette()
        p.setColor(QPalette.Window, util.WINDOW_BG)
        self.setPalette(p)
        if self.scene:
            self.scene.updateAll()

    ## View

    def onSceneProperty(self, prop):
        if prop.name() == "uuid":
            # commands.stack().resetClean()
            self.fileManager.onLocalUUIDUpdated(self.document.url(), prop.get())
        elif prop.name() == "currentDateTime":
            # Graphical timeline should never be shown if there are no events,
            # and if there are events then currentDateTime will never be null.
            if prop.get():
                self.ui.actionShow_Graphical_Timeline.setEnabled(True)
                self.ui.actionExpand_Graphical_Timeline.setEnabled(True)
            else:
                self.ui.actionShow_Graphical_Timeline.setEnabled(False)
                self.ui.actionExpand_Graphical_Timeline.setEnabled(False)
            firstDate = self.documentView.timelineModel.firstEventDateTime()
            if firstDate and prop.get() == firstDate:
                self.ui.actionNext_Event.setEnabled(True)
                self.ui.actionPrevious_Event.setEnabled(False)
            elif prop.get() == self.documentView.timelineModel.lastEventDateTime():
                self.ui.actionNext_Event.setEnabled(False)
                self.ui.actionPrevious_Event.setEnabled(True)
            else:
                self.ui.actionNext_Event.setEnabled(True)
                self.ui.actionPrevious_Event.setEnabled(True)
            self.updateWindowTitle()
        elif prop.name() == "alias":
            self.updateWindowTitle()
        elif prop.name() == "showAliases":
            on = prop.get()
            if on != self.ui.actionShow_Aliases.isChecked():
                was = self._blocked
                self._blocked = True
                self.ui.actionShow_Aliases.setChecked(on)
                self._blocked = was
            self.updateWindowTitle()  # may not be called if clean state doesn't change
        elif prop.name() == "hideNames":
            on = prop.get()
            if on != self.ui.actionHide_Names.isChecked():
                was = self._blocked
                self._blocked = True
                self.ui.actionHide_Names.setChecked(on)
                self._blocked = was
            self.updateWindowTitle()  # may not be called if clean state doesn't change
        elif prop.name() == "hideEmotionalProcess":
            on = prop.get()
            if on != self.ui.actionHide_Emotional_Process.isChecked():
                self.ui.actionHide_Emotional_Process.setChecked(on)
        elif prop.name() == "hideEmotionColors":
            on = prop.get()
            if on != self.ui.actionHide_Emotion_Colors.isChecked():
                self.ui.actionHide_Emotion_Colors.setChecked(on)
        elif prop.name() == "hideVariablesOnDiagram":
            on = prop.get()
            if on != self.ui.actionHide_Variables_on_Diagram.isChecked():
                self.ui.actionHide_Variables_on_Diagram.setChecked(on)
        elif prop.name() == "hideVariableSteadyStates":
            on = prop.get()
            if on != self.ui.actionHide_Variable_Steady_States.isChecked():
                self.ui.actionHide_Variable_Steady_States.setChecked(on)
        elif prop.name() == "legendData":
            self._blocked = True
            self.ui.actionShow_Legend.setChecked(prop.get()["shown"])
            self._blocked = False
        elif prop.name() == "hideDateSlider":
            self._blocked = True
            self.ui.actionShow_Graphical_Timeline.setChecked(not prop.get())
            self._blocked = False

    def onLayerAnimationFinished(self):
        self.updateWindowTitle()

    @util.blocked
    def onShowCurrentDateTime(self, on):
        self.view.onShowCurrentDateTime(on)
        self.ui.actionShow_Current_Date.setChecked(on)

    @util.blocked
    def onShowLegend(self, on):
        if on != self.ui.actionShow_Legend.isChecked():
            self.ui.actionShow_Legend.setChecked(on)
        self.view.onShowLegend(on)

    @util.blocked
    def onHideToolBars(self, on):
        if on != self.ui.actionHide_ToolBars.isChecked():
            self.ui.actionHide_ToolBars.setChecked(on)
        self._blocked = False
        self.scene.setHideToolBars(on, undo=(not self._isOpeningDiagram))

    @util.blocked
    def onShowAliases(self, on):
        if not on and (
            self.scene
            and self.scene.readOnly()
            and self.scene.requirePasswordForRealNames()
        ):
            while self.scene.requirePasswordForRealNames():
                password, ok = QInputDialog.getText(
                    self,
                    "Input Password",
                    "Enter the password provided by the diagram author.",
                    QLineEdit.Password,
                )
                if ok is False:
                    return
                elif password == self.scene.password():
                    self.scene.setRequirePasswordForRealNames(False)
        if on != self.ui.actionShow_Aliases.isChecked():
            self.ui.actionShow_Aliases.setChecked(on)
        # Optimize hiding names (this doesn't really help much)
        self._blocked = False
        if self.scene:
            self.scene.setShowAliases(on, undo=(not self._isOpeningDiagram))

    @util.blocked
    def onHideEmotionalProcess(self, on):
        if on != self.ui.actionHide_Emotional_Process.isChecked():
            self.ui.actionHide_Emotional_Process.setChecked(on)
        self.scene.setHideEmotionalProcess(on, undo=(not self._isOpeningDiagram))

    @util.blocked
    def onHideEmotionColors(self, on):
        if on != self.ui.actionHide_Emotion_Colors.isChecked():
            self.ui.actionHide_Emotion_Colors.setChecked(on)
        self.scene.setHideEmotionColors(on, undo=(not self._isOpeningDiagram))

    @util.blocked
    def onHideNames(self, on):
        self.scene.setHideNames(on)

    @util.fblocked
    def onHideVariablesOnDiagram(self, on):
        if on != self.ui.actionHide_Variables_on_Diagram.isChecked():
            self.ui.actionHide_Variables_on_Diagram.setChecked(on)
        self.scene.setHideVariablesOnDiagram(on, undo=(not self._isOpeningDiagram))

    @util.fblocked
    def onHideVariableSteadyStates(self, on):
        if on != self.ui.actionHide_Variable_Steady_States.isChecked():
            self.ui.actionHide_Variable_Steady_States.setChecked(on)
        self.scene.setHideVariableSteadyStates(on, undo=(not self._isOpeningDiagram))

    def onGraphicalTimeline(self):
        on = self.ui.actionShow_Graphical_Timeline.isChecked()
        if on != self.ui.actionShow_Graphical_Timeline.isChecked():
            self._blocked = True
            self.ui.actionShow_Graphical_Timeline.setChecked(on)
            self._blocked = False
        undo = not self._isOpeningDiagram
        self.scene.setHideDateSlider(not on, undo=undo)

    def onExpandGraphicalTimeline(self, on):
        if self._blocked:
            return
        was = self._blocked
        self._blocked = True
        self.ui.actionExpand_Graphical_Timeline.setChecked(on)
        self._blocked = was
        self.documentView.setExpandGraphicalTimeline(on)

    def onGraphicalTimelineExpanded(self, on):
        if self._blocked:
            return
        was = self._blocked
        self._blocked = True
        self.ui.actionExpand_Graphical_Timeline.setChecked(on)
        self._blocked = was

    def onQmlSelectionChanged(self):
        self.documentView.controller.updateActions()

    def onServerRefresh(self):
        self.serverFileModel.update()

    def onServerReload(self):
        self.serverFileModel.reload()

    def onBetaWiki(self):
        QDesktopServices.openUrl(
            QUrl("http://vedanamedia.com/our-products/family-diagram/beta-program/")
        )

    def onShowHelpTips(self, on):
        self.documentView.view.setShowHelpTips(on)

    def onShowManual(self):
        self.onShowManualLatest()
        # appDataDir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        # fpath = os.path.join(appDataDir, 'misc', 'User-Manual', 'Family Diagram Manual.html')
        # QDesktopServices.openUrl(QUrl.fromLocalFile(fpath))
        # # if not self.manualView:
        # #     self.manualView = QWebEngineView()
        # #     self.manualView.setPage(util.WebEnginePage())
        # # self.manualView.load(QUrl("qrc:///userManual/Family Diagram Manual.html"))
        # # self.manualView.show()

    def onShowManualLatest(self):
        QDesktopServices.openUrl(
            QUrl("https://alaskafamilysystems.com/products/family-diagram/user-manual/")
        )

    def onShowDiscussionForom(self):
        QDesktopServices.openUrl(QUrl("https://discussions.familydiagram.com/"))

    def onResetAll(self):
        hadActiveLayers = bool(self.scene.activeLayers())
        self.scene.resetAll()  # should call zoomFit via activeLayersChanged
        self.documentView.searchModel.clear()
        if not hadActiveLayers:
            self.view.zoomFit()

    def onJumpToNow(self):
        self.scene.jumpToNow()

    def onStartProfile(self):
        self.ui.actionStart_Profile.setEnabled(False)
        self.ui.actionStop_Profile.setEnabled(True)

        import cProfile

        _profile = cProfile.Profile()
        _profile.enable()
        atexit.register(self._profile_atexit)

    def onStopProfile(self):
        self.ui.actionStart_Profile.setEnabled(True)
        self.ui.actionStop_Profile.setEnabled(False)

        self._profile.disable()
        import io, pstats

        s = io.StringIO()
        sortby = "cumulative"
        ps = pstats.Stats(self._profile, stream=s).sort_stats(sortby)
        ps.print_stats()  # ('pksampler')
        log.info(s.getvalue())
        self._profile = None
        atexit.unregister(self._profile_atexit)

    def _profile_atexit(self):
        if self._profile:
            self.onStopProfile()

    @util.blocked
    def onClearPreferences(self, dummy=None):
        ok = QMessageBox.question(
            self,
            "Clear and quit?",
            "This will quit the app. OK?",
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Ok,
        )
        if ok == QMessageBox.Ok:
            self.prefs.clear()
            self.prefs.sync()
            QApplication.instance().quit()

    def onExportSceneDict(self):
        if self.scene:
            data = {}
            self.scene.write(data)
            log.info(data)

    def onSaveSceneAsJSON(self):
        self.saveAs(as_json=True)

    ## Session

    def onActiveFeaturesChanged(self, newFeatures, oldFeatures):
        """Called by AppController."""
        if self.session.activeFeatures() == []:
            # disable entire app to force downloading a newer version.
            self.fileManager.setEnabled(False)
            self.documentView.setEnabled(False)
            self.closeDocument()
        elif self.session.hasFeature(vedana.LICENSE_FREE):
            # Only one diagram, no file browser, open functions
            self.fileManager.setEnabled(False)
            self.documentView.setEnabled(True)
            # self.view.purchaseButton.show()
            self.ui.actionShow_Account.setVisible(True)
            self.view.sceneToolBar.accountButton.setAutoInvertColor(False)
            self.view.sceneToolBar.accountButton.setUncheckedPixmapPath(
                util.QRC + "cart-button.png"
            )
        elif self.session.hasFeature(
            vedana.LICENSE_PROFESSIONAL, vedana.LICENSE_BETA, vedana.LICENSE_ALPHA
        ):
            self.fileManager.setEnabled(True)
            self.documentView.setEnabled(True)
            self.view.setEnabled(True)
            self.view.sceneToolBar.accountButton.setAutoInvertColor(True)
            self.view.sceneToolBar.accountButton.setUncheckedPixmapPath(
                util.QRC + "unlock-icon.png"
            )
            # self.view.purchaseButton.hide()
        else:
            log.error(f"Unknown active features: {self.session.activeFeatures()}")
        self.documentView.controller.updateActions()
        self.updateWindowTitle()

    ## Server

    def onUploadToServer(self):
        """
        This goes here because it connects a button in the DocumentView to the
        ServerFileModel, and then also opens the resulting file.
        """

        def onFinished():
            reply = onFinished._reply
            reply.finished.disconnect(onFinished)
            try:
                self.session.server().checkHTTPReply(reply)
            except HTTPError as e:
                QMessageBox.information(
                    None,
                    "Error uploading to server",
                    "There was a problem uploading this file to the server. Please contact support at info@alaskafamilysystems.com.\n\nYour local copy of this file is unchanged.",
                )
                return
            if hasattr(reply, "_pk_body"):
                bdata = reply._pk_body
            else:
                bdata = reply.readAll()
            data = pickle.loads(bdata)
            data["status"] = CUtil.FileIsCurrent
            data["owner"] = data["user"]["username"]
            diagram = Diagram.create(data)
            self.serverFileModel._addOrUpdateDiagram(diagram)
            fpath = self.serverFileModel.localPathForID(data["id"])
            localFPath = self.document.url().toLocalFile()
            self.fileManager.onServerFileClicked(fpath)
            deleteLocalCopy = QMessageBox.question(
                None,
                "Delete local copy?",
                self.S_CONFIRM_DELETE_LOCAL_COPY_OF_UPLOADED_DIAGRAM,
            )
            if deleteLocalCopy == QMessageBox.Yes:
                shutil.rmtree(localFPath)

        ok = QMessageBox.question(
            None,
            "Are you sure?",
            self.S_CONFIRM_UPLOAD_DIAGRAM,
        )
        if ok != QMessageBox.Yes:
            return
        data = {}
        self.scene.write(data)
        basename = QFileInfo(self.document.url().toLocalFile()).baseName()
        args = {
            "user_id": self.session.user.id,
            "name": basename,
            "data": pickle.dumps(data),
        }
        reply = self.session.server().nonBlockingRequest("POST", "/diagrams", data=args)
        reply.finished.connect(onFinished)
        onFinished._reply = reply

    ## Welcome

    def showWelcome(self):
        if self.accountDialog.isShown():
            return
        if not self.welcomeDialog.isShown():
            self.welcomeDialog.show()

    def onWelcomeHidden(self):
        if not self.session.activeFeatures():
            self.showAccount()

    def onSafeAreaMarginsChanged(self, margins):
        pass
        # self.here(margins)

    def onScreenOrientationChanged(self, orientation):
        """TODO: Support iPhone X save areas."""
        # self.here(orientation)
        m = CUtil.instance().safeAreaMargins()
        self.documentView.adjust()
        # self.here(m.left(), m.top(), m.right(), m.bottom())
        # self.here(orientation)
