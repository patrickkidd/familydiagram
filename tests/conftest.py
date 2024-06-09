# std lib
import os, sys, time, pickle, uuid, contextlib, logging
from datetime import datetime
import tempfile, shutil
import contextlib
import PyQt5.QtCore
import PyQt5.QtGui

# third-party
import requests
import pytest, mock
import flask.testing
from flask import Flask

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
for part in ("../pkdiagram/_pkdiagram", ".."):
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), part))
from pkdiagram import (
    version,
    util,
    Scene,
    objects,
    Application,
    MainWindow,
    SceneModel,
    Session,
    HTTPResponse,
    Server,
    AppController,
    Person,
)
from pkdiagram.pyqt import *
import vedana
from fdserver import create_app, extensions
from fdserver.extensions import db
from fdserver.testclient import TestClient
from fdserver.models import User, Diagram, License, Policy, Machine, Activation, Session

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

util.init_logging()


def pytest_addoption(parser):
    parser.addoption(
        "--attach",
        action="store_true",
        help="Wait for an attached debugger before running test",
    )


def pytest_generate_tests(metafunc):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    attach = metafunc.config.getoption("attach")
    if attach and pytest_generate_tests._first_call:
        util.wait_for_attach()
        pytest_generate_tests._first_call = False


pytest_generate_tests._first_call = True


# def cleanupSessionAppDataDir():
#     global _tmpAppDataDir
#     if util._tmpAppDataDir:
#         # Debug('Deleting', _tmpAppDataDir)
#         shutil.rmtree(_tmpAppDataDir)
#         _tmpAppDataDir = None
# import atexit
# atexit.register(cleanupSessionAppDataDir)


# def resetSessionAppDataDir():
#     global _tmpAppDataDir
#     if util._tmpAppDataDir:
#         cleanupTmpAppDataDir()
#     import shutil, tempfile, atexit
#     _tmpAppDataDir = tempfile.mkdtemp()
#     # Debug('Created temp dir:', _tmpAppDataDir)


#####################################################
##
##  Server fixtures
##
#####################################################


@pytest.fixture
def flask_app(tmp_path):

    DB_PATH = tmp_path

    kwargs = {
        "ENV": "unittest",
        "CONFIG": "testing",
        "TESTING": True,
        "FD_DIR": DB_PATH,
        "DATABASE": DB_PATH,
        "MAIL_DEFAULT_SENDER": "patrickkidd@gmail.com",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SERVER_NAME": "127.0.0.1",
        "SESSION_COOKIE_DOMAIN": "turin.local",  # avoid warning
        "STRIPE_ENABLED": ENABLE_STRIPE,
        "STRIPE_KEY": os.getenv("FD_TEST_STRIPE_KEY"),
    }

    class TestApp(Flask):
        def test_client(self, **kwargs):
            return super().test_client(app=self, **kwargs)

    app = create_app(kwargs, app_class=TestApp)

    # prevent error "Instance <...> is not bound to a Session; attribute refresh operation cannot proceed"
    from sqlalchemy.orm import scoped_session

    from flask_mail import Mail

    # Apparently, required for app.config['TESTING'] == True
    extensions.mail = Mail()
    extensions.mail.init_app(app)

    # db.session = app.db.create_scoped_session()
    app.test_client_class = TestClient

    with app.app_context():
        db.create_all()
        yield app


@pytest.fixture
def test_user(flask_qnam):
    args = {
        "username": "patrickkidd+unittest@gmail.com",
        "password": "something",
        "first_name": "Unit",
        "last_name": "Tester",
    }
    user = User(
        username=args["username"],
        password=args["password"],
        first_name=args["first_name"],
        last_name=args["last_name"],
        status="confirmed",
    )
    user._plaintext_password = args["password"]
    db.session.add(user)
    db.session.merge(user)
    user.set_free_diagram(pickle.dumps({}))
    db.session.commit()
    return user


@pytest.fixture
def test_user_2(flask_qnam):
    args = {
        "username": "patrickkidd+unittest+2@gmail.com",
        "password": "something else",
        "first_name": "Unit",
        "last_name": "Tester 2",
    }
    user = User(
        username=args["username"],
        password=args["password"],
        first_name=args["first_name"],
        last_name=args["last_name"],
        status="confirmed",
    )
    user._plaintext_password = args["password"]
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_policy(flask_qnam):
    policy = Policy(
        code=vedana.LICENSE_PROFESSIONAL_MONTHLY,
        product=vedana.LICENSE_PROFESSIONAL,
        name="Unit Test Monthly",
        interval="month",
        amount=0.99,
        maxActivations=2,
        active=True,
        public=True,
    )
    db.session.add(policy)
    db.session.commit()
    return policy


