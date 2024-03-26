import logging

import pytest
import mock

from pkdiagram import util, objects, EventKind, SceneModel, Scene, Person
from pkdiagram.pyqt import Qt, QQuickItem, QApplication
from pkdiagram.addanythingdialog import AddAnythingDialog
from test_peoplepicker import add_and_keyClicks, add_new_person, add_existing_person
from tests.test_addanythingdialog import (
    scene,
    dlg,
    START_DATETIME,
    END_DATETIME,
)

log = logging.getLogger(__name__)


def test_required_fields(qtbot, dlg):
    dlg.clear()

    def _required_text(objectName):
        name = dlg.itemProp(objectName, "text")
        return AddAnythingDialog.S_REQUIRED_FIELD_ERROR.format(name=name)

    def submit():
        dlg.mouseClick("AddEverything_submitButton")

    qtbot.clickOkAfter(
        submit,
        text=_required_text("kindLabel"),
    )
    dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(EventKind.CustomIndividual))

    qtbot.clickOkAfter(
        submit,
        text=_required_text("peopleALabel"),
    )
    dlg.add_new_person(dlg, "peoplePickerA", "John Doe")

    # qtbot.clickOkAfter(
    #     submit,
    #     text=_required_text("peopleBLabel"),
    # )
    # _add_new_person(dlg, "peoplePickerB", "Jane Doe")

    # qtbot.clickOkAfter(
    #     submit,
    #     text=_required_text("descriptionLabel"),
    # )
    # TODO: description for pair-bond events
    # https://alaskafamilysystems.atlassian.net/browse/FD-42
    # dlg.keyClicks("descriptionEdit", "Something happened")

    # qtbot.clickOkAfter(
    #     submit,
    #     text=_required_text("locationLabel"),
    # )
    # dlg.keyClicks("locationEdit", "Anchorage, AK")

    qtbot.clickOkAfter(
        submit,
        text=_required_text("startDateTimeLabel"),
    )

    START_DATE = "1/1/2001"
    START_TIME = "12:34am"
    END_DATE = "1/1/2002"
    END_TIME = "09:45am"
    RESET_FOCUS = False
    RETURN_TO_FINISH = False

    dlg.focusItem("startDateButtons.dateTextInput")
    dlg.keyClick("startDateButtons.dateTextInput", Qt.Key_Backspace)
    dlg.keyClicks(
        "startDateButtons.dateTextInput",
        START_DATE,
        resetFocus=RESET_FOCUS,
        returnToFinish=RETURN_TO_FINISH,
    )

    dlg.focusItem("startDateButtons.timeTextInput")
    dlg.keyClick("startDateButtons.timeTextInput", Qt.Key_Backspace)
    dlg.keyClicks(
        "startDateButtons.timeTextInput",
        START_TIME,
        returnToFinish=RETURN_TO_FINISH,
    )

    dlg.mouseClick("isDateRangeBox")
    assert dlg.rootProp("isDateRange") == True

    qtbot.clickOkAfter(
        submit,
        text=_required_text("endDateTimeLabel"),
    )

    dlg.keyClicksClear("endDateButtons.dateTextInput")
    dlg.keyClicks(
        "endDateButtons.dateTextInput",
        END_DATE,
        resetFocus=RESET_FOCUS,
        returnToFinish=RETURN_TO_FINISH,
    )
    assert dlg.rootProp("endDateTime") == util.validatedDateTimeText(END_DATE, "")
    dlg.keyClicksClear("endDateButtons.timeTextInput")
    dlg.keyClicks(
        "endDateButtons.timeTextInput",
        END_TIME,
        resetFocus=RESET_FOCUS,
        returnToFinish=RETURN_TO_FINISH,
    )

    submitted = util.Condition(dlg.submitted)
    submit()
    assert submitted.callCount == 1, "submitted signal emitted too many times"


