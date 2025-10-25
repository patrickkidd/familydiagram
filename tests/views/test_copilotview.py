import os.path
import logging
import contextlib

import pytest
import mock
from langchain_core.documents import Document

# from tests.models.test_copilotengine import copilot

from btcopilot.pro.copilot import Engine, Response
from pkdiagram.pyqt import QWidget, QUrl, QHBoxLayout, QTimer
from pkdiagram import util
from pkdiagram.views.qml import CopilotView
from pkdiagram.widgets import QmlWidgetHelper
from pkdiagram.models.copilotengine import CopilotEngine, formatSources

_log = logging.getLogger(__name__)


@pytest.fixture
def view(test_session, qtbot, scene, qmlEngine):
    qmlEngine.setScene(scene)
    qmlEngine.session.init(sessionData=test_session.account_editor_dict())

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


# LOREM = "Lorem ipsum odor amet, consectetuer adipiscing elit. Nunc metus at platea inceptos eros urna curabitur. Id primis maximus tortor egestas nostra suspendisse cubilia nibh."


def test_init(view):
    assert view.item.property("noChatLabel").property("visible") == True


@pytest.fixture
def llm_response(qmlEngine):

    @contextlib.contextmanager
    def _llm_response(responseText: str, sourcesText: str, numSources: int):

        def _ask(self, question, includeTags):

            def _send():
                qmlEngine.copilot.responseReceived.emit(
                    responseText, sourcesText, numSources
                )

            QTimer.singleShot(1, _send)
            qmlEngine.copilot.requestSent.emit(question)

        with mock.patch.object(CopilotEngine, "_ask", _ask):
            yield

    return _llm_response


def test_ask(view, llm_response):

    RESPONSE_1 = "Hello back"
    SOURCES_1 = "some sources"

    with llm_response(RESPONSE_1, SOURCES_1, 2):
        view.inputMessage("Hello there")
    assert view.textInput.property("text") == ""
    assert view.aiBubbleAdded.wait() == True
    assert view.aiBubbleAdded.callArgs[0][0].property("responseText") == RESPONSE_1
    assert view.aiBubbleAdded.callArgs[0][0].property("sourcesText") == SOURCES_1
    assert view.item.property("noChatLabel").property("visible") == False

    RESPONSE_2 = "I'm here"

    view.aiBubbleAdded.reset()
    with llm_response(RESPONSE_2, "", 0):
        view.inputMessage("Say somethign else")
    assert view.textInput.property("text") == ""
    assert view.aiBubbleAdded.wait() == True
    assert view.aiBubbleAdded.callArgs[0][0].property("responseText") == RESPONSE_2
    assert view.aiBubbleAdded.callArgs[0][0].property("sourcesText") == formatSources(
        []
    )
    assert view.item.property("noChatLabel").property("visible") == False


def test_server_down(view, server_down):
    with server_down():
        view.inputMessage("Here we going?")
    assert view.aiBubbleAdded.wait() == True
    assert (
        view.aiBubbleAdded.callArgs[0][0].property("responseText")
        == util.S_SERVER_IS_DOWN
    )


def test_server_error(qmlEngine, view, server_error):
    with server_error(status_code=500):
        view.inputMessage("Here we going?")
    assert view.aiBubbleAdded.wait() == True
    assert (
        view.aiBubbleAdded.callArgs[0][0].property("responseText")
        == util.S_SERVER_ERROR
    )


TIMEOUT_MS = 30000


@pytest.mark.vector_db(
    path=os.path.realpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "btcopilot",
            "instance",
            "vector_db",
        )
    )
)
@pytest.mark.real_server
@pytest.mark.integration
def test_full_stack(view):
    last_response = None

    def _on_response(self, response: Response):
        nonlocal last_response
        last_response = response

    with mock.patch.object(Engine, "_on_response", _on_response):
        view.inputMessage("What year was the NIMH study conducted?")
        assert view.aiBubbleAdded.wait(maxMS=TIMEOUT_MS) == True
        assert (
            view.aiBubbleAdded.callArgs[0][0].property("responseText")
            == last_response.answer
        )
        _log.info(last_response.answer)
