import logging

import pytest
import mock

from pkdiagram import util, objects, EventKind, SceneModel, Scene, Person
from pkdiagram.pyqt import Qt, QQuickItem, QApplication
from pkdiagram.addanythingdialog import AddAnythingDialog
from test_peoplepicker import add_and_keyClicks, add_new_person, add_existing_person


_log = logging.getLogger(__name__)

# pytest.skip("AddAnythingDialog tests are not yet implemented", allow_module_level=True)


@pytest.fixture
def dlg(qtbot):
    scene = Scene()
    sceneModel = SceneModel()
    sceneModel.scene = scene
    scene._sceneModel = sceneModel

    dlg = AddAnythingDialog(sceneModel=sceneModel)
    dlg.resize(600, 800)
    dlg.setRootProp("sceneModel", sceneModel)
    dlg.setScene(scene)
    dlg.show()
    qtbot.addWidget(dlg)
    qtbot.waitActive(dlg)
    assert dlg.isShown()
    assert dlg.itemProp("AddEverything_submitButton", "text") == "Add"

    yield dlg

    dlg.setScene(None)
    dlg.hide()


ONE_NAME = "John Doe"


# def _add_person(
#     dlg: AddAnythingDialog,
#     peoplePickerItem: str,
#     firstName=ONE_FIRST_NAME,
#     lastName=ONE_LAST_NAME,
#     returnToFinish=True
# ):
#     personItemAddDone = util.Condition(dlg.findItem(peoplePickerItem).itemAddDone)
#     dlg.mouseClick(f"{peoplePickerItem}.buttons.addButton")
#     assert personItemAddDone.wait() == True
#     personItem = personItemAddDone.callArgs[1][0]
#     textEdit = personItem.findChild(QQuickItem, "textEdit")
#     dlg.keyClicks(textEdit, f"{firstName} {lastName}", resetFocus=False, returnToFinish=returnToFinish)


def _add_new_person(
    dlg: AddAnythingDialog,
    peoplePickerObjectName,
    textInput: str,
    returnToFinish: bool = True,
):
    add_new_person(
        dlg,
        textInput,
        peoplePickerObjectName=peoplePickerObjectName,
        returnToFinish=returnToFinish,
    )


def _add_existing_person(
    dlg: AddAnythingDialog,
    peoplePickerObjectName,
    person: Person,
):
    add_existing_person(dlg, person, peoplePickerObjectName=peoplePickerObjectName)


def _select_autocomplete_person(
    dlg: AddAnythingDialog, peoplePickerItem: str, person: Person
):
    personItemAddDone = util.Condition(dlg.findItem(peoplePickerItem).itemAddDone)
    dlg.mouseClick(f"{peoplePickerItem}.buttons.addButton")
    assert personItemAddDone.wait() == True
    personItem = personItemAddDone.callArgs[0][0]
    personTextEdit = personItem.findChildren(QQuickItem, "textEdit")[0]
    dlg.mouseDClickItem(personTextEdit)
    dlg.keyClicksClear(personTextEdit)
    dlg.keyClicks(personTextEdit, person.fullNameOrAlias())
    popupListView = dlg.findItem(f"{peoplePickerItem}.popupListView")
    dlg.sceneModel.refreshProperty("peopleModel")
    dlg.clickListViewItem_actual(popupListView, person.fullNameOrAlias())


def _set_required_fields(dlg, kind=EventKind.Birth):

    RESET_FOCUS = False
    RETURN_TO_FINISH = False

    #

    if kind:
        dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))

    #

    # TODO: Custom events, and/or Custom Pair-Bond events.
    # https://alaskafamilysystems.atlassian.net/browse/FD-42
    # dlg.keyClicks("descriptionEdit", "Something happened")

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


def test_init(dlg):
    assert [
        i for i in dlg.findItem("kindBox").property("model")
    ] == EventKind.menuLabels()


def test_init_with_existing_people(dlg):
    existingPeopleA = [
        Person(name="Joseph", lastName="Donner"),
        Person(name="Josephina", lastName="Donner"),
    ]
    existingPeopleB = [
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
    ]
    dlg.scene.addItems(*(existingPeopleA + existingPeopleB))
    dlg.setExistingPeopleA(existingPeopleA)
    dlg.setExistingPeopleB(existingPeopleB)
    assert {x.id for x in dlg.existingPeopleA()} == {x.id for x in existingPeopleA}
    assert [x.id for x in dlg.existingPeopleB()] == [x.id for x in existingPeopleB]


def test_add_new_person(dlg):
    scene = dlg.sceneModel.scene
    submitted = util.Condition(dlg.submitted)
    _add_new_person(dlg, "peoplePickerA", "John Doe", returnToFinish=False)
    _set_required_fields(dlg)
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


def test_add_existing_person(qtbot, dlg):
    scene = dlg.sceneModel.scene
    existingPerson = Person(name="John", lastName="Doe")
    scene.addItems(existingPerson)
    submitted = util.Condition(dlg.submitted)
    _set_required_fields(dlg, kind=EventKind.Cutoff)
    _add_existing_person(dlg, "peoplePickerA", existingPerson)

    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1, "submitted signal emitted too many times"
    assert len(scene.people()) == 1


@pytest.mark.parametrize("kind", [x for x in EventKind if not EventKind.isDyadic(x)])
def test_monadic_event_people_pickers(dlg, kind):
    dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))
    assert dlg.itemProp("peoplePickerB", "visible") == False
    assert dlg.itemProp("peopleBLabel", "visible") == False


@pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isDyadic(x)])
def test_dyadic_event_people_pickers(dlg, kind):
    dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))
    assert dlg.itemProp("peoplePickerB", "visible") == True
    assert dlg.itemProp("peopleBLabel", "visible") == True


@pytest.mark.skip("Not finished")
def test_startDateTime_pickers(qtbot, dlg):
    dlg.clear()

    DATE_TIME = util.Date(2023, 2, 1)

    _run_dateTimePickers(
        dlg, DATE_TIME, "startDateButtons", "startDatePicker", "startTimePicker"
    )
    assert dlg.rootProp("startDateTime") == DATE_TIME


@pytest.mark.skip("Not finished")
def test_endDateTime_pickers(qtbot, dlg):
    dlg.clear()

    DATE_TIME = util.Date(2023, 2, 1)

    dlg.mouseClick("isDateRangeBox")
    assert dlg.itemProp("isDateRangeBox", "checked")

    _run_dateTimePickers(
        dlg, DATE_TIME, "endDateButtons", "endDatePicker", "endTimePicker"
    )
    assert dlg.rootProp("endDateTime") == DATE_TIME


def test_validation(qtbot, dlg):
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
    dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(EventKind.Custom))

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


@pytest.mark.skip("Not finished")
def test_add_new_person_born(dlg):
    scene = dlg.sceneModel.scene
    submitted = util.Condition(dlg.submitted)
    _set_required_fields(dlg)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1, "submitted signal emitted too many times"

    scene = dlg.sceneModel.scene
    assert len(scene.people()) == 1, f"Incorrect number of people added to scene"
    person = scene.query1(name="John", lastName="Doe")
    assert person, f"Could not find created person {ONE_NAME}"
    assert len(person.events()) == 1, f"Incorrect number of events added to scene"
    event = person.events()[0]
    assert event.uniqueId() == EventKind.Birth.value
    assert event.description == EventKind.Birth.name


@pytest.mark.parametrize("kind", [x for x in EventKind if x != EventKind.Custom])
def test_description_disabled_for_uniqueId(dlg, kind):
    dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))
    assert dlg.itemProp("descriptionEdit", "enabled") == False


# def test_add_new_people_pair_bond(dlg):
#     scene = dlg.sceneModel.scene


@pytest.mark.skip("Not finished")
def test_add_dyadic_event_with_one_person_selected(qtbot, dlg):
    _set_required_fields(dlg, people=False)
    _add_new_person(dlg)
    qtbot.clickOkAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_EVENT_DYADIC,
    )


@pytest.mark.skip("Not finished")
@pytest.mark.parametrize("eventKind", [x for x in EventKind if EventKind.isDyadic(x)])
def test_add_dyadic_event_with_three_people_selected(qtbot, dlg, eventKind):
    _set_required_fields(dlg, kind=False, people=False)
    _add_new_person(dlg)
    dlg.clickComboBoxItem("kindBox", eventKind.name)
    qtbot.clickOkAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_EVENT_DYADIC,
    )


@pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isMonadic(x)])
def test_dynamic_fields_for_monadic(dlg, kind):
    dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))
    # _set_required_fields(dlg, kind=kind)
    assert dlg.itemProp("descriptionEdit", "enabled") == bool(kind == EventKind.Custom)
    assert dlg.itemProp("peopleALabel", "text") == EventKind.personALabel(kind)
    assert dlg.itemProp("peopleBLabel", "visible") == False
    assert dlg.itemProp("peoplePickerB", "visible") == False


@pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isPairBond(x)])
def test_dynamic_fields_for_pair_bond_kind(dlg, kind):
    _set_required_fields(dlg, kind=kind)
    assert dlg.itemProp("descriptionEdit", "enabled") == False
    assert dlg.itemProp("peopleALabel", "text") == EventKind.personALabel(kind)
    assert dlg.itemProp("peopleBLabel", "visible") == True
    assert dlg.itemProp("peoplePickerB", "visible") == True
    assert dlg.itemProp("peopleBLabel", "text") == EventKind.personBLabel(kind)


@pytest.mark.parametrize("kind", [x for x in EventKind if not EventKind.isDyadic(x)])
def test_dynamic_fields_for_non_dyadic_kind(dlg, kind):
    _set_required_fields(dlg, kind=kind)
    assert dlg.itemProp("descriptionEdit", "enabled") == bool(kind == EventKind.Custom)
    assert dlg.itemProp("peopleALabel", "text") == EventKind.personALabel(kind)
    assert dlg.itemProp("peopleBLabel", "visible") == EventKind.isDyadic(kind)
    assert dlg.itemProp("peoplePickerB", "visible") == EventKind.isDyadic(kind)
    assert dlg.itemProp("peopleBLabel", "text") == EventKind.personBLabel(kind)


# def test_person_help_text_add_one_person(qtbot, dlg):
#     _set_required_fields(dlg, people=False)
#     _add_new_person(dlg)
#     dlg.clickComboBoxItem("kindBox", EventKind.Birth.name)
#     assert (
#         dlg.itemProp("eventHelpText", "text")
#         == AddAnythingDialog.S_EVENT_MULTIPLE_INDIVIDUALS
#     )


# def test_dyadic_with_gt_two_people(qtbot, dlg):
#     _set_required_fields(dlg, people=False)
#     _add_new_person(dlg, firstName="John", lastName="Doe")
#     _add_new_person(dlg, firstName="Jane", lastName="Doe")
#     _add_new_person(dlg, firstName="Joseph", lastName="Belgard")
#     dlg.clickComboBoxItem("kindBox", EventKind.Birth.name)
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