@pytest.fixture
def test_license(test_user, test_policy):
    license = License(user=test_user, policy=test_policy)
    db.session.add(license)
    db.session.commit()

    return license


@pytest.fixture
def test_machine(test_user):
    machine = Machine(user=test_user, name="Some user's iMac", code=util.HARDWARE_UUID)
    db.session.add(machine)
    db.session.commit()
    return machine


@pytest.fixture
def test_activation(test_license, test_machine):
    activation = Activation(license=test_license, machine=test_machine)
    db.session.add(activation)
    db.session.commit()
    return activation


@pytest.fixture
def test_client_policy(flask_qnam):
    policy = Policy(
        code=vedana.LICENSE_CLIENT_ONCE,
        product=vedana.LICENSE_CLIENT,
        name="Automated Test Client Once",
        interval=None,
        amount=0.99,
        maxActivations=2,
        active=True,
        public=True,
    )
    db.session.add(policy)
    db.session.commit()
    return policy


@pytest.fixture
def test_client_license(test_user, test_client_policy):
    license = License(user=test_user, policy=test_client_policy)
    db.session.add(license)
    db.session.commit()
    return license


@pytest.fixture
def test_client_activation(test_client_license, test_machine):
    activation = Activation(license=test_client_license, machine=test_machine)
    db.session.add(activation)
    db.session.commit()
    return activation


@pytest.fixture
def test_session(test_user):
    session = Session(user=test_user)
    db.session.add(session)
    db.session.commit()
    return session


# # TODO: Pribably remove
# @pytest.fixture
# def client(flask_app):
#     """ An anonymous user that isn't encrypted - normal https. """
#     from flaskr import customclient
#     return flask_app.test_client(encrypted=False)


# TODO: Should go away, but used in a lot of tests.
@pytest.fixture
def test_user_client(flask_qnam, test_user):
    """A logged in client that is also encrypted."""
    from flaskr import customclient

    flask_app.test_client_class = customclient.CustomClient
    return flask_app.test_client(app=flask_app, user=test_user)


@pytest.fixture
def test_user_diagrams(test_user, test_user_2):

    NUM_DIAGRAMS = 10

    data = pickle.dumps(Scene().data())
    ids = []
    for i in range(NUM_DIAGRAMS):
        if i % 2 == 0:
            user = test_user
        else:
            user = test_user_2
        diagram = Diagram(user_id=user.id, data=data, updated_at=datetime.now())
        db.session.add(diagram)
        db.session.merge(diagram)
        ids.append(diagram.id)
    return Diagram.query.filter(Diagram.id.in_(ids)).all()


@pytest.fixture
def blockingRequest_200(monkeypatch):
    def _blockingRequest(*args, **kwargs):
        return HTTPResponse(body=b"", status_code=200, headers={})

    monkeypatch.setattr(Server, "blockingRequest", _blockingRequest)


#####################################################
##
##  Qt App fixtures
##
#####################################################


def _sendCustomRequest(request, verb, data=b"", client=None, noconnect=False):
    # Debug(f"_sendCustomRequest: request.url(): {request.url()}")
    # Qt -> Flask
    headers = []
    for name in request.rawHeaderList():
        key = bytes(name).decode("utf-8")
        value = bytes(request.rawHeader(name)).decode("utf-8")
        headers.append((key, value))
    query_string = None
    if request.url().hasQuery():
        query_string = request.url().query()
    # method = request.attribute(QNetworkRequest.CustomVerbAttribute).decode('utf-8')
    # send
    if not noconnect:
        response = flask.testing.FlaskClient.open(
            client,
            request.url().path(),
            method=verb.decode("utf-8"),
            headers=headers,
            data=data,
        )

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
            if hasattr(self, "_data"):
                return QByteArray(self._data)
            else:
                return QByteArray(b"")

    reply = NetworkReply()
    if noconnect:
        reply.setAttribute(QNetworkRequest.HttpStatusCodeAttribute, 0)
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
        # Debug(verb, request.url())
        reply.finished.emit()

    QTimer.singleShot(10, doFinished)  # after return
    return reply


