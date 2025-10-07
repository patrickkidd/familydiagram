import logging

import pytest
import mock

from pkdiagram import util
from pkdiagram.scene import Person, Marriage, EventKind, RelationshipKind
from pkdiagram.views import EventForm

from tests.views import TestEventForm

_log = logging.getLogger(__name__)


ONE_NAME = "John Doe"
START_DATETIME = util.Date(2001, 1, 1, 6, 7)
END_DATETIME = util.Date(2002, 1, 1, 6, 7)

DEPENDS = pytest.mark.depends_on("PersonPicker", "PeoplePicker", "DatePicker")


@pytest.fixture
def view(qtbot, scene, qmlEngine):
    qmlEngine.sceneModel.onEditorMode(True)
    qmlEngine.setScene(scene)
    widget = EventForm(qmlEngine)
    widget.resize(600, 1000)
    widget.setScene(scene)
    widget.show()
    qtbot.addWidget(widget)
    qtbot.waitActive(widget)
    assert widget.isShown()

    # widget.adjustFlickableHack()

    view = TestEventForm(widget)
    view.view.addEvent()
    view.item.property("addPage").setProperty("interactive", False)

    yield view

    widget.setScene(None)
    widget.hide()
    widget.deinit()


@pytest.mark.parametrize("editorMode", [True, False])
def test_init(qmlEngine, view, editorMode):
    qmlEngine.sceneModel.onEditorMode(editorMode)
    assert view.item.property("kind") == None
    assert view.kindBox.property("currentIndex") == -1
    assert view.tagsEdit.property("isDirty") == False
    assert view.tagsEdit.property("visible") == editorMode
    assert view.rootProp("tagsLabel").property("visible") == editorMode


@pytest.mark.parametrize("kind", [EventKind.Birth, EventKind.Adopted])
def test_attrs(scene, view, kind: EventKind):
    mother = scene.addItem(Person(name="Mother"))
    view.addEvent([])
    view.set_kind(kind)
    view.personPicker.set_existing_person(mother)
    view.set_startDateTime(START_DATETIME)
    view.set_location("Somewhere")
    view.set_notes("Some notes")
    view.clickSaveButton()

    child = mother.marriages[0].children[0]
    assert child.name() == None
    event = child.events()[0]
    assert event.kind() == kind
    assert event.description() == kind.name
    assert event.location() == "Somewhere"
    assert event.notes() == "Some notes"
    if kind == EventKind.Birth:
        assert child.birthDateTime() == START_DATETIME
    elif kind == EventKind.Adopted:
        assert child.adopted() == True
        assert child.adoptedDateTime() == START_DATETIME
    elif kind == EventKind.Death:
        assert child.deceased() == True
        assert child.deathDateTime() == START_DATETIME
    assert scene.currentDateTime() == START_DATETIME


def test_attrs_Death(scene, view):
    person = scene.addItem(Person(name="John Doe"))
    view.addEvent([])
    view.set_kind(EventKind.Death)
    view.personPicker.set_existing_person(person)
    view.set_startDateTime(START_DATETIME)
    view.set_location("Somewhere")
    view.set_notes("Some notes")
    view.clickSaveButton()

    event = person.events()[0]
    assert event.kind() == EventKind.Death
    assert event.description() == EventKind.Death.name
    assert event.location() == "Somewhere"
    assert event.notes() == "Some notes"
    assert person.deceased() == True
    assert person.deceasedDateTime() == START_DATETIME
    assert scene.currentDateTime() == START_DATETIME


def test_attrs_VariableShift(scene, view):
    mother = scene.addItem(Person(name="Mother"))
    view.view.addEvent()
    view.set_kind(EventKind.VariableShift)
    view.personPicker.set_existing_person(mother)
    view.set_relationship(RelationshipKind.Inside)
    view.targetsPicker.add_new_person("Jane Doe")
    view.trianglesPicker.add_new_person("John Doe")
    view.set_description("Some description")
    view.set_startDateTime(START_DATETIME)
    view.set_location("Somewhere")
    view.set_notes("Some notes")
    view.clickSaveButton()

    event = mother.emotions()[0].events()[0]
    assert event.kind() == EventKind.VariableShift
    assert event.description() == "Some description"
    assert event.location() == "Somewhere"
    assert event.notes() == "Some notes"
    assert scene.currentDateTime() == START_DATETIME
