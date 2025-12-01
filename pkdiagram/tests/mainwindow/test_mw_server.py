import datetime
import logging
import os.path
import pickle
from unittest import mock

import pytest
from sqlalchemy import inspect

import btcopilot
from pkdiagram.pyqt import QFileInfo, QMessageBox, Qt, QApplication
from pkdiagram import util
from pkdiagram.scene import Scene, Person
from pkdiagram.documentview import DocumentController
from pkdiagram.mainwindow import MainWindow, FileManager
from pkdiagram.app import AppController
from pkdiagram.models.serverfilemanagermodel import ServerFileManagerModel

from btcopilot.extensions import db
from btcopilot.pro.models import Diagram


_log = logging.getLogger(__name__)


pytestmark = [
    pytest.mark.component("MainWindow"),
    pytest.mark.depends_on("DocumentView"),
]


@pytest.mark.parametrize("license", (btcopilot.LICENSE_FREE, btcopilot.LICENSE_CLIENT))
def test_login_shows_free_diagram(request, test_user, qtbot, create_ac_mw, license):
    if license == btcopilot.LICENSE_CLIENT:
        request.getfixturevalue("test_client_activation")

    ac, mw = create_ac_mw(session=False)
    assert mw.accountDialog.isShown()

    qtbot.clickOkAfter(
        lambda: ac.session.login(
            username=test_user.username, password=test_user._plaintext_password
        ),
        contains=AppController.S_USING_FREE_LICENSE,
    )
    assert ac.session.isLoggedIn()
    # assert mw.accountDialog.isShown() == False
    assert mw.scene.serverDiagram().user_id == ac.session.user.id
    assert mw.scene.serverDiagram().isFreeDiagram()
    assert mw.documentView.sceneModel.isOnServer


def _open_server_file_item(mw, index):
    itemDelegates = mw.fileManager.itemProp(
        "serverFileList", "itemDelegates"
    ).toVariant()
    path = itemDelegates[index].property("dPath")
    # mw.fileManager.clickListViewItem_actual('serverFileList', 'Free Diagram')
    mw.fileManager.findItem("serverFileList").selected.emit(path)


def _numServerFileItems(mw):
    ret = len(mw.fileManager.itemProp("serverFileList", "itemDelegates").toVariant())
    # _log.info(f"num: {ret}")
    return ret


def test_rw_edit_on_client_diagram(
    test_user, test_activation, test_user_2, create_ac_mw
):
    data = Scene(items=[Person(name="you")]).data()
    test_user_2.set_free_diagram(pickle.dumps(data), _commit=True)
    test_user_2.free_diagram.grant_access(
        test_user, btcopilot.ACCESS_READ_WRITE, _commit=True
    )

    # Edit from user with rw access
    ac, mw = create_ac_mw()
    util.wait(mw.serverFileModel.updateFinished)
    row = mw.serverFileModel.rowForDiagramId(test_user_2.free_diagram_id)
    assert util.waitForCondition(
        lambda: _numServerFileItems(mw) >= (len(test_user.diagrams) + 1)
    )

    _open_server_file_item(mw, row)
    mw.scene.addItems(Person(name="me"))
    mw.save()

    # Ensure change made it to database
    free_diagram = Diagram.query.get(test_user_2.free_diagram_id)
    scene = Scene()
    scene.read(pickle.loads(free_diagram.data))
    assert len(scene.people()) == 2
    assert scene.people()[0].name() == "you"
    assert scene.people()[1].name() == "me"


def test_open_server_file_no_server(
    test_activation, test_user_diagrams, test_user, server_down, create_ac_mw
):
    ac, mw = create_ac_mw()
    util.wait(mw.serverFileModel.updateFinished)
    assert util.waitForCondition(
        lambda: _numServerFileItems(mw) >= len(test_user.diagrams)
    )

    with server_down(True):
        with mock.patch.object(QMessageBox, "warning") as warning:
            _open_server_file_item(mw, 1)
            assert warning.call_count == 1
            assert warning.call_args.args[2] == FileManager.S_SERVER_SYNC_FAILED


@pytest.mark.parametrize("delete_local", [True, False])
def test_upload_to_server(qtbot, test_activation, create_ac_mw, tmp_path, delete_local):
    ac, mw = create_ac_mw()
    tmp_fd_path = os.path.join(tmp_path, "test.fd")
    util.touchFD(os.path.join(tmp_path, "test.fd"))
    mw.open(tmp_fd_path)
    data = mw.scene.data()
    local_bdata = pickle.dumps(data)
    localFileName = QFileInfo(mw.document.url().toLocalFile()).baseName()

    def _question(*args):
        if question.call_count == 2:
            if delete_local:
                return QMessageBox.Yes
            else:
                return QMessageBox.No
        else:
            return QMessageBox.Yes

    with mock.patch(
        "pkdiagram.pyqt.QMessageBox.question", side_effect=_question
    ) as question:
        mw.documentView.controller.uploadToServer.emit()
        util.waitALittle()  # for the network request to complete, then raise the "delete" confirm dialog
    assert question.call_count == 2
    assert question.call_args_list[0].args[2] == MainWindow.S_CONFIRM_UPLOAD_DIAGRAM
    assert (
        question.call_args_list[1].args[2]
        == MainWindow.S_CONFIRM_DELETE_LOCAL_COPY_OF_UPLOADED_DIAGRAM
    )
    diagram_id = mw.scene.serverDiagram().id
    server_diagram = Diagram.query.get(diagram_id)
    assert server_diagram.data == local_bdata
    assert server_diagram.name == localFileName
    assert os.path.exists(tmp_fd_path) is (not delete_local)


