import logging

from pkdiagram.pyqt import (
    QQuickItem,
    QEventLoop,
    QTimer,
)
from pkdiagram import util
from pkdiagram.scene import Person
from pkdiagram.widgets import QmlWidgetHelper


_log = logging.getLogger(__name__)


def waitForPersonPickers():
    # For some reason a QEventLoop is needed to finish laying out the component
    # instead of QApplication.processEvents()
    loop = QEventLoop()
    QTimer.singleShot(10, loop.quit)  # may need to be longer?
    loop.exec()


class TestPeoplePicker:

    def __init__(self, view: QmlWidgetHelper, item: QQuickItem):
        self.view = view
        self.item = item
        self.model = item.property("model")

    def _validate(self):
        if not self.item.metaObject().className().startswith("PeoplePicker"):
            raise TypeError(
                f"Expected a PeoplePicker, got {self.item.metaObject().className()}"
            )
        elif not self.item.property("visible"):
            raise ValueError(f"Expected PeoplePicker '{self.item}' to be visible.")

    def add_and_keyClicks(
        self,
        textInput: str,
        returnToFinish: bool = True,
        resetFocus: bool = False,
    ) -> QQuickItem:

        _log.debug(f"add_and_keyClicks('{textInput}', '{self.item}', {returnToFinish})")

        self._validate()

        itemAddDone = util.Condition(self.item.itemAddDone)
        waitForPersonPickers()
        #
        self.view.mouseClickItem(
            self.item.property("buttons").property("addButtonItem")
        )
        assert itemAddDone.wait() == True, "PersonPicker delegate not created"
        itemDelegate = itemAddDone.callArgs[-1][0]
        textEdit = itemDelegate.property("textEdit")
        popupListView = itemDelegate.property("popupListView")
        assert popupListView.property("visible") == False
        self.view.keyClicks(
            textEdit, textInput, resetFocus=resetFocus, returnToFinish=returnToFinish
        )
        return itemDelegate

    def add_new_person(
        self,
        textInput: str,
        gender: str = None,
        returnToFinish=True,
        resetFocus: bool = False,
    ) -> QQuickItem:

        self._validate()

        itemDelegate = self.add_and_keyClicks(
            textInput,
            returnToFinish=returnToFinish,
            resetFocus=resetFocus,
        )
        if gender is not None:
            genderLabel = next(
                x["name"]
                for x in util.PERSON_KINDS
                if x["kind"] == util.PERSON_KIND_FEMALE
            )

            genderBox = itemDelegate.findChild(QQuickItem, "genderBox")
            assert genderBox is not None, f"Could not find genderBox for {itemDelegate}"
            self.view.clickComboBoxItem(genderBox, genderLabel)

        return itemDelegate

    def add_existing_person(
        self,
        person: Person,
        autoCompleteInput: str = None,
        gender: str = None,
        returnToFinish: bool = False,
        resetFocus: bool = False,
    ) -> QQuickItem:

        self._validate()

        if autoCompleteInput is None:
            autoCompleteInput = person.fullNameOrAlias()
        itemDelegate = self.add_and_keyClicks(
            autoCompleteInput,
            returnToFinish=returnToFinish,
            resetFocus=resetFocus,
        )
        popupListView = itemDelegate.property("popupListView")
        assert popupListView.property("visible") == True
        self.view.clickListViewItem_actual(popupListView, person.fullNameOrAlias())

        if gender is not None:
            genderLabel = next(
                x["name"] for x in util.PERSON_KINDS if x["kind"] == gender
            )
            genderBox = itemDelegate.findChild(QQuickItem, "genderBox")
            assert genderBox is not None, f"Could not find genderBox for {itemDelegate}"
            self.view.clickComboBoxItem(genderBox, genderLabel)

        return itemDelegate

    def set_existing_people(self, people: list[Person]):
        itemAddDone = util.Condition(self.item.itemAddDone)
        self.item.setExistingPeople(people)
        util.waitALittle()
        while itemAddDone.callCount < len(people):
            _log.info(
                f"Waiting for {len(people) - itemAddDone.callCount} / {len(people)} itemAddDone signals"
            )
            assert itemAddDone.wait() == True
        # _log.info(f"Got {itemAddDone.callCount} / {len(people)} itemAddDone signals")

    def delete_person(self, delegate: QQuickItem):
        _log.debug(f"delete_person({delegate})")
        self.view.mouseClickItem(delegate)
        self.view.mouseClickItem(
            self.item.property("buttons").property("removeButtonItem")
        )

    def _get_role_id(model, role_name):
        roles = model.roleNames()
        for role_id, name in roles.items():
            if name == role_name:
                return role_id
