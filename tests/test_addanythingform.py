import logging

import pytest
import mock


from pkdiagram import util, objects, EventKinds, SceneModel, Scene
from pkdiagram.pyqt import Qt, QQuickItem
from pkdiagram.addanythingdialog import AddAnythingDialog
from test_emotionproperties import (
    emotionProps,
    runEmotionProperties,
    assertEmotionProperties,
)


_log = logging.getLogger(__name__)

pytest.skip("AddAnythingDialog tests are not yet implemented", allow_module_level=True)


ONE_FIRST_NAME = "John"
ONE_LAST_NAME = "Doe"


def _add_person(dlg, first_name=ONE_FIRST_NAME, last_name=ONE_LAST_NAME):
    personItemAddDone = util.Condition(dlg.findItem("peoplePicker").itemAddDone)
    dlg.mouseClick("peoplePicker.buttons.addButton")
    assert personItemAddDone.wait() == True
    personItem = personItemAddDone.callArgs[0][0]
    personTextEdit = personItem.findChildren(QQuickItem, "textEdit")[0]
    dlg.mouseDClickItem(personTextEdit)
    dlg.keyClicks(personTextEdit, f"{first_name} {last_name}")


def _set_required_fields(dlg, kind=EventKinds.Birth.name, people=True):

    RESET_FOCUS = False
    RETURN_TO_FINISH = False

    #

    if people:
        _add_person(dlg)

    #

    if kind:
        dlg.clickComboBoxItem("kindBox", kind)

    #

    dlg.keyClicks("descriptionEdit", "Something happened")

    #

    dlg.keyClicks("locationEdit", "Anchorage, AK")

    #

    START_DATE = "1/1/2001"
    START_TIME = "12:34am"

    dlg.mouseClick("isDateRangeBox")
    assert dlg.rootProp("isDateRange") == True

    dlg.focusItem("startDateButtons.dateTextInput")
    dlg.keyClick("startDateButtons.dateTextInput", Qt.Key_Backspace)
    dlg.keyClicks(
        "startDateButtons.dateTextInput",
        START_DATE,
        resetFocus=RESET_FOCUS,
        returnToFinish=RETURN_TO_FINISH,
    )
    #
    dlg.focusItem("startDateButtons.timeTextInput")
    dlg.keyClick("startDateButtons.timeTextInput", Qt.Key_Backspace)
    dlg.keyClicks(
        "startDateButtons.timeTextInput",
        START_TIME,
        returnToFinish=RETURN_TO_FINISH,
    )

    #

    END_DATE = "1/1/2002"
    END_TIME = "09:45am"

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


@pytest.fixture
def dlg(qtbot):
    scene = Scene()
    sceneModel = SceneModel()
    sceneModel.scene = scene
    scene._sceneModel = sceneModel

    dlg = AddAnythingDialog(sceneModel=sceneModel)
    dlg.resize(600, 800)
    # dlg.setRootProp("sceneModel", qmlScene._sceneModel)
    dlg.setScene(scene)
    dlg.show()
    qtbot.addWidget(dlg)
    qtbot.waitActive(dlg)
    assert dlg.isShown()
    assert dlg.itemProp("AddEverything_submitButton", "text") == "Add"

    yield dlg

    dlg.setScene(None)
    dlg.hide()


def test_init(dlg):
    pass


def _run_dateTimePickers(dlg, dateTime, buttonsItem, datePickerItem, timePickerItem):
    S_DATE_TIME = util.dateString(dateTime)

    dlg.keyClicks(
        f"{buttonsItem}.dateTextInput",
        S_DATE_TIME,
        resetFocus=False,
    )
    assert dlg.itemProp(buttonsItem, "dateTime") == dateTime
    assert dlg.itemProp(datePickerItem, "dateTime") == dateTime
    assert dlg.itemProp(timePickerItem, "dateTime") == dateTime


def test_startDateTime_pickers(qtbot, dlg):
    dlg.clear()

    DATE_TIME = util.Date(2023, 2, 1)

    _run_dateTimePickers(
        dlg, DATE_TIME, "startDateButtons", "startDatePicker", "startTimePicker"
    )
    assert dlg.rootProp("startDateTime") == DATE_TIME


def test_endDateTime_pickers(qtbot, dlg):
    dlg.clear()

    DATE_TIME = util.Date(2023, 2, 1)

    dlg.mouseClick("isDateRangeBox")
    assert dlg.itemProp("isDateRangeBox", "checked")

    _run_dateTimePickers(
        dlg, DATE_TIME, "endDateButtons", "endDatePicker", "endTimePicker"
    )
    assert dlg.rootProp("endDateTime") == DATE_TIME


