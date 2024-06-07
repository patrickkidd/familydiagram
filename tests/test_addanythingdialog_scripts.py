import datetime

from pkdiagram.pyqt import QApplication, Qt
from pkdiagram import util, EventKind
from tests.test_addanythingdialog import (
    scene,
    dlg,
    START_DATETIME,
    END_DATETIME,
)


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

    # Add person by birth
    qtbot.mouseClick(addAnythingButton)
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

    # Add Marriage
    johnDoe.setSelected(True)
    qtbot.mouseClick(addAnythingButton)
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
