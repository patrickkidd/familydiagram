import pytest
from unittest.mock import MagicMock, patch

from btcopilot.schema import EventKind, VariableShift
from pkdiagram.pyqt import QDateTime, QDate
from pkdiagram.scene import Scene, Person, Event
from pkdiagram.personal.clustermodel import ClusterModel


@pytest.fixture
def session():
    mock = MagicMock()
    mock.server.return_value = MagicMock()
    return mock


@pytest.fixture
def clusterModel(session):
    model = ClusterModel(session)
    yield model
    model.deinit()


def test_init(clusterModel):
    assert clusterModel.clusters == []
    assert clusterModel.count == 0
    assert clusterModel.hasClusters == False
    assert clusterModel.detecting == False
    assert clusterModel.selectedClusterId == ""


def test_scene_assignment(clusterModel, scene):
    clusterModel.scene = scene
    assert clusterModel.scene == scene


def test_scene_clears_clusters(clusterModel, scene):
    clusterModel._clusters = [{"id": "c1", "title": "Test"}]
    clusterModel._eventToCluster = {1: "c1"}
    clusterModel.scene = scene
    assert clusterModel.clusters == []
    assert clusterModel.count == 0


def test_diagram_id_assignment(clusterModel):
    clusterModel.diagramId = 123
    assert clusterModel.diagramId == 123


def test_select_cluster(clusterModel):
    clusterModel._clusters = [
        {"id": "c1", "title": "Test Cluster", "eventIds": [1, 2]}
    ]
    clusterModel.selectCluster("c1")
    assert clusterModel.selectedClusterId == "c1"


def test_select_cluster_clears_selection(clusterModel):
    clusterModel._clusters = [
        {"id": "c1", "title": "Test Cluster", "eventIds": [1, 2]}
    ]
    clusterModel.selectCluster("c1")
    clusterModel.selectCluster("")
    assert clusterModel.selectedClusterId == ""


def test_cluster_for_event(clusterModel):
    clusterModel._clusters = [{"id": "c1", "title": "Test", "eventIds": [1, 2]}]
    clusterModel._eventToCluster = {1: "c1", 2: "c1"}
    assert clusterModel.clusterForEvent(1) == "c1"
    assert clusterModel.clusterForEvent(2) == "c1"
    assert clusterModel.clusterForEvent(3) == ""


def test_cluster_by_id(clusterModel):
    clusterModel._clusters = [
        {"id": "c1", "title": "First"},
        {"id": "c2", "title": "Second"},
    ]
    result = clusterModel.clusterById("c1")
    assert result["title"] == "First"
    result = clusterModel.clusterById("c2")
    assert result["title"] == "Second"
    result = clusterModel.clusterById("c3")
    assert result == {}


def test_cluster_at(clusterModel):
    clusterModel._clusters = [
        {"id": "c1", "title": "First"},
        {"id": "c2", "title": "Second"},
    ]
    assert clusterModel.clusterAt(0)["title"] == "First"
    assert clusterModel.clusterAt(1)["title"] == "Second"
    assert clusterModel.clusterAt(2) == {}
    assert clusterModel.clusterAt(-1) == {}


def test_events_in_cluster(clusterModel):
    clusterModel._clusters = [{"id": "c1", "title": "Test", "eventIds": [1, 2, 3]}]
    result = clusterModel.eventsInCluster("c1")
    assert result == [1, 2, 3]
    result = clusterModel.eventsInCluster("c2")
    assert result == []


def test_build_event_mapping(clusterModel):
    clusterModel._clusters = [
        {"id": "c1", "title": "First", "eventIds": [1, 2]},
        {"id": "c2", "title": "Second", "eventIds": [3, 4, 5]},
    ]
    clusterModel._buildEventMapping()
    assert clusterModel._eventToCluster == {
        1: "c1",
        2: "c1",
        3: "c2",
        4: "c2",
        5: "c2",
    }


def test_detect_requires_scene(clusterModel, session):
    clusterModel.diagramId = 123
    clusterModel.detect()
    session.server().nonBlockingRequest.assert_not_called()


def test_detect_requires_diagram_id(clusterModel, scene, session):
    clusterModel.scene = scene
    clusterModel.detect()
    session.server().nonBlockingRequest.assert_not_called()


def test_detect_with_no_events(clusterModel, scene, session):
    clusterModel.scene = scene
    clusterModel.diagramId = 123
    clusterModel.detect()
    assert clusterModel.clusters == []
    session.server().nonBlockingRequest.assert_not_called()


def test_detect_with_events(clusterModel, scene, session):
    person = Person()
    scene.addItem(person)
    person.setName("Test Person")

    dt = QDateTime(QDate(2024, 1, 15))
    event = Event(kind=EventKind.Shift, person=person, dateTime=dt)
    event.setDescription("Test event")
    event.setSymptom(VariableShift.Up)
    scene.addItem(event)

    clusterModel.scene = scene
    clusterModel.diagramId = 123

    clusterModel.detect()

    assert clusterModel.detecting == True
    session.server().nonBlockingRequest.assert_called_once()
    call_args = session.server().nonBlockingRequest.call_args
    assert call_args[0][0] == "POST"
    assert "/personal/diagrams/123/clusters" in call_args[0][1]


