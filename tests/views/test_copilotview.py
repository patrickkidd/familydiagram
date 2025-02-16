import os.path
import logging
import contextlib

import pytest
import mock

from btcopilot import Engine
from pkdiagram.pyqt import QWidget, QUrl, QHBoxLayout
from pkdiagram import util
from pkdiagram.views.qml import CopilotView
from pkdiagram.widgets import QmlWidgetHelper

from btcopilot.tests.conftest import llm_response

_log = logging.getLogger(__name__)


@pytest.fixture
def view(tmp_path, test_session, qtbot, scene, qmlEngine):
    qmlEngine.setScene(scene)

    class TestCopilotView(QWidget, QmlWidgetHelper):
        pass

    FPATH = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "pkdiagram",
        "resources",
        "qml",
        "CopilotView.qml",
    )
    qmlEngine.session.init(sessionData=test_session.account_editor_dict())
    _view = TestCopilotView()
    _view.initQmlWidgetHelper(qmlEngine, QUrl.fromLocalFile(FPATH))
    _view.checkInitQml()
    _view.resize(600, 800)
    _view.show()
    Layout = QHBoxLayout(_view)
    Layout.addWidget(_view.qml)
    qtbot.addWidget(_view)
    qtbot.waitActive(_view)

    yield CopilotView(_view, _view.qml.rootObject())

    _view.hide()
    _view.deinit()


def test_ask(flask_app, llm_response, view):
    RESPONSE_1 = "Hello back"
    RESPONSE_2 = "I'm here"

    with llm_response(RESPONSE_1):
        view.inputMessage("Here we going?")
    assert view.aiBubbleAdded.wait() == True
    assert view.aiBubbleAdded.callArgs[0][0].property("text") == RESPONSE_1

    view.aiBubbleAdded.reset()
    with llm_response(RESPONSE_2):
        view.inputMessage("Say somethign else")
    assert view.aiBubbleAdded.wait() == True
    assert view.aiBubbleAdded.callArgs[0][0].property("text") == RESPONSE_2


def test_server_down(view, server_down):
    with server_down():
        view.inputMessage("Here we going?")
    assert view.aiBubbleAdded.wait() == True
    assert view.aiBubbleAdded.callArgs[0][0].property("text") == util.S_SERVER_IS_DOWN


def test_server_error(view):
    with mock.patch.object(Engine, "ask", side_effect=ValueError("Some exception")):
        view.inputMessage("Here we going?")
    assert view.aiBubbleAdded.wait() == True
    assert view.aiBubbleAdded.callArgs[0][0].property("text") == util.S_SERVER_ERROR
