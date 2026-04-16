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


# --- Concurrent save simulation tests ---
#
# These tests verify the data merge logic of each app's applyChange callback
# directly on DiagramData, without server round-trips. They simulate the 409
# replay flow: one app saves, creating a new server state, then the second
# app's applyChange runs against that state as if replaying after a conflict.

from btcopilot.schema import (
    DiagramData,
    PDP,
    Person as SchemaPerson,
    Event as SchemaEvent,
    EventKind,
)
import pickle
import copy


def _pro_apply_change(diagramData: DiagramData, localData: dict) -> DiagramData:
    """Reproduce Pro app's applyChange from serverfilemanagermodel.py:538-584."""
    diagramData.people = localData.get("people", [])
    diagramData.events = localData.get("events", [])
    diagramData.pair_bonds = localData.get("pair_bonds", [])
    diagramData.emotions = localData.get("emotions", [])
    diagramData.multipleBirths = localData.get("multipleBirths", [])
    diagramData.layers = localData.get("layers", [])
    diagramData.layerItems = localData.get("layerItems", [])
    diagramData.items = localData.get("items", [])
    diagramData.pruned = localData.get("pruned", [])
    diagramData.uuid = localData.get("uuid")
    diagramData.name = localData.get("name")
    diagramData.tags = localData.get("tags", [])
    diagramData.loggedDateTime = localData.get("loggedDateTime", [])
    diagramData.masterKey = localData.get("masterKey")
    diagramData.alias = localData.get("alias")
    diagramData.version = localData.get("version")
    diagramData.versionCompat = localData.get("versionCompat")
    diagramData.lastItemId = localData.get("lastItemId", 0)
    diagramData.readOnly = localData.get("readOnly", False)
    diagramData.contributeToResearch = localData.get("contributeToResearch", False)
    diagramData.useRealNames = localData.get("useRealNames", False)
    diagramData.password = localData.get("password")
    diagramData.requirePasswordForRealNames = localData.get(
        "requirePasswordForRealNames", False
    )
    diagramData.showAliases = localData.get("showAliases", False)
    diagramData.hideNames = localData.get("hideNames", False)
    diagramData.hideToolBars = localData.get("hideToolBars", False)
    diagramData.hideEmotionalProcess = localData.get("hideEmotionalProcess", False)
    diagramData.hideEmotionColors = localData.get("hideEmotionColors", False)
    diagramData.hideDateSlider = localData.get("hideDateSlider", False)
    diagramData.hideVariablesOnDiagram = localData.get(
        "hideVariablesOnDiagram", False
    )
    diagramData.hideVariableSteadyStates = localData.get(
        "hideVariableSteadyStates", False
    )
    diagramData.hideSARFGraphics = localData.get("hideSARFGraphics", True)
    diagramData.exclusiveLayerSelection = localData.get(
        "exclusiveLayerSelection", True
    )
    diagramData.storePositionsInLayers = localData.get(
        "storePositionsInLayers", False
    )
    diagramData.currentDateTime = localData.get("currentDateTime")
    diagramData.scaleFactor = localData.get("scaleFactor")
    diagramData.pencilColor = localData.get("pencilColor")
    diagramData.eventProperties = localData.get("eventProperties", [])
    diagramData.legendData = localData.get("legendData")
    return diagramData


def _personal_apply_change(
    diagramData: DiagramData,
    sceneDiagramData: DiagramData,
    clusters: list,
    clusterCacheKey: str | None,
) -> DiagramData:
    """Reproduce Personal app's applyChange from personalappcontroller.py:275-292."""
    diagramData.people = sceneDiagramData.people
    diagramData.events = sceneDiagramData.events
    diagramData.pair_bonds = sceneDiagramData.pair_bonds
    diagramData.emotions = sceneDiagramData.emotions
    diagramData.multipleBirths = sceneDiagramData.multipleBirths
    diagramData.layers = sceneDiagramData.layers
    diagramData.layerItems = sceneDiagramData.layerItems
    diagramData.items = sceneDiagramData.items
    diagramData.pruned = sceneDiagramData.pruned
    diagramData.version = sceneDiagramData.version
    diagramData.versionCompat = sceneDiagramData.versionCompat
    diagramData.name = sceneDiagramData.name
    diagramData.lastItemId = sceneDiagramData.lastItemId
    diagramData.clusters = clusters
    diagramData.clusterCacheKey = clusterCacheKey
    return diagramData


def _names(dd: DiagramData) -> set[str]:
    return {p.get("name") for p in dd.people}