@pytest.fixture(scope="session", autouse=True)
def qApp():

    qApp = Application(sys.argv)

    yield qApp

    qApp.deinit()


@pytest.fixture
def flask_qnam(flask_app, tmp_path):
    """Per-test wrapper for tmp data dir and Qt HTTP requests."""

    # Tie Qt HTTP requests to flask server
    def sendCustomRequest(request, verb, data=b""):
        with flask_app.test_client() as client:
            return _sendCustomRequest(request, verb, data=data, client=client)

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            mock.patch.object(appdirs, "user_data_dir", return_value=str(tmp_path))
        )
        stack.enter_context(
            mock.patch.object(util, "appDataDir", return_value=str(tmp_path))
        )
        stack.enter_context(
            mock.patch.object(
                util.QNAM.instance(), "sendCustomRequest", sendCustomRequest
            )
        )

        yield QApplication.instance()


@pytest.fixture
def server_down(flask_app, flask_qnam):
    """
    Can be called repeatedly to turn the server on/off.
    - Just sets up a stack for reversion.
    - Only a fixture for convenience to avoid an import.
    """

    @contextlib.contextmanager
    def _server_down(down=True):

        # No connection to server
        def sendCustomRequest(request, verb, data=b""):
            with flask_app.test_client() as client:
                return _sendCustomRequest(
                    request, verb, data=data, client=client, noconnect=down
                )

        was = util.QNAM.instance().sendCustomRequest

        util.QNAM.instance().sendCustomRequest = sendCustomRequest

        yield

        util.QNAM.instance().sendCustomRequest = was

    return _server_down


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
        return QTest.keyClicks(*args, **kwargs)

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
        if self.DEBUG:
            log.info(f"PKQtBot.mouseClick({args}, {kwargs})")
        if len(args) == 1:
            args = (args[0], Qt.LeftButton)
        return super().mouseClick(*args, **kwargs)

    def mouseDClick(self, *args, **kwargs):
        if self.DEBUG:
            log.info(f"PKQtBot.mouseDClick({args}, {kwargs})")
        return super().mouseDClick(*args, **kwargs)

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
            assert msgBoxAccepted.wait() == True, f"QMessageBox not raised in time."

    def assert_QMessageBox_hasText(self, messageBox, **kwargs):
        if messageBox.text():
            text = messageBox.text()
        elif messageBox.informativeText():
            text = messageBox.informativeText()
        else:
            text = messageBox.detailedText()

        log.info(f"QMessageBox: '{text}'")
        if "text" in kwargs and kwargs["text"] not in messageBox.text():
            messageBox.close()
            pytest.xfail(
                f"QMessageBox text: '{messageBox.text()}' expected text: '{kwargs['text']}'."
            )
        elif (
            "informativeText" in kwargs
            and kwargs["informativeText"] not in messageBox.informativeText()
        ):
            messageBox.close()
            pytest.xfail(
                f"QMessageBox informativeText: {messageBox.informativeText()} expected text: {kwargs['informativeText']}."
            )
        elif (
            "detailedText" in kwargs
            and kwargs["detailedText"] not in messageBox.detailedText()
        ):
            messageBox.close()
            pytest.xfail(
                f"QMessageBox detailedText: {messageBox.detailedText()} expected text: {kwargs['detailedText']}."
            )

    def clickButtonAfter(self, action, button: int, **hasTextArgs):
        def doClickYes():
            widget = QApplication.activeModalWidget()
            if isinstance(widget, QMessageBox):
                self.assert_QMessageBox_hasText(widget, **hasTextArgs)
                buttonWidget = widget.button(button)
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
#     util.CUtil.instance().fileOpened[util.FDDocument].connect(onFileOpened)
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
    p1 = objects.Person(name="p1")
    p2 = objects.Person(name="p2")
    m = objects.Marriage(p1, p2)
    p = objects.Person(name="p")
    p.setParents(m)
    s.addItem(p1)
    s.addItem(p2)
    s.addItem(m)
    s.addItem(p)

    def cleanup():
        s.deinit()

    request.addfinalizer(cleanup)
    return s


# TODO: DECRECATED
@pytest.fixture
def qmlScene(simpleScene):
    sceneModel = SceneModel()
    sceneModel.scene = simpleScene
    simpleScene._sceneModel = sceneModel

    yield simpleScene

    simpleScene.deinit()


