import os.path
import logging
import json
import contextlib
import base64
import pickle
from pathlib import Path

import pytest
from mock import patch

# from pkdiagram.tests.models.test_copilotengine import copilot

from btcopilot.schema import asdict
from btcopilot.extensions import db
from btcopilot.pro.models import Diagram
from pkdiagram.pyqt import QTimer, QQuickWidget, QUrl, QApplication
from pkdiagram import util
from pkdiagram.server_types import User
from pkdiagram.personal import PersonalAppController
from pkdiagram.personal.models import (
    Discussion,
    Statement,
    Speaker,
    SpeakerType,
)

from btcopilot.tests.conftest import flask_app
from btcopilot.tests.personal.conftest import chat_flow
from pkdiagram.tests.widgets.qmlwidgets import QmlHelper, waitForListViewDelegates


_log = logging.getLogger(__name__)


@pytest.fixture
def personalApp(test_session, flask_app, qmlEngine):
    from _pkdiagram import CUtil

    personalApp = PersonalAppController()
    personalApp.appConfig.set(
        "lastSessionData", test_session.account_editor_dict(), pickled=True
    )
    # Set context properties that DiscussView.qml expects
    # Don't call personalApp.init() as it expects QQmlApplicationEngine with objectCreated signal
    qmlEngine.rootContext().setContextProperty("CUtil", CUtil.instance())
    qmlEngine.rootContext().setContextProperty("util", personalApp.util)
    qmlEngine.rootContext().setContextProperty("session", personalApp.session)
    qmlEngine.rootContext().setContextProperty("personalApp", personalApp)
    qmlEngine.rootContext().setContextProperty("sceneModel", personalApp.sceneModel)
    qmlEngine.rootContext().setContextProperty("peopleModel", personalApp.peopleModel)
    yield personalApp


@pytest.fixture
def view(qtbot, qmlEngine, personalApp: PersonalAppController):
    # session.init(sessionData=test_session.account_editor_dict())

    SOURCE_FPATH = str(
        Path(__file__).resolve().parent.parent.parent
        / "resources"
        / "qml"
        / "Personal"
        / "DiscussView.qml"
    )

    _view = QQuickWidget(qmlEngine, None)
    _view.setSource(QUrl.fromLocalFile(SOURCE_FPATH))
    _view.setFormat(util.SURFACE_FORMAT)

    _view.setResizeMode(QQuickWidget.SizeRootObjectToView)
    _view.resize(600, 800)
    _view.show()
    qtbot.addWidget(_view)
    qtbot.waitActive(_view)

    yield _view

    _view.hide()
    _view.setSource(QUrl(""))


def test_refresh_diagram(
    test_user, test_session, view, personalApp: PersonalAppController
):
    from btcopilot.personal.models import Discussion, Speaker, SpeakerType

    SPEAKERS = [
        Speaker(id=1, name="Alice", type=SpeakerType.Expert),
        Speaker(id=2, name="Bob", type=SpeakerType.Subject),
    ]

    DISCUSSIONS = [
        Discussion(
            id=1,
            diagram_id=123,
            summary="my dog flew away",
            user_id=123,
            speakers=SPEAKERS,
        ),
        Discussion(
            id=2,
            diagram_id=123,
            summary="clouds ate my cake",
            user_id=123,
            speakers=SPEAKERS,
        ),
        Discussion(
            id=3,
            diagram_id=123,
            summary="clouds ate my cake again",
            user_id=123,
            speakers=SPEAKERS,
        ),
    ]

    with (
        patch.object(personalApp.session, "server") as server,
        patch.object(personalApp.session, "_user") as user,
    ):

        def nonBlockingRequest(*args, **kwargs):
            diagram = test_user.free_diagram
            data = diagram.as_dict(
                include={
                    # "discussions": {"include": ["statements", "speakers"]},
                    "access_rights": {},
                },
                exclude="data",
            )
            data["id"] = test_user.free_diagram_id
            data["discussions"] = [
                x.as_dict(include=["statements", "speakers"]) for x in DISCUSSIONS
            ]
            data["data"] = base64.b64encode(diagram.data).decode("utf-8")
            kwargs["success"](data)

            return type("MockReply", (), {})()

        server.return_value.nonBlockingRequest = nonBlockingRequest
        user.free_diagram_id = 123

        personalApp._refreshDiagram()

        assert len(personalApp._discussions) == 3
        assert personalApp._discussions[0].id == 1
        assert personalApp._discussions[0].summary == "my dog flew away"
        assert personalApp._discussions[1].id == 2
        assert personalApp._discussions[1].summary == "clouds ate my cake"


