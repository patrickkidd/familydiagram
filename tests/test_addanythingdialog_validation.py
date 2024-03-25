import logging

import pytest
import mock

from pkdiagram import util, objects, EventKind, SceneModel, Scene, Person
from pkdiagram.pyqt import Qt, QQuickItem, QApplication
from pkdiagram.addanythingdialog import AddAnythingDialog
from test_peoplepicker import add_and_keyClicks, add_new_person, add_existing_person
from tests.test_addanythingdialog import (
    _add_new_person,
    _add_existing_person,
    _run_dateTimePickers,
    _set_fields,
    scene,
    dlg,
    SET_START_DATETIME,
    SET_END_DATETIME,
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
    _add_new_person(dlg, "peoplePickerA", "John Doe")

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


def test_confirm_replace_birth_events(qtbot, scene, dlg):
    EVENT_KIND = EventKind.Birth
    submitted = util.Condition(dlg.submitted)
    people = [
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
    ]
    scene.addItems(*people)
    people[0].setBirthDateTime(util.Date(2011, 1, 1))
    people[1].setBirthDateTime(util.Date(2012, 1, 1))
    _set_fields(dlg, EVENT_KIND, peopleA=people, description=False, fillRequired=True)
    qtbot.clickYesAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_REPLACE_EXISTING.format(
            n_existing=2, eventKind=EVENT_KIND
        ),
    )
    assert submitted.callCount == 1
    assert people[0].birthDateTime() == SET_START_DATETIME
    assert people[1].birthDateTime() == SET_START_DATETIME


def test_confirm_replace_death_events(qtbot, scene, dlg):
    EVENT_KIND = EventKind.Death
    submitted = util.Condition(dlg.submitted)
    people = [
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
    ]
    scene.addItems(*people)
    people[0].setDeceasedDateTime(util.Date(2014, 1, 1))
    people[1].setDeceasedDateTime(util.Date(2015, 1, 1))
    _set_fields(dlg, EVENT_KIND, peopleA=people, description=False, fillRequired=True)
    qtbot.clickYesAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_REPLACE_EXISTING.format(
            n_existing=2, eventKind=EVENT_KIND
        ),
    )
    assert submitted.callCount == 1
    assert people[0].deceasedDateTime() == SET_START_DATETIME
    assert people[1].deceasedDateTime() == SET_START_DATETIME


@pytest.mark.parametrize("kind", [EventKind.Birth, EventKind.Death])
def test_no_confirm_replace_events(qtbot, scene, dlg, kind):
    submitted = util.Condition(dlg.submitted)
    people = [
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
    ]
    scene.addItems(*people)
    _set_fields(dlg, kind, peopleA=people, description=False, fillRequired=True)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1
    if kind == EventKind.Birth:
        assert people[0].birthDateTime() == SET_START_DATETIME
        assert people[1].birthDateTime() == SET_START_DATETIME
    else:
        assert people[0].deceasedDateTime() == SET_START_DATETIME
        assert people[1].deceasedDateTime() == SET_START_DATETIME


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
    _set_fields(dlg, kind, peopleA=peopleA, peopleB=peopleB, fillRequired=True)
    qtbot.clickYesAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_ADD_MANY_SYMBOLS.format(numSymbols=4),
    )
    assert len(scene.emotions()) == 4
    assert len(scene.people()) == 4
