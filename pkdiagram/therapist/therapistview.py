import logging

from _pkdiagram import CUtil

from pkdiagram.pyqt import (
    pyqtSignal,
    Qt,
    QApplication,
    QQmlEngine,
    QQuickWidget,
    QUrl,
    QMargins,
)
from pkdiagram import util
from pkdiagram.app import Session, AppConfig
from pkdiagram.therapist import Therapist
from pkdiagram.views import AccountDialog


_log = logging.getLogger(__name__)


class TherapistView(QQuickWidget):

    closed = pyqtSignal()

    def __init__(self, session: Session, parent=None):
        self.qmlEngine = QQmlEngine()
        super().__init__(self.qmlEngine, parent)

        self.appConfig: AppConfig = appConfig
        self.session = session
        self.therapist = Therapist(self.session)

        for path in util.QML_IMPORT_PATHS:
            self.qmlEngine.addImportPath(path)

        self.accountDialog = AccountDialog(self.qmlEngine, self)
        self.accountDialog.init()

        if not self.session.activeFeatures():
            self.showAccount()

        # CUtil.instance().safeAreaMarginsChanged[QMargins].connect(
        #     self.onSafeAreaMarginsChanged
        # )

        # Init

        # self.onSafeAreaMarginsChanged(CUtil.instance().safeAreaMargins())

    def init(self):
        from _pkdiagram import CUtil

        self.setFormat(util.SURFACE_FORMAT)
        self.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.setSource(QUrl("resources:qml/TherapistApplication.qml"))

    def deinit(self):
        self.setSource(QUrl(""))
        self.accountDialog.deinit()

    def showAccount(self):
        if not self.accountDialog.isShown():
            if not self.session.isLoggedIn():
                lastSessionData = self.appConfig.get(
                    "lastSessionData", {}, pickled=True
                )
                if lastSessionData:
                    self.session.login(token=lastSessionData["session"]["token"])
            self.accountDialog.show()

    # def onSafeAreaMarginsChanged(self, margins: QMargins):
    #     # _log.info(
    #     #     f"onSafeAreaMarginsChanged: left: {margins.left()}, top: {margins.top()}, right: {margins.right()}, bottom: {margins.bottom()}"
    #     # )
    #     self.setContentsMargins(
    #         margins.left(), margins.top(), margins.right(), margins.bottom()
    #     )
