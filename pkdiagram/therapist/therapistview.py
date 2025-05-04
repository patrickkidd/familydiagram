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
from pkdiagram.app import Session
from pkdiagram.therapist import Therapist


_log = logging.getLogger(__name__)


class TherapistView(QQuickWidget):

    closed = pyqtSignal()

    def __init__(self, session: Session, parent=None):
        self.qmlEngine = QQmlEngine()
        super().__init__(self.qmlEngine, parent)

        self.session = session
        self.therapist = Therapist(self)

        for path in util.QML_IMPORT_PATHS:
            self.qmlEngine.addImportPath(path)

        CUtil.instance().safeAreaMarginsChanged[QMargins].connect(
            self.onSafeAreaMarginsChanged
        )

        # Init

        self.onSafeAreaMarginsChanged(CUtil.instance().safeAreaMargins())

    def init(self):
        from _pkdiagram import CUtil

        self.util = QApplication.instance().qmlUtil()  # should be local, not global
        self.qmlEngine.rootContext().setContextProperty("util", self.util)
        self.qmlEngine.rootContext().setContextProperty("session", self.session)
        self.qmlEngine.rootContext().setContextProperty("therapist", self.therapist)
        self.setFormat(util.SURFACE_FORMAT)
        self.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.setSource(QUrl("resources:qml/TherapistView.qml"))

    def deinit(self):
        self.setSource(QUrl(""))

    def onSafeAreaMarginsChanged(self, margins: QMargins):
        # _log.info(
        #     f"onSafeAreaMarginsChanged: left: {margins.left()}, top: {margins.top()}, right: {margins.right()}, bottom: {margins.bottom()}"
        # )
        self.setContentsMargins(
            margins.left(), margins.top(), margins.right(), margins.bottom()
        )