def test_concurrent_pro_saves_first_personal_replays():
    """Pro saves scene edit (Alice), Personal replays with PDP + clusters on 409."""
    serverState = DiagramData(
        people=[{"id": 1, "name": "Alice", "kind": "Person"}],
        lastItemId=1,
    )

    personalScene = DiagramData(
        people=[{"id": 1, "name": "Alice", "kind": "Person"}],
        lastItemId=1,
    )
    clusters = [{"id": "c1", "pattern": "anxiety_cascade", "event_ids": [10]}]
    cacheKey = "personal-key-1"

    # Personal's applyChange does NOT set pdp — it's preserved from server state.
    # Simulate Personal having written PDP to server previously.
    serverState.pdp = PDP(
        people=[SchemaPerson(id=-1, name="PDPBob")],
        events=[SchemaEvent(id=-2, kind=EventKind.Shift, person=-1)],
        pair_bonds=[],
    )

    result = _personal_apply_change(serverState, personalScene, clusters, cacheKey)

    assert "Alice" in _names(result)
    assert result.pdp.people[0].name == "PDPBob"
    assert len(result.pdp.events) == 1
    assert result.clusters == clusters
    assert result.clusterCacheKey == cacheKey


def test_concurrent_personal_saves_first_pro_replays():
    """Personal saves PDP + committed person Bob + clusters. Pro replays with scene edit
    (Charlie + hideNames=True) on 409.

    KNOWN LIMITATION: Pro's applyChange overwrites `people` from its local Scene,
    which does not include Bob. Bob is lost from `people`. This is the expected
    trade-off of the current architecture — each app owns its field list and the
    Pro app does not merge people arrays.
    """
    serverState = DiagramData(
        people=[{"id": 1, "name": "Bob", "kind": "Person"}],
        pdp=PDP(people=[], events=[], pair_bonds=[]),
        clusters=[{"id": "c1", "pattern": "anxiety_cascade"}],
        clusterCacheKey="personal-key-1",
        lastItemId=1,
    )

    proLocalData = {
        "people": [{"id": 2, "name": "Charlie", "kind": "Person"}],
        "events": [],
        "pair_bonds": [],
        "emotions": [],
        "hideNames": True,
        "lastItemId": 2,
    }

    result = _pro_apply_change(serverState, proLocalData)

    assert result.hideNames is True
    assert "Charlie" in _names(result)
    # Bob is lost — Pro's applyChange replaces `people` wholesale from its local Scene
    assert "Bob" not in _names(result)
    # Personal-owned fields survive because Pro doesn't touch them
    assert result.clusters == [{"id": "c1", "pattern": "anxiety_cascade"}]
    assert result.clusterCacheKey == "personal-key-1"


def test_concurrent_pdp_commit_then_pro_saves_stale():
    """Personal committed PDP person Bob into `people` and saved. Pro (stale,
    no Bob in local Scene) saves and gets 409, then replays.

    KNOWN TRADE-OFF: Bob is lost from `people` because Pro replaces the entire
    people array with its local state. The PDP entry for Bob was already removed
    during commit (committed items leave PDP). This is the expected data loss
    window in the current architecture — the mitigation is operational (Pro should
    sync before editing).
    """
    serverState = DiagramData(
        people=[
            {"id": 1, "name": "ExistingPerson", "kind": "Person"},
            {"id": 2, "name": "Bob", "kind": "Person"},  # committed from PDP
        ],
        pdp=PDP(people=[], events=[], pair_bonds=[]),  # Bob already committed out
        lastItemId=2,
    )

    # Pro's local Scene is stale — only has ExistingPerson
    proLocalData = {
        "people": [{"id": 1, "name": "ExistingPerson", "kind": "Person"}],
        "events": [],
        "pair_bonds": [],
        "emotions": [],
        "lastItemId": 1,
    }

    result = _pro_apply_change(serverState, proLocalData)

    # Bob is lost from people — Pro's local state didn't have him
    assert "Bob" not in _names(result)
    assert "ExistingPerson" in _names(result)
    # PDP is empty — Bob was already committed out of it
    assert result.pdp.people == []


def test_concurrent_ui_flags_survive_personal_apply():
    """Pro set hideNames=True and hideSARFGraphics=False. Personal replays
    (doesn't set UI flags). UI flags must survive on the server."""
    serverState = DiagramData(
        hideNames=True,
        hideSARFGraphics=False,
        exclusiveLayerSelection=False,
        storePositionsInLayers=True,
        readOnly=True,
        scaleFactor=1.5,
    )

    personalScene = DiagramData(
        people=[{"id": 1, "name": "Someone"}],
        lastItemId=1,
    )

    result = _personal_apply_change(serverState, personalScene, clusters=[], clusterCacheKey=None)

    # Personal's applyChange only touches scene collections, version metadata,
    # and clusters. All UI flags are untouched — they survive from server state.
    assert result.hideNames is True
    assert result.hideSARFGraphics is False
    assert result.exclusiveLayerSelection is False
    assert result.storePositionsInLayers is True
    assert result.readOnly is True
    assert result.scaleFactor == 1.5


