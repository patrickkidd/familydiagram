import logging

import pytest
import mock

from pkdiagram import util, objects, EventKind, SceneModel, Scene, Person, Marriage
from pkdiagram.pyqt import (
    Qt,
    QQuickItem,
    QApplication,
    QMetaObject,
    Q_RETURN_ARG,
    QVariant,
    QJSValue,
    QEventLoop,
    QTimer,
    QRectF,
)
from pkdiagram.addanythingdialog import AddAnythingDialog

_log = logging.getLogger(__name__)


ONE_NAME = "John Doe"
START_DATETIME = util.Date(2001, 1, 1, 6, 7)
END_DATETIME = util.Date(2002, 1, 1, 6, 7)


class TestAddAnythingDialog(AddAnythingDialog):

    def test_initForSelection(self, selection):
        if Marriage.marriageForSelection(selection):
            self.initForSelection(selection)
            # personAPickerItem = self.findItem("personAPicker")
            # itemAddDoneA = util.Condition(personAPickerItem.itemAddDone)
            # personBPickerItem = self.findItem("personBPicker")
            # itemAddDoneB = util.Condition(personBPickerItem.itemAddDone)
            # while itemAddDoneA.callCount < 1:
            #     _log.info(f"Waiting for {len(selection) - itemAddDone.callCount} / {len(selection)} itemAddDone signals")
            #     assert itemAddDoneA.wait() == True
            # while itemAddDoneB.callCount < 1:
            #     assert itemAddDoneB.wait() == True
        else:
            peoplePickerItem = self.findItem("peoplePicker")
            itemAddDone = util.Condition(peoplePickerItem.itemAddDone)
            self.initForSelection(selection)
            while itemAddDone.callCount < len(selection):
                _log.info(
                    f"Waiting for {len(selection) - itemAddDone.callCount} / {len(selection)} itemAddDone signals"
                )
                assert (
                    itemAddDone.wait() == True
                ), f"itemAddDone signal not emitted, called {itemAddDone.callCount} times"


@pytest.fixture
def scene():
    scene = Scene()
    yield scene


@pytest.fixture
def dlg(qtbot, scene):
    sceneModel = SceneModel()
    sceneModel.scene = scene
    scene._sceneModel = sceneModel

    dlg = TestAddAnythingDialog(sceneModel=sceneModel)
    dlg.resize(600, 800)
    dlg.setRootProp("sceneModel", sceneModel)
    dlg.setScene(scene)
    dlg.show()
    qtbot.addWidget(dlg)
    qtbot.waitActive(dlg)
    assert dlg.isShown()
    assert dlg.itemProp("AddEverything_submitButton", "text") == "Add"
    dlg.mouseClick("clearFormButton")

    yield dlg

    dlg.setScene(None)
    dlg.hide()


def test_init(dlg):
    assert dlg.rootProp("kind") == None
    assert dlg.itemProp("kindBox", "currentIndex") == -1


def test_clear(dlg):
    dlg.set_kind(EventKind.Conflict)  # dyadic for end date
    dlg.set_startDateTime(START_DATETIME)
    dlg.set_endDateTime(END_DATETIME)
    dlg.set_description("something")
    dlg.set_notes("here are some notes")
    dlg.set_anxiety(util.VAR_VALUE_UP)
    dlg.set_symptom(util.VAR_VALUE_DOWN)
    dlg.set_functioning(util.VAR_VALUE_SAME)
    dlg.mouseClick("clearFormButton")
    assert dlg.rootProp("startDateTime") == None
    assert dlg.rootProp("endDateTime") == None
    assert dlg.rootProp("description") == ""
    assert dlg.rootProp("notes") == ""
    assert dlg.rootProp("anxiety") == None
    assert dlg.rootProp("symptom") == None
    assert dlg.rootProp("functioning") == None


def test_clear_birth(dlg):
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person("personPicker", "John Done")
    dlg.set_new_person("personAPicker", "Jon Done")
    dlg.set_new_person("personBPicker", "Jane Done")
    assert dlg.itemProp("personPicker", "isSubmitted") == True
    assert dlg.itemProp("personAPicker", "isSubmitted") == True
    assert dlg.itemProp("personBPicker", "isSubmitted") == True
    dlg.mouseClick("clearFormButton")
    assert dlg.itemProp("personPicker", "isSubmitted") == False
    assert dlg.itemProp("personAPicker", "isSubmitted") == False
    assert dlg.itemProp("personBPicker", "isSubmitted") == False


