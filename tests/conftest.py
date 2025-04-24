import os, sys
import time
import contextlib
import logging
import tempfile
import uuid
from typing import Optional

import pytest, mock
import flask.testing

# Load python init by path since it doesn't exist in a package.
import importlib

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
spec = importlib.util.spec_from_file_location(
    "python_init", os.path.join(ROOT, "python_init.py")
)
python_init = importlib.util.module_from_spec(spec)
spec.loader.exec_module(python_init)
python_init.init_dev()

# pkdiagram
for part in ("../_pkdiagram", ".."):
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), part))

from _pkdiagram import CUtil
from pkdiagram.pyqt import (
    Qt,
    QNetworkReply,
    QByteArray,
    QNetworkRequest,
    QNetworkAccessManager,
    QTimer,
    QApplication,
    QIODevice,
    QQmlError,
    QTest,
    QPlainTextEdit,
    QWindow,
    QWidget,
    QMouseEvent,
    QEvent,
    QVariant,
    QMessageBox,
    QEventLoop,
    QSettings,
    QGraphicsView,
    QVBoxLayout,
    QUrl,
)
from pkdiagram import version, util
from pkdiagram.qnam import QNAM
from pkdiagram.server_types import HTTPResponse, Server
from pkdiagram.scene import Scene, Person, Marriage
from pkdiagram.models import ServerFileManagerModel
from pkdiagram.widgets import QmlWidgetHelper
from pkdiagram.mainwindow import MainWindow
from pkdiagram.documentview import QmlEngine
from pkdiagram.app import Application, AppController, Session as fe_Session, QmlUtil

from fdserver.tests.conftest import *
from fdserver.models import User
import flask_bcrypt

import appdirs


version.IS_ALPHA = False
version.IS_BETA = False
version.IS_ALPHA_BETA = False
util.IS_TEST = True
util.ENABLE_OPENGL = False
util.ANIM_DURATION_MS = 0
util.LAYER_ANIM_DURATION_MS = 0
util.QML_LAZY_DELAY_INTERVAL_MS = 0  # total lazy loading
DATA_ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
ENABLE_STRIPE = False

log = logging.getLogger(__name__)


_componentStatus = {}
_currentTestItem = None


def pytest_addoption(parser):
    parser.addoption(
        "--disable-watchdog",
        action="store_true",
        default=False,
        help="Disable Qt watchdog for kill hung tests.",
    )
    parser.addoption(
        "--disable-dependencies",
        action="store_true",
        default=False,
        help="Disable skipping tests when a component test fails.",
    )
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Tun integration tests",
    )


def pytest_configure(config):
    config.watchdog_disabled = config.getoption("--disable-watchdog")
    config.dependency_disabled = config.getoption("--disable-dependencies")
    config.addinivalue_line("markers", "integration: mark test as integration test.")


def pytest_collection_modifyitems(session, config, items):

    # Skip mark "integration" by default, run only "integration" marks when "--integration" is passed
    if not util.IS_DEBUGGER:
        if not config.getoption("--integration"):
            skip_mark = pytest.mark.skip(reason="Requires passing --integration to run")
            for item in items:
                if "integration" in [x.name for x in item.own_markers]:
                    item.add_marker(skip_mark)
        else:
            skip_mark = pytest.mark.skip(
                reason="Skipped because --integration was passed"
            )
            for item in items:
                if "integration" not in [x.name for x in item.own_markers]:
                    item.add_marker(skip_mark)

    # Reorder test items based on component dependencies.
    if config.dependency_disabled:
        return

    component_tests = {}
    ordered_items = []
    non_component_items = []

    # Sort items into their respective component lists
    for item in items:
        component_marker = item.get_closest_marker("component")
        if component_marker:
            component = component_marker.args[0]
            component_tests.setdefault(component, []).append(item)
        else:
            non_component_items.append(item)

    visited = set()

    def add_with_dependencies(component):
        if component in visited:
            return
        visited.add(component)
        for item in component_tests.get(component, []):
            dependency_marker = item.get_closest_marker("depends_on")
            if dependency_marker:
                for dependency in dependency_marker.args:
                    add_with_dependencies(dependency)
            ordered_items.append(item)

    for component in component_tests.keys():
        add_with_dependencies(component)

    items[:] = ordered_items + non_component_items


_test_case_name = None


