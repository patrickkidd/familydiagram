import os, os.path
import pickle
import pytest

import vedana
import pkdiagram
from pkdiagram.pyqt import QObject, QApplication
from pkdiagram import (
    util,
    Scene,
    Person,
    Event,
    QmlWidgetHelper,
    Session,
    CaseProperties,
)
from pkdiagram import (
    SearchModel,
    TimelineModel,
    SceneModel,
    PeopleModel,
    AccessRightsModel,
)

from fdserver.extensions import db
from fdserver.models import User, Diagram

pytestmark = [
    pytest.mark.component("CaseProperties"),
    pytest.mark.depends_on(
        "Scene", "Session", "SearchView", "TagsModel", "AccessRightsModel"
    ),
]


@pytest.fixture
def create_cp(request, test_session, test_user, qtbot, qmlEngine):

    created = []

    def _create_cp(session=True, loadFreeDiagram=False, editorMode=True):
        qmlEngine.sceneModel.onEditorMode(editorMode)
        if session:
            test_session = request.getfixturevalue("test_session")
            db.session.add(test_session)
            qmlEngine.session.init(sessionData=test_session.account_editor_dict())
        else:
            qmlEngine.session.init()
        scene = Scene()
        qmlEngine.setScene(scene)
        if loadFreeDiagram:
            diagram = Diagram.query.get(test_user.free_diagram_id).as_dict()
            diagram = pkdiagram.Diagram.create(diagram)
            qmlEngine.sceneModel.setServerDiagram(diagram)
            qmlEngine.accessRightsModel.setServerDiagram(diagram)

        w = CaseProperties(qmlEngine, "qml/CaseProperties.qml", parent=None)
        w.show(animate=False, tab="settings")
        w.resize(510, 600)
        w.setItemProp("settingsView", "contentY", 643)

        created.append(w)
        return w

    yield _create_cp

    for w in created:
        w.deinit()


@pytest.mark.parametrize("editorMode", [True, False])
def test_editorMode_enabled(test_session, create_cp, qmlEngine, editorMode):
    cp = create_cp(editorMode=editorMode)
    assert cp.itemProp("variablesBox", "visible") == editorMode


def test_serverBox_disabled_free(create_cp):
    cp = create_cp(loadFreeDiagram=True)
    assert cp.itemProp("accessRightsBox", "enabled") == False
    assert cp.itemProp("uploadBox", "visible") == False


def test_add_access_right_as_client(
    test_user, test_user_2, test_client_activation, create_cp, qmlEngine
):
    db.session.add(test_user.free_diagram)
    cp = create_cp(loadFreeDiagram=True)
    data = pickle.loads(test_user.free_diagram.data)
    qmlEngine.sceneModel.scene.read(data)
    cp.keyClicks("addAccessRightBox", test_user_2.username, returnToFinish=True)
    diagram = Diagram.query.get(test_user.free_diagram.id)
    assert len(diagram.access_rights) == 1
    assert diagram.access_rights[0].right == vedana.ACCESS_READ_ONLY


def test_add_only_one_access_right_as_client(
    test_user, test_user_2, test_client_activation, qtbot, create_cp, qmlEngine
):
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
    db.session.add(test_user)
    data = pickle.loads(test_user.free_diagram.data)
    qmlEngine.sceneModel.scene.read(data)

    cp.keyClicks("addAccessRightBox", test_user_2.username, returnToFinish=True)
    db.session.add(test_user)
    diagram = Diagram.query.get(test_user.free_diagram.id)
    assert len(diagram.access_rights) == 1
    assert diagram.access_rights[0].right == vedana.ACCESS_READ_ONLY

    qtbot.clickOkAfter(
        lambda: cp.keyClicks(
            "addAccessRightBox", test_user_3.username, returnToFinish=True
        ),
        contains=AccessRightsModel.S_CLIENT_ONLY_ALLOWED_ONE_RIGHT,
    )
    diagram = Diagram.query.get(test_user.free_diagram.id)
    assert (
        len(diagram.access_rights) == 1
    ), "Client should not be able to add more than one access right."


def test_add_one_access_right_for_free_as_client(
    test_user, test_user_2, test_client_activation, qtbot, create_cp, qmlEngine
):
    cp = create_cp(loadFreeDiagram=True)
    db.session.add(test_user)
    data = pickle.loads(test_user.free_diagram.data)
    qmlEngine.sceneModel.scene.read(data)
    cp.keyClicks("addAccessRightBox", test_user_2.username, returnToFinish=True)
    db.session.add(test_user)
    diagram = Diagram.query.get(test_user.free_diagram.id)
    assert len(diagram.access_rights) == 1
    assert diagram.access_rights[0].right == vedana.ACCESS_READ_ONLY

    qtbot.clickOkAfter(
        lambda: cp.keyClicks(
            "addAccessRightBox", test_user_2.username, returnToFinish=True
        ),
        text="already exists.",
    )
    assert len(diagram.access_rights) == 1


def test_edit_access_right(test_user, test_user_2, test_client_activation, create_cp):
    test_user.free_diagram.grant_access(
        test_user_2, vedana.ACCESS_READ_WRITE, _commit=True
    )

    cp = create_cp(loadFreeDiagram=True)
    accessRightItems = cp.itemProp("accessRightsBox", "accessRightItems").toVariant()
    accessRightBox = accessRightItems[0].findChild(QObject, "rightBox")
    cp.clickComboBoxItem(accessRightBox, "Read Only")
    diagram = Diagram.query.get(test_user.free_diagram_id)
    assert len(diagram.access_rights) == 1
    assert diagram.access_rights[0].right == vedana.ACCESS_READ_ONLY


def test_delete_access_right(test_user, test_user_2, test_client_activation, create_cp):
    test_user.free_diagram.grant_access(
        test_user_2, vedana.ACCESS_READ_WRITE, _commit=True
    )

    cp = create_cp(loadFreeDiagram=True)
    cp.clickListViewItem("accessRightsBox", 0)
    cp.findItem("accessRightsCrudButtons_removeButton").clicked.emit()
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
