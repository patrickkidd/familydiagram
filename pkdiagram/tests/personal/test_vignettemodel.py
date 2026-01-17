import pytest
from unittest.mock import MagicMock, patch

from btcopilot.schema import EventKind, VariableShift
from pkdiagram.pyqt import QDateTime, QDate
from pkdiagram.scene import Scene, Person, Event
from pkdiagram.personal.vignettemodel import VignetteModel


@pytest.fixture
def session():
    mock = MagicMock()
    mock.server.return_value = MagicMock()
    return mock


@pytest.fixture
def vignetteModel(session):
    model = VignetteModel(session)
    yield model
    model.deinit()


def test_init(vignetteModel):
    assert vignetteModel.vignettes == []
    assert vignetteModel.count == 0
    assert vignetteModel.hasVignettes == False
    assert vignetteModel.detecting == False
    assert vignetteModel.selectedVignetteId == ""


def test_scene_assignment(vignetteModel, scene):
    vignetteModel.scene = scene
    assert vignetteModel.scene == scene


def test_scene_clears_vignettes(vignetteModel, scene):
    vignetteModel._vignettes = [{"id": "v1", "title": "Test"}]
    vignetteModel._eventToVignette = {1: "v1"}
    vignetteModel.scene = scene
    assert vignetteModel.vignettes == []
    assert vignetteModel.count == 0


def test_diagram_id_assignment(vignetteModel):
    vignetteModel.diagramId = 123
    assert vignetteModel.diagramId == 123


def test_select_vignette(vignetteModel):
    vignetteModel._vignettes = [
        {"id": "v1", "title": "Test Vignette", "eventIds": [1, 2]}
    ]
    vignetteModel.selectVignette("v1")
    assert vignetteModel.selectedVignetteId == "v1"


def test_select_vignette_clears_selection(vignetteModel):
    vignetteModel._vignettes = [
        {"id": "v1", "title": "Test Vignette", "eventIds": [1, 2]}
    ]
    vignetteModel.selectVignette("v1")
    vignetteModel.selectVignette("")
    assert vignetteModel.selectedVignetteId == ""


def test_vignette_for_event(vignetteModel):
    vignetteModel._vignettes = [{"id": "v1", "title": "Test", "eventIds": [1, 2]}]
    vignetteModel._eventToVignette = {1: "v1", 2: "v1"}
    assert vignetteModel.vignetteForEvent(1) == "v1"
    assert vignetteModel.vignetteForEvent(2) == "v1"
    assert vignetteModel.vignetteForEvent(3) == ""


def test_vignette_by_id(vignetteModel):
    vignetteModel._vignettes = [
        {"id": "v1", "title": "First"},
        {"id": "v2", "title": "Second"},
    ]
    result = vignetteModel.vignetteById("v1")
    assert result["title"] == "First"
    result = vignetteModel.vignetteById("v2")
    assert result["title"] == "Second"
    result = vignetteModel.vignetteById("v3")
    assert result == {}


def test_vignette_at(vignetteModel):
    vignetteModel._vignettes = [
        {"id": "v1", "title": "First"},
        {"id": "v2", "title": "Second"},
    ]
    assert vignetteModel.vignetteAt(0)["title"] == "First"
    assert vignetteModel.vignetteAt(1)["title"] == "Second"
    assert vignetteModel.vignetteAt(2) == {}
    assert vignetteModel.vignetteAt(-1) == {}


def test_events_in_vignette(vignetteModel):
    vignetteModel._vignettes = [{"id": "v1", "title": "Test", "eventIds": [1, 2, 3]}]
    result = vignetteModel.eventsInVignette("v1")
    assert result == [1, 2, 3]
    result = vignetteModel.eventsInVignette("v2")
    assert result == []


def test_build_event_mapping(vignetteModel):
    vignetteModel._vignettes = [
        {"id": "v1", "title": "First", "eventIds": [1, 2]},
        {"id": "v2", "title": "Second", "eventIds": [3, 4, 5]},
    ]
    vignetteModel._buildEventMapping()
    assert vignetteModel._eventToVignette == {
        1: "v1",
        2: "v1",
        3: "v2",
        4: "v2",
        5: "v2",
    }


def test_detect_requires_scene(vignetteModel, session):
    vignetteModel.diagramId = 123
    vignetteModel.detect()
    session.server().nonBlockingRequest.assert_not_called()


def test_detect_requires_diagram_id(vignetteModel, scene, session):
    vignetteModel.scene = scene
    vignetteModel.detect()
    session.server().nonBlockingRequest.assert_not_called()


def test_detect_with_no_events(vignetteModel, scene, session):
    vignetteModel.scene = scene
    vignetteModel.diagramId = 123
    vignetteModel.detect()
    assert vignetteModel.vignettes == []
    session.server().nonBlockingRequest.assert_not_called()


def test_detect_with_events(vignetteModel, scene, session):
    person = Person()
    scene.addItem(person)
    person.setName("Test Person")

    dt = QDateTime(QDate(2024, 1, 15))
    event = Event(kind=EventKind.Shift, person=person, dateTime=dt)
    event.setDescription("Test event")
    event.setSymptom(VariableShift.Up)
    scene.addItem(event)

    vignetteModel.scene = scene
    vignetteModel.diagramId = 123

    vignetteModel.detect()

    assert vignetteModel.detecting == True
    session.server().nonBlockingRequest.assert_called_once()
    call_args = session.server().nonBlockingRequest.call_args
    assert call_args[0][0] == "POST"
    assert "/personal/diagrams/123/vignettes" in call_args[0][1]


def test_deinit_clears_scene(vignetteModel, scene):
    vignetteModel.scene = scene
    vignetteModel.deinit()
    assert vignetteModel.scene is None


def test_set_vignettes_data(vignetteModel):
    vignettes = [
        {"id": "v1", "title": "Test Vignette", "eventIds": [1, 2, 3]},
        {"id": "v2", "title": "Another Vignette", "eventIds": [4, 5]},
    ]
    cacheKey = "abc123"

    vignetteModel.setVignettesData(vignettes, cacheKey)

    assert vignetteModel.vignettes == vignettes
    assert vignetteModel.cacheKey == cacheKey
    assert vignetteModel.count == 2
    assert vignetteModel.hasVignettes == True
    assert vignetteModel.vignetteForEvent(1) == "v1"
    assert vignetteModel.vignetteForEvent(4) == "v2"


def test_vignettes_detected_signal(vignetteModel, scene, session):
    from unittest.mock import MagicMock

    person = Person()
    scene.addItem(person)
    person.setName("Test Person")

    dt = QDateTime(QDate(2024, 1, 15))
    event = Event(kind=EventKind.Shift, person=person, dateTime=dt)
    event.setDescription("Test event")
    event.setSymptom(VariableShift.Up)
    scene.addItem(event)

    vignetteModel.scene = scene
    vignetteModel.diagramId = 123

    signal_handler = MagicMock()
    vignetteModel.vignettesDetected.connect(signal_handler)

    vignetteModel.detect()

    # Signal not emitted during detection (only after response)
    signal_handler.assert_not_called()
