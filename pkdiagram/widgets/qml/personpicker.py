import logging

from pkdiagram import util
from pkdiagram.pyqt import QApplication, QQuickItem
from pkdiagram import QmlWidgetHelper


_log = logging.getLogger(__name__)


def _validate(personPickerItem):
    if not personPickerItem.metaObject().className().startswith("PersonPicker"):
        raise TypeError(
            f"Expected a PersonPicker, got {personPickerItem.metaObject().className()}"
        )
    elif not personPickerItem.property("visible"):
        raise ValueError(f"Expected PersonPicker '{personPickerItem}' to be visible.")


def set_new_person(
    dlg: QmlWidgetHelper,
    textInput: str,
    personPicker: str = "personPicker",
    gender: str = None,
    returnToFinish: bool = True,
    resetFocus: bool = False,
) -> QQuickItem:
    # _log.info(f"set_new_person('{textInput}', {returnToFinish})")

    personPickerItem = dlg.findItem(personPicker)
    _validate(personPickerItem)

    if gender is None:
        gender = util.PERSON_KIND_NAMES[0]

    # textEdit = dlg.findChild(QQuickItem, "textEdit")
    assert dlg.itemProp(f"{personPicker}.popupListView", "visible") == False
    dlg.keyClicks(
        f"{personPicker}.textEdit",
        textInput,
        resetFocus=resetFocus,
        returnToFinish=returnToFinish,
    )
    if gender:
        dlg.clickComboBoxItem(f"{personPicker}.genderBox", gender)
    QApplication.processEvents()


def set_existing_person(
    dlg: QmlWidgetHelper,
    person: str,
    autoCompleteInput: str = None,
    personPicker: str = "personPicker",
    returnToFinish: bool = False,
    resetFocus: bool = False,
) -> QQuickItem:
    if not autoCompleteInput:
        autoCompleteInput = person.fullNameOrAlias()

    personPickerItem = dlg.findItem(personPicker)
    _validate(personPickerItem)

    # _log.info(
    #     f"set_existing_person('{personPicker}.textEdit', '{autoCompleteInput}', returnToFinish={returnToFinish})"
    # )
    assert dlg.itemProp(f"{personPicker}.popupListView", "visible") == False
    numVisibleAutoCompleteItemsUpdated = util.Condition(
        personPickerItem.numVisibleAutoCompleteItemsUpdated
    )
    dlg.keyClicks(
        f"{personPicker}.textEdit",
        autoCompleteInput,
        resetFocus=resetFocus,
        returnToFinish=returnToFinish,
    )
    assert numVisibleAutoCompleteItemsUpdated.wait() == True
    assert dlg.itemProp(f"{personPicker}.textEdit", "text") == autoCompleteInput
    assert dlg.itemProp(f"{personPicker}.popupListView", "visible") == True
    QApplication.processEvents()
    assert dlg.itemProp(f"{personPicker}.popupListView", "numVisibleItems") > 0
    if person:
        dlg.clickListViewItem_actual(
            f"{personPicker}.popupListView", person.fullNameOrAlias()
        )
        assert dlg.itemProp(f"{personPicker}.popupListView", "visible") == False
