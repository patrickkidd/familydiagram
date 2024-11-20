"""
Not used yet, left here for reference.
"""

import logging

from pkdiagram.pyqt import (
    Qt,
    pyqtSlot,
    QSortFilterProxyModel,
    qmlRegisterType,
    QModelIndex,
)
from pkdiagram.models import ModelHelper


_log = logging.getLogger(__name__)


class PeopleSearchModel(QSortFilterProxyModel, ModelHelper):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex):
        # Implement custom filtering logic here
        # For example, only accept rows where the first column's data matches the filter
        filter_text = self.filterRegExp().pattern()
        if filter_text:
            index = self.sourceModel().index(source_row, 0, source_parent)
            return filter_text.lower() in self.sourceModel().data(index).lower()
        return True

    def lessThan(self, left, right):
        # Implement custom sorting logic here
        # For example, sort by the data in the first column
        left_data = self.sourceModel().data(left)
        right_data = self.sourceModel().data(right)
        return left_data.lower() < right_data.lower()

    @pyqtSlot(str)
    def updateFilter(self, filterText):
        _log.info(filterText)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterFixedString(filterText)
        self.invalidateFilter()


qmlRegisterType(PeopleSearchModel, "PK.Models", 1, 0, "PeopleSearchModel")
