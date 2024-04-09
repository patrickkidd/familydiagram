import logging

from pkdiagram import util, objects
from pkdiagram.pyqt import (
    QQuickItem,
    QEventLoop,
    QTimer,
)
from pkdiagram import Scene, Person, QmlWidgetHelper, SceneModel


_log = logging.getLogger(__name__)


def add_and_keyClicks(
    dlg: QmlWidgetHelper,
    textInput: str,
    peoplePicker="peoplePicker",
    returnToFinish: bool = True,
) -> QQuickItem:

    _log.info(f"add_and_keyClicks('{textInput}', '{peoplePicker}', {returnToFinish})")

    peoplePickerItem = dlg.findItem(peoplePicker)
    if not peoplePickerItem.metaObject().className().startswith("PeoplePicker"):
        raise TypeError(
            f"Expected a PeoplePicker, got {peoplePickerItem.metaObject().className()}"
        )
    elif not peoplePickerItem.property("visible"):
        raise ValueError(f"Expected PeoplePicker '{peoplePicker}' to be visible.")
    itemAddDone = util.Condition(peoplePickerItem.itemAddDone)
    # For some reason a QEventLoop is needed to finish laying out the component
    # instead of QApplication.processEvents()
    loop = QEventLoop()
    QTimer.singleShot(1, loop.quit)
    loop.exec()
    #
    dlg.mouseClick(f"{peoplePicker}.addButton")
    assert itemAddDone.wait() == True, "PersonPicker delegate not created"
    itemDelegate = itemAddDone.callArgs[-1][0]
    textEdit = itemDelegate.findChild(QQuickItem, "textEdit")
    popupListView = itemDelegate.findChild(QQuickItem, "popupListView")
    assert popupListView.property("visible") == False
    dlg.keyClicks(textEdit, textInput, resetFocus=False, returnToFinish=returnToFinish)
    return itemDelegate


def add_new_person(
    dlg: QmlWidgetHelper,
    textInput: str,
    peoplePicker="peoplePicker",
    gender: str = None,
    returnToFinish=True,
) -> QQuickItem:
    itemDelegate = add_and_keyClicks(
        dlg,
        textInput,
        peoplePicker=peoplePicker,
        returnToFinish=returnToFinish,
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
) -> QQuickItem:
    if autoCompleteInput is None:
        autoCompleteInput = person.fullNameOrAlias()
    itemDelegate = add_and_keyClicks(
        picker,
        autoCompleteInput,
        peoplePicker=peoplePicker,
        returnToFinish=False,
    )
    popupListView = itemDelegate.findChild(QQuickItem, "popupListView")
    assert popupListView.property("visible") == True
    picker.clickListViewItem_actual(popupListView, person.fullNameOrAlias()) == True
    return itemDelegate


def delete_person(
    picker: QmlWidgetHelper, delegate: QQuickItem, peoplePicker="peoplePicker"
):
    _log.info(f"delete_person({delegate})")
    picker.mouseClick(delegate)
    removeButton = picker.findItem("buttons_removeButton")
    picker.mouseClick(removeButton)


def _get_role_id(model, role_name):
    roles = model.roleNames()
    for role_id, name in roles.items():
        if name == role_name:
            return role_id