def test_required_field_validation(qtbot, dlg):
    dlg.clear()

    def _required_text(objectName):
        name = dlg.itemProp(objectName, "text")
        return AddAnythingDialog.S_REQUIRED_FIELD_ERROR.format(name=name)

    def submit():
        dlg.mouseClick("AddEverything_submitButton")

    qtbot.clickOkAfter(
        submit,
        text=_required_text("peopleLabel"),
    )

    _add_person(dlg)
    qtbot.clickOkAfter(
        submit,
        text=_required_text("kindLabel"),
    )

    dlg.clickComboBoxItem("kindBox", EventKinds.Birth.name)
    qtbot.clickOkAfter(
        submit,
        text=_required_text("descriptionLabel"),
    )

    dlg.keyClicks("descriptionEdit", "Something happened")
    qtbot.clickOkAfter(
        submit,
        text=_required_text("locationLabel"),
    )

    dlg.keyClicks("locationEdit", "Anchorage, AK")
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

    dlg.mouseClick("isDateRangeBox")
    assert dlg.rootProp("isDateRange") == True

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


def test_add_new_person_born(dlg):
    scene = dlg.sceneModel.scene
    submitted = util.Condition(dlg.submitted)
    _set_required_fields(dlg)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1, "submitted signal emitted too many times"

    scene = dlg.sceneModel.scene
    assert len(scene.people()) == 1, f"Incorrect number of people added to scene"
    person = scene.query1(name="John", last_name="Doe")
    assert person, f"Could not find created person {ONE_FIRST_NAME} {ONE_LAST_NAME}"
    assert len(person.events()) == 1, f"Incorrect number of events added to scene"
    event = person.events()[0]
    assert event.uniqueId() == EventKinds.Birth.value
    assert event.description == EventKinds.Birth.name


@pytest.mark.parametrize("eventKind", [x for x in EventKinds if x != EventKinds.Custom])
def test_description_disabled_for_uniqueId(dlg, eventKind):
    dlg.clickComboBoxItem("kindBox", eventKind.name)
    assert dlg.itemProp("descriptionEdit", "enabled") == bool(
        eventKind != EventKinds.Custom
    )


# def test_add_new_people_pair_bond(dlg):
#     scene = dlg.sceneModel.scene


def test_add_dyadic_event_with_one_person_selected(qtbot, dlg):
    _set_required_fields(dlg, people=False)
    _add_person(dlg)
    qtbot.clickOkAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_EVENT_DYADIC,
    )


@pytest.mark.parametrize("eventKind", [x for x in EventKinds if EventKinds.isDyadic(x)])
def test_add_dyadic_event_with_three_people_selected(qtbot, dlg, eventKind):
    _set_required_fields(dlg, kind=False, people=False)
    _add_person(dlg)
    dlg.clickComboBoxItem("kindBox", eventKind.name)
    qtbot.clickOkAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_EVENT_DYADIC,
    )


# def test_person_help_text_add_one_person(qtbot, dlg):
#     _set_required_fields(dlg, people=False)
#     _add_person(dlg)
#     dlg.clickComboBoxItem("kindBox", EventKinds.Birth.name)
#     assert (
#         dlg.itemProp("eventHelpText", "text")
#         == AddAnythingDialog.S_EVENT_MULTIPLE_INDIVIDUALS
#     )


# def test_dyadic_with_gt_two_people(qtbot, dlg):
#     _set_required_fields(dlg, people=False)
#     _add_person(dlg, first_name="John", last_name="Doe")
#     _add_person(dlg, first_name="Jane", last_name="Doe")
#     _add_person(dlg, first_name="Joseph", last_name="Belgard")
#     dlg.clickComboBoxItem("kindBox", EventKinds.Birth.name)
#     assert (
#         dlg.itemProp("eventHelpText", "text")
#         == AddAnythingDialog.S_EVENT_MULTIPLE_INDIVIDUALS
#     )


# - add_new_people_as_pair_bond
# - add_two_existing_as_pair_bond_married
# - add_one_existing_one_new_as_pair_bond
# - select_isDateRange_for_distinct_event_type
# - select_not_isDateRange_for_range_event_type
# - select_dyadic_event_with_one_person_selected
# - select_dyadic_event_with_three_people_selected
#
