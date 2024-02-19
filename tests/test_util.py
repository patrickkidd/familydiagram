import os.path, tempfile
import mock
import pytest
from pkdiagram.pyqt import QDate, QDateTime, QComboBox, QRect, QMessageBox, QTimer
from pkdiagram import util


def test_dates():
    bday = util.Date(1980, 5, 11)
    assert bday == util.validatedDateTimeText("05/11/1980")
    assert util.dateString(bday) == "05/11/1980"


def test_dateTimes():
    bday = util.Date(1980, 5, 11, 15, 35)
    assert bday == util.validatedDateTimeText("05/11/1980 3:35 pm")
    assert util.dateString(bday) == "05/11/1980"
    assert util.dateTimeString(bday) == "05/11/1980 3:35 pm"


def test_dateTimes_useTime():
    bday = util.Date(1980, 5, 11, 15, 35)
    assert bday == util.validatedDateTimeText("05/11/1980", "3:35 pm")
    assert util.dateString(bday) == "05/11/1980"
    assert util.dateTimeString(bday) == "05/11/1980 3:35 pm"


def test_init_person_box(simpleScene):
    p1 = simpleScene.query1(name="p1")
    cb = QComboBox()
    util.initPersonBox(simpleScene, cb, selected=p1)
    assert p1 is not None
    assert cb.currentText() == "p1"

    # TODO: test `exclude` param


def test_date_overlap():

    def date(x):
        return QDateTime(QDate(x, 1, 1))

    # inside
    assert util.dateRangesOverlap(date(2000), date(2003), date(2001), date(2002))
    # before + inside
    assert util.dateRangesOverlap(date(2000), date(2002), date(1999), date(2001))
    # inside + after
    assert util.dateRangesOverlap(date(2000), date(2002), date(2001), date(2004))
    # before
    assert not util.dateRangesOverlap(date(2000), date(2001), date(1998), date(1999))
    # after
    assert not util.dateRangesOverlap(date(2000), date(2001), date(2002), date(2003))


def test_QRect_contains():
    CUtil = util.CUtil
    assert CUtil.QRect_contains_QRect(QRect(0, 0, 10, 10), QRect(1, 1, 9, 9))
    assert not CUtil.QRect_contains_QRect(QRect(0, 0, 10, 10), QRect(-1, -1, 9, 9))
    assert not CUtil.QRect_contains_QRect(QRect(1, 1, 9, 9), QRect(0, 0, 10, 10))


def test_qenum():
    assert util.qenum(QMessageBox, QMessageBox.No) == "QMessageBox.No"


def test_fblocked():
    class A:
        def __init__(self):
            self.count = 0

        def one(self):
            self.count += 1
            self.two()

        @util.fblocked
        def two(self):
            """Block just one method call."""
            self.count += 1
            self.one()

        @util.fblocked
        def three(self):
            """Block self but not two()."""
            self.count += 1
            self.two()

    a = A()
    a.one()
    assert a.count == 3

    a.two()
    assert a.count == 5  # would be three if not fblocked

    a.three()
    assert a.count == 8


def test_blocked_exception():

    inner = mock.MagicMock()

    class MyClass:
        @util.blocked
        def myfunc(self):
            if throw:
                raise RuntimeError("here")
            else:
                inner()

    myClass = MyClass()

    throw = True
    with pytest.raises(RuntimeError):
        myClass.myfunc()
    assert inner.call_count == 0

    throw = False
    myClass.myfunc()
    assert inner.call_count == 1


def test_Condition_lambda_condition():
    cond = util.Condition(condition=lambda: cond.callCount > 0)
    timer = QTimer()
    timer.setInterval(0)
    timer.timeout.connect(cond)
    # Zero-length timer shouldn't run until first idle frame
    # opened up by the &.wait() call below.
    timer.start()

    # Should block until the very next idle frame after condition is met,
    # i.e. after the first time the timer times out.
    # Timeout exception should not be raised in the meantime.
    # So call count should only be 1 when wait returns.
    cond.wait()
    assert cond.callCount == 1

    timer.stop()


def test_write_read_with_hash(tmp_path):
    fpath = os.path.join(tmp_path, "somefile")
    BDATA = b"1235"
    util.writeWithHash(fpath, BDATA)
    bdata = util.readWithHash(fpath)
    assert BDATA == bdata