def test_deinit_clears_scene(clusterModel, scene):
    clusterModel.scene = scene
    clusterModel.deinit()
    assert clusterModel.scene is None


def test_set_clusters_data(clusterModel):
    clusters = [
        {"id": "c1", "title": "Test Cluster", "eventIds": [1, 2, 3]},
        {"id": "c2", "title": "Another Cluster", "eventIds": [4, 5]},
    ]
    cacheKey = "abc123"

    clusterModel.setClustersData(clusters, cacheKey)

    assert clusterModel.clusters == clusters
    assert clusterModel.cacheKey == cacheKey
    assert clusterModel.count == 2
    assert clusterModel.hasClusters == True
    assert clusterModel.clusterForEvent(1) == "c1"
    assert clusterModel.clusterForEvent(4) == "c2"


def test_clusters_detected_signal(clusterModel, scene, session):
    from unittest.mock import MagicMock

    person = Person()
    scene.addItem(person)
    person.setName("Test Person")

    dt = QDateTime(QDate(2024, 1, 15))
    event = Event(kind=EventKind.Shift, person=person, dateTime=dt)
    event.setDescription("Test event")
    event.setSymptom(VariableShift.Up)
    scene.addItem(event)

    clusterModel.scene = scene
    clusterModel.diagramId = 123

    signal_handler = MagicMock()
    clusterModel.clustersDetected.connect(signal_handler)

    clusterModel.detect()

    # Signal not emitted during detection (only after response)
    signal_handler.assert_not_called()


def test_detect_skips_when_cache_key_unchanged(clusterModel, scene, session):
    """T7-12: detect() is idempotent — skips re-detection when events haven't changed."""
    person = Person()
    scene.addItem(person)
    person.setName("Test Person")

    dt = QDateTime(QDate(2024, 1, 15))
    event = Event(kind=EventKind.Shift, person=person, dateTime=dt)
    event.setDescription("Test event")
    event.setSymptom(VariableShift.Up)
    scene.addItem(event)

    clusterModel.scene = scene
    clusterModel.diagramId = 123

    # First detect — should make network request
    clusterModel.detect()
    assert session.server().nonBlockingRequest.call_count == 1

    # Simulate successful response by setting cacheKey
    events_data = []
    for e in sorted(scene.events(onlyDated=True), key=lambda e: e.dateTime().toMSecsSinceEpoch()):
        event_dict = {
            "id": e.id,
            "dateTime": e.dateTime().toString("yyyy-MM-dd"),
            "symptom": VariableShift.Up.value if e.symptom() else None,
            "anxiety": None,
            "relationship": None,
            "functioning": None,
        }
        events_data.append(event_dict)
    cache_key = ClusterModel._computeLocalCacheKey(events_data)

    # Simulate detection completion
    clusterModel._detecting = False
    clusterModel._cacheKey = cache_key
    clusterModel._clusters = [{"id": "c1", "title": "Test", "eventIds": [event.id]}]

    # Second detect — should skip (cache key unchanged)
    clusterModel.detect()
    assert session.server().nonBlockingRequest.call_count == 1  # Still 1, not 2


def test_show_clusters_property(clusterModel):
    """T7-12: showClusters property toggles and persists."""
    assert clusterModel.showClusters == True

    signal_handler = MagicMock()
    clusterModel.showClustersChanged.connect(signal_handler)

    clusterModel.setShowClusters(False)
    assert clusterModel.showClusters == False
    signal_handler.assert_called_once()

    signal_handler.reset_mock()
    clusterModel.setShowClusters(True)
    assert clusterModel.showClusters == True
    signal_handler.assert_called_once()


def test_show_clusters_no_signal_on_same_value(clusterModel):
    """T7-12: No signal emitted when setting showClusters to same value."""
    signal_handler = MagicMock()
    clusterModel.showClustersChanged.connect(signal_handler)

    clusterModel.setShowClusters(True)  # Already True
    signal_handler.assert_not_called()


def test_show_clusters_persisted_in_cache(clusterModel, tmp_path):
    """T7-12: showClusters state persists across cache save/load."""
    import json

    clusterModel.setCacheDir(tmp_path)
    clusterModel._diagramId = 123

    # Set to False and save
    clusterModel.setShowClusters(False)
    clusterModel._clusters = [{"id": "c1", "title": "Test", "eventIds": [1]}]
    clusterModel._saveCache()

    # Verify file contents
    cache_file = tmp_path / "clusters_123.json"
    assert cache_file.exists()
    data = json.loads(cache_file.read_text())
    assert data["showClusters"] == False

    # Create new model and load cache
    new_model = ClusterModel(MagicMock())
    new_model.setCacheDir(tmp_path)
    new_model.diagramId = 123
    assert new_model.showClusters == False
    new_model.deinit()
