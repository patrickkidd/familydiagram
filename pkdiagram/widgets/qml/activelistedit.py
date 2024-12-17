import logging

from pkdiagram.pyqt import QQuickItem, QApplication
from pkdiagram.widgets import QmlWidgetHelper

_log = logging.getLogger(__name__)


class ActiveListEdit:

    def __init__(self, view: QmlWidgetHelper, item: QQuickItem):
        assert item is not None, "ActiveListEdit item is None"
        self._view = view
        self._item = item

    def root(self) -> QQuickItem:
        return self._view.qml.rootObject()

    def delegate(self, itemName: str, throw=True) -> QQuickItem:
        """
        Because they are frequently deleted and recreated. try not to re-use
        the return value.
        """
        QApplication.processEvents()
        listView = self._item.property("listView")
        delegates = listView.property("delegates").toVariant()
        foundTags = [x.property("itemName") for x in delegates]
        try:
            delegate = next(x for x in delegates if x.property("itemName") == itemName)
        except StopIteration:
            if throw:
                raise RuntimeError(
                    f"Could not find ActiveListEdit row '{itemName}', only found: {foundTags}"
                )
            else:
                return None
        else:
            return delegate

    def textEdit(self, itemName: str) -> QQuickItem:
        return self.delegate(itemName).property("textEdit")

    def checkBox(self, itemName: str) -> QQuickItem:
        return self.delegate(itemName).property("checkBox")

    def renameRow(self, oldName: str, newName: str):
        self._view.mouseDClickItem(self.textEdit(oldName))
        assert (
            self.textEdit(oldName).property("editMode") == True
        ), f"Could not double-click to edit tag '{oldName}'"
        self._view.keyClicksItem(
            self.textEdit(oldName),
            newName,
            returnToFinish=True,
        )
        assert (
            self.textEdit(newName).property("text") == newName
        ), f"Could not rename tag '{oldName}' to {newName}"

    def clickAddAndRenameRow(self, itemName: str):
        model = self._item.property("model")
        addButton = self._item.property("crudButtons").property("addButtonItem")
        wasTags = [model.data(model.index(0, 0)) for i in range(model.rowCount())]
        self._view.mouseClickItem(addButton)
        nowTags = [model.data(model.index(0, 0)) for i in range(model.rowCount())]
        newTag = list(set(nowTags).difference(set(wasTags)))[0]
        self.renameRow(newTag, itemName)

    def clickActiveBox(self, itemName: str):
        model = self._item.property("model")
        assert (
            model.rowCount() > 0
        ), "Can't click the tag activate checkbox if the TagsModel is empty"
        #
        delegate = self.delegate(itemName)
        checkBox = delegate.property("checkBox")
        className = checkBox.metaObject().className()
        if not className.startswith("CheckBox"):
            raise ValueError(f"Expected a CheckBox, got {className}")
        iTag = delegate.property("iTag")
        was = model.data(model.index(iTag, 0), role=model.ActiveRole)
        assert (
            checkBox.isVisible() == True
        ), f"Cannot click tag checkbox for '{itemName}' if it isn't enabled"
        assert (
            checkBox.isEnabled() == True
        ), f"Cannot click tag checkbox for '{itemName}' if it isn't enabled."
        self._view.mouseClickItem(checkBox)
        QApplication.processEvents()
        assert (
            model.data(model.index(iTag, 0), role=model.ActiveRole) != was
        ), f"Checkbox for list item '{itemName}' did not change check state"