# def test_create_discussion(view):
#     newButton = view.rootObject().property("newButton")
#     qml = QmlHelper(view)
#     qml.mouseClick(newButton)


@pytest.fixture
def statements():
    expert = Speaker(id=1, person_id=9, name="Expert", type=SpeakerType.Expert)
    subject = Speaker(id=2, person_id=8, name="Subject", type=SpeakerType.Subject)
    return [
        Statement(id=1, text="hello 1", speaker=expert),
        Statement(id=2, text="hello 2", speaker=subject),
        Statement(id=3, text="hello 3", speaker=expert),
        Statement(id=4, text="hello 4", speaker=subject),
    ]


@pytest.fixture
def discussions(statements):
    return [
        Discussion(id=1, diagram_id=123, summary="my dog flew away", user_id=123),
        Discussion(
            id=2,
            diagram_id=123,
            summary="clouds ate my cake",
            user_id=123,
            statements=statements,
        ),
        Discussion(
            id=3, diagram_id=123, summary="clouds ate my cake again", user_id=123
        ),
    ]


@pytest.mark.skip(
    reason="Flaky QML UI test - discussionList not visible after button clicks"
)
def test_create_discussion(
    test_user, server_response, view, personalApp: PersonalAppController
):
    from btcopilot.personal.models import Discussion, Speaker, SpeakerType

    qml = QmlHelper(view)
    newDiscussionButton = view.rootObject().property("newDiscussionButton")
    discussionList = view.rootObject().property("discussionList")
    discussionsButton = view.rootObject().property("discussionsButton")
    assert discussionList.property("count") == 0

    with (
        patch.object(personalApp, "_diagram", Diagram(id=123, user_id=test_user.id)),
        server_response(
            resource="/personal/discussions",
            method="POST",
            headers={b"Content-Type": b"application/json"},
            body=json.dumps(
                Discussion(
                    id=1,
                    diagram_id=123,
                    summary="my dog flew away",
                    user_id=123,
                    speakers=[
                        Speaker(
                            id=1, person_id=4, name="Alice", type=SpeakerType.Expert
                        ),
                        Speaker(
                            id=2, person_id=5, name="Bob", type=SpeakerType.Subject
                        ),
                    ],
                ).as_dict(include="speakers"),
            ),
        ),
    ):
        qml.mouseClick(newDiscussionButton)
    util.waitALittle()
    qml.mouseClick(discussionsButton)
    delegates = waitForListViewDelegates(discussionList, 1)
    assert discussionList.property("count") == 1
    assert delegates[0].property("dText") == personalApp.discussions[0].summary


def test_show_discussion(view, personalApp: PersonalAppController, discussions):
    with (
        patch("pkdiagram.personal.PersonalAppController._refreshDiagram"),
        patch.object(personalApp, "_currentDiscussion", discussions[1]),
    ):
        statementsList = view.rootObject().property("statementsList")
        personalApp.statementsChanged.emit()
        delegates = waitForListViewDelegates(statementsList, 4)
        assert len(delegates) == len(discussions[1].statements())


