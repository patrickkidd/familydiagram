import os
import os.path
import logging

import pytest
import mock

from pkdiagram.pyqt import QApplication, QDateTime, QTimer, QEventLoop
from pkdiagram import util
from pkdiagram.scene import Person, EventKind

from .test_addanythingdialog import view, START_DATETIME, END_DATETIME


_log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.component("AddAnythingDialog"),
    pytest.mark.depends_on("Scene"),
]


def test_add_pairbond_and_children(scene, view):
    submitted = util.Condition(view.view.submitted)
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("John Doe")
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    assert submitted.wait() == True
    assert len(scene.people()) == 1

    personA = scene.query1(name="John")
    personA.setSelected(True)
    view.initForSelection(scene.selectedItems())
    QApplication.processEvents()
    view.set_kind(EventKind.Married)
    view.personBPicker.set_new_person("Jane Doe")
    view.set_startDateTime(START_DATETIME.addYears(25))
    view.clickAddButton()
    assert submitted.wait() == True
    assert len(scene.people()) == 2
    # personB = scene.query1(name="Jane")
    assert len(personA.marriages[0].events()) == 1
    personA.marriages[0].events()[0].uniqueId() == EventKind.Married.value


def test_mw_add_pairbond_and_children(scene, view):
    submitted = util.Condition(view.view.submitted)
    # Add person and parents by birth
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("John Doe")
    view.personAPicker.set_new_person("James Doe")
    view.personBPicker.set_new_person(
        "Janet Doe",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
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
    view.initForSelection([johnDoe])
    view.set_kind(EventKind.Married)
    view.personBPicker.set_new_person(
        "Janet Doran",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    view.set_startDateTime(START_DATETIME.addYears(25))
    view.clickAddButton()
    assert submitted.wait() == True
    assert len(scene.people()) == 4
    janetDoran = scene.query1(name="Janet", lastName="Doran")
    assert len(janetDoran.marriages) == 1
    assert johnDoe.marriages == janetDoran.marriages
    assert len(janetDoran.marriages[0].events()) == 1
    assert janetDoran.marriages[0].events()[0].dateTime() == START_DATETIME.addYears(25)

    # Add first kid
    view.initForSelection([])
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("Roberto Doe")
    view.personAPicker.set_existing_person(person=johnDoe)
    view.personBPicker.set_existing_person(person=janetDoran)
    view.set_startDateTime(START_DATETIME.addYears(26))
    view.clickAddButton()
    assert len(scene.people()) == 5
    robertoDoe = scene.query1(name="Roberto", lastName="Doe")
    assert robertoDoe.birthDateTime() == START_DATETIME.addYears(26)
    assert set(robertoDoe.parents().people) == {johnDoe, janetDoran}

    # Add second kid
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person(
        "Roberta Doe",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    view.personAPicker.set_existing_person(person=johnDoe)
    view.personBPicker.set_existing_person(person=janetDoran)
    view.set_startDateTime(START_DATETIME.addYears(27))
    view.clickAddButton()
    assert len(scene.people()) == 6
    robertaDoe = scene.query1(name="Roberta", lastName="Doe")
    assert robertaDoe.birthDateTime() == START_DATETIME.addYears(27)
    assert robertaDoe.x() > robertoDoe.x()
    assert robertaDoe.y() == robertoDoe.y()
    assert set(robertaDoe.parents().people) == {johnDoe, janetDoran}


# Add pair-bond via birth of child
#    assert not married
#    make them married after the fact


def test_add_pairbond_event_to_existing_pairbond(scene, view):
    personA, personB = Person(name="John"), Person(name="Jane")
    # marriage = Marriage(personA, personB)
    scene.addItems(personA, personB)

    view.set_kind(EventKind.Married)
    view.personAPicker.set_existing_person(person=personA)
    view.personBPicker.set_existing_person(person=personB)
    view.set_startDateTime(END_DATETIME)
    view.clickAddButton()

    scene.setCurrentDateTime(END_DATETIME)

    view.set_kind(EventKind.Bonded)
    view.personAPicker.set_existing_person(person=personA)
    view.personBPicker.set_existing_person(person=personB)
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()


def test_mw_add_birth_w_parents_and_birth(scene, view):
    submitted = util.Condition(view.view.submitted)

    # Add person by birth
    view.set_kind(EventKind.Birth)

    view.personPicker.set_new_person("John Doe")
    view.personAPicker.set_new_person("James Doe")
    view.personBPicker.set_new_person(
        "Janet Doe",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
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
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person(
        "Janet Doran",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    view.set_startDateTime(START_DATETIME.addYears(25))
    view.clickAddButton()
    assert submitted.wait() == True
    assert len(scene.people()) == 4
    janetDoran = scene.query1(name="Janet", lastName="Doran")
    assert len(janetDoran.marriages) == 0


def test_add_second_marriage_to_person(scene, view):
    person = Person(name="John", lastName="Doe")
    scene.addItem(person)
    view.set_kind(EventKind.Married)
    view.personAPicker.set_existing_person(person=person)
    view.personBPicker.set_new_person("Jane Doe")
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    spouse1 = scene.query1(name="Jane", lastName="Doe")
    assert len(person.marriages) == 1
    assert len(spouse1.marriages) == 1
    assert person in spouse1.marriages[0].people

    view.set_kind(EventKind.Married)
    view.personAPicker.set_existing_person(person=person)
    view.personBPicker.set_new_person("Janet Doe")
    view.set_startDateTime(START_DATETIME.addDays(5))
    view.clickAddButton()
    spouse2 = scene.query1(name="Janet", lastName="Doe")
    assert len(person.marriages) == 2
    assert len(spouse2.marriages) == 1
    assert person in spouse2.marriages[0].people


@pytest.mark.skip("Not sure this is needed any more")
def test_no_Marriage_DeferredDelete(data_root, scene, view):
    """
    Disable the hack in PathItem.eventFilter for DeferredDelete and see how this
    causes it to get called.
    """

    import pickle

    with open(
        os.path.join(data_root, "blow-up-itemdetails.fd", "diagram.pickle"), "rb"
    ) as f:
        bdata = f.read()
    data = pickle.loads(bdata)
    scene.read(data)

    patrick = scene.query1(name="Patrick")
    bob = scene.query1(name="bob")

    view.initForSelection([patrick.marriages[0]])
    view.set_kind(EventKind.CustomPairBond)
    view.set_startDateTime(QDateTime(1990, 1, 1, 0, 0))
    view.set_description("Something pair-bond-y")
    view.clickAddButton()

    view.initForSelection([patrick])
    view.set_kind(EventKind.Birth)
    view.set_startDateTime(QDateTime(1900, 1, 1, 0, 0))

    _log.info("Running event loop")
    loop = QEventLoop()
    QTimer.singleShot(2000, loop.quit)

    with mock.patch(
        "pkdiagram.scene.pathitem.PathItem.onDeferredDelete"
    ) as onDeferredDelete:
        loop.exec()
    assert onDeferredDelete.call_count == 0