def pytest_runtest_setup(item):
    """Skip tests based on component dependency rules if dependencies failed."""
    global _currentTestItem, _test_case_name

    _test_case_name = f"{item.fspath}::{item.name}"

    if item.config.dependency_disabled:
        return

    _currentTestItem = item

    dependency_marker = item.get_closest_marker("depends_on")
    if dependency_marker:
        for dependency in dependency_marker.args:
            if _componentStatus.get(dependency) == "failed":
                pytest.fail(
                    f"Skipping {item.name} tests because {dependency} tests failed"
                )


def pytest_report_teststatus(report, config):
    """Track failures for components so dependent tests case be skipped."""
    global _currentTestItem, _componentStatus

    if config.dependency_disabled:
        return

    if _currentTestItem and report.failed:  # during call
        component_marker = _currentTestItem.get_closest_marker("component")
        if component_marker:
            component = component_marker.args[0]
            _componentStatus[component] = "failed"


@pytest.fixture
def blockingRequest_200(monkeypatch):
    def _blockingRequest(*args, **kwargs):
        return HTTPResponse(body=b"", status_code=200, headers={})

    monkeypatch.setattr(Server, "blockingRequest", _blockingRequest)


# Flask -> Qt
class NetworkReply(QNetworkReply):
    def abort(self):
        pass

    def writeData(self, data):
        if not hasattr(self, "_data"):
            self._data = b""
        self._data = self._data + data
        return len(data)

    # def readData(self, maxSize):
    #     return self._data
    def readAll(self):
        if getattr(self, "_hasReadAll", False):
            return QByteArray(b"")
        self._hasReadAll = True
        if hasattr(self, "_data"):
            return QByteArray(self._data)
        else:
            return QByteArray(b"")


from typing import Union
from dataclasses import dataclass

from werkzeug.wrappers import Response


@dataclass
class MockedResponse:
    resource: str
    response: Response
    method: str = "GET"


_mockedFlaskResponsesStack: list[list[MockedResponse]] = []


@pytest.fixture
def server_response():

    @contextlib.contextmanager
    def _server_response(
        resource, method: str = None, status_code: int = 200, body: bytes = b""
    ):
        _mockedFlaskResponsesStack.append(
            MockedResponse(
                resource=resource, method=method, response=Response(body, status_code)
            )
        )
        yield
        _mockedFlaskResponsesStack.pop()

    return _server_response


def _sendCustomRequest(
    request, verb, data=b"", client=None, noconnect=False, status_code=None
):
    # Debug(f"_sendCustomRequest: request.url(): {request.url()}")
    # Qt -> Flask
    headers = []
    for name in request.rawHeaderList():
        key = bytes(name).decode("utf-8")
        value = bytes(request.rawHeader(name)).decode("utf-8")
        headers.append((key, value))
    # method = request.attribute(QNetworkRequest.CustomVerbAttribute).decode('utf-8')
    # send
    if not noconnect and status_code is None:
        if request.url().query():
            resource = request.url().path() + "?" + request.url().query()
        else:
            resource = request.url().path()

        response = None
        for mapping in _mockedFlaskResponsesStack:
            if mapping.resource == resource:
                response = mapping.response
                break
        if not response:
            response = flask.testing.FlaskClient.open(
                client,
                resource,
                method=verb.decode("utf-8"),
                headers=headers,
                data=data,
            )

    reply = NetworkReply()
    reply.setAttribute(QNetworkRequest.CustomVerbAttribute, verb)
    if noconnect:
        status_code = 0
    if status_code is not None:
        reply.setAttribute(QNetworkRequest.HttpStatusCodeAttribute, status_code)
    else:
        reply.setAttribute(
            QNetworkRequest.HttpStatusCodeAttribute, response.status_code
        )
        for key, value in response.headers:
            reply.setRawHeader(key.encode("utf-8"), value.encode("utf-8"))
        reply.open(QIODevice.ReadWrite)
        reply.write(response.data)
    reply.setRequest(request)
    reply.setOperation(
        (
            {
                "HEAD": QNetworkAccessManager.HeadOperation,
                "GET": QNetworkAccessManager.GetOperation,
                "PUT": QNetworkAccessManager.PutOperation,
                "POST": QNetworkAccessManager.PostOperation,
                "DELETE": QNetworkAccessManager.DeleteOperation,
            }
        ).get(verb.decode(), QNetworkAccessManager.CustomOperation)
    )

    def doFinished():
        # log.info(
        #     f"<<<<<<<<<<<<<<<<<<<< doFinished: {verb} {reply.request().url().toString()} _test_case_name: {reply._test_case_name}"
        # )
        if reply._test_case_name == _test_case_name:
            reply.finished.emit()
        else:
            log.warning(
                f"Skipping reply.finished.emit() Test case name mismatch: {reply._test_case_name} != {_test_case_name}"
            )

    QTimer.singleShot(1, doFinished)  # after return
    reply._test_case_name = _test_case_name
    return reply


