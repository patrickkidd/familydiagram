import os.path
import pickle

import pytest
import mock

import btcopilot
from _pkdiagram import CUtil
from pkdiagram.pyqt import QApplication, QUrl
from pkdiagram import util
from pkdiagram.mainwindow import FileManager

from btcopilot.extensions import db
from btcopilot.pro.models import Diagram


@pytest.fixture
def create_fm(qtbot, request, qmlEngine):

    created = []

    def _create_fm(session=True):

        if session:
            if session is True:
                test_session = request.getfixturevalue("test_session")
            else:
                test_session = session
            qmlEngine.session.init(sessionData=test_session.account_editor_dict())
        else:
            qmlEngine.session.deinit()

        fm = FileManager(qmlEngine, parent=None)
        fm.init()
        fm.resize(800, 600)
        fm.show()
        qtbot.addWidget(fm)
        qtbot.waitActive(fm)

        created.append(fm)
        return fm

    yield _create_fm

    QApplication.instance().processEvents()

    for fm in created:
        fm.hide()
        fm.deinit()


def test_local_filter(tmp_path, create_fm):

    NUM_FILES = 10

    fpaths = []
    for i in range(NUM_FILES):
        if i % 2 == 0:
            name = f"Diagram {i}-even.fd"
        else:
            name = f"Diagram {i}-odd.fd"
        fpath = os.path.join(tmp_path, name)
        util.touchFD(fpath)
        fpaths.append(fpath)

    with mock.patch.object(
        CUtil.instance(),
        "fileList",
        return_value=[QUrl.fromLocalFile(x) for x in fpaths],
    ):
        fm = create_fm()
    assert fm.rootProp("localFilesShown") == True

    localFileModel = fm.rootProp("localFileModel")
    assert localFileModel.rowCount() == NUM_FILES

    fm.keyClicks("localSearchBar.searchBox", "-odd")
    fm.itemProp("localSearchBar.searchBox", "text") == "-odd"
    assert localFileModel.searchText == "-odd"
    assert localFileModel.rowCount() == NUM_FILES / 2


def test_local_onFileStatusChanged(tmp_path, create_fm):
    name = f"Diagram-123.fd"
    fpath = os.path.join(tmp_path, name)
    util.touchFD(fpath)

    with mock.patch.object(
        CUtil.instance(),
        "fileList",
        return_value=[QUrl.fromLocalFile(fpath)],
    ):
        fm = create_fm()
    assert fm.rootProp("localFilesShown") == True

    localFileModel = fm.rootProp("localFileModel")
    with mock.patch.object(localFileModel, "updateFileEntry") as updateFileEntry:
        localFileModel.onFileStatusChanged(
            QUrl.fromLocalFile(fpath), CUtil.FileIsCurrent
        )
    assert updateFileEntry.call_args[1]["path"] == fpath
    assert updateFileEntry.call_args[1]["status"] == CUtil.FileIsCurrent
    assert updateFileEntry.call_args[1]["modified"] == os.stat(fpath).st_mtime


def test_server_filter_owner(
    test_user,
    test_user_diagrams,
    test_session,
    test_activation,
    test_user_2,
    create_fm,
    qmlEngine,
):
    for diagram in test_user_diagrams:
        if diagram.user_id == test_user_2.id:
            diagram.grant_access(test_user, btcopilot.ACCESS_READ_ONLY)
    db.session.commit()

    fm = create_fm()
    serverFileModel = fm.rootProp("serverFileModel")
    updateFinished = util.Condition(serverFileModel.updateFinished)
    qmlEngine.session.init(
        sessionData=test_session.account_editor_dict(), syncWithServer=False
    )
    assert updateFinished.wait() == True

    assert fm.itemProp("tabBar", "visible") == True
    assert fm.itemProp("tabBar.serverViewButton", "visible") == True
    fm.mouseClick("tabBar.serverViewButton")
    assert fm.rootProp("localFilesShown") == False
    assert serverFileModel.rowCount() == len(test_user_diagrams) + 1

    fm.keyClicks("serverSearchBar.searchBox", "patrickkidd+unittest+2@gmail.com")
    assert serverFileModel.rowCount() == len(test_user_diagrams) / 2


def test_diagrams_get_others_diagrams(
    flask_app, server_response, test_user, test_user_2, create_fm
):
    test_user.roles = btcopilot.ROLE_ADMIN
    diagram_1 = Diagram(
        data=pickle.dumps({}), name="first diagram", user_id=test_user_2.id
    )
    diagram_2 = Diagram(
        data=pickle.dumps({}), name="second diagram", user_id=test_user_2.id
    )
    db.session.add_all([diagram_1, diagram_2])
    db.session.commit()

    fm = create_fm()
    userIdEdit = fm.rootProp("userIdEdit")
    serverFileList = fm.rootProp("serverFileList")
    model = serverFileList.property("model")

    with server_response(
        f"/v1/diagrams?user_id={test_user_2.id}",
        method="GET",
        body=pickle.dumps(
            [
                diagram_1.as_dict(exclude="data", include="saved_at"),
                diagram_2.as_dict(exclude="data", include="saved_at"),
            ]
        ),
    ):

        fm.mouseClick("tabBar.serverViewButton")
        fm.keyClicksItem(userIdEdit, str(test_user_2.id))
    assert util.wait(model.updateFinished) == True
    assert serverFileList.property("count") == 2
    delegates = serverFileList.property("itemDelegates").toVariant()
    assert delegates[0].property("dName") == diagram_1.name
    assert delegates[1].property("dName") == diagram_2.name


def test_server_doesnt_init_in_edit_mode_admin_user(
    test_user, test_user_diagrams, create_fm, qmlEngine
):
    test_user.roles = "admin"
    db.session.commit()

    fm = create_fm()
    assert qmlEngine.session.isAdmin
    assert fm.findItem("serverFileList").property("editMode") == False


def test_free_licence_hides_server_view(test_user, create_fm):
    fm = create_fm()
    assert fm.findItem("serverViewButton").property("visible") == False


# TODO:
# - Free license hides server view
#