def test_clear_monadic(dlg):
    dlg.set_kind(EventKind.Adopted)
    dlg.set_new_person("personPicker", "John Done")
    assert dlg.itemProp("personPicker", "isSubmitted") == True
    dlg.mouseClick("clearFormButton")
    assert dlg.itemProp("personPicker", "isSubmitted") == False


def test_clear_custom_individual(dlg):
    dlg.set_kind(EventKind.CustomIndividual)
    dlg.add_new_person("peoplePicker", "John Done")
    assert dlg.peopleEntries()
    dlg.mouseClick("clearFormButton")
    assert dlg.peopleEntries() == []


def test_clear_pairbond(dlg):
    dlg.set_kind(EventKind.Married)
    dlg.set_new_person("personAPicker", "John Done")
    dlg.set_new_person("personBPicker", "Jane Done")
    assert dlg.itemProp("personAPicker", "isSubmitted")
    assert dlg.itemProp("personBPicker", "isSubmitted")
    dlg.mouseClick("clearFormButton")
    assert not dlg.itemProp("personAPicker", "isSubmitted")
    assert not dlg.itemProp("personBPicker", "isSubmitted")


def test_clear_dyadic(dlg):
    dlg.set_kind(EventKind.Conflict)
    dlg.add_new_person("moversPicker", "John Doe")
    dlg.add_new_person("moversPicker", "Jane Doe")
    dlg.add_new_person("receiversPicker", "Jane Doe")
    dlg.add_new_person("receiversPicker", "Jane Done")
    assert dlg.moverEntries()
    assert dlg.receiverEntries()
    dlg.mouseClick("clearFormButton")
    assert dlg.moverEntries() == []
    assert dlg.receiverEntries() == []