@pytest.fixture(scope="session", autouse=True)
def qApp():
    log.debug(f"Create qApp for familydiagram/tests")

    # from PyQt5.QtCore import QLoggingCategory
    # QLoggingCategory.setFilterRules("qt.quick.mouse.debug=true")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    # Just a placeholder to avoid overwriting the user app folder one; each test
    # will be mocked
    prefs = QSettings(os.path.join(tempfile.mkdtemp(), "settings.ini"), "vedanamedia")

    def _prefs(self):
        return prefs

    with mock.patch.object(Application, "prefs", _prefs):
        app = Application(sys.argv)
        CUtil.instance().forceDocsPath(
            os.path.join(tempfile.mkdtemp(), "documents")
        )  # to kill the file list query

    _orig_Server_deinit = Server.deinit

    def _Server_deinit(self):
        _orig_Server_deinit(self)
        if self._repliesInFlight:
            assert (
                util.wait(self.allRequestsFinished, maxMS=2000) == True
            ), f"Did not complete Server requests: {self.summarizePendingRequests()}"

    _orig_ServerFileManagerModel_deinit = ServerFileManagerModel.deinit

    def _ServerFileManagerModel_deinit(self):
        _orig_ServerFileManagerModel_deinit(self)
        if self._indexReplies:
            assert (
                util.wait(self.updateFinished, maxMS=2000) == True
            ), f"Did not complete ServerFileManager requests: {self.summarizePendingRequests()}"

    _orig_QmlUtil_deinit = QmlUtil.deinit

    def _QmlUtil_deinit(self):
        _orig_QmlUtil_deinit(self)
        if self._httpRequests:

            def _summarize(requests):
                return ", ".join(x.reply.request().url() for x in requests)

            assert (
                util.Condition(condition=lambda: self._httpRequests == []).wait()
                == True
            ), f"Did not complete QmlUtil requests: {_summarize(self._httpRequests)}"

    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(Server, "deinit", _Server_deinit))
        stack.enter_context(
            mock.patch.object(
                ServerFileManagerModel, "deinit", _ServerFileManagerModel_deinit
            )
        )
        stack.enter_context(mock.patch.object(QmlUtil, "deinit", _QmlUtil_deinit))
        stack.enter_context(
            mock.patch("pkdiagram.app.Analytics.startTimer", return_value=123)
        )
        stack.enter_context(mock.patch("pkdiagram.app.Analytics.killTimer"))
        # stack.enter_context(mock.patch("fdserver.extensions.init_excepthook"))
        yield app

    app.deinit()


@pytest.fixture(autouse=True)
def prefs(request, tmp_path):
    """
    More than just "prefs" now
    """

    dont_mock_bcrypt = request.node.get_closest_marker("dont_mock_bcrypt")

    prefs = QSettings(os.path.join(tempfile.mkdtemp(), "settings.ini"), "vedanamedia")
    with contextlib.ExitStack() as stack:
        stack.enter_context(
            mock.patch("pkdiagram.app.Application.prefs", return_value=prefs)
        )
        # bcrypt was using 45s
        stack.enter_context(
            mock.patch.object(
                CUtil, "documentsFolderPath", return_value=str(tmp_path / "documents")
            )
        )
        use_bcrypt = request.node.get_closest_marker("use_bcrypt")
        if use_bcrypt is None:
            stack.enter_context(
                mock.patch.object(
                    flask_bcrypt, "generate_password_hash", return_value=b"1234"
                )
            )
            stack.enter_context(
                mock.patch.object(
                    flask_bcrypt, "check_password_hash", return_value=True
                )
            )
        yield prefs


