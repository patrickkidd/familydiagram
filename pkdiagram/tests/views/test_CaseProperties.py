import os, os.path
import pickle
import pytest

import btcopilot
from pkdiagram.documentview import RightDrawerView
from pkdiagram.pyqt import QObject, QApplication
from pkdiagram import util
from pkdiagram.server_types import Diagram as fe_Diagram
from pkdiagram.scene import Scene
from pkdiagram.models import AccessRightsModel
from pkdiagram.views import CaseProperties

from btcopilot.extensions import db
from btcopilot.pro.models import User, Diagram

pytestmark = [
    pytest.mark.component("CaseProperties"),
    pytest.mark.depends_on(
        "Scene", "Session", "SearchDialog", "TagsModel", "AccessRightsModel"
    ),
]


@pytest.fixture
def create_cp(request, test_session, test_user, qtbot, qmlEngine, scene):

    created = []

    def _create_cp(session=True, loadFreeDiagram=False, editorMode=True):
        qmlEngine.sceneModel.onEditorMode(editorMode)
        if session:
            test_session = request.getfixturevalue("test_session")
            db.session.add(test_session)
            qmlEngine.session.init(sessionData=test_session.account_editor_dict())
        else:
            qmlEngine.session.init()
        qmlEngine.setScene(scene)
        if loadFreeDiagram:
            diagram = Diagram.query.get(test_user.free_diagram_id).as_dict()
            diagram = fe_Diagram.create(diagram)
            qmlEngine.sceneModel.setServerDiagram(diagram)
            qmlEngine.accessRightsModel.setServerDiagram(diagram)

        w = CaseProperties(qmlEngine, "qml/CaseProperties.qml", parent=None)
        w.show(animate=False, tab="settings")
        w.resize(510, 600)
        # w.setItemProp("settingsView", "contentY", 643)
        qtbot.addWidget(w)
        qtbot.waitActive(w)

        created.append(w)
        return w

    yield _create_cp

    for w in created:
        w.deinit()


@pytest.mark.parametrize("editorMode", [True, False])
def test_editorMode_enabled(test_session, qApp, create_cp, qmlEngine, editorMode):
    cp = create_cp(editorMode=editorMode)
    assert cp.itemProp("variablesBox", "visible") == editorMode


def test_add_timeline_variable(create_cp, scene):
    VAR_NAME = "here we go"

    view = create_cp()
    variablesCrudButtons = view.rootProp("variablesCrudButtons")
    variablesList = view.rootProp("variablesList")
    itemAddDone = util.Condition(variablesList.itemAddDone)
    QApplication.processEvents()
    view.mouseClickItem(variablesCrudButtons.property("addButtonItem"))
    assert itemAddDone.wait() == True
    itemDelegate = itemAddDone.callArgs[-1][0]
    nameEdit = itemDelegate.property("nameEdit")
    view.mouseDClickItem(nameEdit)
    view.keyClicksItem(nameEdit, "\b" + VAR_NAME)
    assert scene.eventProperties()[0]["name"] == VAR_NAME


def test_serverBox_disabled_free(create_cp):
    cp = create_cp(loadFreeDiagram=True)
    assert cp.itemProp("accessRightsBox", "enabled") == False
    assert cp.itemProp("uploadBox", "visible") == False


def test_add_access_right_as_client(
    test_user, test_user_2, test_client_activation, create_cp, qmlEngine, test_session
):
    # Ensure test_user_2 is in the database
    db.session.add(test_user_2)
    db.session.commit()

    cp = create_cp(loadFreeDiagram=True)

    # Re-initialize session with fresh data that includes test_user_2
    qmlEngine.session.init(sessionData=test_session.account_editor_dict())
    db.session.add(test_user)
    data = pickle.loads(test_user.free_diagram.data)
    qmlEngine.sceneModel.scene.read(data)

    # Test the UI interaction
    cp.keyClicks("addAccessRightBox", test_user_2.username, returnToFinish=True)

    db.session.expire_all()
    diagram = Diagram.query.get(test_user.free_diagram.id)
    assert len(diagram.access_rights) == 1
    assert diagram.access_rights[0].right == btcopilot.ACCESS_READ_ONLY


