import logging

import pytest
import mock

from pkdiagram import util
from pkdiagram.scene import Person, Marriage, EventKind, RelationshipKind
from pkdiagram.views import AddAnythingDialog

from tests.views import TestAddAnythingDialog

_log = logging.getLogger(__name__)


ONE_NAME = "John Doe"
START_DATETIME = util.Date(2001, 1, 1, 6, 7)
END_DATETIME = util.Date(2002, 1, 1, 6, 7)

DEPENDS = pytest.mark.depends_on("PersonPicker", "PeoplePicker", "DatePicker")


@pytest.fixture
def view(qtbot, scene, qmlEngine):
    qmlEngine.sceneModel.onEditorMode(True)
    qmlEngine.setScene(scene)
    widget = AddAnythingDialog(qmlEngine)
    widget.resize(600, 1000)
    widget.setScene(scene)
    widget.show()
    qtbot.addWidget(widget)
    qtbot.waitActive(widget)
    assert widget.isShown()

    # widget.adjustFlickableHack()

    view = TestAddAnythingDialog(widget)
    view.initForSelection([])
    view.item.property("addPage").setProperty("interactive", False)

    yield view

    widget.setScene(None)
    widget.hide()
    widget.deinit()


def test_show(qmlEngine, view):
    qmlEngine.sceneModel.onEditorMode(False)
    # activeFocusItem = view.item.window().activeFocusItem()
    # textEdit = view.peoplePicker.item.pickerAtIndex(0).property("textEdit")
    # assert activeFocusItem == textEdit
    util.exec_()


@pytest.mark.parametrize("editorMode", [True, False])
def test_init(qmlEngine, view, editorMode):
    qmlEngine.sceneModel.onEditorMode(editorMode)
    assert view.item.property("kind") == None
    assert view.kindBox.property("currentIndex") == -1
    assert view.tagsEdit.property("isDirty") == False
    assert view.tagsEdit.property("visible") == editorMode
    assert view.rootProp("tagsLabel").property("visible") == editorMode


@pytest.mark.parametrize("kind", [EventKind.Birth, EventKind.Adopted, EventKind.Death])
def test_attrs(scene, view, kind: EventKind):
    mother = scene.addItem(Person(name="Mother"))
    view.initForSelection([])
    view.set_kind(kind)
    view.personPicker.set_existing_person(mother)
    if kind not in (EventKind.Birth, EventKind.Adopted, EventKind.Death):
        view.set_description("Some description")
    view.set_startDateTime(START_DATETIME)
    view.set_location("Somewhere")
    view.set_notes("Some notes")
    view.clickAddButton()

    child = mother.marriages().children()
    assert child.name() == None
    event = child.events()[0]
    assert event.uniqueId() == kind.value
    if kind not in (EventKind.Birth, EventKind.Adopted, EventKind.Death):
        assert event.description() == "Some description"
    else:
        assert event.description() == kind.name
    assert event.location() == "Somewhere"
    assert event.notes() == "Some notes"
    if kind == EventKind.Adopted:
        assert child.adopted() == True
        assert child.adoptedDateTime() == START_DATETIME
    elif kind == EventKind.Death:
        assert child.deceased() == True
        assert child.deathDateTime() == START_DATETIME
    assert scene.currentDateTime() == START_DATETIME
