from .pyqt import *
from . import version, util, commands
from .util import CUtil
from .preferences_form import Ui_Preferences


class Preferences(QDialog):
    def __init__(self, mw):
        super().__init__(mw)
        self.ui = Ui_Preferences()
        self.ui.setupUi(self)
        self.mw = mw

        # Signals

        self.ui.reopenFileBox.toggled[bool].connect(self.onReopenLastFile)
        self.ui.enablePinchZoomBox.toggled[bool].connect(self.onEnablePinchZoom)
        self.ui.enableWheelPanBox.toggled[bool].connect(self.onEnableWheelPan)

        self.ui.darkLightSystemBox.toggled[bool].connect(self.onDarkLightMode)
        self.ui.darkLightDarkBox.toggled[bool].connect(self.onDarkLightMode)
        self.ui.darkLightLightBox.toggled[bool].connect(self.onDarkLightMode)

        self.ui.iCloudDriveButton.toggled[bool].connect(self.oniCloudDrive)
        self.ui.localDriveButton.toggled[bool].connect(self.onLocalDrive)
        self.ui.setDocsPathButton.clicked.connect(self.onSetDocsPath)
        self.ui.closeButton.clicked.connect(self.accept)
        self.ui.analyticsBox.toggled[bool].connect(self.onAnalytics)
        CUtil.instance().iCloudOnChanged[bool].connect(self.oniCloudOnChanged)

    @util.blocked
    def init(self, prefs):
        """Called just before exec()."""
        self.prefs = prefs
        # loaded in MainWindow to set them before files are loading.
        self.ui.reopenFileBox.setChecked(
            self.prefs.value("reopenLastFile", defaultValue=True, type=bool)
        )
        self.ui.enablePinchZoomBox.setChecked(util.ENABLE_PINCH_PAN_ZOOM)
        util.ENABLE_WHEEL_PAN = self.prefs.value(
            "enableWheelPan", defaultValue=True, type=bool
        )
        self.ui.enableWheelPanBox.setChecked(util.ENABLE_WHEEL_PAN)
        #
        checkForUpdatesAutomatically = self.prefs.value(
            "checkForUpdatesAutomatically", defaultValue=True, type=bool
        )
        self.ui.checkForUpdatesBox.setChecked(checkForUpdatesAutomatically)
        self.ui.checkForUpdatesBox.setEnabled(not version.IS_ALPHA_BETA)
        #
        darkLightMode = self.prefs.value(
            "darkLightMode", defaultValue=util.PREFS_UI_HONOR_SYSTEM_DARKLIGHT_MODE
        )
        if darkLightMode == util.PREFS_UI_HONOR_SYSTEM_DARKLIGHT_MODE:
            self.ui.darkLightSystemBox.setChecked(True)
        elif darkLightMode == util.PREFS_UI_DARK_MODE:
            self.ui.darkLightDarkBox.setChecked(True)
        elif darkLightMode == util.PREFS_UI_LIGHT_MODE:
            self.ui.darkLightLightBox.setChecked(True)
        #
        iCloudAvailable = CUtil.instance().iCloudAvailable()
        self.ui.iCloudDriveButton.setEnabled(iCloudAvailable)
        if iCloudAvailable:
            iCloudOn = CUtil.instance().iCloudOn()
        else:
            iCloudOn = self.prefs.value("iCloudWasOn", defaultValue=False, type=bool)
        self.ui.iCloudDriveButton.setChecked(iCloudOn)
        self.ui.localDriveButton.setChecked(not iCloudOn)
        localDocsPath = self.prefs.value("localDocsPath", type=str)
        self.ui.localDocsPathLabel.setText(localDocsPath)
        usingLocal = not util.usingOrSimulatingiCloud()
        self.ui.setDocsPathButton.setEnabled(usingLocal)
        self.ui.localDocsPathLabel.setEnabled(usingLocal)

        enableAppUsageAnalytics = self.prefs.value(
            "enableAppUsageAnalytics", defaultValue=True, type=bool
        )
        self.ui.analyticsBox.setChecked(enableAppUsageAnalytics)

    def deinit(self):
        self.prefs = None

    @util.blocked
    def onReopenLastFile(self, on):
        self.prefs.setValue("reopenLastFile", on)
        commands.track("Prefs: reopenLastFile %s" % on)

    @util.blocked
    def onEnablePinchZoom(self, on):
        util.ENABLE_PINCH_PAN_ZOOM = on
        self.prefs.setValue("enablePinchPanZoom", on)
        commands.track("Prefs: enablePinchZoom %s" % on)

    @util.blocked
    def onEnableWheelPan(self, on):
        util.ENABLE_WHEEL_PAN = on
        self.prefs.setValue("enableWheelPan", on)

    @util.blocked
    def onCheckForUpdatesAutomatically(self, on):
        self.prefs.setValue("checkForUpdatesAutomatically", on)
        commands.track("Prefs: checkForUpdatesAutomatically %s" % on)

    @util.blocked
    def onDarkLightMode(self, on):
        if self.ui.darkLightSystemBox.isChecked():
            self.prefs.setValue(
                "darkLightMode", util.PREFS_UI_HONOR_SYSTEM_DARKLIGHT_MODE
            )
        elif self.ui.darkLightDarkBox.isChecked():
            self.prefs.setValue("darkLightMode", util.PREFS_UI_DARK_MODE)
        elif self.ui.darkLightLightBox.isChecked():
            self.prefs.setValue("darkLightMode", util.PREFS_UI_LIGHT_MODE)
        QApplication.instance().paletteChanged.emit(QApplication.instance().palette())
        commands.track("Prefs: darkLightMode %s" % self.prefs.value("darkLightMode"))

    @util.blocked
    def oniCloudOnChanged(self, on):
        """Called when canceled from C code."""
        self.ui.iCloudDriveButton.setChecked(on)

    @util.blocked
    def oniCloudDrive(self, on):
        if on and on != util.usingOrSimulatingiCloud():
            commands.track("iCloud %s" % on)
            # if on:
            #     ret = QMessageBox.question(self, 'Are you sure?',
            #                                'Are you sure you want to move all of your files from your local Documents folder to iCloud Drive?')
            # else:
            #     ret = QMessageBox.Yes
            # if ret == QMessageBox.No:
            #     self.ui.iCloudDriveButton.setChecked(not on)
            #     return
            CUtil.instance().setiCloudOn(on)
            stillOn = (
                util.usingOrSimulatingiCloud()
            )  # may be canceled in C code; need to check
            self.ui.iCloudDriveButton.setChecked(stillOn)
            self.ui.setDocsPathButton.setEnabled(not stillOn)
            self.ui.localDocsPathLabel.setEnabled(not stillOn)

    def onLocalDrive(self, on):
        if on and on != (not util.usingOrSimulatingiCloud()):
            commands.track("Use local drive %s" % on)
            # ret = QMessageBox.question(self, 'Are you sure?',
            #                            'Are you sure you want to move all of your files from iCloud Drive to your local folder?')
            # if ret == QMessageBox.No:
            #     self.ui.localDriveButton.setChecked(not on)
            #     return
            CUtil.instance().setiCloudOn(False)
            localDocsPath = self.prefs.value("localDocsPath", type=str)
            CUtil.instance().forceDocsPath(localDocsPath)
            self.prefs.setValue("iCloudWasOn", False)
            self.ui.setDocsPathButton.setEnabled(True)
            self.ui.localDocsPathLabel.setEnabled(True)

    def onSetDocsPath(self):
        localDocsPath = self.prefs.value("localDocsPath", type=str)
        fpath = QFileDialog.getExistingDirectory(
            QApplication.activeWindow(), "Choose folder", localDocsPath
        )
        if not fpath:
            return
        self.prefs.setValue("localDocsPath", fpath)
        self.ui.localDocsPathLabel.setText(fpath)
        CUtil.instance().forceDocsPath(fpath)

    @util.blocked
    def onAnalytics(self, on):
        self.prefs.setValue("enableAppUsageAnalytics", on)
