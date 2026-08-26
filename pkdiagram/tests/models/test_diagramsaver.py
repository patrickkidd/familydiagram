"""FD-336 / WP-C.

The DiagramSaver extraction must not change a single byte the Pro app writes
to the server (C7/S1), and the saver must own the merge baseline so a polled
cache swap can no longer silently delete another client's work (C7).
"""

import datetime
import pickle
from dataclasses import asdict

from pkdiagram import util
from pkdiagram.models.diagramsaver import DiagramSaver
from pkdiagram.scene import Scene, Person
from pkdiagram.server_types import Diagram as fe_Diagram

from btcopilot.extensions import db
from btcopilot.pro.models import Diagram
from btcopilot.schema import DiagramData

from pkdiagram.tests.models.test_serverfilemanagermodel import create_model


SAMPLE_PDP = {
    "people": [
        {"id": -1, "name": "Ana"},
        {"id": -2, "name": "Ben"},
        {"id": -3, "name": "Cyd"},
    ],
    "events": [],
    "pair_bonds": [],
}

SAMPLE_CLUSTERS = [
    {"id": "c1", "pattern": "anxiety_cascade", "event_ids": [10, 11]},
    {"id": "c2", "pattern": "triangle_activation", "event_ids": [12]},
]

LEGACY_KEYS = {
    "marriages": [{"id": 3, "personA": 1, "personB": 2}],
    "schemaVersion": 2,
    "retiredSetting": "gone",
}


def _reference_apply_change(dataToSave, openSnapshot):
    """The pre-refactor merge, pinned verbatim from
    `master:pkdiagram/models/serverfilemanagermodel.py` (the closure inside
    setData). This is the byte-identity gate for the refactor, not a place to
    improve the merge — any edit here silently weakens the gate.
    """

    def applyChange(diagramData: DiagramData):
        # Only modify Scene-owned fields (FR-2 in DATA_SYNC_FLOW.md).
        # Same pattern as PersonalAppController.saveDiagram().
        localData = pickle.loads(dataToSave)
        # Scene collections — snapshot-diff merge. For each field,
        # take server's copy unless the user actually edited the
        # item (snapshot vs local differ), preventing a stale
        # snapshot from clobbering concurrent edits.
        for fname in DiagramData.SCENE_COLLECTION_FIELDS:
            setattr(
                diagramData,
                fname,
                DiagramData.apply_local_changes(
                    getattr(diagramData, fname),
                    openSnapshot.get(fname, []),
                    localData.get(fname, []),
                ),
            )
        # Metadata
        diagramData.uuid = localData.get("uuid")
        diagramData.name = localData.get("name")
        diagramData.tags = localData.get("tags", [])
        diagramData.loggedDateTime = localData.get("loggedDateTime", [])
        diagramData.masterKey = localData.get("masterKey")
        diagramData.alias = localData.get("alias")
        diagramData.version = localData.get("version")
        diagramData.versionCompat = localData.get("versionCompat")
        diagramData.lastItemId = max(
            diagramData.lastItemId, localData.get("lastItemId", 0)
        )
        # UI flags
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

    return applyChange


def _row_bytes(diagram_id):
    db.session.expire_all()
    return Diagram.query.get(diagram_id).data


def _write_row(diagram_id, **fields):
    """Another client writing straight to the server row, newer than ours."""
    diagram = Diagram.query.get(diagram_id)
    data = pickle.loads(diagram.data) if diagram.data else {}
    data.update(fields)
    diagram.data = pickle.dumps(data)
    diagram.updated_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=1)
    db.session.commit()


def _reference_bytes(rowBytes, dataToSave, snapshotBytes):
    diagram = fe_Diagram(
        id=0,
        user_id=0,
        access_rights=[],
        created_at=datetime.datetime.utcnow(),
        data=rowBytes,
    )
    openSnapshot = pickle.loads(snapshotBytes) if snapshotBytes else {}
    applyChange = _reference_apply_change(dataToSave, openSnapshot)
    return pickle.dumps(asdict(applyChange(diagram.getDiagramData())))


def _divergent_fields(saved, expected):
    savedData, expectedData = pickle.loads(saved), pickle.loads(expected)
    return sorted(
        k
        for k in set(savedData) | set(expectedData)
        if savedData.get(k) != expectedData.get(k)
    )


def _save_and_compare(model, diagram_id, sceneBytes, baseline):
    rowBytes = model.findDiagram(diagram_id).data
    expected = _reference_bytes(rowBytes, sceneBytes, baseline or rowBytes)
    assert model.saver.save(diagram_id, sceneBytes) == True
    saved = _row_bytes(diagram_id)
    assert saved == expected, (
        f"diverged from the pre-refactor merge: {_divergent_fields(saved, expected)}"
    )


def _two_scene_views():
    """Two successive local views of one document: the second adds a person.
    Non-default UI flags make the whole metadata block load-bearing."""
    scene = Scene(
        showAliases=True,
        hideNames=True,
        hideToolBars=True,
        hideEmotionalProcess=True,
        hideEmotionColors=True,
        hideDateSlider=True,
        items=Person(name="Alice"),
    )
    first = pickle.dumps(scene.data())
    scene.addItems(Person(name="Bob"))
    return first, pickle.dumps(scene.data())


