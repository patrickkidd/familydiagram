"""FD-336 / F-008: the model owns exactly ONE Diagram instance per id.

`syncDiagramFromServer` and `_addOrUpdateDiagram` must refresh the cached
instance in place and hand that same object back. Replacing it splits the
diagram in two: whoever holds the old object (the Scene, the id allocator)
stops seeing what the saver writes, and the client-only fields living on the
instance -- `blockEnd` above all -- are silently reset to their defaults.

Criteria: C7 (exactly one writer for a row) and D9 (a save never drops the
row's id watermark below a block this client already reserved).
"""

import datetime
import pickle

from pkdiagram.scene import Scene, Person
from pkdiagram.server_types import Diagram as fe_Diagram
from pkdiagram.serverblockallocator import ServerBlockAllocator

from btcopilot.pro.models import Diagram

from pkdiagram.tests.models.test_serverfilemanagermodel import (
    create_model,
    _other_client_write,
    _put_statuses,
    _row,
    _row_version,
)


def _first_diagram_id(model):
    return model.index(0, 0).data(model.IDRole)


def _payload(diagram_id, **overrides) -> fe_Diagram:
    """A Diagram built the way an incoming server response is built: the row's
    own fields, with the handful under test overridden."""
    payload = fe_Diagram.create(Diagram.query.get(diagram_id).as_dict())
    for name, value in overrides.items():
        setattr(payload, name, value)
    return payload


def _names(diagram) -> list:
    return [p["name"] for p in pickle.loads(diagram.data)["people"]]


def test_sync_and_update_keep_the_one_cached_instance(create_model):
    """C7: both entry points return / retain the object the model already has,
    so a caller holding it keeps seeing the current diagram."""
    model = create_model()
    diagram_id = _first_diagram_id(model)
    cached = model.findDiagram(diagram_id)

    # Nothing changed on the server: the sync still has to hand back the cached
    # object rather than the throwaway it just parsed.
    assert model.syncDiagramFromServer(diagram_id) is cached

    _other_client_write(diagram_id, people=[{"id": 1, "name": "Theirs"}])
    assert model.syncDiagramFromServer(diagram_id) is cached
    assert cached.version == _row_version(diagram_id)
    assert _names(cached) == ["Theirs"]

    fresher = _payload(
        diagram_id,
        version=cached.version + 1,
        data=pickle.dumps({"people": [{"id": 2, "name": "Newer"}]}),
        updated_at=cached.updated_at + datetime.timedelta(seconds=1),
    )
    model._addOrUpdateDiagram(fresher)
    assert model.findDiagram(diagram_id) is cached
    assert cached.version == fresher.version
    assert _names(cached) == ["Newer"]


def test_reserved_block_survives_a_refresh(create_model):
    """D9: `blockEnd` is client-only -- no server payload carries it -- so a
    refresh that replaces the instance resets it to 0 and the next save stops
    clamping the row's watermark above ids this client already handed out."""
    model = create_model()
    diagram_id = _first_diagram_id(model)
    cached = model.findDiagram(diagram_id)
    cached.blockEnd = 4242

    _other_client_write(diagram_id, people=[{"id": 1, "name": "Theirs"}])
    model.syncDiagramFromServer(diagram_id)
    assert model.findDiagram(diagram_id).blockEnd == 4242

    model._addOrUpdateDiagram(
        _payload(
            diagram_id,
            version=cached.version + 1,
            updated_at=cached.updated_at + datetime.timedelta(seconds=1),
        )
    )
    assert model.findDiagram(diagram_id).blockEnd == 4242


def test_stale_payload_does_not_regress_the_cached_instance(create_model):
    """C7: the gate is the row version. A payload that lost the race carries an
    older version however recent its clock reads, and must leave the cached
    version and blob alone."""
    model = create_model()
    diagram_id = _first_diagram_id(model)
    _other_client_write(diagram_id, people=[{"id": 1, "name": "Current"}])
    model.syncDiagramFromServer(diagram_id)

    cached = model.findDiagram(diagram_id)
    version = cached.version
    data = cached.data

    model._addOrUpdateDiagram(
        _payload(
            diagram_id,
            version=version - 1,
            data=pickle.dumps({"people": [{"id": 9, "name": "Stale"}]}),
            updated_at=cached.updated_at + datetime.timedelta(seconds=30),
        )
    )
    assert model.findDiagram(diagram_id) is cached
    assert model.findDiagram(diagram_id).version == version
    assert model.findDiagram(diagram_id).data == data


def test_first_save_after_a_reservation_does_not_conflict(create_model, monkeypatch):
    """C7/D9: MainWindow binds the allocator to whatever the open-time sync
    returned, and the saver resolves the id through the model on every save. If
    those are two objects, the reservation bumps the version on the one the
    saver never sees and the very first save burns a 409 replay -- and the
    block it reserved is not in the watermark the save writes."""
    model = create_model()
    diagram_id = _first_diagram_id(model)
    opened = model.syncDiagramFromServer(diagram_id)

    allocator = ServerBlockAllocator(opened, model.session.server(), blockSize=100)
    allocator()

    sceneBytes = pickle.dumps(Scene(items=Person(name="Alice")).data())
    with _put_statuses(monkeypatch) as statuses:
        assert (
            model.setData(model.index(0, 0), sceneBytes, role=model.DiagramDataRole)
            == True
        )
    assert statuses == [200]
    assert _row(diagram_id)["lastItemId"] >= allocator._end
    assert _row_version(diagram_id) == model.findDiagram(diagram_id).version


def test_scene_and_saver_hold_the_same_diagram(create_model):
    """C7: the Scene is handed the diagram by the file manager's sync while the
    saver resolves it out of the cache. Two objects here is the split that lets
    a save land on a row the open Scene is no longer tracking."""
    model = create_model()
    diagram_id = _first_diagram_id(model)

    scene = Scene()
    scene.setServerDiagram(model.syncDiagramFromServer(diagram_id))
    assert scene.serverDiagram() is model.findDiagram(diagram_id)
    assert model.saver.resolve(diagram_id) is scene.serverDiagram()

    _other_client_write(diagram_id, people=[{"id": 1, "name": "Theirs"}])
    model.syncDiagramFromServer(diagram_id)
    assert scene.serverDiagram() is model.findDiagram(diagram_id)
    assert scene.serverDiagram().version == _row_version(diagram_id)
