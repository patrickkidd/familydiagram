import pytest
from mock import patch

from pkdiagram.pyqt import QObject, pyqtSlot, QQuickWidget, QUrl, QQuickView
from pkdiagram.util import Condition
from pkdiagram.personal import PersonalAppController
from pkdiagram.personal.models import Discussion, Statement, Speaker, SpeakerType
from pkdiagram.tests.widgets.qmlwidgets import waitForListViewDelegates
from pkdiagram import util


class MockSession(QObject):
    def __init__(self, isLoggedIn=False):
        super().__init__()
        self._isLoggedIn = isLoggedIn

    @pyqtSlot(result=bool)
    def isLoggedIn(self):
        return bool(self._isLoggedIn)


class MockQmlComponent(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)


@pytest.fixture
def controller(test_user, test_session, qmlEngine):

    # from btcopilot.personal.database import Discussion, Statement, Speaker, SpeakerType
    # from pkdiagram.server_types import Diagram

    # diagram = Diagram(**test_user.free_diagram.data())
    # discussions = [
    #     Discussion(
    #         id=1,
    #         user_id=test_user.id,
    #         summary="Test Discussion",
    #         statements=[
    #             Statement(
    #                 id=1,
    #                 speaker_id=1,
    #                 speaker_type=SpeakerType.Personal,
    #                 content="Test Statement 1",
    #             ),
    #             Statement(
    #                 id=2,
    #                 speaker_id=2,
    #                 speaker_type=SpeakerType.Client,
    #                 content="Test Statement 2",
    #             ),
    #         ],
    #         speakers=[
    #             Speaker(id=1, name="Personal 1"),
    #             Speaker(id=2, name="Client 1"),
    #         ],
    #     ),
    # ]

    # diagram.database.add_discussion()

    controller = PersonalAppController()
    with patch.object(
        controller.appConfig,
        "get",
        return_value=test_session.account_editor_dict(),
    ):
        controller.init(qmlEngine)

    yield controller


@pytest.fixture
def view(qtbot, qmlEngine, controller):
    _view = QQuickView(qmlEngine, None)
    statusChanged = Condition(_view.statusChanged)
    _view.setSource(QUrl("resources:/qml/Personal/PersonalContainer.qml"))
    _view.show()
    _view.resize(600, 800)
    assert statusChanged.wait() == True
    yield _view


def __test_main_content_visible_when_logged_in(qmlEngine, controller, view):
    assert (
        view.status() == QQuickWidget.Status.Ready
    ), f"Failed to load PersonalContainer.qml: {view.status()}"

    mainContainer = view.rootObject()
    stack = mainContainer.property("stack")
    assert stack.property("visible") == True
    tabBar = mainContainer.property("tabBar")
    assert tabBar.property("visible") == True

    # Verify account dialog loader is not active
    accountDialog = mainContainer.property("accountDialog")
    assert accountDialog.property("visible") == False


def list_qrc_contents():
    # List contents of resources:/qml/
    qrc_dir = QDir("resources:/qml")
    if qrc_dir.exists():
        entries = qrc_dir.entryList(QDir.Files | QDir.Dirs | QDir.NoDotAndDotDot)
        print("Contents of resources:/qml/")
        for entry in entries:
            print(f"  {entry}")

    # List contents recursively
    def list_recursive(path, indent=0):
        dir_obj = QDir(path)
        if dir_obj.exists():
            entries = dir_obj.entryList(QDir.Files | QDir.Dirs | QDir.NoDotAndDotDot)
            for entry in entries:
                print("  " * indent + entry)
                full_path = f"{path}/{entry}"
                if QDir(full_path).exists():
                    list_recursive(full_path, indent + 1)

    print("\nRecursive listing of resources:/qml/")
    list_recursive("resources:/qml")


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


def test_select_discussion(personalApp: PersonalAppController, discussions, statements):
    with (
        patch("pkdiagram.personal.PersonalAppController._refreshDiagram"),
        patch.object(personalApp, "_discussions", discussions),
    ):
        root = personalApp._engine.rootObjects()[0]
        personalView = root.property("personalView")
        discussView = personalView.property("discussView")
        statementsList = discussView.property("statementsList")

        personalApp.discussionsChanged.emit()

        # Select the second discussion (id=2) which has statements
        personalApp.setCurrentDiscussion(2)
        util.waitALittle()

        # Verify statements are displayed
        delegates = waitForListViewDelegates(statementsList, len(statements))

    assert set(x.property("dText") for x in delegates) == set(
        x.text for x in statements
    )
