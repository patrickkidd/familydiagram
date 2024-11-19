import bisect


class SortedList:
    """sortedcontainers.SortedList was throwing ValueError for items in the list."""

    def __init__(self):
        self._list = []

    def __repr__(self):
        return self._list.__repr__()

    def __len__(self):
        return len(self._list)

    def __getitem__(self, i):
        return self._list[i]

    def bisect_right(self, x):
        return bisect.bisect_right(self._list, x)

    def add(self, x):
        bisect.insort_right(self._list, x)

    def remove(self, x):
        self._list.remove(x)

    def index(self, x):
        return self._list.index(x)

    def to_list(self):
        return list(self._list)
