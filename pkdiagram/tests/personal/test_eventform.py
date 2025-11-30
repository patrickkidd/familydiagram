import base64
import json
import pickle
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from btcopilot.schema import (
    EventKind,
    VariableShift,
    DiagramData,
    PDP,
    Person as SchemaPerson,
    Event as SchemaEvent,
    asdict as schema_asdict,
)
from pkdiagram.pyqt import QApplication
from pkdiagram import util
from pkdiagram.scene import Person, Event
from pkdiagram.server_types import Diagram


pytestmark = [
    pytest.mark.component("Personal"),
    pytest.mark.depends_on("EventForm"),
]

START_DATETIME = util.Date(2001, 1, 1, 6, 7)


def _createBlockingRequestMock(diagram):
    captured = {"payload": None}

    def blockingRequest(verb, endpoint, data=None, bdata=None, headers=None, **kwargs):
        if verb == "PUT" and "/personal/diagrams/" in endpoint:
            captured["payload"] = data
        response = MagicMock()
        response.status_code = 200
        response.body = json.dumps({"version": diagram.version + 1}).encode("utf-8")
        return response

    return blockingRequest, captured


def _extractDiagramDataFromPayload(payload):
    encodedData = payload["data"]
    pickledData = base64.b64decode(encodedData)
    return pickle.loads(pickledData)


def test_open_and_close_event_form(personalApp):
    root = personalApp._engine.rootObjects()[0]
    discussView = root.property("personalView").property("discussView")
    eventDrawer = discussView.property("eventDrawer")
    eventForm = discussView.property("eventForm")

    assert not eventDrawer.property("visible")

    discussView.showEventForm()
    util.waitALittle()
    assert eventDrawer.property("visible")

    eventForm.cancel.emit()
    util.waitUntil(lambda: not eventDrawer.property("visible"))


def test_add_event_saves_diagram(personalApp):
    scene = personalApp.scene
    person = scene.addItem(Person(name="John", lastName="Doe"))

    root = personalApp._engine.rootObjects()[0]
    discussView = root.property("personalView").property("discussView")
    eventForm = discussView.property("eventForm")

    discussView.showEventForm()
    QApplication.processEvents()
    util.waitALittle()

    eventForm.initWithPerson(person.id)
    eventForm.setKind(EventKind.Shift.value)
    eventForm.setProperty("description", "Felt stressed")
    eventForm.setProperty("symptom", VariableShift.Down.value)
    eventForm.property("startDateButtons").setProperty("dateTime", START_DATETIME)

    server = personalApp.session.server()
    blockingRequestMock, captured = _createBlockingRequestMock(personalApp.diagram)
    with patch.object(server, "blockingRequest", blockingRequestMock):
        eventForm.done.emit()
        QApplication.processEvents()

    events = scene.eventsFor(person)
    assert len(events) == 1
    assert events[0].kind() == EventKind.Shift
    assert events[0].person() == person

    assert captured["payload"] is not None
    serverData = _extractDiagramDataFromPayload(captured["payload"])
    assert len(serverData["events"]) == 1
    assert serverData["events"][0]["description"] == "Felt stressed"


def test_edit_event_saves_diagram(personalApp):
    scene = personalApp.scene
    person = scene.addItem(Person(name="Jane", lastName="Doe"))
    event = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            dateTime=START_DATETIME,
            description="Original description",
            symptom=VariableShift.Up,
        )
    )

    personalApp.eventForm.editEvents([event])
    util.waitALittle()

    root = personalApp._engine.rootObjects()[0]
    eventForm = (
        root.property("personalView").property("discussView").property("eventForm")
    )
    assert eventForm.property("isEditing")

    eventForm.setProperty("description", "Updated description")
    eventForm.setProperty("symptom", VariableShift.Down.value)

    server = personalApp.session.server()
    blockingRequestMock, captured = _createBlockingRequestMock(personalApp.diagram)
    with patch.object(server, "blockingRequest", blockingRequestMock):
        eventForm.done.emit()
        QApplication.processEvents()

    assert event.description() == "Updated description"
    assert event.symptom() == VariableShift.Down

    assert captured["payload"] is not None
    serverData = _extractDiagramDataFromPayload(captured["payload"])
    assert len(serverData["events"]) == 1
    assert serverData["events"][0]["description"] == "Updated description"


def test_save_preserves_pdp(personalApp):
    diagramData = DiagramData(
        pdp=PDP(
            people=[SchemaPerson(id=-1, name="PendingPerson")],
            events=[],
            pair_bonds=[],
        ),
        lastItemId=0,
    )
    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.now(),
        data=pickle.dumps(schema_asdict(diagramData)),
    )
    personalApp._diagram = diagram

    scene = personalApp.scene
    person = scene.addItem(Person(name="ScenePerson", lastName="Doe"))

    root = personalApp._engine.rootObjects()[0]
    discussView = root.property("personalView").property("discussView")
    eventForm = discussView.property("eventForm")

    discussView.showEventForm()
    util.waitALittle()

    eventForm.initWithPerson(person.id)
    eventForm.setKind(EventKind.Shift.value)
    eventForm.setProperty("description", "New event")
    eventForm.setProperty("symptom", VariableShift.Down.value)
    eventForm.property("startDateButtons").setProperty("dateTime", START_DATETIME)

    server = personalApp.session.server()
    blockingRequestMock, captured = _createBlockingRequestMock(diagram)
    with patch.object(server, "blockingRequest", blockingRequestMock):
        eventForm.done.emit()
        QApplication.processEvents()

    assert captured["payload"] is not None
    serverData = _extractDiagramDataFromPayload(captured["payload"])

    assert len(serverData["events"]) == 1
    assert serverData["events"][0]["description"] == "New event"

    assert "pdp" in serverData
    assert len(serverData["pdp"]["people"]) == 1
    assert serverData["pdp"]["people"][0]["name"] == "PendingPerson"
