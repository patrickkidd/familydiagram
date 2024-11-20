"""
Client-side representations of server-side objects.

Just implementation of server-side structs and protocols to CRUD them on the server.
"""

import time, pickle, logging
from datetime import datetime
from typing import List, Dict, Optional
import hashlib
import urllib.error
import wsgiref.handlers
import pydantic

import vedana
from pkdiagram.pyqt import (
    QObject,
    QNetworkRequest,
    QNetworkReply,
    QEventLoop,
    QUrl,
    QApplication,
    QTimer,
    pyqtSignal,
)
from pkdiagram import version, util


log = logging.getLogger(__name__)


class Policy(pydantic.BaseModel):
    code: str
    product: str
    name: str
    description: Optional[str]


class License(pydantic.BaseModel):
    policy: Policy
    active: bool
    canceled: bool
    created_at: datetime
    created_at_readable: str


class User(pydantic.BaseModel):
    id: int
    username: str
    secret: Optional[bytes]
    licenses: Optional[List[License]]
    first_name: str
    last_name: str
    roles: List[str]
    free_diagram_id: Optional[int]


class AccessRight(pydantic.BaseModel):
    id: int
    user_id: int
    right: str


class Diagram(pydantic.BaseModel):
    id: int
    user_id: int
    name: Optional[str]
    user: Optional[User]
    use_real_names: Optional[bool]
    require_password_for_real_names: Optional[bool]
    data: Optional[bytes]
    status: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    access_rights: List[AccessRight]

    @classmethod
    def create(cls, data):
        _data = dict(**data)
        user = _data.pop("user")
        access_rights = _data.pop("access_rights")
        return Diagram(
            access_rights=[AccessRight(**entry) for entry in access_rights],
            user=User(**user),
            **_data,
        )

    @classmethod
    def get(cls, diagram_id, session):
        from .session import Session

        response = session.server().blockingRequest("GET", f"/diagrams/{diagram_id}")
        data = pickle.loads(response.body)
        return cls.create(data)

    def check_access(self, user_id, right):
        if user_id == self.user_id:
            return True
        for access_right in self.access_rights:
            if access_right.user_id == user_id:
                if right == vedana.ACCESS_READ_ONLY and access_right.right in (
                    vedana.ACCESS_READ_WRITE,
                    vedana.ACCESS_READ_ONLY,
                ):
                    return True
                elif (
                    right == vedana.ACCESS_READ_WRITE
                    and access_right.right == vedana.ACCESS_READ_WRITE
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


class HTTPResponse(pydantic.BaseModel):
    body: bytes = None
    status_code: int = None
    headers: Optional[Dict[str, str]]

    def __init__(self, _reply=None, **kwargs):
        super().__init__(**kwargs)
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
        if error == QNetworkReply.NoError and status_code in statuses:
            pass
        elif error == QNetworkReply.HostNotFoundError:  # no internet connection
            failMessage = "No internet connection"
        elif error == QNetworkReply.ConnectionRefusedError and not None in statuses:
            failMessage = f"Connection refused: {reply.url().toString()}"
        elif error == QNetworkReply.ContentAccessDenied:
            log.info("Access Denied:", reply.url().toString())
        elif error == QNetworkReply.AuthenticationRequiredError:
            pass
        elif error == QNetworkReply.ContentNotFoundError:
            # if not IS_TEST:
            #     Debug('404 Not Found: ' + reply.url().toString())
            failMessage = f"404 Not Found: {reply.url().toString()}"
            status_code = 404
        elif error == QNetworkReply.OperationCanceledError:  # reply.abort() called
            failMessage = "QNetworkReply.OperationCanceledError"
        elif error == QNetworkReply.SslHandshakeFailedError:
            failMessage = "SSL handshake with server failed."
        elif status_code not in statuses:
            failMessage = util.qtHTTPReply2String(reply)
        # log.debug(f"{reply.request().url().toString()}: status_code: {status_code}")
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
        anonymous=False,
        success=None,
        error=None,
        finished=None,
    ):
        if data and not bdata:
            bdata = pickle.dumps(data)
        url = util.serverUrl(path)
        ## Make a QNetworkRequest with the appropriate signature headers. """

        # Do this like AWS
        # http://s3.amazonaws.com/doc/s3-developer-guide/RESTAuthentication.html
        content_md5 = hashlib.md5(bdata).hexdigest()
        content_type = "text/html"
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Content-Type", content_type.encode("utf-8"))
        request.setRawHeader(b"Content-MD5", content_md5.encode("utf-8"))
        date = wsgiref.handlers.format_date_time(
            time.mktime(datetime.now().timetuple())
        )
        request.setRawHeader(b"Date", date.encode("utf-8"))
        if self._user and not anonymous:
            user = self._user.username
            secret = self._user.secret
        else:
            user = vedana.ANON_USER
            secret = vedana.ANON_SECRET
        parts = urllib.parse.urlparse(url)
        if "?" in url:
            path = parts.path + "?" + parts.query
        else:
            path = parts.path
        signature = vedana.sign(secret, verb, content_md5, content_type, date, path)
        request.setRawHeader(b"FD-Client-Version", bytes(version.VERSION, "utf-8"))
        auth_header = vedana.httpAuthHeader(user, signature)
        request.setRawHeader(b"FD-Authentication", bytes(auth_header, "utf-8"))
        request.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
        request.setAttribute(QNetworkRequest.CustomVerbAttribute, verb.encode("utf-8"))
        # for name in request.rawHeaderList():
        #     Debug('    %s: %s' % (name.data().decode('utf-8'),
        #                                 request.rawHeader(name).data().decode('utf-8')))
        reply = (
            QApplication.instance()
            .qnam()
            .sendCustomRequest(request, verb.encode(), bdata)
        )

        def onFinished():
            reply = QApplication.instance().sender()
            success, error, finished, server = (
                reply.property("pk_success"),
                reply.property("pk_error"),
                reply.property("pk_finished"),
                reply.property("pk_server"),
            )
            try:
                server.checkHTTPReply(reply)
            except HTTPError as e:
                if error:
                    error()
            else:
                # lazy hack to only read once since QNetworkReply is a
                # sequential QIODevice
                bdata = reply._pk_body = reply.readAll()
                try:
                    data = pickle.loads(bdata)
                except pickle.UnpicklingError as e:
                    data = None
                if success:
                    success(data)
            finally:
                if finished:
                    finished(reply)
                self._checkRequestsComplete(reply)

        reply.setProperty("pk_success", success)
        reply.setProperty("pk_error", error)
        reply.setProperty("pk_finished", finished)
        reply.setProperty("pk_server", self)
        reply.finished.connect(onFinished)

        def onSSLErrors(self, errors):
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
        anonymous=False,
        statuses=None,
        timeout_ms=4000,
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
            anonymous=anonymous,
        )
        self._checkRequestsComplete(reply)
        reply.finished.connect(loop.quit)
        QTimer.singleShot(timeout_ms, loop.quit)
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