def test_add_new_person_via_Birth(scene, dlg):
    submitted = util.Condition(dlg.submitted)
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person("personPicker", "John Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1, "submitted signal emitted too many times"

    scene = dlg.sceneModel.scene
    assert len(scene.people()) == 1, f"Incorrect number of people added to scene"
    person = scene.query1(name="John", lastName="Doe")
    assert person, f"Could not find created person {ONE_NAME}"
    assert len(person.events()) == 1, f"Incorrect number of events added to scene"
    event = person.events()[0]
    assert event.uniqueId() == EventKind.Birth.value
    assert event.description() == EventKind.Birth.name


def test_add_new_person_via_Birth_with_one_parent(scene, dlg):
    submitted = util.Condition(dlg.submitted)
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person("personPicker", "John Doe")
    dlg.set_new_person(
        "personAPicker",
        "Joseph Doe",
        gender=util.personKindNameFromKind(util.PERSON_KIND_MALE),
    )
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1, "submitted signal emitted too many times"

    scene = dlg.sceneModel.scene
    assert len(scene.people()) == 3, f"Incorrect number of people added to scene"
    person = scene.query1(name="John", lastName="Doe")
    personA = scene.query1(name="Joseph", lastName="Doe")
    personB = next(x for x in scene.people() if x.id not in {person.id, personA.id})
    assert person, f"Could not find created person {ONE_NAME}"
    assert len(person.events()) == 1, f"Incorrect number of events added to scene"
    event = person.events()[0]
    assert event.uniqueId() == EventKind.Birth.value
    assert event.description() == EventKind.Birth.name
    assert len(person.parents().people) == 2
    assert personA in person.parents().people
    assert personB.gender() == util.PERSON_KIND_FEMALE


def test_add_new_person_with_one_existing_parent_one_new_via_Birth(scene, dlg):
    BIRTH_NOTES = """asd fd fgfg"""

    parentA = scene.addItem(Person(name="John", lastName="Doe"))
    submitted = util.Condition(dlg.submitted)
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person("personPicker", "Josephine Doe")
    dlg.set_existing_person("personAPicker", parentA)
    dlg.set_new_person("personBPicker", "Jane Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.set_notes(BIRTH_NOTES)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1, "submitted signal not emitted exactly once"

    scene = dlg.sceneModel.scene
    assert len(scene.people()) == 3, f"Incorrect number of people added to scene"
    child = scene.query1(name="Josephine", lastName="Doe")
    assert child, f"Could not find created child {ONE_NAME}"
    assert len(child.events()) == 1, f"Incorrect number of events added to scene"
    event = child.events()[0]
    assert event.uniqueId() == EventKind.Birth.value
    assert event.description() == EventKind.Birth.name
    assert event.notes() == BIRTH_NOTES

    parentA = scene.query1(name="John", lastName="Doe")
    parentB = scene.query1(name="Jane", lastName="Doe")
    assert {x.id for x in child.parents().people} == {parentA.id, parentB.id}


def test_add_new_person_with_one_existing_parent_via_Birth(scene, dlg):
    BIRTH_NOTES = "asd fd fgfg "

    parentA = scene.addItem(Person(name="John", lastName="Doe"))
    submitted = util.Condition(dlg.submitted)
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person("personPicker", "Josephine Doe")
    dlg.set_existing_person("personAPicker", parentA)
    dlg.set_startDateTime(START_DATETIME)
    dlg.set_notes(BIRTH_NOTES)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1, "submitted signal not emitted exactly once"

    scene = dlg.sceneModel.scene
    assert len(scene.people()) == 3, f"Incorrect number of people added to scene"
    child = scene.query1(name="Josephine", lastName="Doe")
    assert child, f"Could not find created child {ONE_NAME}"
    assert len(child.events()) == 1, f"Incorrect number of events added to scene"
    event = child.events()[0]
    assert event.uniqueId() == EventKind.Birth.value
    assert event.description() == EventKind.Birth.name
    assert event.notes() == BIRTH_NOTES

    parentA = scene.query1(name="John", lastName="Doe")
    parentB = next(x for x in scene.people() if x.id not in {parentA.id, child.id})
    assert parentB.name() == None
    assert parentB.fullNameOrAlias() == ""


def test_add_new_person_via_CustomIndividual(dlg, scene):
    DESCRIPTION = "Something Happened"
    GENDER = util.PERSON_KIND_FEMALE

    submitted = util.Condition(dlg.submitted)
    dlg.set_kind(EventKind.CustomIndividual)
    dlg.add_new_person("peoplePicker", "John Doe", gender=GENDER)
    dlg.set_description(DESCRIPTION)
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1, "submitted signal emitted too many times"

    scene = dlg.sceneModel.scene
    assert len(scene.people()) == 1, f"Incorrect number of people added to scene"
    person = scene.query1(name="John", lastName="Doe")
    assert person, f"Could not find created person {ONE_NAME}"
    assert person.gender() == GENDER
    assert len(person.events()) == 1, f"Incorrect number of events added to scene"
    event = person.events()[0]
    assert event.uniqueId() == None
    assert event.description() == DESCRIPTION


def test_add_new_person_adopted(scene, dlg):
    submitted = util.Condition(dlg.submitted)
    dlg.set_kind(EventKind.Adopted)
    dlg.set_new_person("personPicker", "John Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    newPerson = scene.query1(name="John", lastName="Doe")
    assert submitted.callCount == 1
    assert len(scene.people()) == 1
    assert newPerson.adopted() == True
    assert newPerson.adoptedDateTime() == START_DATETIME


def test_add_multiple_events_to_new_person(scene, dlg):
    DESCRIPTION = "Something happened"
    submitted = util.Condition(dlg.submitted)
    dlg.set_kind(EventKind.CustomIndividual)
    dlg.add_new_person("peoplePicker", "John Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.set_description(DESCRIPTION)
    dlg.mouseClick("AddEverything_submitButton")
    newPerson = scene.query1(name="John", lastName="Doe")
    assert submitted.callCount == 1
    assert len(scene.people()) == 1
    assert len(newPerson.events()) == 1
    assert newPerson.events()[0].description() == DESCRIPTION
    assert newPerson.events()[0].dateTime() == START_DATETIME

    dlg.mouseClick("clearFormButton")
    dlg.set_kind(EventKind.Birth)
    dlg.set_existing_person("personPicker", newPerson)
    dlg.set_startDateTime(START_DATETIME.addDays(15))
    dlg.mouseClick("AddEverything_submitButton")
    newPerson = scene.query1(name="John", lastName="Doe")
    assert submitted.callCount == 2
    assert len(scene.people()) == 1
    assert len(newPerson.events()) == 2
    assert newPerson.events()[0].uniqueId() == EventKind.Birth.value
    assert newPerson.events()[0].dateTime() == START_DATETIME.addDays(15)
    assert newPerson.events()[1].description() == DESCRIPTION
    assert newPerson.events()[1].dateTime() == START_DATETIME


def test_add_new_person_cutoff_with_date_range(scene, dlg):
    submitted = util.Condition(dlg.submitted)
    dlg.set_kind(EventKind.Cutoff)
    dlg.set_new_person("personPicker", "John Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.set_endDateTime(END_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    newPerson = scene.query1(name="John", lastName="Doe")
    assert submitted.callCount == 1, "submitted signal emitted too many times"
    assert len(scene.people()) == 1
    assert newPerson.emotions()[0].kind() == util.ITEM_CUTOFF
    assert newPerson.emotions()[0].startEvent.dateTime() == START_DATETIME
    assert newPerson.emotions()[0].endEvent.dateTime() == END_DATETIME


def test_add_new_dyadic(scene, dlg):
    dlg.set_kind(EventKind.Away)
    dlg.add_new_person("moversPicker", "John Doe")
    dlg.add_new_person("receiversPicker", "Jane Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    personA = scene.query1(name="John", lastName="Doe")
    personB = scene.query1(name="Jane", lastName="Doe")
    assert len(scene.people()) == 2
    assert len(personA.emotions()) == 1
    assert len(personB.emotions()) == 1
    assert personA.emotions() == personB.emotions()
    assert personA.emotions()[0].kind() == util.ITEM_AWAY
    assert personA.emotions()[0].startDateTime() == START_DATETIME
    assert personA.emotions()[0].endDateTime() == START_DATETIME


def test_add_new_dyadic_isDateRange(scene, dlg):
    dlg.set_kind(EventKind.Away)
    dlg.add_new_person("moversPicker", "John Doe")
    dlg.add_new_person("receiversPicker", "Jane Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.set_endDateTime(END_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    personA = scene.query1(name="John", lastName="Doe")
    personB = scene.query1(name="Jane", lastName="Doe")
    assert len(scene.people()) == 2
    assert len(personA.emotions()) == 1
    assert len(personB.emotions()) == 1
    assert personA.emotions() == personB.emotions()
    assert personA.emotions()[0].kind() == util.ITEM_AWAY
    assert personA.emotions()[0].startDateTime() == START_DATETIME
    assert personA.emotions()[0].endDateTime() == END_DATETIME


def test_add_existing_dyadic(scene, dlg):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    dlg.set_kind(EventKind.Conflict)
    dlg.add_existing_person("moversPicker", personA)
    dlg.add_new_person("receiversPicker", "Jane Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    personB = scene.query1(name="Jane", lastName="Doe")
    assert len(scene.people()) == 2
    assert len(personA.emotions()) == 1
    assert len(personB.emotions()) == 1
    assert personA.emotions() == personB.emotions()
    assert personA.emotions()[0].kind() == util.ITEM_CONFLICT
    assert personA.emotions()[0].startDateTime() == START_DATETIME
    assert personA.emotions()[0].endDateTime() == START_DATETIME


def test_add_multiple_dyadic_to_same_mover_different_receivers(scene, dlg):
    KIND_1 = EventKind.Conflict

    dlg.set_kind(KIND_1)
    dlg.add_new_person("moversPicker", "John Doe")
    dlg.add_new_person("receiversPicker", "Jane Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    personA = scene.query1(name="John", lastName="Doe")
    personB = scene.query1(name="Jane", lastName="Doe")
    assert len(scene.people()) == 2
    assert len(personA.emotions()) == 1
    assert len(personB.emotions()) == 1
    assert personA.emotions() == personB.emotions()
    assert personA.emotions()[0].kind() == util.ITEM_CONFLICT
    assert personA.emotions()[0].startDateTime() == START_DATETIME
    assert personA.emotions()[0].endDateTime() == START_DATETIME

    KIND_2 = EventKind.Away

    dlg.set_kind(KIND_2)
    dlg.add_existing_person("moversPicker", personA)
    dlg.add_new_person("receiversPicker", "Josephine Doe")
    dlg.set_startDateTime(START_DATETIME.addDays(30))
    dlg.mouseClick("AddEverything_submitButton")
    personC = scene.query1(name="Josephine", lastName="Doe")
    assert len(scene.people()) == 3
    assert len(personA.emotions()) == 2
    assert len(personB.emotions()) == 1
    assert len(personC.emotions()) == 1
    assert personA.emotions()[0].kind() == util.ITEM_CONFLICT
    assert personA.emotions()[0].startDateTime() == START_DATETIME
    assert personA.emotions()[0].endDateTime() == START_DATETIME
    assert personA.emotions()[1].kind() == util.ITEM_AWAY
    assert personA.emotions()[1].startDateTime() == START_DATETIME.addDays(30)
    assert personA.emotions()[1].endDateTime() == START_DATETIME.addDays(30)


# @pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isPairBond(x)])
def test_add_existing_pairbond(scene, dlg):
    KIND = EventKind.Separated

    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Jane", lastName="Doe"))
    marriage = scene.addItem(Marriage(personA, personB))
    dlg.set_kind(KIND)
    dlg.set_existing_person("personAPicker", personA)
    dlg.set_existing_person("personBPicker", personB)
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    assert len(marriage.events()) == 1
    assert marriage.events()[0].uniqueId() == KIND.value
    assert marriage.events()[0].description() == EventKind.menuLabelFor(KIND)


def test_add_existing_pairbond_custom(scene, dlg):
    kind = EventKind.CustomPairBond
    DESCRIPTION = "Something Happened"

    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Jane", lastName="Doe"))
    marriage = scene.addItem(Marriage(personA, personB))
    dlg.set_kind(kind)
    dlg.set_existing_person("personAPicker", personA)
    dlg.set_existing_person("personBPicker", personB)
    dlg.set_description(DESCRIPTION)
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    assert len(marriage.events()) == 1
    assert marriage.events()[0].uniqueId() == None
    assert marriage.events()[0].description() == DESCRIPTION


def test_add_multiple_events_to_same_pairbond(scene, dlg):
    KIND_1 = EventKind.Separated

    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Jane", lastName="Doe"))
    marriage = scene.addItem(Marriage(personA, personB))
    dlg.set_kind(KIND_1)
    dlg.set_existing_person("personAPicker", personA)
    dlg.set_existing_person("personBPicker", personB)
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    assert len(marriage.events()) == 1
    assert marriage.events()[0].uniqueId() == KIND_1.value
    assert marriage.events()[0].description() == EventKind.menuLabelFor(KIND_1)

    KIND_2 = EventKind.Bonded

    dlg.mouseClick("clearFormButton")
    dlg.set_kind(KIND_2)
    dlg.set_existing_person("personAPicker", personA)
    dlg.set_existing_person("personBPicker", personB)
    dlg.set_startDateTime(START_DATETIME.addDays(-30))
    dlg.mouseClick("AddEverything_submitButton")
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    assert len(marriage.events()) == 2
    assert marriage.events()[0].uniqueId() == KIND_2.value
    assert marriage.events()[0].description() == EventKind.menuLabelFor(KIND_2)
    assert marriage.events()[1].uniqueId() == KIND_1.value
    assert marriage.events()[1].description() == EventKind.menuLabelFor(KIND_1)


def test_add_new_variables(scene, dlg):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    dlg.set_kind(EventKind.CustomIndividual)
    dlg.add_existing_person("peoplePicker", personA)
    dlg.set_anxiety(util.VAR_VALUE_UP)
    dlg.set_functioning(util.VAR_FUNCTIONING_DOWN)
    dlg.set_symptom(util.VAR_SYMPTOM_SAME)
    dlg.set_description("Something happened")
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    dynamicPropertyNames = [entry["name"] for entry in scene.eventProperties()]
    assert dynamicPropertyNames == [
        util.ATTR_ANXIETY,
        util.ATTR_FUNCTIONING,
        util.ATTR_SYMPTOM,
    ]
    assert personA.events()[0].dynamicProperty("anxiety").get() == util.VAR_VALUE_UP
    assert (
        personA.events()[0].dynamicProperty("functioning").get()
        == util.VAR_FUNCTIONING_DOWN
    )
    assert personA.events()[0].dynamicProperty("symptom").get() == util.VAR_SYMPTOM_SAME
