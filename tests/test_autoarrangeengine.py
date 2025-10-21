"""
Tests for LLM-based auto-arrange functionality.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from pkdiagram.pyqt import QPointF
from pkdiagram.scene import Scene, Person, Marriage
from pkdiagram.models.autoarrangeengine import (
    AutoArrangeEngine,
    PersonState,
    _build_diagram_state,
    _get_gender_string,
    SYSTEM_PROMPT,
)
from pkdiagram import util


def test_get_gender_string():
    """Test gender string conversion."""
    scene = Scene()
    male = Person(gender=util.PERSON_KIND_MALE)
    female = Person(gender=util.PERSON_KIND_FEMALE)
    person = Person(gender=util.PERSON_KIND_PERSON)

    scene.addItems(male, female, person)

    assert _get_gender_string(male) == "male"
    assert _get_gender_string(female) == "female"
    assert _get_gender_string(person) == "person"


def test_person_state_creation():
    """Test PersonState dataclass creation."""
    state = PersonState(
        id="test_123",
        x=100.0,
        y=200.0,
        size=3,
        width=80.0,
        height=80.0,
        name="Test Person",
        gender="male",
        selected=True,
        is_married_to="test_456",
        children_ids=["test_789"],
        parent_ids=[],
    )

    assert state.id == "test_123"
    assert state.x == 100.0
    assert state.y == 200.0
    assert state.selected is True
    assert state.is_married_to == "test_456"
    assert len(state.children_ids) == 1


def test_build_diagram_state_simple():
    """Test building diagram state from scene with simple people."""
    scene = Scene()
    person1 = Person(pos=QPointF(100, 200), size=3)
    person2 = Person(pos=QPointF(300, 400), size=3)

    scene.addItems(person1, person2)
    person1.setSelected(True)

    states = _build_diagram_state(scene)

    assert len(states) == 2
    assert any(s.id == person1.id and s.selected for s in states)
    assert any(s.id == person2.id and not s.selected for s in states)


def test_build_diagram_state_with_marriage():
    """Test building diagram state with married couple."""
    scene = Scene()

    male = Person(gender=util.PERSON_KIND_MALE, pos=QPointF(100, 200))
    female = Person(gender=util.PERSON_KIND_FEMALE, pos=QPointF(200, 200))
    marriage = Marriage(personA=male, personB=female)

    scene.addItems(male, female, marriage)

    states = _build_diagram_state(scene)

    male_state = next(s for s in states if s.id == male.id)
    female_state = next(s for s in states if s.id == female.id)

    assert male_state.is_married_to == female.id
    assert female_state.is_married_to == male.id
    assert male_state.gender == "male"
    assert female_state.gender == "female"


def test_build_diagram_state_with_children():
    """Test building diagram state with parent-child relationships."""
    scene = Scene()

    father = Person(gender=util.PERSON_KIND_MALE, pos=QPointF(100, 100))
    mother = Person(gender=util.PERSON_KIND_FEMALE, pos=QPointF(200, 100))
    child = Person(pos=QPointF(150, 300))

    marriage = Marriage(personA=father, personB=mother)
    scene.addItems(father, mother, child, marriage)

    # Set parents
    child.setParents(marriage)

    states = _build_diagram_state(scene)

    father_state = next(s for s in states if s.id == father.id)
    mother_state = next(s for s in states if s.id == mother.id)
    child_state = next(s for s in states if s.id == child.id)

    assert child.id in father_state.children_ids
    assert child.id in mother_state.children_ids
    assert father.id in child_state.parent_ids
    assert mother.id in child_state.parent_ids


def test_auto_arrange_engine_creation():
    """Test creating AutoArrangeEngine."""
    mock_session = Mock()
    mock_session.token = "test_token"

    engine = AutoArrangeEngine(mock_session)
    assert engine._session == mock_session


def test_auto_arrange_engine_set_scene():
    """Test setting scene on engine."""
    mock_session = Mock()
    scene = Scene()

    engine = AutoArrangeEngine(mock_session)
    engine.setScene(scene)

    assert engine._scene == scene


def test_auto_arrange_engine_no_selected():
    """Test that engine doesn't send request with < 2 selected."""
    mock_session = Mock()
    scene = Scene()

    person1 = Person()
    scene.addItem(person1)

    engine = AutoArrangeEngine(mock_session)
    engine.setScene(scene)

    # Should not make request
    engine.arrange()

    # Verify no request was made
    mock_session.server.assert_not_called()


