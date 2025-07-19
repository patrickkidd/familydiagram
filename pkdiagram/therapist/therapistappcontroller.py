from _pkdiagram import CUtil
from pkdiagram.app import AppConfig
from pkdiagram.pyqt import QObject, QEvent, QApplication, QQmlEngine
from pkdiagram.app import Session
from pkdiagram.therapist import Therapist


class TherapistAppController(QObject):
    """
    App controller for the therapist app.
    """

    def __init__(self, app: QApplication, parent=None):
        super().__init__(parent)

        self.app = app

        self.util = QApplication.instance().qmlUtil()  # should be local, not global

        self.session = Session()
        self.session.changed.connect(self.onSessionChanged)

        self.appConfig = AppConfig(self, prefsName="therapist.alaskafamilysystems.com")
        self.therapist = Therapist(self.session)

    def init(self, engine: QQmlEngine):
        engine.rootContext().setContextProperty("CUtil", CUtil.instance())
        engine.rootContext().setContextProperty("util", self.util)
        engine.rootContext().setContextProperty("session", self.session)
        engine.rootContext().setContextProperty("therapist", self.therapist)
        self.appConfig.init()
        self.session.setQmlEngine(engine)
        lastSessionData = self.appConfig.get("lastSessionData", pickled=True)
        if lastSessionData and not self.appConfig.wasTamperedWith:
            self.session.init(sessionData=lastSessionData)
        else:
            self.session.init()
        self.therapist.init()

    def deinit(self):
        pass

    def exec(self, mw):
        """
        Stuff that happens once per app load on the first MainWindow.
        At this point the MainWindow is fully initialized with a session
        and ready for app-level verbs.
        """
        self.app.exec()

    def onSessionChanged(self, oldFeatures, newFeatures):
        """Called on login, logout, invalidated token."""

        if self.session.isLoggedIn():
            self.appConfig.set("lastSessionData", self.session.data(), pickled=True)
        else:
            self.appConfig.delete("lastSessionData")
        self.appConfig.write()
