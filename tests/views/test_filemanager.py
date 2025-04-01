import os.path

import pytest
import mock

import vedana
from _pkdiagram import CUtil
from pkdiagram.pyqt import QApplication, QUrl
from pkdiagram import util
from pkdiagram.mainwindow import FileManager

from fdserver.extensions import db


pytestmark = pytest.mark.init_filemanager


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
        fm.checkInitQml()
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


def test_local_filter(tmp_path, qmlEngine, create_fm):

    NUM_FILES = 10

    for i in range(NUM_FILES):
        if i % 2 == 0:
            name = f"Diagram {i}-even.fd"
        else:
            name = f"Diagram {i}-odd.fd"
        fpath = os.path.join(tmp_path, name)
        util.touchFD(fpath)
        qmlEngine.localFileModel.onFileAdded(
            QUrl.fromLocalFile(fpath), CUtil.FileIsCurrent
        )

    fm = create_fm()
    assert fm.rootProp("localFilesShown") == True

    assert qmlEngine.localFileModel.rowCount() == NUM_FILES

    fm.keyClicks("localSearchBar.searchBox", "-odd")
    fm.itemProp("localSearchBar.searchBox", "text") == "-odd"
    assert qmlEngine.localFileModel.searchText == "-odd"
    assert qmlEngine.localFileModel.rowCount() == NUM_FILES / 2


def test_local_onFileStatusChanged(tmp_path, qmlEngine, create_fm):
    name = f"Diagram-123.fd"
    fpath = os.path.join(tmp_path, name)
    util.touchFD(fpath)
    qmlEngine.localFileModel.onFileAdded(QUrl.fromLocalFile(fpath), CUtil.FileIsCurrent)

    fm = create_fm()
    assert fm.rootProp("localFilesShown") == True

    with mock.patch.object(
        qmlEngine.localFileModel, "updateFileEntry"
    ) as updateFileEntry:
        qmlEngine.localFileModel.onFileStatusChanged(
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
            diagram.grant_access(test_user, vedana.ACCESS_READ_ONLY)
    db.session.commit()

    fm = create_fm()
    qmlEngine.serverFileModel.update()
    qmlEngine.session.init(
        sessionData=test_session.account_editor_dict(), syncWithServer=False
    )
    assert util.wait(qmlEngine.serverFileModel.updateFinished) == True

    assert fm.itemProp("tabBar", "visible") == True
    assert fm.itemProp("tabBar.serverViewButton", "visible") == True
    fm.mouseClick("tabBar.serverViewButton")
    assert fm.rootProp("localFilesShown") == False
    assert qmlEngine.serverFileModel.rowCount() == len(test_user_diagrams) + 1

    fm.keyClicks("serverSearchBar.searchBox", "patrickkidd+unittest+2@gmail.com")
    assert qmlEngine.serverFileModel.rowCount() == len(test_user_diagrams) / 2


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