@pytest.mark.parametrize("kind", [EventKind.Birth, EventKind.Adopted, EventKind.Death])
def test_confirm_replace_singular_events(qtbot, scene, dlg, kind):
    PRIOR_DATETIME = util.Date(2011, 1, 1)
    EVENT_KIND = EventKind.Birth
    submitted = util.Condition(dlg.submitted)
    person = scene.addItem(Person(name="John", lastName="Doe"))
    if kind == EventKind.Birth:
        person.setBirthDateTime(PRIOR_DATETIME)
    elif kind == EventKind.Adopted:
        person.setAdoptedDateTime(PRIOR_DATETIME)
    elif kind == EventKind.Death:
        person.setDeceasedDateTime(PRIOR_DATETIME)
    dlg.set_kind(kind)
    dlg.set_existing_person("personPicker", person)
    dlg.set_startDateTime(START_DATETIME)
    qtbot.clickYesAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_REPLACE_EXISTING.format(
            n_existing=2, eventKind=EVENT_KIND
        ),
    )
    assert submitted.callCount == 1
    if kind == EventKind.Birth:
        assert person.birthDateTime() == START_DATETIME
    elif kind == EventKind.Adopted:
        assert person.adoptedDateTime() == START_DATETIME
    elif kind == EventKind.Death:
        assert person.deceasedDateTime() == START_DATETIME


@pytest.mark.parametrize(
    "kind",
    [
        EventKind.Conflict,
        EventKind.Distance,
        EventKind.Reciprocity,
        EventKind.Projection,
        EventKind.Toward,
        EventKind.Away,
        EventKind.Inside,
        EventKind.Outside,
        EventKind.DefinedSelf,
    ],
)
def test_confirm_adding_many_symbols(qtbot, scene, dlg, kind):
    peopleA = [
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
    ]
    peopleB = [
        Person(name="Jack", lastName="Doe"),
        Person(name="Jill", lastName="Doe"),
    ]
    scene.addItems(*(peopleA + peopleB))
    dlg.set_kind(kind)
    dlg.add_existing_person("moversPicker", peopleA[0])
    dlg.add_existing_person("moversPicker", peopleA[1])
    dlg.add_existing_person("receiversPicker", peopleB[0])
    dlg.add_existing_person("receiversPicker", peopleB[1])
    qtbot.clickYesAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_ADD_MANY_SYMBOLS.format(numSymbols=4),
    )
    assert len(scene.emotions()) == 4
    assert len(scene.people()) == 4


def test_confirm_adding_many_individual_events(qtbot, scene, dlg):
    DESCRIPTION = "Something happened"
    people = [
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
        Person(name="Jack", lastName="Doe"),
        Person(name="Jill", lastName="Doe"),
    ]
    scene.addItems(*people)
    dlg.set_kind(EventKind.CustomIndividual)
    dlg.add_existing_person("peoplePicker", people[0])
    dlg.add_existing_person("peoplePicker", people[1])
    dlg.add_existing_person("peoplePicker", people[2])
    dlg.add_existing_person("peoplePicker", people[3])
    dlg.set_description(DESCRIPTION)
    qtbot.clickYesAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_ADD_MANY_SYMBOLS.format(numSymbols=4),
    )
    for i, person in enumerate(people):
        assert (
            len(people[0].events()) == 1
        ), f"Person {i} has the wrong number of events"
        assert (
            people[0].events()[0].description() == DESCRIPTION
        ), f"Person {i} has the wrong description"


def test_add_dyadic_event_with_one_person_selected(qtbot, dlg):
    dlg.set_fields(
        kind=EventKind.Conflict, peopleA=True, peopleB=False, fillRequired=True
    )
    qtbot.clickOkAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_EVENT_DYADIC,
    )


@pytest.mark.parametrize("eventKind", [x for x in EventKind if EventKind.isDyadic(x)])
def test_add_dyadic_event_with_three_people_selected(qtbot, dlg, eventKind):
    dlg.set_fields(
        kind=eventKind,
        peopleA=["Someone New", "Someone Strange"],
        peopleB="Someone Else",
        fillRequired=True,
    )
    # dlg.clickComboBoxItem("kindBox", eventKind.name)
    qtbot.clickOkAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_EVENT_DYADIC,
    )
