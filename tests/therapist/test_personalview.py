import pytest
from mock import patch

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QDir, QFileInfo
from PyQt5.QtQml import qmlRegisterType
from PyQt5.QtQml import QQmlEngine, qmlRegisterType
from PyQt5.QtQuick import QQuickView
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtCore import QUrl


# from tests.models.test_copilotengine import copilot

from pkdiagram.pyqt import QQuickWidget, QUrl, QApplication
from pkdiagram.condition import Condition
from pkdiagram.personal import PersonalAppController
from pkdiagram.personal.personal import Discussion


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

    # from btcopilot.schema import Discussion, Statement, Speaker, SpeakerType
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

    controller = PersonalAppController(QApplication.instance())
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
