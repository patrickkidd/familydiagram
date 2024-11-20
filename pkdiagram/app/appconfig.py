import os.path, pickle, logging
from pkdiagram.pyqt import QObject
from pkdiagram import util, version


log = logging.getLogger(__name__)


class AppConfig(QObject):
    """Encrypted disk storage to keep user from tampering with keys, etc.
    Currently uses hardware ID to invalidate session, which is unreliable. So
    But it only invlidates the session which is fine.
    """

    def __init__(self, parent=None, filePath=None, prefsName=None):
        super().__init__(parent)
        self.data = {}
        self.hardwareUUID = None
        self.filePath = filePath
        self.wasTamperedWith = False
        self.prefsName = prefsName

    def init(self):
        self.hardwareUUID = util.HARDWARE_UUID
        if self.filePath is None:
            appDataDir = util.appDataDir()
            fileName = f"cherries-{self.prefsName}" if self.prefsName else "cherries"
            self.filePath = os.path.join(appDataDir, fileName)
        # init from disk
        self.read()

    def deinit(self):
        self.write()

    def savedYet(self):
        return os.path.isfile(self.filePath)

    def isFirstRun(self):
        return self.savedYet()

    def read(self):
        """Read the cache file."""
        if not os.path.isfile(self.filePath):
            return
        try:
            bdata = util.readWithHash(self.filePath)
        except util.FileTamperedWithError:
            self.wasTamperedWith = True
            log.debug("appconfig not encrypted; resetting...")
            self.data = {}
            return
        self.data = pickle.loads(bdata)
        if self.data.get("lastAppVersion") != version.VERSION:
            self.data["versionDeactivated"] = False
            # TODO: maybe handle new app version?
        if self.data.get("hardwareUUID") != self.hardwareUUID:
            log.info(
                "Hardware UUID %s != %s (appconfig transfered from another machine; resetting...)"
                % (self.data.get("hardwareUUID"), self.hardwareUUID)
            )
            self.wasTamperedWith = True
            self.data = {}
            return

    def write(self):
        self.data["hardwareUUID"] = self.hardwareUUID
        self.data["lastAppVersion"] = version.VERSION
        bdata = pickle.dumps(self.data)
        util.writeWithHash(self.filePath, bdata)

    def set(self, key, value, pickled=False):
        if pickled:
            x = pickle.dumps(value)
        else:
            x = value
        self.data[key] = x

    def get(self, key, defaultValue=None, pickled=False):
        ret = self.data.get(key, defaultValue)
        if pickled and ret:
            ret = pickle.loads(ret)
        return ret

    def delete(self, key):
        if key in self.data:
            del self.data[key]
