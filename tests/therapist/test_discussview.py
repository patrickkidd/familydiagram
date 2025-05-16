import os.path
import json
import logging
import contextlib
from dataclasses import asdict

import pytest
from mock import patch

# from tests.models.test_copilotengine import copilot

from pkdiagram.pyqt import QTimer, QQuickWidget, QUrl, QApplication, QQmlEngine
from pkdiagram import util
from pkdiagram.therapist import TherapistAppController
from pkdiagram.therapist.therapist import Response, Therapist, ChatThread
from pkdiagram.app import Session

from tests.widgets.qmlwidgets import QmlHelper


_log = logging.getLogger(__name__)


@pytest.fixture
def controller(qmlEngine):
    controller = TherapistAppController(QApplication.instance())
    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch.object(
                controller.therapist,
                "_threads",
                [
                    ChatThread(id=1, summary="my dog flew away", user_id=123),
                    ChatThread(id=2, summary="clouds ate my cake", user_id=123),
                ],
            )
        )
        stack.enter_context(patch.object(controller.therapist, "_refreshThreads"))

        controller.init(qmlEngine)

        yield controller


@pytest.fixture
def view(qtbot, qmlEngine, controller: TherapistAppController):
    # session.init(sessionData=test_session.account_editor_dict())

    FPATH = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "pkdiagram",
        "resources",
        "qml",
        "Therapist",
        "DiscussView.qml",
    )

    # class DiscussView(QQuickWidget, QmlWidgetHelper):
    #     def __init__(self, parent=None):
    #         super().__init__(qmlEngine, parent)

    _view = QQuickWidget(qmlEngine, None)
    _view.setSource(QUrl.fromLocalFile(FPATH))
    _view.setFormat(util.SURFACE_FORMAT)

    _view.setResizeMode(QQuickWidget.SizeRootObjectToView)
    _view.resize(600, 800)
    _view.show()
    qtbot.addWidget(_view)
    qtbot.waitActive(_view)

    yield _view

    _view.hide()
    _view.setSource(QUrl(""))


def test_init_threads(server_response, view, controller: TherapistAppController):

    threadsDrawer = view.rootObject().property("threadsDrawer")
    threadList = view.rootObject().property("threadList")
    rowAdded = util.Condition(threadList.rowAdded)
    controller.therapist.threadsChanged.emit()
    view.rootObject().showThreads()
    assert util.wait(threadsDrawer.opened) == True
    # delegates = threadList.property("delegates")
    QApplication.processEvents()
    assert rowAdded.waitForCallCount(len(controller.therapist.threads)) == True
    x = 333


def test_ask(view, therapist):

    MESSAGE = "hello there"
    RESPONSE = Response(
        message="some response",
        added_data_points=[],
        removed_data_points=[],
        guidance=[],
    )

    qml = QmlHelper(view)

    textEdit = view.rootObject().property("textEdit")
    submitButton = view.rootObject().property("submitButton")
    aiBubbleAdded = util.Condition(view.rootObject().aiBubbleAdded)
    noChatLabel = view.rootObject().property("noChatLabel")

    qml.keyClicks(textEdit, MESSAGE)
    with patch("pkdiagram.therapist.Therapist._sendMessage") as _sendMessage:
        qml.mouseClick(submitButton)
    assert _sendMessage.call_count == 1
    therapist.responseReceived.emit(RESPONSE.message, [], [], [])

    assert textEdit.property("text") == ""
    assert aiBubbleAdded.wait() == True
    assert aiBubbleAdded.callArgs[0][0].property("responseText") == RESPONSE.message
    assert noChatLabel.property("visible") == False
