import logging

from pkdiagram.pyqt import QQuickItem
from pkdiagram import util
from pkdiagram.pyqt import QApplication, QQuickItem
from pkdiagram.widgets import QmlWidgetHelper


_log = logging.getLogger(__name__)


class TestPersonPicker:

    def __init__(self, view: QmlWidgetHelper, item: QQuickItem):
        assert item is not None, "PersonPicker item is None"
        self.view = view
        self.item = item
        self.textEdit = self.item.property("textEdit")
        self.popupListView = self.item.property("popupListView")

    def _validate(self):
        if not self.item.metaObject().className().startswith("PersonPicker"):
            raise TypeError(
                f"Expected a PersonPicker, got {self.item.metaObject().className()}"
            )
        elif not self.item.property("visible"):
            raise ValueError(
                f"Expected PersonPicker '{self.item.metaObject().className()}[{self.item.objectName()}]' to be visible."
            )

    def set_new_person(
        self,
        nameInput: str,
        gender: str = None,
        returnToFinish: bool = True,
        resetFocus: bool = False,
    ) -> QQuickItem:
        # _log.info(f"set_new_person('{nameInput}', {returnToFinish})")

        self._validate()

        if gender is None:
            gender = util.PERSON_KIND_NAMES[0]

        # textEdit = self.view.findChild(QQuickItem, "textEdit")
        assert self.popupListView.property("visible") == False
        textEdit = self.item.property("textEdit")
        self.view.keyClicksItem(
            textEdit,
            nameInput,
            resetFocus=resetFocus,
            returnToFinish=returnToFinish,
        )
        if gender and returnToFinish:
            genderBox = self.item.property("genderBox")
            self.view.clickComboBoxItem(genderBox, gender)
        QApplication.processEvents()

    def set_existing_person(
        self,
        person: str,
        autoCompleteInput: str = None,
        returnToFinish: bool = False,
        resetFocus: bool = False,
    ) -> QQuickItem:
        if not autoCompleteInput:
            autoCompleteInput = person.fullNameOrAlias()

        self._validate()

        # _log.info(
        #     f"set_existing_person('{personPicker}.textEdit', '{autoCompleteInput}', returnToFinish={returnToFinish})"
        # )
        assert self.popupListView.property("visible") == False
        numVisibleAutoCompleteItemsUpdated = util.Condition(
            self.item.numVisibleAutoCompleteItemsUpdated
        )
        self.view.keyClicksItem(
            self.textEdit,
            autoCompleteInput,
            resetFocus=resetFocus,
            returnToFinish=returnToFinish,
        )
        assert numVisibleAutoCompleteItemsUpdated.wait() == True
        assert self.textEdit.property("text") == autoCompleteInput
        assert self.popupListView.property("visible") == True
        QApplication.processEvents()
        assert self.popupListView.property("numVisibleItems") > 0
        if person:
            self.view.clickListViewItem_actual(
                self.popupListView, person.fullNameOrAlias()
            )
            assert self.popupListView.property("visible") == False
