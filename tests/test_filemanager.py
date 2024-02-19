import time
import os.path
import pytest
import conftest

from sqlalchemy import inspect

import vedana
from pkdiagram import util, CUtil, SceneModel, Session, FileManager
from pkdiagram.pyqt import QApplication, QTest

from fdserver.extensions import db


@pytest.fixture
def create_fm(qtbot, request):

    created = []

    def _create_fm(session=True):

        _session = Session()
        if session:
            if session is True:
                test_session = request.getfixturevalue("test_session")
            else:
                test_session = session
            _session.init(sessionData=test_session.account_editor_dict())
        else:
            _session.deinit()

        fm = FileManager(_session, parent=None)
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
        fm.deinit()
        fm.hide()
        fm.session.deinit()


def test_local_filter(tmp_path, create_fm):

    CUtil.instance().forceDocsPath(str(tmp_path))

    NUM_FILES = 10
    for i in range(NUM_FILES):
        if i % 2 == 0:
            name = f"Diagram {i}-even.fd"
        else:
            name = f"Diagram {i}-odd.fd"
        fpath = os.path.join(tmp_path, name)
        util.touchFD(fpath)
    QTest.qSleep(1000)
    QApplication.processEvents()

    fm = create_fm()
    assert fm.rootProp("localFilesShown") == True

    localFileModel = fm.rootProp("localFileModel")
    assert localFileModel.rowCount() == NUM_FILES

    fm.keyClicks("localSearchBar.searchBox", "-odd")
    fm.itemProp("localSearchBar.searchBox", "text") == "-odd"
    assert localFileModel.searchText == "-odd"
    assert localFileModel.rowCount() == NUM_FILES / 2


def test_server_filter_owner(
    test_user, test_user_diagrams, test_session, test_activation, test_user_2, create_fm
):
    for diagram in test_user_diagrams:
        if diagram.user_id == test_user_2.id:
            diagram.grant_access(test_user, vedana.ACCESS_READ_ONLY)
    db.session.commit()

    fm = create_fm()
    serverFileModel = fm.rootProp("serverFileModel")
    updateFinished = util.Condition(serverFileModel.updateFinished)
    fm.session.init(
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


def test_server_doesnt_init_in_edit_mode_admin_user(
    test_user, test_user_diagrams, create_fm
):
    test_user.roles = "admin"
    db.session.commit()

    fm = create_fm()
    assert fm.session.isAdmin
    assert fm.findItem("serverFileList").property("editMode") == False


def test_free_licence_hides_server_view(test_user, create_fm):
    fm = create_fm()
    assert fm.findItem("serverViewButton").property("visible") == False


# TODO:
# - Free license hides server view
#
