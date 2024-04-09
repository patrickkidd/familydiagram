import logging

import pytest

from pkdiagram import util, objects
from pkdiagram.pyqt import Qt, QApplication, QVBoxLayout, QWidget, QQuickItem
from pkdiagram import Scene, Person, QmlWidgetHelper, SceneModel


_log = logging.getLogger(__name__)


def set_new_person(
    dlg: QmlWidgetHelper,
    textInput: str,
    personPicker: str = "personPicker",
    gender: str = None,
    returnToFinish: bool = True,
) -> QQuickItem:
    _log.info(f"set_new_person('{textInput}', {returnToFinish})")

    if gender is None:
        gender = util.PERSON_KIND_NAMES[0]

    # textEdit = dlg.findChild(QQuickItem, "textEdit")
    assert dlg.itemProp(f"{personPicker}.popupListView", "visible") == False
    dlg.keyClicks(
        f"{personPicker}.textEdit",
        textInput,
        resetFocus=False,
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
) -> QQuickItem:
    if not autoCompleteInput:
        autoCompleteInput = person.fullNameOrAlias()

    _log.info(
        f"set_existing_person('{personPicker}.textEdit', '{autoCompleteInput}', returnToFinish={returnToFinish})"
    )
    assert dlg.itemProp(f"{personPicker}.popupListView", "visible") == False
    personPickerItem = dlg.findItem(personPicker)
    numVisibleAutoCompleteItemsUpdated = util.Condition(
        personPickerItem.numVisibleAutoCompleteItemsUpdated
    )
    dlg.keyClicks(
        f"{personPicker}.textEdit",
        autoCompleteInput,
        resetFocus=False,
        returnToFinish=False,
    )
    assert numVisibleAutoCompleteItemsUpdated.wait() == True
    assert dlg.itemProp(f"{personPicker}.textEdit", "text") == autoCompleteInput
    assert dlg.itemProp(f"{personPicker}.popupListView", "visible") == True
    assert dlg.itemProp(f"{personPicker}.popupListView", "numVisibleItems") > 0
    if person:
        dlg.clickListViewItem_actual(
            f"{personPicker}.popupListView", person.fullNameOrAlias()
        )
        assert dlg.itemProp(f"{personPicker}.popupListView", "visible") == False
