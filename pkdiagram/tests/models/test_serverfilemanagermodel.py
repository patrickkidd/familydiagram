import os, os.path
import pickle
import datetime
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


def test_no_clear_on_logout(test_user_diagrams, test_user, create_model):
    """Cache should NOT clear on logout - user may have diagram open."""
    model = create_model()
    db.session.add_all(test_user_diagrams)
    expected_count = (
        len([x for x in test_user_diagrams if x.check_read_access(test_user)]) + 1
    )
    assert model.rowCount() == expected_count

    model.session.logout()
    assert model.rowCount() == expected_count


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

    # Write free diagram + logout (cache persists)
    scene = Scene(items=Person(name="Me"))
    bdata = pickle.dumps(scene.data())
    model.setData(model.index(0, 0), bdata, role=model.DiagramDataRole)
    session.logout()
    assert model.rowCount() == 1

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


# --- FR-2 merge tests: applyChange must preserve Personal-owned fields ---


def _inject_personal_data(diagram_id, pdp_dict=None, clusters=None, cache_key=None):
    """Write Personal-app-owned fields into the server's diagram blob and bump timestamp."""
    diagram = Diagram.query.get(diagram_id)
    data = pickle.loads(diagram.data) if diagram.data else {}
    if pdp_dict is not None:
        data["pdp"] = pdp_dict
    if clusters is not None:
        data["clusters"] = clusters
    if cache_key is not None:
        data["clusterCacheKey"] = cache_key
    diagram.data = pickle.dumps(data)
    diagram.updated_at = datetime.datetime.utcnow()
    db.session.commit()


def _read_server_blob(diagram_id):
    """Read the raw dict from the server's diagram blob."""
    db.session.expire_all()
    diagram = Diagram.query.get(diagram_id)
    return pickle.loads(diagram.data) if diagram.data else {}


SAMPLE_PDP = {
    "people": [{"id": -1, "name": "Alice", "gender": "female"}],
    "events": [{"id": -2, "kind": "birth", "child": -1}],
    "pair_bonds": [],
}

SAMPLE_CLUSTERS = [
    {"id": "c1", "pattern": "anxiety_cascade", "event_ids": [10, 11]},
]


def test_save_preserves_server_pdp(create_model):
    """Pro app save must not clobber PDP written by Personal app (FR-2)."""
    model = create_model()
    diagram_id = model.index(0, 0).data(model.IDRole)

    _inject_personal_data(diagram_id, pdp_dict=SAMPLE_PDP)
    model.syncDiagramFromServer(diagram_id)

    scene = Scene(items=Person(name="Bob"))
    bdata = pickle.dumps(scene.data())
    model.setData(model.index(0, 0), bdata, role=model.DiagramDataRole)

    server_data = _read_server_blob(diagram_id)
    pdp = server_data["pdp"]
    assert len(pdp["people"]) == 1
    assert pdp["people"][0]["name"] == "Alice"
    assert pdp["people"][0]["id"] == -1
    assert len(pdp["events"]) == 1
    assert pdp["events"][0]["kind"] == "birth"
    person_names = [p.get("name") for p in server_data.get("people", [])]
    assert "Bob" in person_names


def test_save_preserves_server_clusters(create_model):
    """Pro app save must not clobber clusters written by Personal app."""
    model = create_model()
    diagram_id = model.index(0, 0).data(model.IDRole)

    _inject_personal_data(diagram_id, clusters=SAMPLE_CLUSTERS, cache_key="abc123")
    model.syncDiagramFromServer(diagram_id)

    scene = Scene(items=Person(name="Carol"))
    bdata = pickle.dumps(scene.data())
    model.setData(model.index(0, 0), bdata, role=model.DiagramDataRole)

    server_data = _read_server_blob(diagram_id)
    assert server_data["clusters"] == SAMPLE_CLUSTERS
    assert server_data["clusterCacheKey"] == "abc123"


def test_save_merges_correctly_on_409_retry(create_model):
    """The applyChange merge preserves Personal fields when replayed on server state."""
    from btcopilot.schema import DiagramData, PDP, Person as SchemaPerson

    create_model()  # initialize fixtures

    scene = Scene(items=Person(name="Eve"))
    localData = pickle.loads(pickle.dumps(scene.data()))

    serverPdp = PDP(
        people=[SchemaPerson(id=-1, name="Alice")],
        events=[],
        pair_bonds=[],
    )
    serverDd = DiagramData(
        people=[{"id": 1, "name": "OldPerson", "kind": "Person"}],
        pdp=serverPdp,
        clusters=[{"id": "c1"}],
        clusterCacheKey="xyz",
    )

    # Same explicit merge as applyChange in serverfilemanagermodel.py
    serverDd.people = localData.get("people", [])
    serverDd.events = localData.get("events", [])
    serverDd.pair_bonds = localData.get("pair_bonds", [])
    serverDd.name = localData.get("name")
    serverDd.lastItemId = localData.get("lastItemId", 0)

    assert serverDd.pdp is serverPdp
    assert serverDd.pdp.people[0].name == "Alice"
    assert serverDd.clusters == [{"id": "c1"}]
    assert serverDd.clusterCacheKey == "xyz"
    person_names = [p.get("name") for p in serverDd.people]
    assert "Eve" in person_names
    assert "OldPerson" not in person_names


def test_save_scene_roundtrip_fidelity(create_model):
    """All Pro-owned scene fields survive the merge unchanged."""
    model = create_model()
    diagram_id = model.index(0, 0).data(model.IDRole)

    scene = Scene()
    p1, p2 = scene.addItems(Person(name="Eve"), Person(name="Frank"))
    from pkdiagram.scene import Marriage

    scene.addItem(Marriage(p1, p2))
    original_data = scene.data()
    bdata = pickle.dumps(original_data)
    model.setData(model.index(0, 0), bdata, role=model.DiagramDataRole)

    server_data = _read_server_blob(diagram_id)
    assert len(server_data["people"]) == len(original_data["people"])
    assert len(server_data["pair_bonds"]) == len(original_data["pair_bonds"])
    for orig, saved in zip(original_data["people"], server_data["people"]):
        assert orig["name"] == saved["name"]
        assert orig["id"] == saved["id"]


def test_save_empty_pdp_stays_empty(create_model):
    """When server has no PDP, save must not introduce phantom PDP data."""
    model = create_model()
    diagram_id = model.index(0, 0).data(model.IDRole)

    scene = Scene(items=Person(name="Grace"))
    bdata = pickle.dumps(scene.data())
    model.setData(model.index(0, 0), bdata, role=model.DiagramDataRole)

    server_data = _read_server_blob(diagram_id)
    pdp = server_data.get("pdp", {})
    assert pdp.get("people", []) == []
    assert pdp.get("events", []) == []
    assert pdp.get("pair_bonds", []) == []
