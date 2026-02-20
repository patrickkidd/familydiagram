"""
Client-side representations of server-side scene.

Just implementation of server-side structs and protocols to CRUD them on the server.
"""

import os
import time
import pickle
import logging
import json
import enum
import base64
from datetime import datetime
import hashlib
import urllib.parse
import wsgiref.handlers
from dataclasses import dataclass, InitVar, field, fields
from typing import Union, Callable

import btcopilot
from btcopilot.schema import DiagramData, PDP, asdict, from_dict
from pkdiagram.pyqt import (
    QObject,
    QNetworkRequest,
    QNetworkReply,
    QEventLoop,
    QUrl,
    QUrlQuery,
    QApplication,
    QTimer,
    QMessageBox,
    pyqtSignal,
)
from pkdiagram import version, util
from pkdiagram.qnam import QNAM


log = logging.getLogger(__name__)

FD_NETWORK_TIMEOUT_MS = int(os.getenv("FD_NETWORK_TIMEOUT_MS", 10000))


@dataclass
class Activation:
    license_id: int
    machine_id: int


@dataclass
class Policy:
    id: int
    code: str
    product: str
    name: str
    interval: str
    maxActivations: int

    amount: float
    active: bool
    public: bool

    created_at: datetime

    description: str = None
    updated_at: datetime = None


@dataclass
class License:
    id: int
    policy: Policy
    active: bool
    canceled: bool
    user_id: int
    policy_id: int
    key: str
    stripe_id: str
    activations: list[Activation]
    activated_at: datetime
    canceled_at: datetime
    created_at: datetime
    created_at_readable: str
    updated_at: datetime = None

    def __post_init__(self):
        if isinstance(self.policy, dict):
            self.policy = Policy(**self.policy)
        if isinstance(self.activations, dict):
            self.activations = [Activation(**x) for x in self.activations]


class SpeakerType(enum.StrEnum):
    Expert = "expert"
    Subject = "subject"


@dataclass
class Speaker:
    id: int
    name: str
    person_id: int
    type: SpeakerType


@dataclass
class Statement:
    id: int
    text: str
    speaker: Speaker