def test_add_only_one_access_right_as_client(
    test_user,
    test_user_2,
    test_client_activation,
    qtbot,
    create_cp,
    qmlEngine,
    test_session,
):
    # Ensure test_user_2 and test_user_3 are in the database
    db.session.add(test_user_2)

    test_user_3 = User(
        username="patrickkidd+unittest+3@gmail.com",
        password="something else",
        first_name="Unit",
        last_name="Tester 3",
        status="confirmed",
    )
    db.session.add(test_user_3)
    db.session.commit()

    cp = create_cp(loadFreeDiagram=True)

    # Re-initialize session with fresh data that includes all users after CP is created
    qmlEngine.session.init(sessionData=test_session.account_editor_dict())
    db.session.add(test_user)
    data = pickle.loads(test_user.free_diagram.data)
    qmlEngine.sceneModel.scene.read(data)

    cp.keyClicks("addAccessRightBox", test_user_2.username, returnToFinish=True)
    db.session.expire_all()
    diagram = Diagram.query.get(test_user.free_diagram.id)
    assert len(diagram.access_rights) == 1
    assert diagram.access_rights[0].right == btcopilot.ACCESS_READ_ONLY

    qtbot.clickOkAfter(
        lambda: cp.keyClicks(
            "addAccessRightBox", test_user_3.username, returnToFinish=True
        ),
        contains=AccessRightsModel.S_CLIENT_ONLY_ALLOWED_ONE_RIGHT,
    )
    # Check that no additional access right was created
    diagram = Diagram.query.get(test_user.free_diagram.id)
    assert (
        len(diagram.access_rights) == 1
    ), "Client should not be able to add more than one access right."


def test_add_one_access_right_for_free_as_client(
    test_user,
    test_user_2,
    test_client_activation,
    qtbot,
    create_cp,
    qmlEngine,
    test_session,
):
    # Ensure test_user_2 is in the database
    db.session.add(test_user_2)
    db.session.commit()

    cp = create_cp(loadFreeDiagram=True)

    # Re-initialize session with fresh data that includes test_user_2 after CP is created
    qmlEngine.session.init(sessionData=test_session.account_editor_dict())
    db.session.add(test_user)
    data = pickle.loads(test_user.free_diagram.data)
    qmlEngine.sceneModel.scene.read(data)
    cp.keyClicks("addAccessRightBox", test_user_2.username, returnToFinish=True)
    db.session.expire_all()
    diagram = Diagram.query.get(test_user.free_diagram.id)
    assert len(diagram.access_rights) == 1
    assert diagram.access_rights[0].right == btcopilot.ACCESS_READ_ONLY

    qtbot.clickOkAfter(
        lambda: cp.keyClicks(
            "addAccessRightBox", test_user_2.username, returnToFinish=True
        ),
        text="already exists.",
    )
    # Check that no duplicate access right was created
    db.session.expire_all()
    diagram = Diagram.query.get(test_user.free_diagram.id)
    assert len(diagram.access_rights) == 1


def test_edit_access_right(test_user, test_user_2, test_client_activation, create_cp):
    test_user.free_diagram.grant_access(
        test_user_2, btcopilot.ACCESS_READ_WRITE, _commit=True
    )

    cp = create_cp(loadFreeDiagram=True)
    accessRightItems = cp.itemProp("accessRightsBox", "accessRightItems").toVariant()
    accessRightBox = accessRightItems[0].findChild(QObject, "rightBox")
    cp.clickComboBoxItem(accessRightBox, "Read Only")
    # Check that the change was persisted to the database
    db.session.expire_all()
    diagram = Diagram.query.get(test_user.free_diagram_id)
    assert len(diagram.access_rights) == 1
    assert diagram.access_rights[0].right == btcopilot.ACCESS_READ_ONLY


