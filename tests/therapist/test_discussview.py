import os.path
import logging
import contextlib
from dataclasses import asdict

import pytest
from mock import patch

# from tests.models.test_copilotengine import copilot

from fdserver.extensions import db
from fdserver.models import Diagram
from pkdiagram.pyqt import QTimer, QQuickWidget, QUrl, QApplication
from pkdiagram import util
from pkdiagram.server_types import User
from pkdiagram.therapist import TherapistAppController
from pkdiagram.therapist.therapist import (
    Response,
    Therapist,
    Discussion,
    Statement,
    Speaker,
    SpeakerType,
)

from fdserver.tests.conftest import flask_app
from fdserver.tests.therapist.conftest import chat_flow
from tests.widgets.qmlwidgets import QmlHelper, waitForListViewDelegates


_log = logging.getLogger(__name__)


@pytest.fixture
def controller(test_session, flask_app, qmlEngine):
    controller = TherapistAppController(QApplication.instance())
    controller.appConfig.set(
        "lastSessionData", test_session.account_editor_dict(), pickled=True
    )
    with (
        patch.object(controller.therapist, "init"),
        patch.object(controller.therapist, "_refreshPDP"),
        flask_app.app_context(),
    ):

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
def therapist(controller):
    return controller.therapist


def test_refresh_diagram(
    test_user, test_session, view, controller: TherapistAppController
):
    from fdserver.therapist.models import Discussion, Speaker, SpeakerType

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
            data["database"] = dict(diagram.get_database())
            kwargs["success"](data)

            return type("MockReply", (), {})()

        server.return_value.nonBlockingRequest = nonBlockingRequest
        user.free_diagram_id = 123

        controller.therapist._refreshDiagram()

        assert len(controller.therapist._discussions) == 3
        assert controller.therapist._discussions[0].id == 1
        assert controller.therapist._discussions[0].summary == "my dog flew away"
        assert controller.therapist._discussions[1].id == 2
        assert controller.therapist._discussions[1].summary == "clouds ate my cake"


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


def test_show_discussion(view, controller: TherapistAppController, discussions):

    with (
        patch("pkdiagram.therapist.Therapist._refreshDiagram"),
        patch.object(controller.therapist, "_currentDiscussion", discussions[1]),
    ):
        statementsList = view.rootObject().property("statementsList")
        controller.therapist.statementsChanged.emit()
        delegates = waitForListViewDelegates(statementsList, 4)
        assert len(delegates) == len(discussions[1].statements())


def test_select_discussion(
    view, controller: TherapistAppController, discussions, statements
):
    with (
        patch("pkdiagram.therapist.Therapist._refreshDiagram"),
        patch.object(controller.therapist, "_discussions", discussions),
    ):

        discussionList = view.rootObject().property("discussionList")
        statementsList = view.rootObject().property("statementsList")

        controller.therapist.discussionsChanged.emit()
        view.rootObject().showDiscussions()
        delegates = waitForListViewDelegates(discussionList, len(discussions))

        qml = QmlHelper(view)
        secondDelegate = discussionList.itemAtIndex(1)
        qml.mouseClick(secondDelegate)
        delegates = waitForListViewDelegates(statementsList, len(statements))

    assert set(x.property("dText") for x in delegates) == set(
        x.text for x in statements
    )


def test_ask(qtbot, view, controller, therapist, discussions):

    MESSAGE = "hello there"
    RESPONSE = Response(message="some response", pdp={})

    textEdit = view.rootObject().property("textEdit")
    submitButton = view.rootObject().property("submitButton")
    aiBubbleAdded = util.Condition(view.rootObject().aiBubbleAdded)
    noChatLabel = view.rootObject().property("noChatLabel")
    statementsList = view.rootObject().property("statementsList")

    qml = QmlHelper(view)
    with (
        patch.object(therapist, "_currentDiscussion", new=discussions[0]),
        patch.object(therapist, "_sendStatement", autospec=True) as _sendStatement,
    ):
        therapist.statementsChanged.emit()
        qml.keyClicks(textEdit, MESSAGE, returnToFinish=False)
        qml.mouseClick(submitButton)
        therapist.requestSent.emit(MESSAGE)
        delegates = waitForListViewDelegates(statementsList, 1)
        assert _sendStatement.call_count == 1
        assert _sendStatement.call_args[0][0] == MESSAGE

    therapist.responseReceived.emit(RESPONSE.message, {})
    delegates = waitForListViewDelegates(statementsList, 2)
    assert textEdit.property("text") == ""
    assert aiBubbleAdded.wait() == True
    assert aiBubbleAdded.callArgs[0][0].property("responseText") == RESPONSE.message
    assert noChatLabel.property("visible") == False
    assert delegates[0].property("dSpeakerType") == SpeakerType.Subject.value
    assert delegates[1].property("dSpeakerType") == SpeakerType.Expert.value


@pytest.mark.chat_flow
def test_ask_full_stack(test_user, view, controller, therapist, chat_flow, flask_app):

    from fdserver.therapist.models import Discussion, Speaker, Statement, SpeakerType
    from pkdiagram.therapist.therapist import (
        # Response,
        # Therapist,
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

    with (
        patch.object(
            therapist,
            "_currentDiscussion",
            new=MobileDiscussion(
                id=1,
                diagram_id=test_user.free_diagram_id,
                summary="my dog flew away",
                user_id=123,
            ),
        ),
        flask_app.app_context(),
    ):
        therapist.statementsChanged.emit()
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
