import os.path
import json
import logging
import contextlib
from dataclasses import asdict

import pytest
from mock import patch

# from tests.models.test_copilotengine import copilot

from fdserver.models import ChatMessageOrigin
from pkdiagram.pyqt import QTimer, QQuickWidget, QUrl, QApplication
from pkdiagram import util
from pkdiagram.therapist import TherapistAppController
from pkdiagram.therapist.therapist import Response, Therapist, ChatThread, ChatMessage

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


def test_init_threads_then_select_thread(view, controller: TherapistAppController):
    """
    Threads list isn't loaded until it's init'ed so have to make this one test.
    """
    NUM_THREADS = len(controller.therapist.threads)

    with patch.object(Therapist, "_refreshMessages"):

        threadList = view.rootObject().property("threadList")
        controller.therapist.threadsChanged.emit()
        view.rootObject().showThreads()
        assert (
            util.waitForCondition(
                lambda: threadList.property("numDelegates") == NUM_THREADS
            )
            == True
        )

        NEW_MESSAGES = [
            ChatMessage(id=1, text="hello 1", origin=ChatMessageOrigin.AI.value),
            ChatMessage(id=2, text="hello 2", origin=ChatMessageOrigin.User.value),
            ChatMessage(id=3, text="hello 3", origin=ChatMessageOrigin.AI.value),
            ChatMessage(id=4, text="hello 4", origin=ChatMessageOrigin.User.value),
        ]

        NEW_THREAD = controller.therapist.threads[1]

        qml = QmlHelper(view)
        secondDelegate = threadList.property("delegates").toVariant()[1]
        orig_setCurrentThread = Therapist._setCurrentThread
        with patch.object(
            Therapist,
            "_setCurrentThread",
            side_effect=orig_setCurrentThread,
            autospec=True,
        ):
            qml.mouseClick(secondDelegate)
            with patch.object(controller.therapist, "_messages", NEW_MESSAGES):
                assert util.waitForCallCount(view.rootObject().aiBubbleAdded, 2) == True
                assert (
                    util.waitForCallCount(view.rootObject().humanBubbleAdded, 2) == True
                )
    # assert _setCurrentThread.call_count == 1
    # assert _setCurrentThread.call_args[0][1] == NEW_THREAD.id


def test_ask(view, controller):

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
    controller.therapist.responseReceived.emit(RESPONSE.message, [], [], [])

    assert textEdit.property("text") == ""
    assert aiBubbleAdded.wait() == True
    assert aiBubbleAdded.callArgs[0][0].property("responseText") == RESPONSE.message
    assert noChatLabel.property("visible") == False
