from pkdiagram.pyqt import QNetworkAccessManager


class QNAM(QNetworkAccessManager):

    _instance = None

    @staticmethod
    def instance():
        if not QNAM._instance:
            QNAM._instance = QNAM()
        return QNAM._instance
