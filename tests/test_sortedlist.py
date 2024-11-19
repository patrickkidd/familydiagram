from pkdiagram import util


def test_SortedList():
    from sortedcontainers import SortedList

    d1 = util.Date(1955, 12, 3)
    d2 = util.Date(1980, 5, 11)
    d3 = util.Date(1980, 5, 11)
    d4 = util.Date(2015, 1, 1)
    stuff = SortedList()
    stuff.add(d1)
    stuff.add(d2)
    stuff.add(d3)
    stuff.add(d4)
    assert d2 in stuff
    assert d3 in stuff
