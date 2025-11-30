import os, os.path
import pickle
import pytest
from sqlalchemy import inspect

import btcopilot
from pkdiagram import util
from pkdiagram.server_types import Diagram as fe_Diagram
from pkdiagram.models import ServerFileManagerModel
from pkdiagram.scene import Scene, Person
from pkdiagram.app import Session as fe_Session

from btcopilot.extensions import db
from btcopilot.pro.models import Diagram


@pytest.fixture
def create_model(request):

    created = []

    def _create_model(session=True):
        model = ServerFileManagerModel()
        _session = fe_Session()
        if session:
            if session is True:
                test_session = request.getfixturevalue("test_session")
            else:
                test_session = session
            _session.init(
                sessionData=test_session.account_editor_dict(), syncWithServer=False
            )
        else:
            _session.init(syncWithServer=False)

        model.init()
        model.setSession(_session)
        assert util.wait(model.updateFinished) == True

        created.append(model)
        return model

    yield _create_model

    for model in created:
        if model.session:
            model.session.deinit()
        model.deinit()


def _grant_ro_access(diagrams, grantee):
    for diagram in diagrams:
        if diagram.user_id != grantee.id:
            diagram.grant_access(grantee, btcopilot.ACCESS_READ_ONLY)
    db.session.commit()


def test_get_index(test_user_diagrams, test_user, create_model):
    model = create_model()

    db.session.add_all((test_user, *test_user_diagrams))
    _grant_ro_access(test_user_diagrams, test_user)
    model.update()
    assert util.Condition(model.updateFinished).wait()
    assert model.rowCount() == len(test_user_diagrams) + 1


def test_get_index_other_user(test_user, test_user_2, create_model):
    test_user.roles = "admin"
    diagram_1 = Diagram(data=pickle.dumps({}), user_id=test_user_2.id)
    diagram_2 = Diagram(data=pickle.dumps({}), user_id=test_user_2.id)
    db.session.add_all([diagram_1, diagram_2])
    db.session.commit()

    model = create_model()

    model.userId = str(test_user_2.id)
    assert model.userId == str(test_user_2.id)
    updateFinished = util.Condition(model.updateFinished)
    assert updateFinished.wait() == True
    assert model.rowCount() == 2


# def test_disk_cache(test_user, test_user_diagrams, create_model):
#     model = create_model()

#     db.session.add_all((test_user, *test_user_diagrams))
#     assert (
#         model.rowCount()
#         == len([x for x in test_user_diagrams if x.user_id == test_user.id]) + 1
#     )
#     model.write()

#     model2 = ServerFileManagerModel(dataPath=model.dataPath)
#     model2.init()
#     model2.setSession(model.session)
#     updateFinished = util.Condition(model2.updateFinished)
#     indexGETResponse2 = util.Condition(model2.indexGETResponse)
#     diagramGETResponse2 = util.Condition(model2.diagramGETResponse)
#     assert updateFinished.wait() == True
#     assert indexGETResponse2.callCount == 1
#     assert diagramGETResponse2.callCount == 0
#     assert model2.rowCount() == model.rowCount()
#     # assert encryption.isEncrypted(model.index(0, 0).data(role=model.DiagramDataRole)) == False
#     # assert encryption.isEncrypted(model.index(1, 0).data(role=model.DiagramDataRole)) == False
#     # assert encryption.isEncrypted(model.index(2, 0).data(role=model.DiagramDataRole)) == False
#     # assert encryption.isEncrypted(model.index(3, 0).data(role=model.DiagramDataRole)) == False
#     # assert encryption.isEncrypted(model.index(4, 0).data(role=model.DiagramDataRole)) == False


# def test_cached_fds_are_encrypted(test_user_diagrams, create_model):
#     model = create_model()
#     assert model.rowCount() == 6
#     def _is_fd_encrypted(row):
#         diagram_id = model.index(row, 0).data(model.IDRole)
#         fpath = model.localPathForID(diagram_id)
#         with open(os.path.join(fpath, 'diagram.pickle'), 'rb') as f:
#             ebdata = f.read()
#             return encryption.isEncrypted(ebdata)
#     assert _is_fd_encrypted(0)
#     assert _is_fd_encrypted(1)
#     assert _is_fd_encrypted(2)
#     assert _is_fd_encrypted(3)
#     assert _is_fd_encrypted(4)


