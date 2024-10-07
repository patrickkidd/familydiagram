import logging

from pkdiagram import util
from pkdiagram.pyqt import (
    QQuickItem,
    QEventLoop,
    QTimer,
)
from pkdiagram import Person, QmlWidgetHelper


_log = logging.getLogger(__name__)


def waitForPersonPickers():
    # For some reason a QEventLoop is needed to finish laying out the component
    # instead of QApplication.processEvents()
    loop = QEventLoop()
    QTimer.singleShot(10, loop.quit)  # may need to be longer?
    loop.exec()


def _validate(peoplePickerItem):
    if not peoplePickerItem.metaObject().className().startswith("PeoplePicker"):
        raise TypeError(
            f"Expected a PeoplePicker, got {peoplePickerItem.metaObject().className()}"
        )
    elif not peoplePickerItem.property("visible"):
        raise ValueError(f"Expected PeoplePicker '{peoplePickerItem}' to be visible.")


def add_and_keyClicks(
    dlg: QmlWidgetHelper,
    textInput: str,
    peoplePicker="peoplePicker",
    returnToFinish: bool = True,
    resetFocus: bool = False,
) -> QQuickItem:

    _log.debug(f"add_and_keyClicks('{textInput}', '{peoplePicker}', {returnToFinish})")

    peoplePickerItem = dlg.findItem(peoplePicker)
    _validate(peoplePickerItem)

    itemAddDone = util.Condition(peoplePickerItem.itemAddDone)
    waitForPersonPickers()
    #
    dlg.mouseClick(f"{peoplePicker}.addButton")
    assert itemAddDone.wait() == True, "PersonPicker delegate not created"
    itemDelegate = itemAddDone.callArgs[-1][0]
    textEdit = itemDelegate.findChild(QQuickItem, "textEdit")
    popupListView = itemDelegate.findChild(QQuickItem, "popupListView")
    assert popupListView.property("visible") == False
    dlg.keyClicks(
        textEdit, textInput, resetFocus=resetFocus, returnToFinish=returnToFinish
    )
    return itemDelegate


def add_new_person(
    dlg: QmlWidgetHelper,
    textInput: str,
    peoplePicker="peoplePicker",
    gender: str = None,
    returnToFinish=True,
    resetFocus: bool = False,
) -> QQuickItem:

    peoplePickerItem = dlg.findItem(peoplePicker)
    _validate(peoplePickerItem)

    itemDelegate = add_and_keyClicks(
        dlg,
        textInput,
        peoplePicker=peoplePicker,
        returnToFinish=returnToFinish,
        resetFocus=resetFocus,
    )
    if gender is not None:
        genderLabel = next(
            x["name"] for x in util.PERSON_KINDS if x["kind"] == util.PERSON_KIND_FEMALE
        )

        genderBox = itemDelegate.findChild(QQuickItem, "genderBox")
        assert genderBox is not None, f"Could not find genderBox for {itemDelegate}"
        dlg.clickComboBoxItem(genderBox, genderLabel)

    return itemDelegate


def add_existing_person(
    picker: QmlWidgetHelper,
    person: Person,
    autoCompleteInput: str = None,
    peoplePicker="peoplePicker",
    gender: str = None,
    returnToFinish: bool = False,
    resetFocus: bool = False,
) -> QQuickItem:

    peoplePickerItem = picker.findItem(peoplePicker)
    _validate(peoplePickerItem)

    if autoCompleteInput is None:
        autoCompleteInput = person.fullNameOrAlias()
    itemDelegate = add_and_keyClicks(
        picker,
        autoCompleteInput,
        peoplePicker=peoplePicker,
        returnToFinish=returnToFinish,
        resetFocus=resetFocus,
    )
    popupListView = itemDelegate.findChild(QQuickItem, "popupListView")
    assert popupListView.property("visible") == True
    picker.clickListViewItem_actual(popupListView, person.fullNameOrAlias()) == True

    if gender is not None:
        genderLabel = next(x["name"] for x in util.PERSON_KINDS if x["kind"] == gender)
        genderBox = itemDelegate.findChild(QQuickItem, "genderBox")
        assert genderBox is not None, f"Could not find genderBox for {itemDelegate}"
        picker.clickComboBoxItem(genderBox, genderLabel)

    return itemDelegate


def delete_person(
    picker: QmlWidgetHelper, delegate: QQuickItem, peoplePicker="peoplePicker"
):
    _log.debug(f"delete_person({delegate})")
    picker.mouseClick(delegate)
    removeButton = picker.findItem("buttons_removeButton")
    picker.mouseClick(removeButton)


def _get_role_id(model, role_name):
    roles = model.roleNames()
    for role_id, name in roles.items():
        if name == role_name:
            return role_id