@pytest.fixture(autouse=True)
def watchdog(request, qApp):

    integration = "integration" in [m.name for m in request.node.iter_markers()]

    start_time = time.time()
    watchog_mark = request.node.get_closest_marker("watchdog")
    if watchog_mark:
        timeout_ms = watchog_mark.kwargs["timeout_ms"]
    else:
        timeout_ms = 10000

    if not __debug__ and not request.config.watchdog_disabled and not integration:

        class Watchdog:

            def __init__(self, timeout_ms):
                self._killed = False
                self._canceled = False
                self._timeout_ms = timeout_ms

            def cancel(self):
                """
                Really just for test_hangWatchdog()
                """
                self._canceled = True

            def kill(self):
                log.info(f"Watchdog timer reached after {timeout_ms}ms, closing window")
                w = QApplication.activeWindow()
                if w:
                    w.close()
                self._killed = True

            def killed(self):
                return self._killed

            def cancelled(self):
                return self._canceled

        watchdog = Watchdog(timeout_ms)
        watchdogTimer = QTimer(qApp)
        watchdogTimer.setInterval(timeout_ms)
        watchdogTimer.timeout.connect(watchdog.kill)
        watchdogTimer.start()
        log.debug(f"Starting watchdog timer for {timeout_ms}ms")

    else:
        # log.warning("Qt hung test watchdog disabled.")
        watchdog = None

    yield watchdog

    if watchdog:
        watchdogTimer.stop()
        if watchdog.killed() and not watchdog.cancelled():
            pytest.fail(f"Watchdog triggered after {timeout_ms}ms.")
    else:
        elapsed = time.time() - start_time
        if elapsed > timeout_ms:
            log.warning(
                f"Watchdog would have been triggered after {timeout_ms}ms; test took {elapsed}ms."
            )


@pytest.fixture
def qmlEngine(qApp):

    qmlErrors = []
    _qmlEngine = QmlEngine(fe_Session(), qApp)

    def _onWarnings(errors: list[QQmlError]):
        qmlErrors.extend(errors)

    _qmlEngine.warnings.connect(_onWarnings)

    yield _qmlEngine

    _qmlEngine.deinit()

    # Ignore errors after teardown and before the next test case, they don't
    # effect the logic under test.
    if qmlErrors:
        msgs = "\n".join(x.toString() for x in qmlErrors)
        pytest.fail(f"QmlEngine warnings/errors: {msgs}")


@pytest.fixture(autouse=True)
def flask_qnam(tmp_path, request):
    """Per-test wrapper for tmp data dir and Qt HTTP requests."""

    if request.node.get_closest_marker("real_server"):
        with mock.patch.object(util, "SERVER_URL_ROOT", "http://127.0.0.1:8888"):
            yield
        return

    # Tie Qt HTTP requests to flask server
    def sendCustomRequest(qt_request, verb, data=b""):

        # on demand, not every test
        flask_app = request.getfixturevalue("flask_app")

        with flask_app.test_client() as client:
            ret = _sendCustomRequest(qt_request, verb, data=data, client=client)
            return ret

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            mock.patch.object(appdirs, "user_data_dir", return_value=str(tmp_path))
        )
        stack.enter_context(
            mock.patch.object(util, "appDataDir", return_value=str(tmp_path))
        )
        stack.enter_context(
            mock.patch.object(QNAM.instance(), "sendCustomRequest", sendCustomRequest)
        )

        yield QApplication.instance()


@pytest.fixture
def server_down(flask_app):
    """
    Can be called repeatedly to turn the server on/off.
    - Just sets up a stack for reversion.
    - Only a fixture for convenience to avoid an import.
    """

    @contextlib.contextmanager
    def _server_down(down=True):

        def sendCustomRequest(request, verb, data=b""):
            with flask_app.test_client() as client:
                return _sendCustomRequest(
                    request, verb, data=data, client=client, noconnect=down
                )

        with mock.patch.object(QNAM.instance(), "sendCustomRequest", sendCustomRequest):
            yield

    return _server_down


@pytest.fixture
def server_error(flask_app):
    """
    Can be called repeatedly to return a error status code from Server.nonBlockingRequest().
    """

    @contextlib.contextmanager
    def _server_error(status_code=500):

        def sendCustomRequest(request, verb, data=b""):
            with flask_app.test_client() as client:
                return _sendCustomRequest(
                    request, verb, data=data, client=client, status_code=status_code
                )

        with mock.patch.object(QNAM.instance(), "sendCustomRequest", sendCustomRequest):
            yield

    return _server_error


@pytest.fixture
def data_root():
    return DATA_ROOT


from pytestqt.qtbot import QtBot


