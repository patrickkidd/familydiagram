import signal, os.path, logging

import btcopilot
from pkdiagram.pyqt import QObject, QTimer, QSize, QMessageBox, QApplication
from pkdiagram import util, version, pepper
from pkdiagram.app import AppConfig, Session, Analytics


CUtil = util.CUtil

log = logging.getLogger(__name__)


class AppController(QObject):
    """
    App-level singleton that manages MainWindows verbs.

    Handles pre-window init like appconfig, cached session creds login, EULA.

    Synonym: MainwindowController

    Currently the app only has one mainwindow, so it manages that one.
    This allows the MainWindow to focus on the documentview instead of
    cluttering it up with all the app-level init and event handling.
    """

    S_APPCONFIG_TAMPERED_WITH = "The license info on this computer has been tampered with. You will be logged out and will need to log in again."

    S_VERSION_DEACTIVATED = "The app has been disabled due to a critical bug fix. Please update to the newest version to continue using it. We are sorry for the inconvenience but this is to ensure the safety of your data and your computer."

    S_UPGRADED_TO_PRO_LICENSE = 'You have upgraded to a subscription which gives you full access to all features.\n\nIf you were working on your free diagram, you can find it listed in the server files view as "Free Diagram". We hope you find Family Diagram useful.'

    S_USING_FREE_LICENSE = 'You are now using the free license. You will only have access to a single diagram which cannot be saved or transfered from this computer. This makes it possible for anyone to research their own family.\n\nYou can import a diagram from another person, though this will overwrite any previous contents of your free diagram. This allows you to import your diagram from a coach, for example. You cannot send or use your free diagram outside of this computer.\n\nIf you want to create more diagrams or access the research server, you will need to purchase the full version of this app by clicking "Family Diagram" -> "Show Account" in the menu bar. An option to export to a coach or to make a backup is to purchase a monthly subscription and immediately cancel it, giving you one month to export as many copies as you like.'

    S_APPCONFIG_UPGRADED_LOGIN_REQUIRED = (
        "The app configuration has been upgraded. Please log in again."
    )

    def __init__(self, app, prefsName=None):
        super().__init__(app)
        self.isInitialized = False

        self.mw = None
        self.app = app
        self.prefs = QApplication.instance().prefs()
        self._pendingOpenFilePath = None
        self.appConfig = AppConfig(app, prefsName=prefsName)
        self._analytics = Analytics(datadog_api_key=pepper.DATADOG_API_KEY)
        self.session = Session(self._analytics)
        if not self.prefs.value(
            "enableAppUsageAnalytics", defaultValue=True, type=bool
        ):
            self._analytics.setEnabled(False)

        self.app.appFilter.fileOpen.connect(self.onOSFileOpen)
        self.app.appFilter.urlOpened.connect(self.onURLOpened)
        self.app.appFilter.escapeKey.connect(self.onEscapeKey)
        self.session.changed.connect(self.onSessionChanged)

        # Allow ctrl-c to quit the app
        timer = QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(1250)

        def _quit(x, y):
            app.quit()

        signal.signal(signal.SIGINT, _quit)

    def init(self):
        assert not self.isInitialized

        self._analytics.init()

        self.appConfig.init()

        self.isInitialized = True

    def deinit(self):
        self.appConfig.deinit()
        self.session.deinit()

        self._analytics.deinit()

    def _pre_event_loop(self, mw):
        """
        Everything before the event loop.
        - More of a script where the components are initialized than an init with incomplete state until complete.
        """

        assert mw.isInitialized
        assert self.mw is None
        self.mw = mw

        # AppConfig Protection

        if self.appConfig.wasV1:
            QMessageBox.warning(
                None, "Login required", self.S_APPCONFIG_UPGRADED_LOGIN_REQUIRED
            )
        elif self.appConfig.wasTamperedWith:
            QMessageBox.warning(
                None, "App configuration tampered with.", self.S_APPCONFIG_TAMPERED_WITH
            )
            os.remove(self.appConfig.filePath)

        # Syncronous init from AppConfig or else from Network

        lastSessionData = self.appConfig.get("lastSessionData", pickled=True)
        if lastSessionData and not self.appConfig.wasTamperedWith:
            self.session.init(sessionData=lastSessionData)
        else:
            self.session.init()

        # EULA

        acceptedEULA = not self.prefs.value("acceptedEULA", defaultValue=False)
        if acceptedEULA:
            if not mw.showEULA():
                return  # TODO: Move showEULA out of MainWindow

        # Read Preferences

        if version.IS_ALPHA_BETA:
            checkForUpdatesAutomatically = True
        else:
            checkForUpdatesAutomatically = self.prefs.value(
                "checkForUpdatesAutomatically", defaultValue=True
            )
        if checkForUpdatesAutomatically:
            CUtil.instance().checkForUpdates()

        util.ENABLE_PINCH_PAN_ZOOM = self.prefs.value(
            "enablePinchPanZoom", type=bool, defaultValue=util.ENABLE_PINCH_PAN_ZOOM
        )
        util.ENABLE_WHEEL_PAN = self.prefs.value("enableWheelPan", defaultValue=True)

        showCurrentDate = self.prefs.value(
            "showCurrentDate", type=bool, defaultValue=True
        )
        mw.onShowCurrentDateTime(showCurrentDate)

        size = self.prefs.value("windowSize", type=QSize, defaultValue=QSize(900, 650))
        mw.resize(size)

        editorMode = self.prefs.value("editorMode", type=bool, defaultValue=False)
        mw.onEditorMode(editorMode)

        ## Welcome Modal

        dontShowWelcome = self.prefs.value(
            "dontShowWelcome", defaultValue=False, type=bool
        )
        # show welcome no matter what
        if not dontShowWelcome:  # disable welcome screen for now
            mw.showWelcome()
        elif not self.session.activeFeatures():
            mw.showAccount()

        if self.session.hasFeature(btcopilot.LICENSE_FREE):
            mw.serverFileModel.syncDiagramFromServer(self.session.user.free_diagram_id)

        mw.show()

        # Open file requested by OS on launch (and override saved last opened file)
        if self._pendingOpenFilePath and self.session.hasFeature(
            btcopilot.LICENSE_PROFESSIONAL
        ):
            # Means OS requested opening file before mw was ready
            self.onFileOpen(self._pendingOpenFilePath)
            self._pendingOpenFilePath = None
        else:
            if self.prefs.value("reopenLastFile", defaultValue=True, type=bool):
                mw.openLastFile()

    def _event_loop(self, mw):
        mw.closed.connect(self.app.quit)
        self.app.exec()
        mw.closed.disconnect(self.app.quit)

    def _post_event_loop(self, mw):
        """Everything after the event loop. Releases MW ref."""

        ## Write Preferences

        self.prefs.setValue("windowSize", mw.size())
        lastFileWasOpen = not mw.atHome() and not self.session.hasFeature(
            btcopilot.LICENSE_FREE
        )
        self.prefs.setValue("lastFileWasOpen", lastFileWasOpen)
        showCurrentDate = mw.ui.actionShow_Current_Date.isChecked()
        self.prefs.setValue("showCurrentDate", showCurrentDate)
        self.prefs.sync()

        self.mw = None

    def exec(self, mw):
        """
        Stuff that happens once per app load on the first MainWindow.
        At this point the MainWindow is fully initialized with a session
        and ready for app-level verbs.
        """
        self._pre_event_loop(mw)

        self._event_loop(mw)

        self._post_event_loop(mw)

    ## Events

    def onOSFileOpen(self, fpath):
        """Called from QEvent.FileOpen (Drop from Finder)."""
        if util.suffix(fpath) != util.EXTENSION:
            log.debug(f"Ignoring command line argument: {fpath}")
            return

        if self.mw:
            self.mw.open(filePath=fpath)
        else:
            self._pendingOpenFilePath = fpath

    def onURLOpened(self, url):
        """Called when familydiagram:// URL is opened"""
        log.info(f"URL opened: {url}")

        if not url.startswith("familydiagram://"):
            log.warning(f"Ignoring non-familydiagram URL: {url}")
            return

        if "authenticate" not in url:
            log.warning(f"Unknown URL path: {url}")
            QMessageBox.warning(None, "Unknown URL", f"Unknown URL action: {url}")
            return

        if not self.session.isLoggedIn():
            QMessageBox.warning(
                None,
                "Not Logged In",
                "You must be logged in to Family Diagram to authenticate to the training web app.",
            )
            return

        try:
            import pickle

            response = self.session.server().blockingRequest(
                "GET", "/sessions/web-auth-token"
            )
            data = pickle.loads(response.body)
            authUrl = data["url"]

            from pkdiagram.widgets.authdialog import AuthUrlDialog

            dialog = AuthUrlDialog(authUrl, self.mw)
            dialog.exec_()
        except Exception as e:
            log.error(f"Failed to get auth URL: {e}", exc_info=True)
            QMessageBox.critical(
                None,
                "Authentication Error",
                f"Failed to generate authentication link: {str(e)}",
            )

    def onEscapeKey(self, e):
        if self.mw:
            self.mw.documentView.controller.closeTopLevelView()
            e.accept()

    def onSessionChanged(self, oldFeatures, newFeatures):
        """Called on login, logout, invalidated token."""

        if self.session.isLoggedIn():
            self.appConfig.set("lastSessionData", self.session.data(), pickled=True)

            # If logged in, activeFeatures will always be at least btcopilot.LICENSE_FREE
            # If not logged in, there is always the possibility that lastSessionData will set activeFeatures
            # If not logged in and no active features, then always show the account dialog to force a login

            if self.session.activeFeatures() == []:
                if self.session.isVersionDeactivated():
                    QMessageBox.information(
                        None, "Version Deactivated", self.S_VERSION_DEACTIVATED
                    )
            elif self.session.hasFeature(btcopilot.LICENSE_FREE):
                if not oldFeatures or btcopilot.any_license_match(
                    oldFeatures,
                    (
                        btcopilot.LICENSE_PROFESSIONAL,
                        btcopilot.LICENSE_BETA,
                        btcopilot.LICENSE_ALPHA,
                    ),
                ):
                    if not self.session.isInitializing():
                        QMessageBox.information(
                            None, "Using free license", self.S_USING_FREE_LICENSE
                        )

                    if self.mw:
                        self.mw.serverFileModel.syncDiagramFromServer(
                            self.session.user.free_diagram_id
                        )
                        self.mw.openFreeLicenseDiagram()

            elif self.session.hasFeature(
                btcopilot.LICENSE_PROFESSIONAL,
                btcopilot.LICENSE_BETA,
                btcopilot.LICENSE_ALPHA,
            ):
                self.mw.fileManager.show()
                if btcopilot.any_license_match(oldFeatures, [btcopilot.LICENSE_FREE]):
                    if not self.session.isInitializing():
                        QMessageBox.information(
                            None,
                            "Upgraded to Pro License.",
                            self.S_UPGRADED_TO_PRO_LICENSE,
                        )
                    if self.mw:
                        self.mw.serverFileModel.update()
            else:
                log.info(f"Unknown active features: {self.session.activeFeatures()}")

        else:
            # When the user logs out, already promted to confirm via Qml.
            self.appConfig.delete("lastSessionData")
            self.mw.fileManager.hide()
        self.appConfig.write()

        if self.mw:
            self.mw.onActiveFeaturesChanged(newFeatures, oldFeatures)
