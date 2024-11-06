import os.path, datetime, pickle, logging
from contextlib import ExitStack

import pytest
import mock
from sqlalchemy import inspect

from conftest import _scene_data
import vedana
from pkdiagram import (
    util,
    mainwindow,
    Scene,
    Person,
    AppConfig,
    Session,
    AppController,
    MainWindow,
    FileManager,
    DocumentController,
)
from pkdiagram.pyqt import Qt, QFileInfo, QMessageBox, QApplication, QTimer

from fdserver.extensions import db
from fdserver.models import Diagram


_log = logging.getLogger(__name__)


pytestmark = [
    pytest.mark.component("MainWindow"),
    pytest.mark.depends_on("DocumentView"),
]


@pytest.mark.parametrize("license", (vedana.LICENSE_FREE, vedana.LICENSE_CLIENT))
def test_login_shows_free_diagram(request, test_user, qtbot, create_ac_mw, license):
    if license == vedana.LICENSE_CLIENT:
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
    assert mw.documentView.sceneModel.isOnServer == True


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


@pytest.mark.parametrize("is_server_down", (True, False))
def test_init_open_n_reopen_server_file(
    test_activation,
    test_user_diagrams,
    test_user,
    create_ac_mw,
    server_down,
    is_server_down,
):
    # Load a file from the server in one MainWindow
    ac1, mw1 = create_ac_mw()
    assert util.wait(mw1.serverFileModel.updateFinished) == True
    assert (
        util.waitForCondition(
            lambda: _numServerFileItems(mw1) >= len(test_user.diagrams)
        )
        == True
    )
    _open_server_file_item(mw1, 1)
    assert mw1.document
    assert mw1.documentView.sceneModel.isOnServer == True
    ac1._post_event_loop(mw1)
    mw1.deinit()

    with server_down(is_server_down):
        # Load a second window to see if it loads the same file from the server
        ac2, mw2 = create_ac_mw()
        util.wait(mw2.serverFileModel.updateFinished)
        assert mw2.document
        assert mw2.documentView.sceneModel.isOnServer == True
        ac2._post_event_loop(mw2)
        mw2.deinit()


def test_open_server_file_no_server(
    test_activation, test_user_diagrams, test_user, server_down, create_ac_mw
):

    # Populate server file cache
    ac1, mw1 = create_ac_mw()
    util.wait(mw1.serverFileModel.updateFinished)
    assert (
        util.waitForCondition(
            lambda: _numServerFileItems(mw1) >= len(test_user.diagrams)
        )
        == True
    )
    ac1._post_event_loop(mw1)
    mw1.deinit()

    with server_down(True):
        # Load a second window to see if it loads the same file from the server
        ac2, mw2 = create_ac_mw()
        util.wait(mw2.serverFileModel.updateFinished)
        assert (
            util.waitForCondition(
                lambda: _numServerFileItems(mw2) >= len(test_user.diagrams)
            )
            == True
        )
        _open_server_file_item(mw2, 2)
        assert mw2.document
        assert mw2.documentView.sceneModel.isOnServer == True
        mw2.deinit()


def test_rw_edit_on_client_diagram(
    test_user, test_activation, test_user_2, create_ac_mw
):
    data = Scene(items=[Person(name="you")]).data()
    test_user_2.set_free_diagram(pickle.dumps(data), _commit=True)
    test_user_2.free_diagram.grant_access(
        test_user, vedana.ACCESS_READ_WRITE, _commit=True
    )

    # Edit from user with rw access
    ac, mw = create_ac_mw()
    util.wait(mw.serverFileModel.updateFinished)
    row = mw.serverFileModel.rowForDiagramId(test_user_2.free_diagram_id)
    assert (
        util.waitForCondition(
            lambda: _numServerFileItems(mw) >= (len(test_user.diagrams) + 1)
        )
        == True
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
        QApplication.processEvents()  # for the network request to complete, then raise the "delete" confirm dialog
    assert question.call_count == 2
    assert (
        question.call_args_list[0].args[2]
        == DocumentController.S_CONFIRM_UPLOAD_DIAGRAM
    )
    assert (
        question.call_args_list[1].args[2]
        == DocumentController.S_CONFIRM_DELETE_LOCAL_COPY_OF_UPLOADED_DIAGRAM
    )
    diagram_id = mw.scene.serverDiagram().id
    server_diagram = Diagram.query.get(diagram_id)
    assert server_diagram.data == local_bdata
    assert server_diagram.name == localFileName
    assert os.path.exists(tmp_fd_path) == (not delete_local)


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
                _diagram.grant_access(test_user, vedana.ACCESS_READ_WRITE)
            else:
                _diagram.grant_access(test_user, vedana.ACCESS_READ_ONLY)
            diagram_id = _diagram.id
            break
    db.session.commit()

    ac, mw = create_ac_mw()
    util.wait(mw.serverFileModel.updateFinished)
    diagram = mw.serverFileModel.findDiagram(diagram_id)
    fpath = mw.serverFileModel.pathForDiagram(diagram)
    mw.onServerFileClicked(fpath, diagram)
    if is_owner or has_write:
        assert mw.documentView.sceneModel.readOnly == False
    else:
        assert mw.documentView.sceneModel.readOnly == True


def test_delete_server_file(test_user_diagrams, qtbot, create_ac_mw):
    ac, mw = create_ac_mw()
    updateFinished = util.Condition(mw.serverFileModel.updateFinished)
    model = mw.fileManager.serverFileModel
    assert updateFinished.wait() == True
    assert model.rowCount() == len(test_user_diagrams) / 2 + 1

    ROW = 2
    diagram_id = model.index(ROW, 0).data(model.IDRole)
    diagram = model.findDiagram(diagram_id)
    fpath = model.localPathForID(diagram_id)
    assert os.path.exists(fpath) == True
    assert Diagram.query.get(diagram_id) != None

    qtbot.clickYesAfter(lambda: model.deleteFileAtRow(ROW))
    assert os.path.exists(fpath) == False
    assert Diagram.query.get(diagram_id) == None


@pytest.mark.parametrize("dontShowServerFileUpdated", [True, False])
def test_current_server_file_updated_elsewhere(
    qtbot, test_user, create_ac_mw, dontShowServerFileUpdated
):
    diagram_id = test_user.free_diagram_id
    ac, mw = create_ac_mw()
    model = mw.fileManager.serverFileModel
    util.wait(mw.serverFileModel.updateFinished)

    mw.prefs.setValue("dontShowServerFileUpdated", dontShowServerFileUpdated)
    _open_server_file_item(mw, 0)
    assert mw.scene.query1(name="Patrick") == None

    # Simulate save on another machine
    data = _scene_data(Person(name="Patrick"))
    diagram = Diagram.query.get(diagram_id)
    diagram.update(data=pickle.dumps(data), _commit=True)
    inspect(diagram).session.add(diagram)
    inspect(diagram).session.commit()

    # Simulate periodic poll on this machine
    mw.serverFileModel.update()
    if dontShowServerFileUpdated:
        util.wait(mw.serverFileModel.updateFinished)
    else:
        qtbot.clickOkAfter(
            lambda: util.wait(mw.serverFileModel.updateFinished),
            contains=MainWindow.S_DIAGRAM_UPDATED_FROM_SERVER,
        )
    assert mw.scene.query1(name="Patrick")