def test_delete_access_right(test_user, test_user_2, test_client_activation, create_cp):
    test_user.free_diagram.grant_access(
        test_user_2, btcopilot.ACCESS_READ_WRITE, _commit=True
    )

    cp = create_cp(loadFreeDiagram=True)
    cp.clickListViewItem("accessRightsBox", 0)
    cp.findItem("accessRightsCrudButtons_removeButton").clicked.emit()
    # Check that the access right was deleted from the database
    db.session.expire_all()
    diagram = Diagram.query.get(test_user.free_diagram_id)
    assert len(diagram.access_rights) == 0


@pytest.mark.parametrize("is_on_server", [True, False])
def test_serverBox_enabled_with_client_license(
    tmp_path, test_session, test_client_activation, create_cp, is_on_server, qmlEngine
):
    if is_on_server:
        cp = create_cp(loadFreeDiagram=True)
    else:
        cp = create_cp()
        tmp_fd_path = os.path.join(tmp_path, "test.fd")
        util.touchFD(os.path.join(tmp_path, "test.fd"))
        with open(os.path.join(tmp_fd_path, "diagram.pickle"), "rb") as f:
            data = pickle.loads(f.read())
            scene = Scene()
            scene.read(data)
            qmlEngine.sceneModel.scene = scene

    if is_on_server:
        assert cp.itemProp("accessRightsBox", "enabled") == True
        assert cp.itemProp("uploadBox", "visible") == False
    else:
        assert cp.itemProp("accessRightsBox", "enabled") == False
        assert cp.itemProp("uploadBox", "visible") == True


@pytest.mark.parametrize("is_on_server", [True, False])
def test_serverBox_enabled_with_pro_license(test_activation, create_cp, is_on_server):
    if is_on_server:
        cp = create_cp(loadFreeDiagram=True)
    else:
        cp = create_cp()

    if is_on_server:
        assert cp.itemProp("accessRightsBox", "enabled") == True
        assert cp.itemProp("uploadBox", "visible") == False
    else:
        assert cp.itemProp("accessRightsBox", "enabled") == False
        assert cp.itemProp("uploadBox", "visible") == True


@pytest.mark.parametrize("is_read_only", [True, False])
def test_variablesBox_enabled(test_activation, create_cp, is_read_only, qmlEngine):
    cp = create_cp(loadFreeDiagram=True)
    qmlEngine.sceneModel.scene.setReadOnly(is_read_only)
    qmlEngine.sceneModel.refreshProperty("readOnly")

    assert cp.itemProp("variablesBox", "enabled") == (not is_read_only)


def _tabLabels(cp):
    tabBar = cp.findItem("tabBar")
    tabButtons = tabBar.property("contentItem").property("contentItem").childItems()
    return [x.property("text") for x in tabButtons[: tabBar.property("count")]]


# [Oracle: R-0059]
def test_tabs(create_cp):
    """A release build does not build the Chat tab at all, so the bar carries
    one fewer button rather than a hidden one holding its place."""
    cp = create_cp()
    # Same order as the toolbar buttons and the Ctrl+2..5 shortcuts.
    assert _tabLabels(cp) == ["Timeline", "Triangles", "Settings"]

    # Each tab still shows its own page, whatever its position in the bar.
    cp.setCurrentTab(RightDrawerView.Triangles.value)
    assert cp.currentTab() == RightDrawerView.Triangles.value

    assert cp.itemProp("stack", "currentIndex") == 3

    cp.setCurrentTab(RightDrawerView.Settings.value)
    assert cp.currentTab() == RightDrawerView.Settings.value

    assert cp.itemProp("stack", "currentIndex") == 1

    # A tab this build does not offer is simply not selectable.
    cp.setCurrentTab(RightDrawerView.Chat.value)
    assert cp.currentTab() == RightDrawerView.Settings.value


# [Oracle: R-0048, R-0059]
@pytest.mark.beta
def test_tabs_include_chat_in_a_beta_build(create_cp):
    cp = create_cp()
    assert _tabLabels(cp) == ["Timeline", "Triangles", "Chat", "Settings"]

    cp.setCurrentTab(RightDrawerView.Chat.value)
    assert cp.currentTab() == RightDrawerView.Chat.value

    assert cp.itemProp("stack", "currentIndex") == 2
