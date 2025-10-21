"""
LLM-based auto-arrange engine for family diagrams.

Uses an LLM to intelligently rearrange selected people in a family diagram
based on their relationships, current positions, and sizes.
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict

from pkdiagram.pyqt import (
    pyqtSlot,
    pyqtSignal,
    QObject,
    QNetworkRequest,
    QPointF,
)
from pkdiagram.scene import Scene, Person, Marriage
from pkdiagram import util


_log = logging.getLogger(__name__)


@dataclass
class PersonState:
    """State of a single person in the diagram."""

    id: str  # Person's unique ID
    x: float  # X coordinate in scene
    y: float  # Y coordinate in scene
    size: int  # Person size (affects bounding rect scale)
    width: float  # Calculated bounding rect width
    height: float  # Calculated bounding rect height
    name: str  # Person's name (for LLM context)
    gender: str  # 'male', 'female', or 'person'
    selected: bool  # Whether this person is selected for rearrangement
    is_married_to: Optional[str] = None  # ID of spouse if married
    children_ids: List[str] = None  # IDs of children
    parent_ids: List[str] = None  # IDs of parents

    def __post_init__(self):
        if self.children_ids is None:
            self.children_ids = []
        if self.parent_ids is None:
            self.parent_ids = []


@dataclass
class ArrangeRequest:
    """Request to LLM for auto-arrangement."""

    people: List[PersonState]
    session_token: str


# System prompt for the LLM
SYSTEM_PROMPT = """You are an expert at arranging family diagrams with beautiful, readable layouts.

You will receive a JSON description of people in a family diagram with:
- Their current x,y positions (floating point coordinates)
- Their size and bounding rectangle dimensions
- Their relationships (marriages, parent-child)
- Whether they are selected for rearrangement

Your task: Rearrange ONLY the selected people to create a clean, well-organized layout.

**Critical Rules:**
1. ONLY move people where "selected": true - NEVER change positions of unselected people
2. Keep married couples horizontally adjacent (male typically left, female right)
3. Position children below their parents
4. Use proper spacing based on person sizes (use their width/height dimensions)
5. Minimize line crossings for marriage and parent-child connections
6. Maintain generational levels (grandparents above parents above children)
7. Respect unselected people as "anchors" - arrange selected people relative to them

**Output Format:**
Return ONLY a JSON object mapping person IDs to their new x,y coordinates:
```json
{
  "person_id_1": {"x": 123.5, "y": 456.7},
  "person_id_2": {"x": 234.6, "y": 456.7},
  "person_id_3": {"x": 160.0, "y": 340.0}
}
```

**Important:**
- Use precise floating-point coordinates
- Only include selected people in your response
- Consider the visual flow: top to bottom = older to younger generation
- Use the person's width/height to calculate appropriate spacing
- Aim for symmetry and balance in the layout
"""


def _get_gender_string(person: Person) -> str:
    """Convert person gender to string."""
    if person.gender() == util.PERSON_KIND_MALE:
        return "male"
    elif person.gender() == util.PERSON_KIND_FEMALE:
        return "female"
    else:
        return "person"


def _build_diagram_state(scene: Scene) -> List[PersonState]:
    """Build the diagram state from the scene."""
    people = scene.people()
    person_states = []

    # Build marriage map
    marriage_map = {}  # person_id -> spouse_id
    for marriage in scene.marriages():
        personA = marriage.personA()
        personB = marriage.personB()
        if personA and personB:
            marriage_map[personA.id] = personB.id
            marriage_map[personB.id] = personA.id

    # Build parent-child maps
    children_map = {}  # person_id -> [child_ids]
    parent_map = {}  # person_id -> [parent_ids]

    for person in people:
        children_map[person.id] = []

    for person in people:
        if person.childOf and person.childOf.marriage():
            marriage = person.childOf.marriage()
            personA = marriage.personA()
            personB = marriage.personB()

            if personA:
                children_map.setdefault(personA.id, []).append(person.id)
                parent_map.setdefault(person.id, []).append(personA.id)
            if personB:
                children_map.setdefault(personB.id, []).append(person.id)
                parent_map.setdefault(person.id, []).append(personB.id)

    # Build person states
    for person in people:
        pos = person.scenePos()
        size = person.size()
        rect = util.personRectForSize(size)

        state = PersonState(
            id=person.id,
            x=pos.x(),
            y=pos.y(),
            size=size,
            width=rect.width(),
            height=rect.height(),
            name=person.name() or f"Person_{person.id}",
            gender=_get_gender_string(person),
            selected=person.isSelected(),
            is_married_to=marriage_map.get(person.id),
            children_ids=children_map.get(person.id, []),
            parent_ids=parent_map.get(person.id, []),
        )
        person_states.append(state)

    return person_states


class AutoArrangeEngine(QObject):
    """
    LLM-based auto-arrange engine.
    Sends diagram state to backend LLM service and applies returned positions.
    """

    requestSent = pyqtSignal()
    responseReceived = pyqtSignal(int, arguments=["numPeopleArranged"])
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    def __init__(self, session):
        super().__init__()
        self._session = session
        self._scene: Scene = None

    def setScene(self, scene: Scene):
        self._scene = scene

    @pyqtSlot()
    def arrange(self):
        """Trigger auto-arrangement of selected people."""
        self._arrange()

    def _arrange(self):
        """
        Internal arrange method (mockable for testing).
        """
        if not self._scene:
            _log.warning("No scene set for auto-arrange")
            return

        selected_people = self._scene.selectedPeople()
        if len(selected_people) < 2:
            _log.info("Need at least 2 selected people for auto-arrange")
            return

        # Build diagram state
        people_states = _build_diagram_state(self._scene)

        # Prepare request
        request_data = {
            "people": [asdict(p) for p in people_states],
            "session": self._session.token,
            "system_prompt": SYSTEM_PROMPT,
        }

        def onSuccess(data):
            """Handle successful LLM response."""
            try:
                # Parse response - data is the direct dictionary mapping person_id -> {x, y}
                if isinstance(data, str):
                    positions = json.loads(data)
                else:
                    positions = data

                # Apply positions with undo support
                person_map = {p.id: p for p in self._scene.people()}
                num_arranged = 0

                with self._scene.macro("AI Arrange", undo=True):
                    for person_id, pos_data in positions.items():
                        person = person_map.get(person_id)
                        if person and person.isSelected():
                            new_pos = QPointF(pos_data["x"], pos_data["y"])
                            person.setItemPos(new_pos, undo=True)
                            num_arranged += 1
                            _log.debug(f"Arranged {person.name()} to {new_pos}")

                _log.info(f"Auto-arranged {num_arranged} people via LLM")
                self.responseReceived.emit(num_arranged)

            except Exception as e:
                _log.error(f"Failed to parse LLM response: {e}", exc_info=True)
                self.serverError.emit(f"Failed to parse response: {str(e)}")

        def onError():
            """Handle request error."""
            if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
                self.serverDown.emit()
            else:
                error_msg = reply.errorString()
                _log.error(f"Auto-arrange request failed: {error_msg}")
                self.serverError.emit(error_msg)

        # Send request to backend
        reply = self._session.server().nonBlockingRequest(
            "POST",
            "/copilot/auto-arrange",
            data=request_data,
            headers={"Content-Type": "application/json"},
            error=onError,
            success=onSuccess,
        )

        self._session.track("AutoArrangeEngine.arrange")
        self.requestSent.emit()