class PKQtBot(QtBot):

    DEBUG = False

    def waitActive(self, w, timeout=1000):
        w.activateWindow()
        QApplication.instance().processEvents()  # ugh....
        super().waitActive(w, timeout=timeout)

    def keyClick(self, *args, **kwargs):
        if self.DEBUG:
            log.info(f"PKQtBot.keyClick({args}, {kwargs})")
        return super().keyClick(*args, **kwargs)

    def keyClicks(self, *args, **kwargs):
        if self.DEBUG:
            log.info(f"PKQtBot.keyClicks({args}, {kwargs})")

        # Qt does the same iteration, just need to avoid sending \n
        sequence = args[1]
        for x in sequence:
            if x == "\n":
                x = Qt.Key_Return
            QTest.keyClick(args[0], x, **kwargs)

    def __keyClicks(self, *args, **kwargs):
        w = args[0]
        QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier)  # focus in
        QTest.keyClicks(*args, **kwargs)
        if not isinstance(args[0], QPlainTextEdit):
            QTest.keyClick(w, Qt.Key_Tab)  # focus out
            self.waitUntil(lambda: not w.hasFocus())
            # self.qWait(100)
        else:
            w.clearFocus()
            # # just try to focus out
            # aw = QApplication.activeWindow()
            # if aw is None:
            #     w.activateWindow()
            #     QApplication.setActiveWindow(w.window())
            # QApplication.activeWindow().setFocus()

    def keyClicksClear(self, w, unfocus=True):
        """Clear text in widget."""
        self.mouseClick(w, Qt.LeftButton)
        w.selectAll()
        self.keyClick(w, Qt.Key_Backspace)
        w.editingFinished.emit()  # punt
        # if isinstance(w, QLineEdit) and unfocus:
        #     self.keyClick(w, Qt.Key_Tab)
        # else:
        #     w.clearFocus()

    def keyClicksDateEdit(self, dateEdit, s, inTable=False):
        le = dateEdit.lineEdit()
        self.mouseClick(le, Qt.LeftButton)
        self.keyClick(le, Qt.Key_A, Qt.ControlModifier)
        self.keyClick(le, Qt.Key_Backspace)
        super().keyClicks(le, s)
        if inTable:
            self.keyClick(le, Qt.Key_Enter)
        else:
            le.clearFocus()
        if inTable:
            self.wait(10)  # processEvents()

    def mouseClick(self, *args, **kwargs):
        if len(args) == 1:
            args = (args[0], Qt.LeftButton)
        if args[0] is None:
            raise ValueError(
                "Cannot click on None, will cause assertion in QtTest.framework/Headers/qtestmouse.h, line 185"
            )
        assert (
            args[0] is not None
        ), f"qtbot.mouseClick will crash if passing `None` as the widget."
        return super().mouseClick(*args, **kwargs)

    def mouseDClick(self, *args, **kwargs):
        if self.DEBUG:
            log.info(f"PKQtBot.mouseDClick({args}, {kwargs})")
        return super().mouseDClick(*args, **kwargs)

    def mouseClickGraphicsItem(self, view: QGraphicsView, item):
        rect = view.mapFromScene(item.mapToScene(item.boundingRect())).boundingRect()
        self.mouseClick(
            view.viewport(),
            Qt.LeftButton,
            modifier=Qt.KeyboardModifier.NoModifier,
            pos=rect.center(),
        )

    def mouseDClickGraphicsItem(self, view: QGraphicsView, item):
        rect = view.mapFromScene(item.mapToScene(item.boundingRect())).boundingRect()
        self.mouseDClick(
            view.viewport(),
            Qt.LeftButton,
            modifier=Qt.KeyboardModifier.NoModifier,
            pos=rect.center(),
        )

    @staticmethod
    def mouseMove(
        windowOrWidget: Optional[QWindow | QWidget], pos=None, modifiers=None, delay=-1
    ):
        pos = windowOrWidget.rect().center() if pos is None else pos
        modifiers = Qt.NoModifier if modifiers is None else modifiers
        event = QMouseEvent(
            QEvent.Type.MouseMove,
            pos,
            Qt.NoButton,
            Qt.NoButton,
            modifiers,
        )
        QApplication.instance().sendEvent(windowOrWidget, event)
        # QtBot.mouseMove(windowOrWidget, pos, delay)

    def qWait(self, ms):
        QTest.qWait(ms)

    def printTable(self, view, selectedCol=0):
        import sys

        fmt = "{:<20s}"
        print()
        model = view.model()
        selectedRows = set([i.row() for i in view.selectionModel().selectedIndexes()])
        nCols = model.columnCount()
        for col in range(nCols):
            label = model.headerData(col, Qt.Horizontal)
            s = fmt.format(label)
            if col < nCols - 1:
                s = s + "| "
            if col == 0:
                iS = "".ljust(4)
            else:
                iS = ""
            sys.stdout.write("%s %s" % (iS, s))
        sys.stdout.write("\n")
        nCols = model.columnCount()
        for row in range(model.rowCount()):
            if view.isRowHidden(row):
                continue
            for col in range(nCols):
                index = model.index(row, col)
                s = model.data(index, Qt.DisplayRole)
                if isinstance(s, QVariant) and s.isNull():
                    s = ""
                else:
                    s = str(s)
                if view.selectionModel().isSelected(index):
                    x = "[%s]" % s
                else:
                    x = s
                z = fmt.format(x)
                if col < nCols - 1:
                    z = z + "| "
                if col == 0:
                    iS = ("%i:" % row).ljust(4)
                else:
                    iS = ""
                sys.stdout.write("%s %s" % (iS, z))
            sys.stdout.write("\n")
        sys.stdout.flush()

    def selectTableViewItem(self, tv, s, column=0, modifiers=Qt.NoModifier):
        foundItems = {}
        for row in range(tv.model().rowCount()):
            index = tv.model().index(row, column)
            tv.scrollTo(index)
            itemP = tv.visualRect(index).center()
            itemS = tv.model().index(row, column).data(Qt.DisplayRole)
            foundItems[row] = itemS
            if not itemP.isNull() and itemS == s:
                self.mouseClick(tv.viewport(), Qt.LeftButton, modifiers, itemP)
        if not s in foundItems.values():
            self.printTable(tv, column)
        assert s in foundItems.values()

    def clickTabWidgetPage(self, tabWidget, iPage):
        self.mouseClick(
            tabWidget.tabBar(),
            Qt.LeftButton,
            Qt.NoModifier,
            tabWidget.tabBar().tabRect(iPage).center(),
        )

    def assertNoTableViewItem(self, tv, text, column):
        count = 0
        for row in range(tv.model().rowCount()):
            index = tv.model().index(row, column)
            itemS = tv.model().index(row, column).data(Qt.DisplayRole)
            if itemS == text:
                count += 1
        assert count == 0

    def qWaitForMessageBox(self, action, contains=None, handleClick=None):
        from PyQt5.QtWidgets import QAbstractButton

        msgBoxAccepted = util.Condition()

        def acceptMessageBox():
            # def isWindowUp():
            #     return bool(QApplication.activeModalWidget())
            # self.waitUntil(isWindowUp, 2000)
            widget = QApplication.activeModalWidget()
            if widget:
                if contains:
                    assert contains in widget.text()
                if handleClick:
                    try:
                        ok = handleClick()
                    except Exception as _e:
                        ok = False
                        e = _e
                    msgBoxAccepted()
                    msgBoxAccepted.timer.stop()
                    if not ok:
                        raise e
                elif isinstance(widget, QMessageBox):
                    okButton = widget.button(QMessageBox.Ok)
                    widget.buttonClicked[QAbstractButton].connect(msgBoxAccepted)
                    msgBoxAccepted()
                    self.mouseClick(okButton, Qt.LeftButton)
                    msgBoxAccepted.timer.stop()

        msgBoxAccepted.timer = QTimer(QApplication.instance())
        msgBoxAccepted.timer.timeout.connect(acceptMessageBox)
        msgBoxAccepted.timer.start(100)
        action()
        if contains:
            assert (
                msgBoxAccepted.wait() == True
            ), f'QMessageBox not raised in time containing: "{contains}"'
        else:
            assert (
                msgBoxAccepted.wait() == True
            ), f"QMessageBox not raised in time. {QApplication.activeWindow()}"

    def assert_QMessageBox_hasText(self, messageBox, **kwargs):
        if messageBox.text():
            text = messageBox.text()
        elif messageBox.informativeText():
            text = messageBox.informativeText()
        else:
            text = messageBox.detailedText()

        log.debug(f"QMessageBox: '{text}'")
        if "text" in kwargs and kwargs["text"] not in messageBox.text():
            messageBox.close()
            pytest.fail(
                f"expected text: '{kwargs['text']}', found text: '{messageBox.text()}'."
            )
        elif (
            "informativeText" in kwargs
            and kwargs["informativeText"] not in messageBox.informativeText()
        ):
            messageBox.close()
            pytest.fail(
                f"expected text: {kwargs['informativeText']}, QMessageBox::informativeText: {messageBox.informativeText()}."
            )
        elif (
            "detailedText" in kwargs
            and kwargs["detailedText"] not in messageBox.detailedText()
        ):
            messageBox.close()
            pytest.fail(
                f"expected text: {kwargs['detailedText']}, QMessageBox::detailedText: {messageBox.detailedText()}."
            )

    def clickButtonAfter(self, action, button: int, **hasTextArgs):
        def doClickYes():
            widget = QApplication.activeModalWidget()
            if isinstance(widget, QMessageBox):
                self.assert_QMessageBox_hasText(widget, **hasTextArgs)
                buttonWidget = widget.button(button)
                if not buttonWidget:
                    raise ValueError(
                        f"Button {button} not found in {widget} with text '{widget.text()}'"
                    )
                self.mouseClick(buttonWidget, Qt.LeftButton)
                return True
            else:
                widget.hide()
                pytest.fail(f"Expected QMessageBox, got {widget}")

        self.qWaitForMessageBox(action, handleClick=doClickYes)

    def clickYesAfter(self, action, **hasTextArgs):
        self.clickButtonAfter(action, QMessageBox.Yes, **hasTextArgs)

    def clickNoAfter(self, action, **hasTextArgs):
        self.clickButtonAfter(action, QMessageBox.No, **hasTextArgs)

    def clickOkAfter(self, action, **hasTextArgs):
        self.clickButtonAfter(action, QMessageBox.Ok, **hasTextArgs)

    def clickCancelAfter(self, action, **hasTextArgs):
        self.clickButtonAfter(action, QMessageBox.Cancel, **hasTextArgs)

    def hitEscapeAfter(self, action, **hasTextArgs):
        def doHitEscape():
            widget = QApplication.activeModalWidget()
            if isinstance(widget, QMessageBox):
                self.assert_QMessageBox_hasText(widget, **hasTextArgs)
                self.keyClicks(QApplication.activeModalWidget(), Qt.Key_Escape)
                return True
            else:
                pytest.fail(f"Expected QMessageBox, got {widget}")

        self.qWaitForMessageBox(action, handleClick=doHitEscape)

    def callAfter(self, action: callable, after: callable):
        QTimer.singleShot(100, after)
        action()

    def clickAndProcessEvents(self, button):
        self.mouseClick(button, Qt.LeftButton)
        # For some reason a QEventLoop is needed to finish laying out the Qml component
        # instead of QApplication.processEvents()
        loop = QEventLoop()
        QTimer.singleShot(10, loop.quit)  # may need to be longer?
        loop.exec()


