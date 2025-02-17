import os.path
import logging

import pytest
import mock
from langchain.docstore.document import Document

from btcopilot import Engine, Response
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


def test_ask(llm_response, flask_app, view):

    RESPONSE_1 = "Hello back"
    PASSAGE_1 = "Some content 1"
    PASSAGE_2 = "Some content 2"
    TITLE_1 = "Book 1"
    TITLE_2 = "Book 2"
    AUTHORS_1 = "Author 1"
    AUTHORS_2 = "Author 2"

    with llm_response(
        RESPONSE_1,
        sources=[
            Document(
                page_content=PASSAGE_1,
                metadata={
                    "fd_file_name": "bleh1.pdf",
                    "fd_title": TITLE_1,
                    "fd_authors": AUTHORS_1,
                },
            ),
            Document(
                page_content=PASSAGE_2,
                metadata={
                    "fd_file_name": "bleh2.pdf",
                    "fd_title": TITLE_2,
                    "fd_authors": AUTHORS_2,
                },
            ),
        ],
    ):
        view.inputMessage("Here we going?")
    assert view.aiBubbleAdded.wait() == True
    assert view.aiBubbleAdded.callArgs[0][0].property(
        "text"
    ) == util.formatChatResponse(
        {
            "response": RESPONSE_1,
            "sources": [
                {"passage": PASSAGE_1, "fd_title": TITLE_1, "fd_authors": AUTHORS_1},
                {"passage": PASSAGE_2, "fd_title": TITLE_2, "fd_authors": AUTHORS_2},
            ],
        }
    )

    RESPONSE_2 = "I'm here"

    view.aiBubbleAdded.reset()
    with llm_response(RESPONSE_2):
        view.inputMessage("Say somethign else")
    assert view.aiBubbleAdded.wait() == True
    assert view.aiBubbleAdded.callArgs[0][0].property(
        "text"
    ) == util.formatChatResponse({"response": RESPONSE_2, "sources": []})


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


TIMEOUT_MS = 30000


@pytest.mark.vector_db(
    path=os.path.realpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "fdserver",
            "instance",
            "vector_db",
        )
    )
)
@pytest.mark.integration
def test_full_stack(view, flask_app):
    last_response = None

    def _on_response(self, response: Response):
        nonlocal last_response
        last_response = response

    with mock.patch.object(Engine, "_on_response", _on_response):
        view.inputMessage("What year was the NIMH study conducted?")
        assert view.aiBubbleAdded.wait(maxMS=TIMEOUT_MS) == True
        assert (
            view.aiBubbleAdded.callArgs[0][0].property("text") == last_response.answer
        )
        _log.info(last_response.answer)
