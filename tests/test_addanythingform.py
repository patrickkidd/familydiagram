import logging

import pytest
import mock


from pkdiagram import util, objects, EventKinds, SceneModel, Scene
from pkdiagram.pyqt import Qt
from pkdiagram.addanythingdialog import AddAnythingDialog
from test_emotionproperties import (
    emotionProps,
    runEmotionProperties,
    assertEmotionProperties,
)


_log = logging.getLogger(__name__)


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


def test_add_new_person(qtbot, dlg):
    scene = dlg.sceneModel.scene
    dlg.clear()

    # dlg.keyClicks("people_firstNameInput", "Patrick")
    # dlg.keyClicks("people_lastNameInput", "Stinson")
    # assert dlg.itemProp("people_helpText", "text") == util.S_PERSON_NOT_FOUND

    def _validation(objectName):
        name = dlg.itemProp(objectName, "text")
        return AddAnythingDialog.S_REQUIRED_FIELD_ERROR.format(name=name)

    def submit():
        dlg.mouseClick("AddEverything_submitButton")

    qtbot.clickOkAfter(
        submit,
        text=_validation("peopleLabel"),
    )

    personItemAddDone = util.Condition(dlg.findItem("peoplePicker").itemAddDone)
    dlg.mouseClick("peoplePicker.buttons.addButton")
    assert personItemAddDone.wait() == True
    personItem = personItemAddDone.callArgs[0][0]
    dlg.mouseDClickItem(personItem)
    dlg.keyClicks(personItem, "John Doe")
    qtbot.clickOkAfter(
        submit,
        text=_validation("kindLabel"),
    )

    dlg.clickComboBoxItem("kindBox", EventKinds.Born.name)
    qtbot.clickOkAfter(
        submit,
        text=_validation("descriptionLabel"),
    )

    dlg.keyClicks("descriptionEdit", "Something happened")
    qtbot.clickOkAfter(
        submit,
        text=_validation("locationLabel"),
    )

    dlg.keyClicks("locationEdit", "Anchorage, AK")
    qtbot.clickOkAfter(
        submit,
        text=_validation("startDateTimeLabel"),
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
        text=_validation("endDateTimeLabel"),
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

    scene = dlg.sceneModel.scene
    assert len(scene.people()) == 1, f"Incorrect number of people added to scene"
    person = scene.query_1(first_name="Patrick", last_name="Stinson")
    assert len(person.events()) == 1, f"Incorrect number of events added to scene"
    event = person.events()[0]
    assert event.uniqueId() == EventKinds.Born.value
    assert event.description == EventKinds.Born.name


def test_add_new_people_pair_bond(dlg):
    scene = dlg.sceneModel.scene


# - add_new_people_as_pair_bond
# - add_two_existing_as_pair_bond_married
# - add_one_existing_one_new_as_pair_bond
# - select_isDateRange_for_distinct_event_type
# - select_not_isDateRange_for_range_event_type
# - select_dyadic_event_with_one_person_selected
# - select_dyadic_event_with_three_people_selected
#