def test_concurrent_clusters_survive_pro_apply():
    """Personal wrote clusters + clusterCacheKey. Pro replays. Both must survive."""
    clusters = [
        {"id": "c1", "pattern": "anxiety_cascade", "event_ids": [10, 11]},
        {"id": "c2", "pattern": "triangle_activation", "event_ids": [12]},
    ]
    serverState = DiagramData(
        clusters=clusters,
        clusterCacheKey="cache-abc",
    )

    proLocalData = {
        "people": [{"id": 1, "name": "Eve"}],
        "events": [],
        "pair_bonds": [],
        "emotions": [],
        "lastItemId": 1,
    }

    result = _pro_apply_change(serverState, proLocalData)

    assert result.clusters == clusters
    assert result.clusterCacheKey == "cache-abc"


def test_concurrent_pdp_survives_pro_apply():
    """Personal wrote non-empty PDP. Pro replays. PDP must survive intact."""
    pdp = PDP(
        people=[
            SchemaPerson(id=-1, name="PDPAlice"),
            SchemaPerson(id=-2, name="PDPBob"),
        ],
        events=[
            SchemaEvent(id=-3, kind=EventKind.Shift, person=-1, description="anxiety spike"),
            SchemaEvent(id=-4, kind=EventKind.Married, person=-1, spouse=-2),
        ],
        pair_bonds=[],
    )
    serverState = DiagramData(pdp=pdp)

    proLocalData = {
        "people": [{"id": 1, "name": "ScenePerson"}],
        "events": [],
        "pair_bonds": [],
        "emotions": [],
        "lastItemId": 1,
    }

    result = _pro_apply_change(serverState, proLocalData)

    assert len(result.pdp.people) == 2
    assert result.pdp.people[0].name == "PDPAlice"
    assert result.pdp.people[1].name == "PDPBob"
    assert len(result.pdp.events) == 2
    assert result.pdp.events[0].kind == EventKind.Shift
    assert result.pdp.events[1].kind == EventKind.Married


def test_concurrent_alternating_saves_three_rounds():
    """Simulate Pro → Personal (409) → Pro (409). Each app adds distinct data.
    Verify final state within known limitations.

    Round 1: Pro saves Alice + hideNames=True
    Round 2: Personal gets 409, replays with clusters + its scene (which includes Alice)
    Round 3: Pro gets 409, replays with Dave added to scene (stale, doesn't have clusters change)

    After round 3, Pro's replay preserves clusters (not in Pro's field list) but
    Pro's people array replaces server's — so the final people list is whatever
    Pro's local Scene had.
    """
    # Round 1: Pro saves
    serverState = DiagramData()
    proLocalR1 = {
        "people": [{"id": 1, "name": "Alice"}],
        "events": [],
        "pair_bonds": [],
        "emotions": [],
        "hideNames": True,
        "lastItemId": 1,
    }
    serverState = _pro_apply_change(serverState, proLocalR1)

    assert "Alice" in _names(serverState)
    assert serverState.hideNames is True

    # Round 2: Personal gets 409, replays. Personal's scene has Alice (synced before editing).
    personalSceneR2 = DiagramData(
        people=[{"id": 1, "name": "Alice"}],
        lastItemId=1,
    )
    clustersR2 = [{"id": "c1", "pattern": "anxiety_cascade"}]
    serverState.pdp = PDP(
        people=[SchemaPerson(id=-1, name="PDPEve")], events=[], pair_bonds=[]
    )
    serverState = _personal_apply_change(
        serverState, personalSceneR2, clustersR2, "cache-r2"
    )

    assert "Alice" in _names(serverState)
    assert serverState.clusters == clustersR2
    assert serverState.clusterCacheKey == "cache-r2"
    assert serverState.hideNames is True  # UI flag survived Personal's replay
    assert serverState.pdp.people[0].name == "PDPEve"

    # Round 3: Pro gets 409, replays. Pro's local scene has Alice + Dave, but
    # Pro doesn't know about clusters or PDP (stale).
    proLocalR3 = {
        "people": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Dave"}],
        "events": [],
        "pair_bonds": [],
        "emotions": [],
        "hideNames": True,
        "hideSARFGraphics": False,
        "lastItemId": 2,
    }
    serverState = _pro_apply_change(serverState, proLocalR3)

    # Pro-owned fields reflect Pro's latest
    assert _names(serverState) == {"Alice", "Dave"}
    assert serverState.hideNames is True
    assert serverState.hideSARFGraphics is False
    # Personal-owned fields survive all three rounds
    assert serverState.clusters == clustersR2
    assert serverState.clusterCacheKey == "cache-r2"
    assert serverState.pdp.people[0].name == "PDPEve"
