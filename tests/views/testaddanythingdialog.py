import logging

import mock

from pkdiagram import util
from pkdiagram.pyqt import (
    Q_RETURN_ARG,
    Qt,
    QMetaObject,
    QVariant,
    QQuickItem,
    QDateTime,
)
from pkdiagram.scene import LifeChange, Person, Marriage, PathItem
from pkdiagram.views import AddAnythingDialog

from tests.widgets import TestPersonPicker, TestPeoplePicker, TestActiveListEdit


_log = logging.getLogger(__name__)


class TestAddAnythingDialog:

    def __init__(self, view: AddAnythingDialog):
        self.view = view
        self.item = view.qml.rootObject()

        self.addButton = self.item.property("addButton")
        self.clearButton = self.item.property("clearButton")
        self.cancelButton = self.item.property("cancelButton")
        self.kindBox = self.item.property("kindBox")
        self.descriptionEdit = self.item.property("descriptionEdit")
        self.startDateButtons = self.item.property("startDateButtons")
        self.startDatePicker = self.item.property("startDatePicker")
        self.startTimePicker = self.item.property("startTimePicker")
        self.endDateButtons = self.item.property("endDateButtons")
        self.endDatePicker = self.item.property("endDatePicker")
        self.endTimePicker = self.item.property("endTimePicker")
        self.locationEdit = self.item.property("locationEdit")
        self.tagsEdit = self.item.property("tagsEdit")
        self.notesEdit = self.item.property("notesEdit")
        self.isDateRangeBox = self.item.property("isDateRangeBox")

        self.personPicker = TestPersonPicker(
            self.view, self.item.property("personPicker")
        )
        self.personAPicker = TestPersonPicker(
            self.view, self.item.property("personAPicker")
        )
        self.personBPicker = TestPersonPicker(
            self.view, self.item.property("personBPicker")
        )
        self.peoplePicker = TestPeoplePicker(
            self.view, self.item.property("peoplePicker")
        )
        self.moversPicker = TestPeoplePicker(
            self.view, self.item.property("moversPicker")
        )
        self.receiversPicker = TestPeoplePicker(
            self.view, self.item.property("receiversPicker")
        )

        self.personLabel = self.item.property("personLabel")
        self.peopleLabel = self.item.property("peopleLabel")
        self.moversLabel = self.item.property("moversLabel")
        self.receiversLabel = self.item.property("receiversLabel")

    # QmlWidgetHelper passthrough

    def rootProp(self, propName: str):
        return self.item.property(propName)

    # Methods

    def clickAddButton(self):
        self.view.mouseClickItem(self.addButton)

    def clickClearButton(self):
        self.view.mouseClickItem(self.clearButton)

    def clickCancelButton(self):
        self.view.mouseClickItem(self.cancelButton)

    def initForSelection(self, selection: list[PathItem]):
        if Marriage.marriageForSelection(selection):
            self.view.initForSelection(selection)
            # personAPickerItem = self.view.findItem("personAPicker")
            # itemAddDoneA = util.Condition(personAPickerItem.itemAddDone)
            # personBPickerItem = self.view.findItem("personBPicker")
            # itemAddDoneB = util.Condition(personBPickerItem.itemAddDone)
            # while itemAddDoneA.callCount < 1:
            #     _log.info(f"Waiting for {len(selection) - itemAddDone.callCount} / {len(selection)} itemAddDone signals")
            #     assert itemAddDoneA.wait() == True
            # while itemAddDoneB.callCount < 1:
            #     assert itemAddDoneB.wait() == True
        else:
            itemAddDone = util.Condition(self.peoplePicker.item.itemAddDone)
            self.view.initForSelection(selection)
            while itemAddDone.callCount < len(selection):
                _log.info(
                    f"Waiting for {len(selection) - itemAddDone.callCount} / {len(selection)} itemAddDone signals"
                )
                assert (
                    itemAddDone.wait() == True
                ), f"itemAddDone signal not emitted, called {itemAddDone.callCount} times"

    def set_person_picker_gender(self, personPicker, genderLabel):
        genderBox = self.personPicker.property("genderBox")
        assert genderBox is not None, f"Could not find genderBox for {personPicker}"
        self.view.clickComboBoxItem(genderBox, genderLabel)

    def set_people_picker_gender(self, peoplePicker, personIndex, genderLabel):
        peopleAList = self.view.findItem(peoplePicker)
        picker = QMetaObject.invokeMethod(
            peopleAList,
            "pickerAtIndex",
            Qt.DirectConnection,
            Q_RETURN_ARG(QVariant),
            personIndex,
        )
        assert (
            picker is not None
        ), f"Could not find picker for {peoplePicker}:{personIndex}"
        genderBox = picker.findChild("genderBox")
        assert (
            genderBox is not None
        ), f"Could not find genderBox for {peoplePicker}:{personIndex}"
        self.view.clickComboBoxItem(picker, genderLabel)

    def set_kind(self, kind: LifeChange):
        self.view.clickComboBoxItem(
            self.kindBox, LifeChange.menuLabelFor(kind), force=False
        )

    def set_description(self, description: str):
        self.view.keyClicksItem(self.descriptionEdit, description)

    # def set_new_person(
    #     self,
    #     personPicker: str,
    #     textInput: str,
    #     gender: str = None,
    #     returnToFinish: bool = True,
    #     resetFocus: bool = False,
    # ):
    #     set_new_person(
    #         self,
    #         textInput,
    #         personPicker,
    #         gender,
    #         returnToFinish=returnToFinish,
    #         resetFocus=resetFocus,
    #     )
    #     # _log.info(f"set_new_person('{personPicker}', '{textInput}')")
    #     # self.view.keyClicks(f"{personPicker}.textEdit", textInput, returnToFinish=True)
    #     if returnToFinish:
    #         assert self.view.itemProp(personPicker, "isSubmitted") == True
    #         assert self.view.itemProp(personPicker, "isNewPerson") == True
    #         assert self.view.itemProp(personPicker, "personName") == textInput
    #     else:
    #         assert self.view.itemProp(f"{personPicker}.textEdit", "text") == textInput

    # def set_existing_person(
    #     self,
    #     personPicker: str,
    #     person: Person,
    #     autoCompleteInput: str = None,
    #     returnToFinish: bool = False,
    #     resetFocus: bool = False,
    # ):
    #     # _log.info(
    #     #     f"_set_new_person('{personPicker}', {person}, autoCompleteInput='{autoCompleteInput}')"
    #     # )
    #     set_existing_person(
    #         self,
    #         person,
    #         autoCompleteInput,
    #         personPicker,
    #         returnToFinish=returnToFinish,
    #         resetFocus=resetFocus,
    #     )
    #     # assert self.view.itemProp(f"{personPicker}.popupListView", "visible") == False
    #     # if not autoCompleteInput:
    #     #     autoCompleteInput = person.fullNameOrAlias()
    #     # self.view.keyClicks(
    #     #     f"{personPicker}.textEdit",
    #     #     autoCompleteInput,
    #     #     resetFocus=False,
    #     #     returnToFinish=returnToFinish,
    #     # )
    #     # assert self.view.itemProp(f"{personPicker}.popupListView", "visible") == True
    #     # self.view.clickListViewItem_actual(
    #     #     f"personPicker.popupListView", person.fullNameOrAlias()
    #     # )

    # def add_new_person(
    #     self,
    #     peoplePicker: TestPeoplePicker,
    #     textInput: str,
    #     gender: str = None,
    #     returnToFinish: bool = True,
    #     resetFocus: bool = False,
    # ):
    #     add_new_person(
    #         self,
    #         textInput,
    #         peoplePicker=peoplePicker,
    #         gender=gender,
    #         returnToFinish=returnToFinish,
    #         resetFocus=resetFocus,
    #     )

    # def add_existing_person(
    #     self,
    #     peoplePicker: str,
    #     person: Person,
    #     autoCompleteInput: str = None,
    # ):
    #     add_existing_person(
    #         self, person, autoCompleteInput=autoCompleteInput, peoplePicker=peoplePicker
    #     )

    def set_dateTime(
        self,
        dateTime: QDateTime,
        buttonsItem,
        datePickerItem,
        timePickerItem,
        returnToFinish: bool = False,
        resetFocus: bool = False,
    ):

        S_DATE = util.dateString(dateTime)
        S_TIME = util.timeString(dateTime)

        # _log.info(
        #     f"Setting {buttonsItem}, {datePickerItem}, {timePickerItem} to {dateTime}"
        # )

        self.view.keyClicksItem(
            buttonsItem.property("dateTextInput"),
            S_DATE,
            returnToFinish=returnToFinish,
            resetFocus=resetFocus,
        )
        self.view.keyClicksItem(
            buttonsItem.property("timeTextInput"),
            S_TIME,
            returnToFinish=returnToFinish,
            resetFocus=resetFocus,
        )
        assert buttonsItem.property("dateTime") == dateTime
        assert datePickerItem.property("dateTime") == dateTime
        assert timePickerItem.property("dateTime") == dateTime

    def set_startDateTime(self, dateTime):
        self.set_dateTime(
            dateTime, self.startDateButtons, self.startDatePicker, self.startTimePicker
        )

    def set_isDateRange(self, on):
        if not self.item.property("isDateRange"):
            assert self.item.property("endDateTimeLabel").property("visible") == False
            assert self.endDateButtons.property("visible") == False
            assert self.endDatePicker.property("visible") == False
            assert self.endTimePicker.property("visible") == False
            assert (
                self.isDateRangeBox.property("visible") == True
            ), f"isDateRangeBox hidden; incorrect event kind '{self.item.property('kind')}'"
            self.isDateRangeBox.setProperty("checked", True)
            # self.view.mouseClick("isDateRangeBox")
            assert self.item.property("isDateRange") == True

    def set_endDateTime(self, dateTime):
        self.set_isDateRange(True)
        assert self.item.property("endDateTimeLabel").property("visible") == True
        assert self.endDateButtons.property("visible") == True
        assert self.endDatePicker.property("visible") == True
        assert self.endTimePicker.property("visible") == True
        self.set_dateTime(
            dateTime, self.endDateButtons, self.endDatePicker, self.endTimePicker
        )

        # Annoying behavior only in test (so far)
        # Re-set the checkbox since clicking into the text boxes seems to uncheck it
        if not self.item.property("isDateRange"):
            self.isDateRangeBox.setProperty("checked", True)

    def set_notes(self, notes):
        self.view.keyClicksItem(self.notesEdit, notes, returnToFinish=False)

    def expectedFieldLabel(self, expectedTextLabel: QQuickItem):
        name = expectedTextLabel.property("text")
        expectedText = self.view.S_REQUIRED_FIELD_ERROR.format(name=name)
        with mock.patch("PyQt5.QtWidgets.QMessageBox.warning") as warning:
            self.clickAddButton()
            assert warning.call_count == 1
            assert warning.call_args[0][0] == self.view
            assert warning.call_args[0][2] == expectedText

    def pickerNotSubmitted(self, pickerLabel: QQuickItem):
        name = pickerLabel.property("text")
        expectedText = self.view.S_PICKER_NEW_PERSON_NOT_SUBMITTED.format(
            pickerLabel=name
        )
        with mock.patch("PyQt5.QtWidgets.QMessageBox.warning") as warning:
            self.clickAddButton()
            assert warning.call_count == 1
            assert warning.call_args[0][0] == self.view
            assert warning.call_args[0][2] == expectedText

    def set_anxiety(self, x):
        self.view.setVariable("anxiety", x)

    def set_functioning(self, x):
        self.view.setVariable("functioning", x)

    def set_symptom(self, x):
        self.view.setVariable("symptom", x)

    def add_tag(self, tag: str):
        self.view.scrollChildToVisible(self.item.property("addPage"), self.tagsEdit)
        tagsEdit = TestActiveListEdit(self.view, self.tagsEdit)
        tagsEdit.clickAddAndRenameRow(tag)

    def set_active_tags(self, tags: list[str]):
        self.view.scrollChildToVisible(self.item.property("addPage"), self.tagsEdit)
        tagsEdit = TestActiveListEdit(self.view, self.tagsEdit)
        for tag in tags:
            tagsEdit.clickActiveBox(tag)

    # scripts

    def add_person_by_birth(self, personName: str, startDateTime) -> Person:
        self.set_kind(LifeChange.Birth)
        self.personPicker.set_new_person(personName)
        self.set_startDateTime(startDateTime)
        self.clickAddButton()
        person = self.view.scene.query1(methods={"fullNameOrAlias": personName})
        return person

    def add_marriage_to_person(self, person: Person, spouseName, startDateTime):
        pre_marriages = set(person.marriages)
        self.set_kind(LifeChange.Married)
        self.set_existing_person(self.personAPicker, person)
        self.personBPicker.set_new_person(spouseName)
        self.set_startDateTime(startDateTime)
        self.clickAddButton()
        spouse = self.view.scene.query1(methods={"fullNameOrAlias": spouseName})
        return (set(person.marriages) - pre_marriages).pop()

    def add_event_to_marriage(
        self, marriage: Marriage, kind: LifeChange, startDateTime
    ):
        pre_events = set(marriage.events())
        self.set_kind(kind)
        self.set_existing_person(self.personAPicker, marriage.personA())
        self.set_existing_person(self.personBPicker, marriage.personB())
        self.set_startDateTime(startDateTime)
        self.clickAddButton()
        return (set(marriage.events()) - pre_events).pop()