def _assert_byte_identical(model, diagram_id):
    """First save merges against the row as opened; second save merges against
    the baseline the saver kept from the first."""
    first, second = _two_scene_views()
    _save_and_compare(model, diagram_id, first, None)
    _save_and_compare(model, diagram_id, second, first)


def test_bytes_identical_plain_row(create_model):
    """C7/S1: a row carrying neither PDP nor clusters."""
    model = create_model()
    diagram_id = model.index(0, 0).data(model.IDRole)
    _assert_byte_identical(model, diagram_id)


def test_bytes_identical_pdp_and_clusters_row(create_model):
    """C7/S1: a row carrying staged people and clusters written by Personal."""
    model = create_model()
    diagram_id = model.index(0, 0).data(model.IDRole)
    _write_row(
        diagram_id,
        pdp=SAMPLE_PDP,
        clusters=SAMPLE_CLUSTERS,
        clusterCacheKey="cache-abc",
        lastItemId=5000,
        readOnly=True,
        hideSARFGraphics=False,
        scaleFactor=1.5,
    )
    model.syncDiagramFromServer(diagram_id)
    _assert_byte_identical(model, diagram_id)


def test_bytes_identical_legacy_row(create_model):
    """C7/S1: a row whose pickle carries top-level keys DiagramData no longer
    has. Both paths drop them, so the gate is equality, not preservation."""
    model = create_model()
    diagram_id = model.index(0, 0).data(model.IDRole)
    _write_row(diagram_id, **LEGACY_KEYS)
    model.syncDiagramFromServer(diagram_id)
    _assert_byte_identical(model, diagram_id)

    assert not set(LEGACY_KEYS) & set(pickle.loads(_row_bytes(diagram_id)))


def test_baseline_survives_diagram_cache_swap(create_model):
    """C7: the poll replaces the cached Diagram object between saves. A
    baseline stored on that object is lost, and the next save reads another
    client's person as a deletion."""
    model = create_model()
    diagram_id = model.index(0, 0).data(model.IDRole)

    scene = Scene(items=Person(name="Mine"))
    sceneBytes = pickle.dumps(scene.data())
    model.setData(model.index(0, 0), sceneBytes, role=model.DiagramDataRole)

    cached = model.findDiagram(diagram_id)
    ours = pickle.loads(_row_bytes(diagram_id))["people"]
    _write_row(
        diagram_id, people=ours + [{"id": 9001, "name": "Theirs", "kind": "Person"}]
    )
    model.syncDiagramFromServer(diagram_id)
    assert model.findDiagram(diagram_id) is not cached

    model.setData(model.index(0, 0), sceneBytes, role=model.DiagramDataRole)
    names = [p.get("name") for p in pickle.loads(_row_bytes(diagram_id))["people"]]
    assert "Theirs" in names
    assert "Mine" in names


def test_saver_preserves_server_pdp_and_clusters(create_model):
    """Existing-behaviour lock: Personal-owned fields survive a save driven
    through a directly constructed saver."""
    model = create_model()
    diagram_id = model.index(0, 0).data(model.IDRole)
    _write_row(
        diagram_id,
        pdp=SAMPLE_PDP,
        clusters=SAMPLE_CLUSTERS,
        clusterCacheKey="cache-abc",
    )
    model.syncDiagramFromServer(diagram_id)

    saver = DiagramSaver(model.session, model)
    scene = Scene(items=Person(name="Bob"))
    assert saver.save(diagram_id, pickle.dumps(scene.data())) == True

    row = pickle.loads(_row_bytes(diagram_id))
    assert [p["name"] for p in row["pdp"]["people"]] == ["Ana", "Ben", "Cyd"]
    assert row["clusters"] == SAMPLE_CLUSTERS
    assert row["clusterCacheKey"] == "cache-abc"
    assert "Bob" in [p.get("name") for p in row["people"]]


def _save_one(model, diagram_id):
    sceneBytes = pickle.dumps(Scene(items=Person(name="Alice")).data())
    assert model.saver.save(diagram_id, sceneBytes) == True
    return sceneBytes


def test_saver_survives_setSession(create_model):
    """C7: re-applying a session must not swap the saver out from under a
    caller holding it, nor reset the baselines it has accumulated."""
    model = create_model()
    diagram_id = model.index(0, 0).data(model.IDRole)
    saver = model.saver
    sceneBytes = _save_one(model, diagram_id)

    model.setSession(model.session)
    assert model.saver is saver
    assert model.saver._baselines[diagram_id] == sceneBytes


def test_baseline_survives_index_prune(create_model, server_response):
    """C7: a diagram dropping out of an index response is not a user delete.
    Discarding its baseline would make the next save read another client's
    work as deletions."""
    model = create_model()
    diagram_id = model.index(0, 0).data(model.IDRole)
    sceneBytes = _save_one(model, diagram_id)

    with server_response("/v1/diagrams", body=pickle.dumps([])):
        model.update()
        assert util.wait(model.updateFinished) == True
    assert model.findDiagram(diagram_id) is None
    assert model.saver._baselines[diagram_id] == sceneBytes


def test_baseline_dropped_on_delete(qtbot, create_model):
    """C7: an explicit delete retires the diagram, so its baseline goes too."""
    model = create_model()
    diagram_id = model.index(0, 0).data(model.IDRole)
    _save_one(model, diagram_id)

    qtbot.clickYesAfter(lambda: model.deleteFileAtRow(0))
    assert diagram_id not in model.saver._baselines