@pytest.mark.parametrize("is_owner", [(True, False)])
@pytest.mark.parametrize("has_write", [(True, False)])
def test_server_diagram_access(
    test_activation, test_user, test_user_diagrams, create_ac_mw, is_owner, has_write
):
    diagram_id = None
    for _diagram in test_user_diagrams:
        db.session.add(_diagram)  # these diagrams lost their session somehow
        if is_owner and _diagram.user_id == test_user.id:
            diagram_id = _diagram.id
            break
        elif not is_owner and _diagram.user_id != test_user.id:
            if has_write:
                _diagram.grant_access(test_user, btcopilot.ACCESS_READ_WRITE)
            else:
                _diagram.grant_access(test_user, btcopilot.ACCESS_READ_ONLY)
            diagram_id = _diagram.id
            break
    db.session.commit()

    ac, mw = create_ac_mw()
    util.wait(mw.serverFileModel.updateFinished)
    diagram = mw.serverFileModel.findDiagram(diagram_id)
    fpath = mw.serverFileModel.pathForDiagram(diagram)
    mw.onServerFileClicked(fpath, diagram)
    if is_owner or has_write:
        assert not mw.documentView.sceneModel.readOnly
    else:
        assert mw.documentView.sceneModel.readOnly


def test_server_admin_diagram_access_no_rights(
    test_activation, test_user, test_user_2, create_ac_mw
):
    diagram = Diagram(
        user_id=test_user_2.id,
        data=pickle.dumps({}),
        updated_at=datetime.datetime.now(),
    )
    db.session.add(diagram)
    db.session.merge(diagram)

    test_user.roles = btcopilot.ROLE_ADMIN
    db.session.add(test_user)
    db.session.commit()
    diagram_id = diagram.id

    ac, mw = create_ac_mw()
    assert util.wait(mw.serverFileModel.updateFinished)

    userIdEdit = mw.fileManager.rootProp("userIdEdit")
    serverFileList = mw.fileManager.rootProp("serverFileList")
    mw.fileManager.mouseClick("tabBar.serverViewButton")
    mw.fileManager.keyClicksItem(userIdEdit, str(test_user_2.id))
    assert util.wait(mw.serverFileModel.updateFinished)

    diagram = mw.serverFileModel.findDiagram(diagram_id)
    fpath = mw.serverFileModel.pathForDiagram(diagram)
    mw.onServerFileClicked(fpath, diagram)
    assert mw.documentView.sceneModel.readOnly
    assert mw.ui.actionSave_As.isEnabled()


@pytest.mark.parametrize("dontShowServerFileUpdated", [True, False])
def test_current_server_file_updated_elsewhere(
    qtbot, test_user, create_ac_mw, dontShowServerFileUpdated
):
    diagram_id = test_user.free_diagram_id
    ac, mw = create_ac_mw()
    util.wait(mw.serverFileModel.updateFinished)

    mw.prefs.setValue(
        ServerFileManagerModel.PREF_DONT_SHOW_SERVER_FILE_UPDATED,
        dontShowServerFileUpdated,
    )
    _open_server_file_item(mw, 0)
    assert mw.scene.query1(name="Patrick") == None

    # Simulate save on another machine
    data = {}
    scene = Scene()
    scene.addItems(Person(name="Patrick"))
    scene.write(data)
    diagram = Diagram.query.get(diagram_id)
    diagram.update(data=pickle.dumps(data), _commit=True)
    inspect(diagram).session.add(diagram)
    inspect(diagram).session.commit()

    # Simulate periodic poll on this machine
    mw.serverFileModel.update()
    if dontShowServerFileUpdated:
        util.wait(mw.serverFileModel.updateFinished)
    else:

        def clickReloadButton():
            widget = QApplication.activeModalWidget()
            if isinstance(widget, QMessageBox):
                for button in widget.buttons():
                    if button.text() == "Reload Their Changes":
                        qtbot.mouseClick(button, Qt.LeftButton)
                        return True
            return False

        qtbot.qWaitForMessageBox(
            lambda: util.wait(mw.serverFileModel.updateFinished),
            handleClick=clickReloadButton,
        )
    assert mw.scene.query1(name="Patrick")