@patch("pkdiagram.models.autoarrangeengine._build_diagram_state")
def test_auto_arrange_engine_sends_request(mock_build_state):
    """Test that engine sends proper request to server."""
    # Setup mocks
    mock_session = Mock()
    mock_session.token = "test_session_token"
    mock_server = Mock()
    mock_session.server.return_value = mock_server
    mock_session.track = Mock()

    scene = Scene()
    person1 = Person(pos=QPointF(0, 0))
    person2 = Person(pos=QPointF(100, 0))
    scene.addItems(person1, person2)

    person1.setSelected(True)
    person2.setSelected(True)

    # Mock diagram state
    mock_build_state.return_value = [
        PersonState(
            id=person1.id,
            x=0.0,
            y=0.0,
            size=3,
            width=80.0,
            height=80.0,
            name="Person 1",
            gender="person",
            selected=True,
        ),
        PersonState(
            id=person2.id,
            x=100.0,
            y=0.0,
            size=3,
            width=80.0,
            height=80.0,
            name="Person 2",
            gender="person",
            selected=True,
        ),
    ]

    engine = AutoArrangeEngine(mock_session)
    engine.setScene(scene)

    # Trigger arrange
    engine.arrange()

    # Verify request was made
    mock_server.nonBlockingRequest.assert_called_once()

    # Check request parameters
    call_args = mock_server.nonBlockingRequest.call_args
    assert call_args[0][0] == "POST"  # verb
    assert call_args[0][1] == "/copilot/auto-arrange"  # path
    assert call_args[1]["headers"]["Content-Type"] == "application/json"

    # Check request data
    request_data = call_args[1]["data"]
    assert request_data["session"] == "test_session_token"
    assert "people" in request_data
    assert len(request_data["people"]) == 2
    assert request_data["system_prompt"] == SYSTEM_PROMPT


def test_system_prompt_exists():
    """Test that system prompt is defined and reasonable."""
    assert len(SYSTEM_PROMPT) > 100
    assert "selected" in SYSTEM_PROMPT.lower()
    assert "json" in SYSTEM_PROMPT.lower()
    assert "positions" in SYSTEM_PROMPT.lower()


def test_auto_arrange_engine_handles_response():
    """Test that engine properly handles LLM response."""
    mock_session = Mock()
    mock_session.token = "test_token"
    mock_session.track = Mock()

    scene = Scene()
    person1 = Person(pos=QPointF(0, 0))
    person2 = Person(pos=QPointF(100, 0))
    scene.addItems(person1, person2)

    person1.setSelected(True)
    person2.setSelected(True)

    engine = AutoArrangeEngine(mock_session)
    engine.setScene(scene)

    # Create mock response - simplified format without "positions" wrapper
    mock_response = {
        person1.id: {"x": 50.0, "y": 100.0},
        person2.id: {"x": 150.0, "y": 100.0},
    }

    # Mock the macro context manager
    with patch.object(scene, "macro") as mock_macro:
        mock_macro.return_value.__enter__ = Mock()
        mock_macro.return_value.__exit__ = Mock()

        # Trigger success callback directly
        engine._arrange()
        call_args = mock_session.server().nonBlockingRequest.call_args
        success_callback = call_args[1]["success"]

        # Call success callback with mock response
        success_callback(mock_response)

        # Verify positions were updated
        # (In real scenario, setItemPos would be called with undo=True)
        mock_macro.assert_called_once_with("AI Arrange", undo=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