@pytest.fixture
def qtbot(request):
    """Overridden to use our qApp, because the old one was calling abort()."""
    result = PKQtBot(request)
    util.qtbot = result

    yield result


def dataFile(fpath):
    return os.path.join(DATA_ROOT, fpath)


# TIMELINE_TEST_FD = dataFile('TIMELINE_TEST.fd')

# def openSceneFile(filePath):
#     onFileOpened = util.Condition()
#     util.CUtil.instance().fileOpened[FDDocument].connect(onFileOpened)
#     util.CUtil.instance().openExistingFile(QUrl.fromLocalFile(filePath))
#     onFileOpened.wait()
#     assert onFileOpened.callCount == 1
#     doc = onFileOpened.callArgs[0][0]
#     s = Scene(document=doc)
#     bdata = doc.diagramData()
#     data = pickle.loads(bdata)
#     s.read(data)
#     return s


@pytest.fixture
def simpleScene(request):
    s = Scene()
    p1 = Person(name="p1")
    p2 = Person(name="p2")
    m = Marriage(p1, p2)
    p = Person(name="p")
    p.setParents(m)
    s.addItem(p1)
    s.addItem(p2)
    s.addItem(m)
    s.addItem(p)

    def cleanup():
        s.deinit()

    request.addfinalizer(cleanup)
    return s


