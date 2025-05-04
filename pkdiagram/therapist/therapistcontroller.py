from pkdiagram.pyqt import QObject, QEvent, QApplication
from pkdiagram.app import Session


class TherapistController(QObject):
    def __init__(self, app: QApplication, parent=None):
        super().__init__(parent)

        self.app = app

        self.session = Session()
        self.session.changed.connect(self.onSessionChanged)

    def init(self):
        pass

    def deinit(self):
        pass

    def onSessionChanged(self):
        pass

    def exec(self, mw):
        """
        Stuff that happens once per app load on the first MainWindow.
        At this point the MainWindow is fully initialized with a session
        and ready for app-level verbs.
        """
        self.app.exec()
