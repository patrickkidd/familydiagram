import os
import time
import uuid, pickle, logging, copy
import dataclasses
import logging

import vedana

from pkdiagram.pyqt import (
    pyqtSlot,
    pyqtProperty,
    QObject,
    QTimer,
    pyqtSignal,
    QVariant,
    QQmlEngine,
)
from pkdiagram import util, version
from pkdiagram.models import QObjectHelper
from pkdiagram.server_types import User, Diagram, License, Server, HTTPError, Discussion
from pkdiagram.app import Analytics, DatadogLog, DatadogLogStatus, DatadogFDType


log = logging.getLogger(__name__)


class Session(QObject, QObjectHelper):
    """Current state of licenses, features, server state (e.g. users, deactivated versions)
    - Current license (offline storage)
    - Version deactivation.
    """

    changed = pyqtSignal(list, list)
    loginFailed = pyqtSignal()
    logoutFailed = pyqtSignal()
    logoutFinished = pyqtSignal()

    QObjectHelper.registerQtProperties(
        [
            {"attr": "hash", "type": str},
            {"attr": "isAdmin", "type": bool},
            {"attr": "copilot"},
        ]
    )

    def __init__(self, analytics: Analytics | None = None, parent=None):
        super().__init__(parent)
        self._analytics = analytics
        self._qmlEngine = (
            None  # Hack for engine.newObject() so long as QmlUtil is a singleton
        )
        self._server = Server(self)
        self._data = None
        self._user = None
        self._userDict = {}
        self.users = []
        self._isVersionDeactivated = False
        self._activeFeatures = []
        self._isInitializing = False
        self._initialized = False
        self._hash = str(uuid.uuid4())
        self._updateTimer = QTimer(self)
        self._updateTimer.setInterval(60 * 60 * 1000)  # every hour
        self._updateTimer.timeout.connect(self.update)
        self.initQObjectHelper()

    # Verbs

    def init(self, sessionData=None, syncWithServer=True):
        """Check what to do after all of the following have completed:
            1) lastSessionData are verified with the server
            2) The session is logged in and licenses are updated.
            3) The deactivated versions from the server are updated.
        This allows the person to work offline while keeping licenses as current as possible.
        """
        if not sessionData:
            sessionData = {}

        self._isInitializing = True
        if sessionData:
            self.setData(sessionData)  # won't send signals b/c isInitializing is True
            lastLicenses = [
                x
                for x in sessionData.get("licenses", [])
                if x["policy"]["code"] != vedana.LICENSE_FREE
            ]
            self.track("re_logged_in")
        else:
            lastLicenses = []

        if syncWithServer and sessionData:
            args = pickle.dumps(
                {
                    "licenses": lastLicenses,
                    "token": sessionData["session"]["token"],
                }
            )
            try:
                response = self.server().blockingRequest(
                    "GET", "/init", args, anonymous=True
                )
            except HTTPError as e:
                if e.status_code == 404:
                    self.setData(None)
            except RuntimeError as e:
                log.error(e, exc_info=True)
            else:
                data = pickle.loads(response.body)
                self.setData(data)

        oldFeatures = vedana.licenses_features(lastLicenses)
        self.refreshAllProperties()
        self.changed.emit(oldFeatures, self.activeFeatures())

        self._isInitializing = False

    def deinit(self):
        self._server.deinit()  # Required so latent HTTP requests don't return after Server C++ object is deleted
        self.track("session_deinit")

    # Session is a convenient place to put a lot of things

    def setQmlEngine(self, engine: QQmlEngine):
        # Hack for engine.newObject() so long as QmlUtil is a singleton
        self._qmlEngine = engine

    def qmlEngine(self) -> QQmlEngine:
        return self._qmlEngine

    def analytics(self):
        return self._analytics

    def setData(self, data):
        oldFeatures = self.activeFeatures()

        if data:

            # 1. Active Licenses
            activeLicenses = []
            if data["session"]:
                for license in data["session"]["user"]["licenses"]:
                    if license["active"]:
                        for activation in license["activations"]:
                            if (
                                not activation.get("_mock")
                                and activation["machine"]["code"] == util.HARDWARE_UUID
                            ):
                                if not license in activeLicenses:
                                    activeLicenses.append(license)
                if not activeLicenses:
                    activeLicenses = [{"policy": {"code": vedana.LICENSE_FREE}}]

            # 2. Active Features
            self._isVersionDeactivated = bool(
                version.VERSION in data["deactivated_versions"]
            )
            if self._isVersionDeactivated:
                features = []
            else:
                features = vedana.licenses_features(activeLicenses)
                if features is None:
                    features = []
            # Only allow alpha licenses on alpha builds
            if (
                version.IS_ALPHA
            ):  # Given the current feature set of one (i.e. 'professional'), alpha license is the only one honored for alpha builds
                for x in list(features):
                    if x != vedana.LICENSE_ALPHA:
                        features.remove(x)
            if not version.IS_ALPHA:
                while vedana.LICENSE_ALPHA in features:
                    features.remove(vedana.LICENSE_ALPHA)
            # Only allow beta licenses on beta|alpha builds
            if not version.IS_BETA:
                while vedana.LICENSE_BETA in features:
                    features.remove(vedana.LICENSE_BETA)
            if (
                version.IS_BETA
            ):  # Given the current feature set of one (i.e. 'professional'), beta license is the only one honored for beta builds
                for x in list(features):
                    if x != vedana.LICENSE_BETA:
                        features.remove(x)

            self.users = [
                User(
                    id=x["id"],
                    username=x["username"],
                    first_name=x["first_name"],
                    last_name=x["last_name"],
                    roles=x["roles"],
                    free_diagram_id=x["free_diagram_id"],
                    licenses=[],
                    created_at=x.get("created_at"),
                )
                for x in data["users"]
            ]
            if data["session"]:
                userData = data["session"]["user"]
                self._user = User(
                    id=userData["id"],
                    first_name=userData["first_name"],
                    last_name=userData["last_name"],
                    username=userData["username"],
                    secret=userData["secret"].encode() if userData["secret"] else b"",
                    roles=userData["roles"],
                    free_diagram_id=userData["free_diagram_id"],
                    created_at=userData["created_at"],
                    updated_at=(
                        userData["updated_at"] if userData["updated_at"] else None
                    ),
                    licenses=[
                        License(
                            created_at_readable=util.pyDateTimeString(x["created_at"]),
                            **x,
                        )
                        for x in userData["licenses"]
                    ],
                    free_diagram=(
                        Diagram(access_rights=[], **userData["free_diagram"])
                        if "free_diagram" in userData
                        else None
                    ),
                )
                self._userDict = dataclasses.asdict(self._user)
            else:
                self._user = None
                self._userDict = {}
            self._data = data
        else:
            self._data = None
            self._user = None
            self._userDict = {}
            self.users = []
            activeLicenses = []
            features = []
        self._server = Server(self, self._user)
        self._activeFeatures = features
        self._updateHash()
        if not self._isInitializing:
            self.refreshAllProperties()
            self.changed.emit(oldFeatures, features)

    # Attrs

    def get(self, attr):
        if attr == "hash":
            ret = self._hash
        elif attr == "isAdmin":
            ret = bool(self.user and vedana.ROLE_ADMIN in self.user.roles)
        else:
            ret = super().get(attr)
        return ret

    def _updateHash(self):
        self._hash = str(uuid.uuid4())
        self.refreshProperty("hash")

    @pyqtProperty(str)
    def token(self):
        if self._data and self._data["session"]:
            return self._data["session"]["token"]

    @pyqtProperty("QVariantMap", notify=changed)
    def userDict(self):
        return self._userDict
        # user = self.user
        # if user:
        #     ret = {}
        #     ret['id'] = user.id
        #     ret['username'] = user.username
        #     ret['secret'] = user.secret
        #     ret['licenses'] = []
        #     for x in ret['licenses']:
        #         ret['licenses'].append({ 'policy': x['policy'] })
        #     return ret
        # else:
        #     return {}

    @property
    def user(self):
        return self._user

    @pyqtSlot(result=QVariant)
    def data(self):
        return copy.deepcopy(self._data)

    def isInitialized(self):
        return not self._isInitializing

    def isInitializing(self):
        return self._isInitializing

    def isVersionDeactivated(self):
        return self._isVersionDeactivated

    def server(self):
        return self._server

    @pyqtSlot(result=bool)
    def isLoggedIn(self):
        ret = bool(self._user)
        return ret

    @pyqtProperty(bool, notify=changed)
    def loggedIn(self):
        return self.isLoggedIn()

    @pyqtSlot(result=list)
    def activeFeatures(self):
        return self._activeFeatures

    @staticmethod
    def hasFeatureIn(activeFeatures, *codes):
        """Return an OR match for all passed codes."""
        if isinstance(codes, str):
            codes = (codes,)
        # Handle alpha/beta
        if version.IS_ALPHA or version.IS_BETA:
            if vedana.LICENSE_FREE in codes or vedana.LICENSE_CLIENT in codes:
                return False
            if version.IS_ALPHA:
                if (
                    vedana.LICENSE_ALPHA in activeFeatures
                    and not vedana.LICENSE_FREE in codes
                ):
                    return True
                else:
                    return False
            if version.IS_BETA:
                if (
                    vedana.LICENSE_BETA in activeFeatures
                    and not vedana.LICENSE_FREE in codes
                ):
                    return True
                else:
                    return False
        # for code in codes:
        #     if code.startswith(vedana.LICENSE_ALPHA) and not version.IS_ALPHA:
        #         return False
        #     if code.startswith(vedana.LICENSE_BETA) and not version.IS_BETA:
        #         return False
        # Handle release
        for code in codes:
            for x in activeFeatures:
                if x.startswith(code):
                    return True
        return False

    @pyqtSlot(QVariant, result=bool)
    @pyqtSlot(QVariant, QVariant, result=bool)
    @pyqtSlot(QVariant, QVariant, QVariant, result=bool)
    def hasFeature(self, *codes):
        """Return an OR match for all passed codes."""
        return self.hasFeatureIn(self.activeFeatures(), *codes)

    @pyqtSlot(result=bool)
    def hasAnyPaidFeature(self):
        if self.activeFeatures() and not self.hasFeature(vedana.LICENSE_FREE):
            return True
        else:
            return False

    # Verbs

    @pyqtSlot(str, str)
    def login(self, username=None, password=None, token=None):
        if token:
            try:
                response = self.server().blockingRequest("GET", f"/sessions/{token}")
            except HTTPError as e:
                self.loginFailed.emit()
                self.setData(None)
                self.track("logged_failed", properties={"token": token})
            else:
                data = pickle.loads(response.body)
                self.setData(data)
                self.track("logged_in")
        else:
            args = {"username": username, "password": password}
            try:
                response = self.server().blockingRequest("POST", "/sessions", data=args)
            except HTTPError as e:
                self.loginFailed.emit()
                self.setData(None)
            else:
                # Defesive programming, I think this is succeeding with a 401
                # for some reason, so just add logging for now.
                try:
                    data = pickle.loads(response.body)
                except Exception as e:
                    log.error(e, exc_info=True)
                    self.loginFailed.emit()
                    self.setData(None)
                    return
                else:
                    self.setData(data)
                    self.track("logged_in")

    @pyqtSlot()
    def logout(self):
        if self._data:
            wasUser = self._user
            try:
                self.server().blockingRequest("DELETE", f"/sessions/{self.token}")
            except HTTPError as e:
                self.logoutFailed.emit()
            finally:
                self.setData(None)
                self.logoutFinished.emit()
                self.track("logged_out", properties={"user": wasUser})

    @pyqtSlot()
    def update(self):
        """Pull down the latest data from current session.
        Called from AccountDialog whenever something changes; Remote-logout, cart screen, etc.
        """
        if self._data and self._data["session"]["token"]:
            self.login(token=self._data["session"]["token"])

    def error(self, etype, value, tb):
        import traceback
        from pkdiagram.app import DatadogLog
        from pkdiagram.extensions import AccumulativeLogHandler

        log_txt = None
        for handler in logging.getLogger().handlers:
            if isinstance(handler, AccumulativeLogHandler):
                handler.flush()
                log_txt = handler.read()
                break

        self._analytics.send(
            DatadogLog(
                message="".join(traceback.format_exception(etype, value, tb)),
                time=time.time(),
                user=self._user,
                status=DatadogLogStatus.Error,
                log_txt=log_txt,
            )
        )

    def track(self, eventName: str, properties=None):
        """
        The typical entrypoint for analytics is from a session, includes the
        username and that user's session. Tracking without a session is handled
        as a manual edge case.
        """
        if not self._analytics:
            # log.warning("Analytics not initialized on Session object.")
            return

        session_id = self._data["session"]["id"] if self._data else None
        if not properties:
            properties = {}
        self._analytics.send(
            DatadogLog(
                fdtype=DatadogFDType.Action,
                message=eventName,
                user=properties.get("user", self._user),
                status=DatadogLogStatus.Info,
                session_id=session_id,
                time=time.time(),
            )
        )

    def handleLog(self, record: logging.LogRecord):
        """
        Handle logging from the main thread.
        """
        if not self._analytics:
            # log.warning("Analytics not initialized on Session object.")
            return

        session_id = self._data["session"]["id"] if self._data else None
        if record.levelno == logging.CRITICAL:
            status = DatadogLogStatus.Critical
        elif record.levelno == logging.ERROR:
            status = DatadogLogStatus.Error
        elif record.levelno == logging.WARNING:
            status = DatadogLogStatus.Warning
        elif record.levelno == logging.INFO:
            status = DatadogLogStatus.Info
        elif record.levelno == logging.DEBUG:
            status = DatadogLogStatus.Debug
        else:
            raise ValueError(f"Unknown python logging level: {record.levelno}")
        self._analytics.send(
            DatadogLog(
                fdtype=DatadogFDType.Log,
                message=record.getMessage(),
                time=time.time(),
                user=self._user,
                status=status,
                session_id=session_id,
            )
        )

    def trackApp(self, eventName):
        return self.track("Application: " + eventName)

    def trackAction(self, eventName, properties={}):
        return self.track("Action: " + eventName, properties=properties)

    @pyqtSlot(str)
    def trackView(self, eventName):
        return self.track("View: " + eventName)


from pkdiagram.pyqt import qmlRegisterType

qmlRegisterType(Session, "PK.Models", 1, 0, "Session")
