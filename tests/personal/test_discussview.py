import os.path
import logging
import json
import contextlib
from dataclasses import asdict

import pytest
from mock import patch

# from tests.models.test_copilotengine import copilot

from btcopilot.schema import asdict
from btcopilot.extensions import db
from btcopilot.pro.models import Diagram
from pkdiagram.pyqt import QTimer, QQuickWidget, QUrl, QApplication
from pkdiagram import util
from pkdiagram.server_types import User
from pkdiagram.personal import PersonalAppController
from pkdiagram.personal.personal import (
    Response,
    Personal,
    Discussion,
    Statement,
    Speaker,
    SpeakerType,
)

from btcopilot.tests.conftest import flask_app
from btcopilot.tests.personal.conftest import chat_flow
from tests.widgets.qmlwidgets import QmlHelper, waitForListViewDelegates


_log = logging.getLogger(__name__)


@pytest.fixture
def controller(test_session, flask_app, qmlEngine):
    controller = PersonalAppController(QApplication.instance())
    controller.appConfig.set(
        "lastSessionData", test_session.account_editor_dict(), pickled=True
    )
    with (
        patch.object(controller.personal, "init"),
        patch.object(controller.personal, "_refreshPDP"),
    ):

        controller.init(qmlEngine)
        yield controller


@pytest.fixture
def view(qtbot, qmlEngine, controller: PersonalAppController):
    # session.init(sessionData=test_session.account_editor_dict())

    FPATH = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "pkdiagram",
        "resources",
        "qml",
        "Personal",
        "DiscussView.qml",
    )

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


@pytest.fixture
def personal(controller):
    return controller.personal


def test_refresh_diagram(
    test_user, test_session, view, controller: PersonalAppController
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
        patch.object(controller.session, "server") as server,
        patch.object(controller.session, "_user") as user,
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
            data["diagram_data"] = asdict(diagram.get_diagram_data())
            kwargs["success"](data)

            return type("MockReply", (), {})()

        server.return_value.nonBlockingRequest = nonBlockingRequest
        user.free_diagram_id = 123

        controller.personal._refreshDiagram()

        assert len(controller.personal._discussions) == 3
        assert controller.personal._discussions[0].id == 1
        assert controller.personal._discussions[0].summary == "my dog flew away"
        assert controller.personal._discussions[1].id == 2
        assert controller.personal._discussions[1].summary == "clouds ate my cake"


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


def test_create_discussion(
    test_user, server_response, view, controller: PersonalAppController
):
    from btcopilot.personal.models import Discussion, Speaker, SpeakerType

    qml = QmlHelper(view)
    newButton = view.rootObject().property("newButton")
    discussionList = view.rootObject().property("discussionList")
    discussionsButton = view.rootObject().property("discussionsButton")
    assert discussionList.property("count") == 0

    with (
        patch.object(
            controller.personal, "_diagram", Diagram(id=123, user_id=test_user.id)
        ),
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
        qml.mouseClick(newButton)
    util.waitALittle()
    qml.mouseClick(discussionsButton)
    delegates = waitForListViewDelegates(discussionList, 1)
    assert discussionList.property("count") == 1
    assert delegates[0].property("dText") == controller.personal.discussions[0].summary


def test_show_discussion(view, controller: PersonalAppController, discussions):
    with (
        patch("pkdiagram.personal.Personal._refreshDiagram"),
        patch.object(controller.personal, "_currentDiscussion", discussions[1]),
    ):
        statementsList = view.rootObject().property("statementsList")
        controller.personal.statementsChanged.emit()
        delegates = waitForListViewDelegates(statementsList, 4)
        assert len(delegates) == len(discussions[1].statements())


def test_select_discussion(
    view, controller: PersonalAppController, discussions, statements
):
    with (
        patch("pkdiagram.personal.Personal._refreshDiagram"),
        patch.object(controller.personal, "_discussions", discussions),
    ):

        discussionList = view.rootObject().property("discussionList")
        statementsList = view.rootObject().property("statementsList")

        controller.personal.discussionsChanged.emit()
        view.rootObject().showDiscussions()
        delegates = waitForListViewDelegates(discussionList, len(discussions))

        secondDelegate = discussionList.itemAtIndex(1)
        QmlHelper(view).mouseClick(secondDelegate)
        delegates = waitForListViewDelegates(statementsList, len(statements))

    assert set(x.property("dText") for x in delegates) == set(
        x.text for x in statements
    )


def test_ask(qtbot, view, controller, personal, discussions):

    MESSAGE = "hello there"
    RESPONSE = Response(message="some response", pdp={})

    textEdit = view.rootObject().property("textEdit")
    submitButton = view.rootObject().property("submitButton")
    aiBubbleAdded = util.Condition(view.rootObject().aiBubbleAdded)
    noChatLabel = view.rootObject().property("noChatLabel")
    statementsList = view.rootObject().property("statementsList")

    qml = QmlHelper(view)
    with (
        patch.object(personal, "_currentDiscussion", new=discussions[0]),
        patch.object(personal, "_sendStatement", autospec=True) as _sendStatement,
    ):
        personal.statementsChanged.emit()
        qml.keyClicks(textEdit, MESSAGE, returnToFinish=False)
        qml.mouseClick(submitButton)
        personal.requestSent.emit(MESSAGE)
        delegates = waitForListViewDelegates(statementsList, 1)
        assert _sendStatement.call_count == 1
        assert _sendStatement.call_args[0][0] == MESSAGE

    personal.responseReceived.emit(RESPONSE.message, {})
    delegates = waitForListViewDelegates(statementsList, 2)
    assert textEdit.property("text") == ""
    assert aiBubbleAdded.wait() == True
    assert aiBubbleAdded.callArgs[0][0].property("responseText") == RESPONSE.message
    assert noChatLabel.property("visible") == False
    assert delegates[0].property("dSpeakerType") == SpeakerType.Subject.value
    assert delegates[1].property("dSpeakerType") == SpeakerType.Expert.value


@pytest.mark.chat_flow
def test_ask_full_stack(test_user, view, controller, personal, chat_flow, flask_app):

    from btcopilot.personal.models import Discussion, Speaker, Statement, SpeakerType
    from pkdiagram.personal.personal import (
        # Response,
        # Personal,
        Discussion as MobileDiscussion,
        # Statement,
        # Speaker,
        # SpeakerType,
    )

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
        personal,
        "_currentDiscussion",
        new=MobileDiscussion(
            id=1,
            diagram_id=test_user.free_diagram_id,
            summary="my dog flew away",
            user_id=123,
        ),
    ):
        personal.statementsChanged.emit()
        qml.keyClicks(textEdit, MESSAGE, returnToFinish=False)
        qml.mouseClick(submitButton)
        delegates = waitForListViewDelegates(statementsList, 2)
    assert delegates[0].property("dText") == MESSAGE
    assert delegates[0].property("dSpeakerType") == SpeakerType.Subject.value
    assert delegates[1].property("dText") == chat_flow["response"]
    assert delegates[1].property("dSpeakerType") == SpeakerType.Expert.value

    # delegates = waitForListViewDelegates(statementsList)
    # assert len(delegates) == 2
    # assert textEdit.property("text") == ""
    # assert aiBubbleAdded.wait() == True
    # assert aiBubbleAdded.callArgs[0][0].property("responseText") == RESPONSE.message
    # assert noChatLabel.property("visible") == False
