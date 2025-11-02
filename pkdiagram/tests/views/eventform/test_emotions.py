import pytest

from btcopilot.schema import EventKind, RelationshipKind
from pkdiagram import util
from pkdiagram.scene import Person, Event
from pkdiagram.pyqt import QColor

from .test_eventform import view, START_DATETIME


DEPENDS = pytest.mark.depends_on("PersonPicker", "PeoplePicker", "DatePicker")


def test_add_emotion_color_and_notes(scene, view):
    person = scene.addItem(Person(name="John Doe"))
    target = scene.addItem(Person(name="Jane Doe"))
    scene.addEventProperty(util.ATTR_RELATIONSHIP)

    view.set_kind(EventKind.Shift)
    view.personPicker.set_existing_person(person)
    view.set_relationship(RelationshipKind.Conflict)
    view.targetsPicker.add_existing_person(target)
    view.set_description("Some description")
    view.set_startDateTime(START_DATETIME)
    view.set_color("#ff0000")
    view.set_notes("Test notes")
    view.clickSaveButton()

    event = scene.eventsFor(person)[0]
    assert event.color() == "#ff0000"
    assert event.notes() == "Test notes"

    emotions = scene.emotionsFor(event)
    assert len(emotions) == 1
    emotion = emotions[0]

    assert emotion.sourceEvent() is event
    assert emotion.color() == "#ff0000"
    assert emotion.notes() == "Test notes"
    assert emotion.prop("notes").get() == ""
    assert emotion.pen().color() == QColor("#ff0000")


def test_edit_emotion_color_and_notes(scene, view):
    person = scene.addItem(Person(name="John Doe"))
    target = scene.addItem(Person(name="Jane Doe"))

    event = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=[target],
            dateTime=START_DATETIME,
            color="#00ff00",
            notes="Original notes",
        )
    )

    emotions = scene.emotionsFor(event)
    assert len(emotions) == 1
    emotion = emotions[0]

    assert emotion.sourceEvent() is event
    assert emotion.color() == "#00ff00"
    assert emotion.notes() == "Original notes"
    assert emotion.pen().color() == QColor("#00ff00")

    view.view.editEvents(event)
    view.set_color("#ff0000")
    view.set_notes("Updated notes")
    view.clickSaveButton()

    assert event.color() == "#ff0000"
    assert event.notes() == "Updated notes"
    assert emotion.color() == "#ff0000"
    assert emotion.notes() == "Updated notes"
    assert emotion.prop("notes").get() == ""
    assert emotion.pen().color().name() == "#ff0000"