def test_ask(qtbot, view, personalApp, discussions):
    from btcopilot.personal.chat import Response

    MESSAGE = "hello there"
    RESPONSE = Response(statement="some response")

    textEdit = view.rootObject().property("textEdit")
    submitButton = view.rootObject().property("submitButton")
    aiBubbleAdded = util.Condition(view.rootObject().aiBubbleAdded)
    noChatLabel = view.rootObject().property("noChatLabel")
    statementsList = view.rootObject().property("statementsList")

    qml = QmlHelper(view)
    with (
        patch.object(personalApp, "_currentDiscussion", new=discussions[0]),
        patch.object(personalApp, "_sendStatement", autospec=True) as _sendStatement,
    ):
        personalApp.statementsChanged.emit()
        qml.keyClicks(textEdit, MESSAGE, returnToFinish=False)
        qml.mouseClick(submitButton)
        personalApp.requestSent.emit(MESSAGE)
        delegates = waitForListViewDelegates(statementsList, 1)
        assert _sendStatement.call_count == 1
        assert _sendStatement.call_args[0][0] == MESSAGE

    personalApp.responseReceived.emit(RESPONSE.statement)
    delegates = waitForListViewDelegates(statementsList, 2)
    assert textEdit.property("text") == ""
    assert aiBubbleAdded.wait() == True
    assert aiBubbleAdded.callArgs[0][0].property("responseText") == RESPONSE.statement
    assert noChatLabel.property("visible") == False
    assert delegates[0].property("dSpeakerType") == SpeakerType.Subject.value
    assert delegates[1].property("dSpeakerType") == SpeakerType.Expert.value


def test_paste_detection_triggers_import_dialog(
    qtbot, view, personalApp: PersonalAppController
):
    """Pasting >20 chars into empty field should trigger import dialog."""
    from pkdiagram.pyqt import QMessageBox

    textEdit = view.rootObject().property("textEdit")
    PASTED_TEXT = "A" * 30  # > 20 chars

    with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as mock_q:
        # Simulate paste by setting text directly (prevTextLength starts at 0)
        textEdit.setProperty("text", PASTED_TEXT)
        util.waitALittle()

        assert mock_q.call_count == 1
        assert "Import Journal Notes" in mock_q.call_args[0][1]


def test_paste_declined_restores_text(qtbot, view, personalApp: PersonalAppController):
    """When user declines import, pasted text should be restored to input."""
    from pkdiagram.pyqt import QMessageBox

    textEdit = view.rootObject().property("textEdit")
    PASTED_TEXT = "This is some pasted journal content that is long enough"

    with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
        textEdit.setProperty("text", PASTED_TEXT)
        util.waitALittle()

    assert textEdit.property("text") == PASTED_TEXT


def test_paste_accepted_clears_text_and_calls_import(
    qtbot, view, personalApp: PersonalAppController
):
    """When user accepts import, text field should be cleared and importJournalNotes called."""
    from pkdiagram.pyqt import QMessageBox

    textEdit = view.rootObject().property("textEdit")
    PASTED_TEXT = "Journal notes to import - must be over 20 characters"

    # importJournalNotes will emit journalImportFailed since no diagram is loaded
    # which triggers onJournalImportFailed -> criticalBox, so we must mock that too
    importFailed = util.Condition(personalApp.journalImportFailed)

    with (
        patch.object(QMessageBox, "question", return_value=QMessageBox.Yes),
        patch.object(QMessageBox, "critical"),  # Mock the error dialog
    ):
        textEdit.setProperty("text", PASTED_TEXT)
        # Wait for journalImportFailed which proves importJournalNotes was called
        assert importFailed.wait(maxMS=2000)

    # Text should be cleared when import is accepted
    assert textEdit.property("text") == ""