@pytest.fixture
def personProps():
    return {
        "name": "Patrick",
        "middleName": "Kidd",
        "lastName": "Stinson",
        "nickName": "Patricio",
        "birthName": "Stinsonion",
        "size": util.personSizeFromName("Small"),
        "gender": util.personKindFromIndex(1),
        "adopted": Qt.Checked,
        "adoptedDateTime": QDateTime(util.Date(1982, 6, 16)),
        "primary": Qt.Checked,
        "birthDateTime": QDateTime(util.Date(1980, 5, 11)),
        "deceased": Qt.Checked,
        "deceasedDateTime": QDateTime(util.Date(2001, 1, 1)),
        "deceasedReason": "heart attack",
        "notes": "who knows anyway",
        "hideDetails": Qt.Checked,
    }


def setPersonProperties(pp, props):
    pp.setItemProp("personPage", "contentY", 0)
    pp.keyClicks("firstNameEdit", props["name"])
    pp.keyClicks("middleNameEdit", props["middleName"])
    pp.keyClicks("lastNameEdit", props["lastName"])
    pp.keyClicks("nickNameEdit", props["nickName"])
    pp.keyClicks("birthNameEdit", props["birthName"])
    pp.clickComboBoxItem("sizeBox", util.personSizeNameFromSize(props["size"]))
    pp.clickComboBoxItem("kindBox", util.personKindNameFromKind(props["gender"]))
    pp.setItemProp("personPage", "contentY", -300)
    pp.keyClick("adoptedBox", Qt.Key_Space)
    if pp.itemProp("adoptedBox", "checkState") != props["adopted"]:
        pp.mouseClick("adoptedBox")
    assert pp.itemProp("adoptedDateButtons", "enabled") == util.csToBool(
        props["adopted"]
    )
    pp.keyClicks(
        "adoptedDateButtons.dateTextInput", util.dateString(props["adoptedDateTime"])
    )
    pp.mouseClick("primaryBox")
    if pp.itemProp("primaryBox", "checkState") != props["primary"]:
        pp.mouseClick("primaryBox")
    pp.mouseClick("deceasedBox")
    if pp.itemProp("deceasedBox", "checkState") != props["deceased"]:
        pp.keyClick("deceasedBox", Qt.Key_Space)
    assert pp.itemProp("deceasedReasonEdit", "enabled") == util.csToBool(
        props["deceased"]
    )
    assert pp.itemProp("deceasedDateButtons", "enabled") == util.csToBool(
        props["deceased"]
    )
    if util.csToBool(props["deceased"]):
        pp.keyClicks("deceasedReasonEdit", props["deceasedReason"])
        pp.keyClicks(
            "deceasedDateButtons.dateTextInput",
            util.dateString(props["deceasedDateTime"]),
        )
    pp.setCurrentTab("notes")
    pp.keyClicks("notesEdit", props["notes"])


def assertPersonProperties(person, props):
    assert person.name() == props["name"]
    assert person.middleName() == props["middleName"]
    assert person.lastName() == props["lastName"]
    assert person.nickName() == props["nickName"]
    assert person.birthName() == props["birthName"]
    assert person.gender() == props["gender"]
    assert person.adopted() == util.csToBool(props["adopted"])
    assert person.adoptedDateTime() == props["adoptedDateTime"]
    assert person.deceased() == util.csToBool(props["deceased"])
    assert person.deceasedDateTime() == props["deceasedDateTime"]
    assert person.deceasedReason() == props["deceasedReason"]
    assert person.primary() == util.csToBool(props["primary"])


@pytest.fixture
def create_ac_mw(request, qtbot, tmp_path, flask_qnam):
    """
    Create an AppController and MainWindow.
    - Can be called as many times as needed to simulate starting the app again with shared prefs file.
    """

    created = []

    def _create_ac_mw(
        appConfig=None, prefs=None, savedYet=True, session=True, init=True
    ):
        if prefs is None:
            dpath = os.path.join(tmp_path, "settings.ini")
            prefs = util.Settings(dpath, "pytests")
            prefs.setValue("dontShowWelcome", True)
            prefs.setValue("acceptedEULA", True)

        ac = AppController(QApplication.instance(), prefs)
        if savedYet is not None:
            ac.appConfig.savedYet = lambda: savedYet

        mw = MainWindow(appConfig=ac.appConfig, session=ac.session, prefs=prefs)

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
        ac.deinit()


def _scene_data(*items):
    data = {}
    scene = Scene()
    scene.addItems(*items)
    scene.write(data)
    return data


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
#     'hideLayers': False,
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