@pytest.fixture
def scene(qApp):
    _scene = Scene()
    yield _scene
    _scene.deinit()


@pytest.fixture
def create_ac_mw(request, qtbot, tmp_path):
    """
    Create an AppController and MainWindow.
    - Can be called as many times as needed to simulate starting the app again with shared prefs file.
    """

    created = []

    def _create_ac_mw(
        appConfig=None,
        prefs=None,
        savedYet=True,
        session=True,
        editorMode=True,
        prefsName=None,
        init=True,
    ):
        if prefs is None:
            dpath = os.path.join(tmp_path, "settings.ini")
            prefs = Application.instance().prefs()
            prefs.setValue("dontShowWelcome", True)
            prefs.setValue("acceptedEULA", True)
            prefs.setValue("enableAppUsageAnalytics", False)

        if editorMode is not None:
            prefs.setValue("editorMode", editorMode)

        ac = AppController(QApplication.instance(), prefsName=prefsName)
        if savedYet is not None:
            ac.appConfig.savedYet = lambda: savedYet

        mw = MainWindow(appConfig=ac.appConfig, session=ac.session)

        if not appConfig:
            appConfig = {}
        if session:
            if session is True:
                test_session = request.getfixturevalue("test_session")
            else:
                test_session = session
            ac.appConfig.set(
                "lastSessionData", test_session.account_editor_dict(), pickled=True
            )
        if appConfig:
            for k, v in appConfig.items():
                if k == "lastSessionData":
                    pickled = True
                else:
                    pickled = False
                ac.appConfig.set(k, v, pickled=pickled)

        ac.init()
        mw.init()
        mw.show()
        qtbot.addWidget(mw)
        qtbot.waitActive(mw)

        if init:
            ac._pre_event_loop(mw)

        created.append((ac, mw))
        return ac, mw

    yield _create_ac_mw

    for ac, mw in created:
        mw.deinit()
        util.Condition(
            condition=lambda: mw.fileManager.serverFileModel._indexReplies == []
        ).wait()
        assert mw.fileManager.serverFileModel._indexReplies == []
        ac.deinit()