def test_short_paste_no_dialog(qtbot, view, personalApp: PersonalAppController):
    """Pasting <=20 chars should not trigger import dialog."""
    from pkdiagram.pyqt import QMessageBox

    textEdit = view.rootObject().property("textEdit")
    SHORT_TEXT = "A" * 20  # exactly 20 chars, should not trigger

    with patch.object(QMessageBox, "question") as mock_q:
        textEdit.setProperty("text", SHORT_TEXT)
        util.waitALittle()

        assert mock_q.call_count == 0


def test_typing_incrementally_no_dialog(
    qtbot, view, personalApp: PersonalAppController
):
    """Typing text incrementally (not pasting) should never trigger import dialog."""
    from pkdiagram.pyqt import QMessageBox

    textEdit = view.rootObject().property("textEdit")
    qml = QmlHelper(view)

    with patch.object(QMessageBox, "question") as mock_q:
        # Type characters one at a time (simulates normal typing)
        qml.keyClicks(textEdit, "A" * 30, returnToFinish=False)
        util.waitALittle()

        # Dialog should never be triggered because prevTextLength increments with each char
        assert mock_q.call_count == 0


def test_multiple_rapid_paste_events_single_dialog(
    qtbot, view, personalApp: PersonalAppController
):
    """
    iOS fires multiple onTextChanged events for a single paste.
    Guard flag should prevent multiple dialogs.
    """
    from pkdiagram.pyqt import QMessageBox

    textEdit = view.rootObject().property("textEdit")
    PASTED_TEXT = "Journal notes pasted on iOS - fires multiple events"

    with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as mock_q:
        textEdit.setProperty("text", PASTED_TEXT)
        util.waitALittle()

        # Only one dialog should appear despite potential multiple onTextChanged events
        assert mock_q.call_count == 1


@pytest.mark.chat_flow
def test_ask_full_stack(test_user, view, personalApp, chat_flow, flask_app):

    from btcopilot.personal.models import Discussion, Speaker, Statement, SpeakerType
    from pkdiagram.personal.models import Discussion as MobileDiscussion

    expert = Speaker(id=1, person_id=9, name="Expert", type=SpeakerType.Expert)
    subject = Speaker(id=2, person_id=8, name="Subject", type=SpeakerType.Subject)
    statements = [
        Statement(id=1, text="hello 1", speaker=expert),
        Statement(id=2, text="hello 2", speaker=subject),
        Statement(id=3, text="hello 3", speaker=expert),
        Statement(id=4, text="hello 4", speaker=subject),
    ]
    db.session.add_all([expert, subject] + statements)
    db.session.commit()
    discussions = [
        Discussion(
            id=1,
            diagram_id=test_user.free_diagram_id,
            summary="my dog flew away",
            user_id=123,
        ),
        Discussion(
            id=2,
            diagram_id=test_user.free_diagram_id,
            summary="clouds ate my cake",
            user_id=123,
            statements=statements,
        ),
        Discussion(
            id=3,
            diagram_id=test_user.free_diagram_id,
            summary="clouds ate my cake again",
            user_id=123,
        ),
    ]
    db.session.add_all(discussions)
    db.session.commit()

    MESSAGE = "hello there"

    qml = QmlHelper(view)
    textEdit = view.rootObject().property("textEdit")
    submitButton = view.rootObject().property("submitButton")
    statementsList = view.rootObject().property("statementsList")

    with patch.object(
        personalApp,
        "_currentDiscussion",
        new=MobileDiscussion(
            id=1,
            diagram_id=test_user.free_diagram_id,
            summary="my dog flew away",
            user_id=123,
        ),
    ):
        personalApp.statementsChanged.emit()
        qml.keyClicks(textEdit, MESSAGE, returnToFinish=False)
        qml.mouseClick(submitButton)
        delegates = waitForListViewDelegates(statementsList, 2)
    assert delegates[0].property("dText") == MESSAGE
    assert delegates[0].property("dSpeakerType") == SpeakerType.Subject.value
    assert delegates[1].property("dText") == chat_flow["response"]
    assert delegates[1].property("dSpeakerType") == SpeakerType.Expert.value
