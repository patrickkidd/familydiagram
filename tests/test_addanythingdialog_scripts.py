import pytest
import datetime

from pkdiagram.pyqt import QApplication, Qt
from pkdiagram import util, EventKind, MainWindow
from pkdiagram import Person, Marriage
from tests.test_addanythingdialog import scene, dlg, START_DATETIME, END_DATETIME


def test_add_pairbond_and_children(dlg):
    scene = dlg.scene
    submitted = util.Condition(dlg.submitted)
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person("personPicker", "John Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.wait() == True
    assert len(scene.people()) == 1

    personA = scene.query1(name="John")
    personA.setSelected(True)
    dlg.initForSelection(scene.selectedItems())
    QApplication.processEvents()
    dlg.set_kind(EventKind.Married)
    dlg.set_new_person("personBPicker", "Jane Doe")
    dlg.set_startDateTime(START_DATETIME.addYears(25))
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.wait() == True
    assert len(scene.people()) == 2
    # personB = scene.query1(name="Jane")
    assert len(personA.marriages[0].events()) == 1
    personA.marriages[0].events()[0].uniqueId() == EventKind.Married.value


def test_mw_add_pairbond_and_children(qtbot, create_ac_mw):
    ac, mw = create_ac_mw()
    scene = mw.scene
    dlg = mw.documentView.addAnythingDialog
    submitted = util.Condition(dlg.submitted)
    addAnythingButton = mw.documentView.view.rightToolBar.addAnythingButton

    # Add person and parents by birth
    qtbot.clickAndProcessEvents(addAnythingButton)
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person("personPicker", "John Doe")
    dlg.set_new_person("personAPicker", "James Doe")
    dlg.set_new_person(
        "personBPicker",
        "Janet Doe",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.wait() == True
    assert len(scene.people()) == 3
    assert set([x.fullNameOrAlias() for x in scene.people()]) == {
        "John Doe",
        "James Doe",
        "Janet Doe",
    }
    johnDoe = scene.query1(name="John", lastName="Doe")
    assert johnDoe.birthDateTime() == START_DATETIME
    assert set([x.fullNameOrAlias() for x in johnDoe.parents().people]) == {
        "Janet Doe",
        "James Doe",
    }

    # Add by marriage
    johnDoe.setSelected(True)
    qtbot.clickAndProcessEvents(addAnythingButton)
    dlg.set_kind(EventKind.Married)
    dlg.set_new_person(
        "personBPicker",
        "Janet Doran",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    dlg.set_startDateTime(START_DATETIME.addYears(25))
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.wait() == True
    assert len(scene.people()) == 4
    janetDoran = scene.query1(name="Janet", lastName="Doran")
    assert len(janetDoran.marriages) == 1
    assert johnDoe.marriages == janetDoran.marriages
    assert len(janetDoran.marriages[0].events()) == 1
    assert janetDoran.marriages[0].events()[0].dateTime() == START_DATETIME.addYears(25)

    scene.clearSelection()

    # Add first kid
    qtbot.clickAndProcessEvents(addAnythingButton)
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person("personPicker", "Roberto Doe")
    dlg.set_existing_person("personAPicker", person=johnDoe)
    dlg.set_existing_person("personBPicker", person=janetDoran)
    dlg.set_startDateTime(START_DATETIME.addYears(26))
    dlg.mouseClick("AddEverything_submitButton")
    assert len(scene.people()) == 5
    robertoDoe = scene.query1(name="Roberto", lastName="Doe")
    assert robertoDoe.birthDateTime() == START_DATETIME.addYears(26)
    assert set(robertoDoe.parents().people) == {johnDoe, janetDoran}

    scene.clearSelection()

    # Add second kid
    assert johnDoe.isSelected() == False
    qtbot.clickAndProcessEvents(addAnythingButton)
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person(
        "personPicker",
        "Roberta Doe",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    dlg.set_existing_person("personAPicker", person=johnDoe)
    dlg.set_existing_person("personBPicker", person=janetDoran)
    dlg.set_startDateTime(START_DATETIME.addYears(27))
    dlg.mouseClick("AddEverything_submitButton")
    assert len(scene.people()) == 6
    robertaDoe = scene.query1(name="Roberta", lastName="Doe")
    assert robertaDoe.birthDateTime() == START_DATETIME.addYears(27)
    assert robertaDoe.x() > robertoDoe.x()
    assert robertaDoe.y() == robertoDoe.y()
    assert set(robertaDoe.parents().people) == {johnDoe, janetDoran}


# Add pair-bond via birth of child
#    assert not married
#    make them married after the fact


def test_add_pairbond_event_to_existing_pairbond(qtbot, create_ac_mw):
    ac, mw = create_ac_mw()
    scene = mw.scene
    dlg = mw.documentView.addAnythingDialog
    addAnythingButton = mw.documentView.view.rightToolBar.addAnythingButton
    personA, personB = Person(name="John"), Person(name="Jane")
    # marriage = Marriage(personA, personB)
    scene.addItems(personA, personB)

    mw.documentView.controller.onNextEvent()
    mw.documentView.controller.onPrevEvent()

    qtbot.clickAndProcessEvents(addAnythingButton)
    dlg.set_kind(EventKind.Married)
    dlg.set_existing_person("personAPicker", person=personA)
    dlg.set_existing_person("personBPicker", person=personB)
    dlg.set_startDateTime(END_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")

    mw.documentView.controller.onNextEvent()
    mw.documentView.controller.onPrevEvent()

    qtbot.clickAndProcessEvents(addAnythingButton)
    dlg.set_kind(EventKind.Bonded)
    dlg.set_existing_person("personAPicker", person=personA)
    dlg.set_existing_person("personBPicker", person=personB)
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")


def test_mw_add_birth_w_parents_and_birth(qtbot, create_ac_mw):
    ac, mw = create_ac_mw()
    scene = mw.scene
    dlg = mw.documentView.addAnythingDialog
    submitted = util.Condition(dlg.submitted)
    addAnythingButton = mw.documentView.view.rightToolBar.addAnythingButton

    # Add person by birth
    qtbot.clickAndProcessEvents(addAnythingButton)
    dlg.set_kind(EventKind.Birth)

    dlg.set_new_person("personPicker", "John Doe")
    dlg.set_new_person("personAPicker", "James Doe")
    dlg.set_new_person(
        "personBPicker",
        "Janet Doe",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.wait() == True
    assert len(scene.people()) == 3
    assert set([x.fullNameOrAlias() for x in scene.people()]) == {
        "John Doe",
        "James Doe",
        "Janet Doe",
    }
    johnDoe = scene.query1(name="John", lastName="Doe")
    assert johnDoe.birthDateTime() == START_DATETIME
    assert set([x.fullNameOrAlias() for x in johnDoe.parents().people]) == {
        "Janet Doe",
        "James Doe",
    }

    # Add Spouse Birth
    qtbot.clickAndProcessEvents(addAnythingButton)
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person(
        "personPicker",
        "Janet Doran",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    dlg.set_startDateTime(START_DATETIME.addYears(25))
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.wait() == True
    assert len(scene.people()) == 4
    janetDoran = scene.query1(name="Janet", lastName="Doran")
    assert len(janetDoran.marriages) == 0


@pytest.mark.skip(reason="Couldn't figure out how to ")
def test_blow_up_ItemDetails(qtbot, create_ac_mw):
    """Added as a placeholder for future script tests"""
    ac, mw = create_ac_mw()
    scene = mw.scene
    dlg = mw.documentView.addAnythingDialog
    submitted = util.Condition(dlg.submitted)
    addAnythingButton = mw.documentView.view.rightToolBar.addAnythingButton

    person = dlg.add_person_by_birth("John Doe", START_DATETIME)
    marriage = dlg.add_marriage_to_person(
        person, "Jane Doe", START_DATETIME.addYears(20)
    )
    for i in range(3):
        event = dlg.add_event_to_marriage(
            marriage, EventKind.Bonded, START_DATETIME.addYears(25 + i)
        )
        assert event.description() == "Bonded"
        assert event.dateTime() == START_DATETIME.addYears(25 + i)


def test_add_second_marriage_to_person(dlg):
    scene = dlg.scene
    person = Person(name="John", lastName="Doe")
    scene.addItem(person)
    dlg.set_kind(EventKind.Married)
    dlg.set_existing_person("personAPicker", person=person)
    dlg.set_new_person("personBPicker", "Jane Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    spouse1 = scene.query1(name="Jane", lastName="Doe")
    assert len(person.marriages) == 1
    assert len(spouse1.marriages) == 1
    assert person in spouse1.marriages[0].people

    dlg.set_kind(EventKind.Married)
    dlg.set_existing_person("personAPicker", person=person)
    dlg.set_new_person("personBPicker", "Janet Doe")
    dlg.set_startDateTime(START_DATETIME.addDays(5))
    dlg.mouseClick("AddEverything_submitButton")
    spouse2 = scene.query1(name="Janet", lastName="Doe")
    assert len(person.marriages) == 2
    assert len(spouse2.marriages) == 1
    assert person in spouse2.marriages[0].people