@dataclass
class Discussion:
    id: int
    user_id: int
    diagram_id: int
    summary: str
    extracting: bool = False
    statements: list[Statement] = field(default_factory=list)
    speakers: list[Speaker] = field(default_factory=list)
    chat_user_speaker_id: int | None = None
    chat_ai_speaker_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class User:
    id: int
    username: str
    first_name: str
    last_name: str
    roles: list[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    secret: bytes | None = None
    licenses: list[License] | None = None
    free_diagram_id: int | None = None
    free_diagram: Union["Diagram", None] = None
    active: bool | None = None
    status: str | None = None

    def __post_init__(self):
        if self.licenses and isinstance(self.licenses[0], dict):
            self.licenses = [License(**x) for x in self.licenses]

    def hasRoles(self, *roles) -> bool:
        for role in roles:
            if role in self.roles:
                return True
        return False


@dataclass
class AccessRight:
    user_id: int
    right: str
    id: int | None = None
    diagram_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Diagram:
    id: int
    user_id: int
    access_rights: list[AccessRight]
    created_at: datetime
    updated_at: datetime | None = None
    version: int = 1
    name: str | None = None
    user: User | None = None
    use_real_names: bool | None = None
    require_password_for_real_names: bool | None = None
    data: bytes | None = None
    status: int | None = None
    alias: str | None = None
    discussions: list[Discussion] = field(default_factory=list)
    pdp: dict | None = None

    def __post_init__(self, *args, **kwargs):
        if isinstance(self.user, dict):
            self.user = User(**self.user)
        if self.access_rights and isinstance(self.access_rights[0], dict):
            self.access_rights = [AccessRight(**x) for x in self.access_rights]

    # sometimes passed in
    saved_at: InitVar[datetime] = None

    @classmethod
    def create(cls, data):
        _data = dict(**data)
        if "saved_at" in _data:
            _data.pop("saved_at")
        return Diagram(**_data)

    @classmethod
    def get(cls, diagram_id, session):
        response = session.server().blockingRequest("GET", f"/diagrams/{diagram_id}")
        data = pickle.loads(response.body)
        return cls.create(data)

    def save(
        self,
        server,
        applyChange: Callable[[DiagramData], DiagramData],
        stillValidAfterRefresh: Callable[[DiagramData], bool],
        maxRetries: int = 3,
        useJson: bool = False,
    ) -> bool:
        """Save diagram with optimistic locking (version check). Returns True on success."""

        for attempt in range(maxRetries):
            diagramData = self.getDiagramData()

            diagramData = applyChange(diagramData)

            newData = pickle.dumps(asdict(diagramData))

            if useJson:
                endpoint = f"/personal/diagrams/{self.id}"
                data = {
                    "data": base64.b64encode(newData).decode("utf-8"),
                    "expected_version": self.version,
                }
                bdata = None
                headers = {"Content-Type": "application/json"}

            else:
                endpoint = f"/v1/diagrams/{self.id}"
                bdata = pickle.dumps(
                    {
                        "data": newData,
                        "updated_at": datetime.utcnow(),
                        "expected_version": self.version,
                    }
                )
                data = None
                headers = None

            try:
                response = server.blockingRequest(
                    "PUT",
                    endpoint,
                    data=data,
                    bdata=bdata,
                    headers=headers,
                    statuses=[200, 409],
                    from_root=True,
                )
            except HTTPError as e:
                log.error(f"Error saving diagram: {e}")
                QMessageBox.critical(
                    None,
                    "Save Error",
                    f"Unexpected server error (HTTP {e.status_code}) while saving diagram.\n\n"
                    f"Please check your connection and try again.",
                )
                return False

            if useJson:
                responseData = json.loads(response.body.decode("utf-8"))
            else:
                responseData = pickle.loads(response.body)

            if response.status_code == 200:
                self.version = responseData.get("version", self.version + 1)
                self.data = newData
                return True

            if response.status_code == 409:
                log.info(
                    f"Version conflict when saving diagram {self.id}, attempt {attempt + 1} of {maxRetries}"
                )
                self.version = responseData["version"]
                conflictData = responseData["data"]

                if useJson:
                    self.data = base64.b64decode(conflictData)
                else:
                    self.data = conflictData

                refreshedData = self.getDiagramData()

                if not stillValidAfterRefresh(refreshedData):
                    return False

                continue

        return False

    def getDiagramData(self) -> DiagramData:
        data = pickle.loads(self.data) if self.data else {}
        pdp_dict = data.get("pdp", {})
        known = {f.name for f in fields(DiagramData)} - {"pdp"}
        kwargs = {k: data[k] for k in known if k in data}
        kwargs["pdp"] = from_dict(PDP, pdp_dict) if pdp_dict else PDP()
        return DiagramData(**kwargs)

    def setDiagramData(self, diagramData: DiagramData):
        data = pickle.loads(self.data) if self.data else {}

        data["pdp"] = asdict(diagramData.pdp)
        data["lastItemId"] = diagramData.lastItemId
        data["people"] = diagramData.people
        data["events"] = diagramData.events
        data["pair_bonds"] = diagramData.pair_bonds
        data["clusters"] = diagramData.clusters
        data["clusterCacheKey"] = diagramData.clusterCacheKey

        self.data = pickle.dumps(data)

    def check_access(self, user_id, right):
        if user_id == self.user_id:
            return True
        for access_right in self.access_rights:
            if access_right.user_id == user_id:
                if right == btcopilot.ACCESS_READ_ONLY and access_right.right in (
                    btcopilot.ACCESS_READ_WRITE,
                    btcopilot.ACCESS_READ_ONLY,
                ):
                    return True
                elif (
                    right == btcopilot.ACCESS_READ_WRITE
                    and access_right.right == btcopilot.ACCESS_READ_WRITE
                ):
                    return True
        return False

    def isFreeDiagram(self):
        return self.id == self.user.free_diagram_id

    def saved_at(self):
        return self.updated_at if self.updated_at else self.created_at


# class HTTPError(urllib.error.HTTPError):

#     def __str__(self):
#         reason = self.reason if self.reason else None
#         return f"{self.__class__.__qualname__}: Code: {self.code}, Reason: {reason}"


class HTTPError(Exception):
    def __init__(self, *args, status_code=None, url=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = status_code
        self.url = url


@dataclass
class HTTPResponse:
    body: bytes = None
    status_code: int = None
    headers: dict[str, str] = None
    _reply: InitVar[QNetworkReply] = None

    def __post_init__(self, _reply: QNetworkReply = None):
        if _reply:
            self.status_code = _reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            self.headers = {
                bytes(name).decode(): bytes(_reply.rawHeader(name)).decode()
                for name in _reply.rawHeaderList()
            }
        else:
            self.headers = {}


class Server(QObject):
    """
    Async requests means that &.deinit() must be called or the C++
    object may be deleted before the python object.
    """

    # Avoids underlying C++ obejct deleted error when requests complete after
    # the object has been deleted in tests.
    allRequestsFinished = pyqtSignal()

    def __init__(self, parent=None, user=None):
        super().__init__(parent)
        self._user = user
        self._repliesInFlight = []

    def deinit(self):
        pass

    def pendingUrls(self):
        return [reply.request().url().toString() for reply in self._repliesInFlight]

    def summarizePendingRequests(self):
        return "\n".join(util.summarizeReplyShort(x) for x in self._repliesInFlight)

    def _checkRequestsComplete(self, reply):
        if reply in self._repliesInFlight:
            self._repliesInFlight.remove(reply)
        if not self._repliesInFlight:
            self.allRequestsFinished.emit()

    @staticmethod
    def checkHTTPReply(reply, statuses=None, quiet=True):
        """Generic http code handling."""
        if statuses is None:
            statuses = [200, 404]
        error = reply.error()
        failMessage = None
        status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if status_code != 0 and status_code in statuses:
            pass
        if error == QNetworkReply.NoError and status_code in statuses:
            pass
        elif error == QNetworkReply.HostNotFoundError:  # no internet connection
            failMessage = "No internet connection"
        elif error == QNetworkReply.ConnectionRefusedError and not None in statuses:
            failMessage = f"Connection refused: {reply.url().toString()}"
        elif error == QNetworkReply.ContentAccessDenied:
            failMessage = f"Access Denied: {reply.url().toString()}"
        elif error == QNetworkReply.AuthenticationRequiredError:
            pass
        elif error == QNetworkReply.ContentNotFoundError:
            failMessage = f"404 Not Found: {reply.url().toString()}"
            status_code = 404
        elif error == QNetworkReply.OperationCanceledError:  # reply.abort() called
            failMessage = "QNetworkReply.OperationCanceledError"
        elif error == QNetworkReply.SslHandshakeFailedError:
            failMessage = "SSL handshake with server failed."
        elif status_code not in statuses:
            failMessage = util.qtHTTPReply2String(reply)
        # log.debug(
        #     f"Completed: {reply.request().attribute(QNetworkRequest.CustomVerbAttribute).decode()} {reply.request().url().toString()}: status_code: {status_code}"
        # )
        if failMessage:
            raise HTTPError(
                failMessage,
                status_code=status_code,
                url=reply.request().url().toString(),
            )

    def nonBlockingRequest(
        self,
        verb,
        path,
        bdata=b"",
        data=None,
        headers=None,
        anonymous=False,
        success=None,
        error=None,
        finished=None,
        from_root=False,
    ):
        _headers = {"Content-Type": "application/x-python-pickle"}
        _headers.update(headers or {})

        if _headers["Content-Type"] == "application/json":
            bdata = json.dumps(data).encode("utf-8")
        elif data and not bdata:
            bdata = pickle.dumps(data)
        full_url = util.serverUrl(path, from_root=from_root)
        ## Make a QNetworkRequest with the appropriate signature headers. """

        parts = urllib.parse.urlparse(full_url)
        if "?" in full_url:
            full_path = parts.path + "?" + parts.query
        else:
            full_path = parts.path

        if parts.query:
            url = QUrl(parts.scheme + "://" + parts.netloc + full_path)
            query = QUrlQuery()
            for param in parts.query.split("&"):
                key, value = param.split("=")
                query.addQueryItem(key, value)
            url.setQuery(query)
            resource = url.path() + "?" + url.query()
        else:
            url = QUrl(full_url)
            resource = url.path()

        # Do this like AWS
        # http://s3.amazonaws.com/doc/s3-developer-guide/RESTAuthentication.html
        content_md5 = hashlib.md5(bdata).hexdigest()
        # content_type = "text/html"
        request = QNetworkRequest(url)

        for key, value in _headers.items():
            request.setRawHeader(key.encode("utf-8"), value.encode("utf-8"))
        # This one can't be overridden
        request.setRawHeader(b"Content-MD5", content_md5.encode("utf-8"))
        date = wsgiref.handlers.format_date_time(
            time.mktime(datetime.now().timetuple())
        )
        request.setRawHeader(b"Date", date.encode("utf-8"))
        if self._user and not anonymous:
            user = self._user.username
            secret = self._user.secret
        else:
            user = btcopilot.ANON_USER
            secret = btcopilot.ANON_SECRET
        signature = btcopilot.sign(
            secret, verb, content_md5, _headers["Content-Type"], date, resource
        )
        request.setRawHeader(b"FD-Client-Version", bytes(version.VERSION, "utf-8"))
        request.setRawHeader(
            b"FD-Client-App-Type",
            bytes(QApplication.instance().appType().value, "utf-8"),
        )
        auth_header = btcopilot.httpAuthHeader(user, signature)
        request.setRawHeader(b"FD-Authentication", bytes(auth_header, "utf-8"))
        request.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
        request.setAttribute(QNetworkRequest.CustomVerbAttribute, verb.encode("utf-8"))
        # for name in request.rawHeaderList():
        #     Debug('    %s: %s' % (name.data().decode('utf-8'),
        #                                 request.rawHeader(name).data().decode('utf-8')))
        reply = QNAM.instance().sendCustomRequest(request, verb.encode(), bdata)

        def onFinished():
            reply = QApplication.instance().sender()
            success, error, finished, server = (
                reply.property("pk_success"),
                reply.property("pk_error"),
                reply.property("pk_finished"),
                reply.property("pk_server"),
            )
            # Read body first since QNetworkReply is a sequential QIODevice
            bdata = reply._pk_body = reply.readAll()
            try:
                server.checkHTTPReply(reply)
            except HTTPError:
                if error:
                    error()
            else:
                if reply.request().rawHeader(b"Content-Type") == b"application/json":
                    data = json.loads(bytes(bdata).decode("utf-8"))
                else:
                    try:
                        data = pickle.loads(bdata)
                    except pickle.UnpicklingError:
                        data = None
                if success:
                    success(data)
            finally:
                if finished:
                    finished(reply)
                self._checkRequestsComplete(reply)

        reply._pk_body = b""
        reply.setProperty("pk_success", success)
        reply.setProperty("pk_error", error)
        reply.setProperty("pk_finished", finished)
        reply.setProperty("pk_server", self)
        reply.finished.connect(onFinished)

        def onSSLErrors(errors):
            log.error("SSL Errors:")
            for e in errors:
                log.error(f"    {e.errorString()}")
            # sender().ignoreSslErrors()

        reply.sslErrors.connect(onSSLErrors)
        self._repliesInFlight.append(reply)
        return reply

    def blockingRequest(
        self,
        verb,
        path,
        bdata=b"",
        data=None,
        success=None,
        error=None,
        headers=None,
        anonymous=False,
        statuses=None,
        timeout_ms=FD_NETWORK_TIMEOUT_MS,
        from_root=False,
    ) -> HTTPResponse:
        if statuses is None:
            statuses = [200]
        loop = QEventLoop()
        reply = self.nonBlockingRequest(
            verb,
            path,
            bdata=bdata,
            data=data,
            success=success,
            error=error,
            headers=headers,
            anonymous=anonymous,
            from_root=from_root,
        )
        self._checkRequestsComplete(reply)
        reply.finished.connect(loop.quit)

        # def _timeout():
        #     nonlocal loop

        #     log.error(f"Request timeout: {reply.request().url().toString()}")
        #     reply.abort()
        #     loop.quit()

        # QTimer.singleShot(timeout_ms, _timeout)
        loop.exec_()
        self.checkHTTPReply(reply, statuses=statuses)
        # status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        # if status_code != 200:
        #     headers = [f"{x}: {reply.request().rawHeader(x)}" for x in reply.request().rawHeaderList()]
        #     self.checkHTTPReply(reply, statuses=[200])
        #     raise HTTPError(reply.url().toString(), status_code, bytes(reply.readAll()).decode(), headers, None)
        bdata = bytes(reply._pk_body)
        response = HTTPResponse(body=bdata, _reply=reply)
        return response
