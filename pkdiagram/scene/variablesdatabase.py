import copy, bisect

from sortedcontainers import SortedDict


class VariablesDatabase:
    """Enables a quick cached lookup of item variable states for a given date.
    Just returns last variable value for the item in chronological order.
    """

    def __init__(self):
        #   attr: {
        #           dateTime: value,
        #           dateTime: value
        #   }
        self._data = SortedDict()

    def clear(self):
        self._data = SortedDict()

    def set(self, attr, date, value):
        # https://stackoverflow.com/questions/7934547/python-find-closest-key-in-a-dictionary-from-the-given-input-key

        attrEntry = self._data.setdefault(attr, SortedDict())
        attrEntry[date] = value

    def unset(self, attr, date):
        attrEntry = self._data.setdefault(attr, SortedDict())
        if attrEntry and date in attrEntry:
            del attrEntry[date]

    def get(self, attr, date):
        """Returns: (value, changed)"""
        ret = (None, False)
        attrEntry = self._data.get(attr)
        if attrEntry:
            if date in attrEntry:
                # value changed on this date
                ret = (attrEntry[date], True)
            elif date < attrEntry.peekitem(0)[0]:
                # value hasn't been set by this date
                ret = (None, False)
            else:
                # defer to prior date entry with a value set for attr
                dates = attrEntry.keys()
                index = bisect.bisect_right(dates, date)
                lastDate = dates[index - 1]
                ret = (attrEntry[lastDate], False)
        return ret

    def clone(self):
        x = VariablesDatabase()
        x._data = copy.deepcopy(self._data)
        return x
