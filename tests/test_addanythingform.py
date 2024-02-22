import pytest
from pkdiagram import util, objects, EventKind
from pkdiagram.pyqt import Qt
from pkdiagram.addanythingdialog import AddAnythingDialog
from test_emotionproperties import (
    emotionProps,
    runEmotionProperties,
    assertEmotionProperties,
)


@pytest.fixture
def dlg(qmlScene, qtbot):
    dlg = AddAnythingDialog(sceneModel=qmlScene._sceneModel)
    dlg.resize(600, 800)
    # dlg.setRootProp("sceneModel", qmlScene._sceneModel)
    dlg.setScene(qmlScene)
    dlg.show()
    qtbot.addWidget(dlg)
    qtbot.waitActive(dlg)
    assert dlg.isShown()
    assert dlg.itemProp("AddEverything_addButton", "text") == "Add"

    yield dlg

    dlg.setScene(None)
    dlg.hide()


def test_init(dlg):
    pass


def test_add_new_person(dlg):
    scene = dlg.sceneModel.scene

    dlg.keyClicks("people_firstNameInput", "Patrick")
    dlg.keyClicks("people_lastNameInput", "Stinson")
    assert dlg.itemProp("people_helpText", "text") == util.S_PERSON_NOT_FOUND

    dlg.mouseClick("people_confirmAddButton")
    assert dlg.itemProp("people_helpText", "text") == ""

    dlg.itemProp.clickComboBoxItem("kindBox", EventKind.Born.name)

    RESET_FOCUS = False
    RETURN_TO_FINISH = False

    BORN_DATE = "1/1/2001"
    BORN_TIME = "12:34am"

    dlg.keyClicksClear("startDateButtons.dateTextInput")
    dlg.keyClicks(
        "startDateButtons.dateTextInput",
        BORN_DATE,
        resetFocus=RESET_FOCUS,
        returnToFinish=RETURN_TO_FINISH,
    )
    dlg.keyClicksClear("startDateButtons.timeTextInput")
    dlg.keyClicks(
        "startDateButtons.timeTextInput",
        BORN_TIME,
        resetFocus=RESET_FOCUS,
        returnToFinish=RETURN_TO_FINISH,
    )
    dlg.keyClicks("locationInput", "Anchorage, AK`")
    dlg.mouseClick("addButton")

    scene = dlg.sceneModel.scene
    assert len(scene.people()) == 1
    person = scene.query_1(first_name="Patrick", last_name="Stinson")
    assert len(person.events()) == 1
    event = person.events()[0]
    assert event.uniqueId() == EventKind.Born.value
    assert event.description == EventKind.Born.name


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
