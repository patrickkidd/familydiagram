import pytest
from unittest.mock import patch

from btcopilot.schema import EventKind, VariableShift
from pkdiagram.pyqt import QApplication
from pkdiagram import util
from pkdiagram.scene import Person, Event


pytestmark = [
    pytest.mark.component("Personal"),
    pytest.mark.depends_on("EventForm"),
]

START_DATETIME = util.Date(2001, 1, 1, 6, 7)


def test_open_and_close_event_form(personalApp):
    root = personalApp._engine.rootObjects()[0]
    discussView = root.property("personalView").property("discussView")
    eventDrawer = discussView.property("eventDrawer")
    eventForm = discussView.property("eventForm")

    assert not eventDrawer.property("visible")

    discussView.showEventForm()
    QApplication.processEvents()
    util.waitALittle()
    assert eventDrawer.property("visible")

    # Emit QML cancel signal which triggers drawer close
    eventForm.cancel.emit()
    # Wait for close animation to complete
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

    with patch.object(personalApp, "saveDiagram") as saveDiagram:
        eventForm.done.emit()
        QApplication.processEvents()
        assert saveDiagram.call_count == 1

    events = scene.eventsFor(person)
    assert len(events) == 1
    assert events[0].kind() == EventKind.Shift
    assert events[0].person() == person


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
    QApplication.processEvents()
    util.waitALittle()

    root = personalApp._engine.rootObjects()[0]
    eventForm = (
        root.property("personalView").property("discussView").property("eventForm")
    )
    assert eventForm.property("isEditing")

    eventForm.setProperty("description", "Updated description")
    eventForm.setProperty("symptom", VariableShift.Down.value)

    with patch.object(personalApp, "saveDiagram") as saveDiagram:
        eventForm.done.emit()
        QApplication.processEvents()
        assert saveDiagram.call_count == 1

    assert event.description() == "Updated description"
    assert event.symptom() == VariableShift.Down