@pytest.fixture
def create_qml(qtbot, scene, qmlEngine):

    class QmlHelper(QWidget, QmlWidgetHelper):
        pass

    helpers = []

    def _qmlParent(fpath: str) -> QmlWidgetHelper:

        qmlEngine.setScene(scene)
        helper = QmlHelper()
        helper.initQmlWidgetHelper(qmlEngine, QUrl.fromLocalFile(fpath))
        helper.checkInitQml()
        Layout = QVBoxLayout(helper)
        Layout.addWidget(helper.qml)

        helper.resize(600, 800)
        helper.show()
        qtbot.addWidget(helper)
        qtbot.waitActive(helper)
        helpers.append(helper)

        assert helper.isVisible()

        return helper

    yield _qmlParent

    for helper in helpers:
        helper.hide()
        helper.deinit()


# SIMPLE_SCENE_DATA = {
#     'id': None,
#     'tags': [],
#     'loggedDateTime': PyQt5.QtCore.QDateTime(
#         2022,
#         10,
#         5,
#         23,
#         27,
#         16,
#         266),
#     'uuid': None,
#     'masterKey': None,
#     'alias': None,
#     'readOnly': None,
#     'lastItemId': 0,
#     'contributeToResearch': False,
#     'useRealNames': False,
#     'password': '_(bidacd#d&cedjv',
#     'requirePasswordForRealNames': False,
#     'showAliases': False,
#     'hideNames': False,
#     'hideToolBars': False,
#     'hideEmotionalProcess': False,
#     'hideEmotionColors': False,
#     'hideDateSlider': False,
#     'hideVariablesOnDiagram': False,
#     'hideVariableSteadyStates': False,
#     'exclusiveLayerSelection': True,
#     'storePositionsInLayers': False,
#     'currentDateTime': PyQt5.QtCore.QDateTime(
#         2022,
#         10,
#         5,
#         23,
#         27,
#         16,
#         338),
#     'scaleFactor': 0.33,
#     'pencilColor': PyQt5.QtGui.QColor(
#         100,
#         100,
#         100),
#     'eventProperties': [],
#     'legendData': {
#         'shown': False,
#         'size': PyQt5.QtCore.QSize(
#             309,
#             175),
#         'anchor': 'south-east'},
#     'version': '1.5.0',
#     'versionCompat': '1.3.0',
#     'items': [],
#     'name': ''}
