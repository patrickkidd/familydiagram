import os
import os.path
import logging

import pytest
import mock
import datetime

from pkdiagram.pyqt import QApplication, Qt, QDateTime, QTimer, QMessageBox, QEventLoop
from pkdiagram import util, EventKind, MainWindow, commands
from pkdiagram import Person, Marriage, Event
from .test_addanythingdialog import scene, dlg, START_DATETIME, END_DATETIME


_log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.component("AddAnythingDialog"),
    pytest.mark.depends_on("Scene"),
]


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


def test_no_Marriage_DeferredDelete(qtbot, create_ac_mw):
    """
    Disable the hack in PathItem.eventFilter for DeferredDelete and see how this
    causes it to get called.
    """

    from conftest import DATA_ROOT

    ac, mw = create_ac_mw()
    mw.show()
    mw.open(os.path.join(DATA_ROOT, "blow-up-itemdetails.fd"))
    scene = mw.scene
    dlg = mw.documentView.addAnythingDialog
    addAnythingButton = mw.documentView.view.rightToolBar.addAnythingButton

    patrick = scene.query1(name="Patrick")
    bob = scene.query1(name="bob")

    patrick.marriages[0].setSelected(True)
    qtbot.clickAndProcessEvents(addAnythingButton)
    dlg.set_kind(EventKind.CustomPairBond)
    dlg.set_startDateTime(QDateTime(1990, 1, 1, 0, 0))
    dlg.set_description("Something pair-bond-y")
    dlg.mouseClick("AddEverything_submitButton")

    scene.clearSelection()
    patrick.setSelected(True)
    qtbot.clickAndProcessEvents(addAnythingButton)
    dlg.set_kind(EventKind.Birth)
    dlg.set_startDateTime(QDateTime(1900, 1, 1, 0, 0))

    _log.info("Running event loop")
    loop = QEventLoop()
    QTimer.singleShot(2000, loop.quit)

    with mock.patch(
        "pkdiagram.objects.pathitem.PathItem.onDeferredDelete"
    ) as onDeferredDelete:
        loop.exec()
    assert onDeferredDelete.call_count == 0


@pytest.mark.skip(
    reason="Started not accurately reproducing the problem. Was at one point though"
)
def test_no_Marriage_DeferredDelete_2(qtbot, create_ac_mw):
    """
    Disable the hack in PathItem.eventFilter for DeferredDelete and see how this
    causes it to get called.
    """

    ac, mw = create_ac_mw()
    scene = mw.scene
    dlg = mw.documentView.addAnythingDialog
    addAnythingButton = mw.documentView.view.rightToolBar.addAnythingButton

    person_a = Person(name="Person A")
    person_b = Person(name="Person B")
    marriage = Marriage(person_a, person_b)
    scene.addItems(person_a, person_b, marriage)

    marriage.setSelected(True)
    qtbot.clickAndProcessEvents(addAnythingButton)
    dlg.set_kind(EventKind.CustomPairBond)
    dlg.set_startDateTime(QDateTime(1990, 1, 1, 0, 0))
    dlg.set_description("Something pair-bond-y")
    dlg.mouseClick("AddEverything_submitButton")

    scene.clearSelection()
    person_a.setSelected(True)
    qtbot.clickAndProcessEvents(addAnythingButton)
    dlg.set_kind(EventKind.Birth)
    dlg.set_startDateTime(QDateTime(1900, 1, 1, 0, 0))
    QEventLoop().exec()