def test_dataChanged_on_poll(test_user, create_model):
    model = create_model()
    dataChanged = util.Condition(model.dataChanged)
    model.syncDiagramFromServer(test_user.free_diagram_id)
    assert dataChanged.callCount == 0
    assert model.rowCount() == 1

    # Simulate save on another machine
    diagram = Diagram.query.get(test_user.free_diagram_id)
    data = {}
    scene = Scene()
    scene.read(pickle.loads(diagram.data))
    scene.addItems(Person(name="Patrick"))
    scene.write(data)
    diagram.update(data=pickle.dumps(data), _commit=True)
    inspect(diagram).session.add(diagram)
    inspect(diagram).session.commit()

    # Polled update on this machine
    model.syncDiagramFromServer(test_user.free_diagram_id)
    assert dataChanged.callCount == 1
    assert dataChanged.callArgs[0] == (
        model.index(0, 0),
        model.index(0, 0),
        [model.DiagramDataRole],
    )
    scene = Scene()
    bdata = model.data(dataChanged.callArgs[0][0], model.DiagramDataRole)
    scene.read(pickle.loads(bdata))
    assert scene.query1(name="Patrick")

    # Test sync idempotence
    model.syncDiagramFromServer(test_user.free_diagram_id)
    assert dataChanged.callCount == 1


def test_add_diagram_file(test_user, create_model):
    data = {}
    Scene().write(data)
    diagram = Diagram(user_id=test_user.id, data=pickle.dumps(data))
    db.session.add(diagram)
    db.session.commit()

    model = create_model()
    db.session.add(diagram)
    _diagram = fe_Diagram.create(diagram.as_dict())
    model._addOrUpdateDiagram(_diagram)
    fpath = model.localPathForID(diagram.id)
    assert os.path.isdir(fpath) == True


def test_helpers(test_user_diagrams, create_model):
    ROW = 1

    model = create_model()
    diagram_1 = model.diagramForRow(ROW)
    diagram_id = model.index(ROW, 0).data(model.IDRole)
    assert diagram_id == diagram_1.id

    fpath = model.localPathForID(diagram_id)
    diagram = model.serverDiagramForPath(fpath)
    assert model.rowForDiagramId(diagram.id) == ROW


def test_searchText(test_user_diagrams, test_user, create_model):
    SEARCH_TERM = "patrickkidd+unittest+2@gmail.com"

    db.session.add_all((test_user, *test_user_diagrams))
    num_matching_search = len(
        [x for x in test_user_diagrams if SEARCH_TERM in x.user.username]
    )
    _grant_ro_access(test_user_diagrams, test_user)

    model = create_model()
    assert model.rowCount() == len(test_user_diagrams) + 1

    model.searchText = SEARCH_TERM
    assert model.rowCount() == num_matching_search

    model.reset("searchText")
    assert model.rowCount() == len(test_user_diagrams) + 1


def test_clear_on_logout(test_user_diagrams, test_user, create_model):
    model = create_model()
    db.session.add_all(test_user_diagrams)
    assert (
        model.rowCount()
        == len([x for x in test_user_diagrams if x.check_read_access(test_user)]) + 1
    )

    cleared = util.Condition(model.cleared)
    model.session.logout()
    assert cleared.wait() == True
    assert model.rowCount() == 0


def test_dont_clear_cache_on_restart(
    test_user_diagrams, test_user, test_session, create_model
):
    model = create_model()
    db.session.add_all(test_user_diagrams)
    assert (
        model.rowCount()
        == len([x for x in test_user_diagrams if x.check_read_access(test_user)]) + 1
    )

    model.deinit()
    session = fe_Session()
    session.init(sessionData=test_session.account_editor_dict(), syncWithServer=False)
    model2 = ServerFileManagerModel()
    model2.init()
    model2.setSession(session)
    assert util.wait(model2.updateFinished)
    assert (
        model2.rowCount()
        == len([x for x in test_user_diagrams if x.check_read_access(test_user)]) + 1
    )


def test_save_free_diagram_persists(test_session):
    # Read free diagram 1
    model = ServerFileManagerModel()
    session = fe_Session()
    session.init(sessionData=test_session.account_editor_dict(), syncWithServer=False)
    assert session.hasFeature(btcopilot.LICENSE_FREE) == True
    model.init()
    model.setSession(session)
    assert util.wait(model.updateFinished)
    assert model.rowCount() == 1

    # Write free diagram + logout
    scene = Scene(items=Person(name="Me"))
    bdata = pickle.dumps(scene.data())
    model.setData(model.index(0, 0), bdata, role=model.DiagramDataRole)
    session.logout()
    assert model.rowCount() == 0

    # Login + Read free diagram
    session.setData(test_session.account_editor_dict())
    assert util.wait(model.updateFinished)
    assert model.rowCount() == 1
    loaded_bdata = model.index(0, 0).data(model.DiagramDataRole)
    loaded_scene = Scene()
    loaded_scene.read(pickle.loads(loaded_bdata))
    person = loaded_scene.query1(name="Me")
    assert isinstance(person, Person) == True


def test_delete_file(qtbot, create_model):
    model = create_model()
    assert model.rowCount() == 1

    ROW = 0
    diagram_id = model.index(ROW, 0).data(model.IDRole)
    fpath = model.localPathForID(diagram_id)
    assert os.path.exists(fpath) == True
    assert Diagram.query.get(diagram_id) != None

    qtbot.clickYesAfter(lambda: model.deleteFileAtRow(0))
    assert model.rowCount() == 0
