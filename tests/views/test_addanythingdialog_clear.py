import pytest

from pkdiagram import util
from pkdiagram.scene import EventKind, RelationshipKind


from .test_addanythingdialog import view


pytestmark = [
    pytest.mark.component("AddAnythingDialog"),
    pytest.mark.depends_on("Scene"),
]

START_DATETIME = util.Date(2001, 1, 1, 6, 7)
END_DATETIME = util.Date(2002, 1, 1, 6, 7)

DEPENDS = pytest.mark.depends_on("PersonPicker", "PeoplePicker", "DatePicker")


def test_clear(view):
    view.set_kind(EventKind.Birth)
    view.set_startDateTime(START_DATETIME)
    view.set_summary("something")
    view.set_notes("here are some notes")
    view.set_anxiety(util.VAR_VALUE_UP)
    view.set_symptom(util.VAR_VALUE_DOWN)
    view.set_functioning(util.VAR_VALUE_SAME)
    view.spousePicker.add_new_person("Jane Doe")
    view.childPicker.add_new_person("Juaro Doe")
    view.targetsPicker.add_new_person("Jane Doe")
    view.add_tag("tag1")
    view.set_active_tags(["tag1"])
    view.clickClearButton()
    assert view.item.property("startDateTime") == None
    assert view.item.property("endDateTime") == None
    assert view.item.property("summary") == ""
    assert view.item.property("notes") == ""
    assert view.item.property("symptom") == None
    assert view.item.property("anxiety") == None
    assert view.item.property("relationship") == None
    assert view.item.property("functioning") == None
    assert view.item.property("eventModel").tags == []


def test_clear_variables(view):
    view.initForSelection([])
    view.personPicker.add_new_person("John Doe")
    view.set_kind(EventKind.VariableShift)
    view.set_startDateTime(START_DATETIME)
    view.set_endDateTime(END_DATETIME)
    view.set_summary("here are some notes")
    view.set_symptom(util.VAR_VALUE_DOWN)
    view.set_anxiety(util.VAR_VALUE_UP)
    view.set_relationship(RelationshipKind.Inside)
    view.targetsPicker.add_new_person("Juan Doe")
    view.set_functioning(util.VAR_VALUE_SAME)
    view.add_tag("tag1")
    view.set_active_tags(["tag1"])
    view.clickClearButton()
    assert view.item.property("summary") == ""
    assert view.item.property("symptom") == None
    assert view.item.property("anxiety") == None
    assert view.item.property("relationship") == None
    assert view.item.property("functioning") == None
    assert view.item.property("eventModel").tags == []
    assert view.symptomField.property("value") == None
    assert view.anxietyField.property("value") == None
    assert view.relationshipField.property("value") == None
    assert view.functioningField.property("value") == None
    assert view.item.targetsEntries() == None
    assert view.targetsPicker.personEntries() == []


def test_clear_spouse_child(view):
    view.set_kind(EventKind.Birth)
    view.personPicker.add_new_person("John Done")
    view.spousePicker.add_new_person("Jane Doe")
    view.childPicker.set_new_person("Jon Done")
    assert view.personPicker.item.property("isSubmitted") == True
    assert view.spousePicker.item.property("isSubmitted") == True
    assert view.childPicker.item.property("isSubmitted") == True
    view.clickClearButton()
    assert view.personPicker.item.property("isSubmitted") == False
    assert view.spousePicker.item.property("isSubmitted") == False
    assert view.childPicker.item.property("isSubmitted") == False
    assert view.item.personEntry() == None
    assert view.item.spouseEntry() == None
    assert view.item.childEntry() == None
