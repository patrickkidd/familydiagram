from pkdiagram.pyqt import Qt, QObject
from pkdiagram import util, objects, ModelHelper


class MyItem(objects.Item):

    objects.Item.registerProperties(
        [
            {"attr": "myint", "type": int, "default": -1},
            {"attr": "noDefaultNoType"},
            {"attr": "noDefaultWithType", "type": int},
            {"attr": "defaultWithType", "type": int, "default": 9000},
            {"attr": "someBool", "type": bool, "convertTo": Qt.CheckState},
        ]
    )

    def __init__(self, **kwargs):
        super().__init__()
        self.setProperties(**kwargs)  # pass to Item.__init__ instead?


class Model(QObject, ModelHelper):

    PROPERTIES = objects.Item.adjustedClassProperties(
        MyItem,
        [{"attr": "newEntry", "type": int, "default": 678}, {"attr": "newEntryNoType"}],
    )

    ModelHelper.registerQtProperties(PROPERTIES)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._newEntry = self.defaultFor("newEntry")
        self._newEntryNoType = self.defaultFor("newEntryNoType")
        self.initModelHelper()

    def get(self, propName):
        if propName == "newEntry":
            return self._newEntry
        elif propName == "newEntryNoType":
            return self._newEntryNoType
        else:
            return super().get(propName)

    def set(self, propName, x):
        if propName == "newEntry":
            if x != self._newEntry:
                self._newEntry = x
                self.newEntryChanged.emit(x)
        if propName == "newEntryNoType":
            if x != self._newEntryNoType:
                self._newEntryNType = x
                self.newEntryNoTypeChanged.emit(x)
        else:
            return super().set(propName, x)


def test_items_property():
    item1 = MyItem()
    item2 = MyItem()
    model = Model()
    model.items = [item1, item2]
    assert model.items == [item1, item2]


def test_signals():

    item1 = MyItem(myint=10)
    item2 = MyItem()

    model = Model()
    changed = util.Condition()
    model.myintChanged.connect(changed)
    model.items = [item1, item2]

    assert changed.callCount == 0

    model.myint = 123
    assert changed.callCount == 1

    model.resetMyint()
    assert changed.callCount == 2


def test_custom_setter():

    model = Model()
    item = MyItem()
    model.items = [item]
    assert model.newEntry == model.defaultFor("newEntry")

    model.newEntry = 123
    assert model.newEntry == 123

    model.setNewEntry(123)
    assert model.newEntry == 123


def test_default():

    model = Model()
    # test prior to init
    assert model.defaultFor("noDefaultNoType") == ""
    assert model.defaultFor("noDefaultWithType") == 0
    assert model.defaultFor("defaultWithType") == 9000
    assert model.defaultFor("newEntryNoType") == ""

    itemWithValues = MyItem(
        noDefaultNoType="asd", noDefaultWithType=777, defaultWithType=1333
    )
    model.items = [itemWithValues]
    assert model.defaultFor("noDefaultNoType") == ""
    assert model.defaultFor("noDefaultWithType") == 0
    assert model.defaultFor("defaultWithType") == 9000
    assert model.noDefaultNoType == "asd"
    assert model.noDefaultWithType == 777
    assert model.defaultWithType == 1333
    assert model.newEntry == 678
    assert model.newEntryNoType == ""

    itemWithoutValues = MyItem()
    model.items = [itemWithoutValues]
    assert model.defaultFor("noDefaultNoType") == ""
    assert model.defaultFor("noDefaultWithType") == 0
    assert model.defaultFor("defaultWithType") == 9000
    assert model.noDefaultNoType == ""
    assert model.noDefaultWithType == 0
    assert model.defaultWithType == 9000
    assert model.newEntryNoType == ""


def test_sameOf():

    def get():
        get.count += 1
        return get.count

    get.count = 0

    item1 = MyItem(myint=123, defaultWithType=333)
    item2 = MyItem(myint=321, defaultWithType=333)
    model = Model()
    model.items = [item1, item2]
    assert model.sameOf("myint", lambda x: get()) == -1
    assert model.sameOf("defaultWithType", lambda x: x.defaultWithType()) == 333


def test_same():
    item1 = MyItem(myint=123, defaultWithType=333)
    item2 = MyItem(myint=321, defaultWithType=333)
    model = Model()

    # test with items
    assert model.same("myint") == None
    assert model.same("defaultWithType") == None
    assert model.same("noDefaultNoType") == None

    #
    model.items = [item1, item2]
    assert model.same("myint") == -1
    assert model.same("defaultWithType") == 333
    assert model.same("noDefaultNoType") == ""


def test_init_separate():

    item1 = MyItem(myint=123)
    item2 = MyItem(myint=321)

    model = Model()
    model.items = [item1, item2]

    assert model.myint == model.defaultFor("myint")

    item2.prop("myint").set(123)
    assert model.myint == 123

    item2.prop("myint").set(333)
    assert model.myint == model.defaultFor("myint")


def test_reset():

    item1 = MyItem(myint=123)
    item2 = MyItem(myint=321)

    model = Model()
    model.items = [item1, item2]
    myintChanged = util.Condition(model.myintChanged)

    model.myint = 222
    assert myintChanged.callCount == 1
    assert item1.prop("myint").isset() == True
    assert item2.prop("myint").isset() == True
    assert item1.prop("myint").get() != model.defaultFor("myint")
    assert item2.prop("myint").get() != model.defaultFor("myint")

    model.resetMyint()
    assert myintChanged.callCount == 2
    assert item1.prop("myint").isset() == False
    assert item2.prop("myint").isset() == False
    assert item1.prop("myint").get() == model.defaultFor("myint")
    assert item2.prop("myint").get() == model.defaultFor("myint")


def test_deinit():

    item1 = MyItem(myint=123)
    item2 = MyItem(myint=123)

    model = Model()
    model.items = [item1, item2]

    assert model.myint == 123

    model.resetItems()
    assert model.myint == -1


def test_convertTo():
    item1 = MyItem(someBool=True)
    item2 = MyItem(someBool=False)
    item3 = MyItem()

    model = Model()
    model.items = [item1, item2, item3]
    assert model.someBool == Qt.PartiallyChecked

    item1.setSomeBool(True)
    item2.setSomeBool(True)
    item3.setSomeBool(True)
    assert model.someBool == Qt.Checked

    item1.setSomeBool(False)
    item2.setSomeBool(False)
    item3.setSomeBool(False)
    assert model.someBool == Qt.Unchecked

    item1.setSomeBool(False)
    item2.setSomeBool(True)
    item3.setSomeBool(False)
    assert model.someBool == Qt.PartiallyChecked

    # test default without 'default'
    item1.prop("someBool").reset()
    item2.prop("someBool").reset()
    item3.prop("someBool").reset()
    assert (
        model.someBool == Qt.PartiallyChecked
    )  # because &.same() returns None, which is converted to partial check


def test_onProperty_convertTo():
    """Test that a property value is property converted before it is
    tested against the prop sheet model cache.
    """

    item1 = MyItem(someBool=True)
    item2 = MyItem(someBool=False)
    item3 = MyItem(someBool=False)
    model = Model()
    model.items = [item1, item2, item3]
    assert model.someBool == Qt.PartiallyChecked

    someBoolChanged = util.Condition()
    model.someBoolChanged.connect(someBoolChanged)
    assert someBoolChanged.callCount == 0

    # should convert the value before testing, still resulting in
    # someBool == Qt.PartiallyChecked and not emit the someBoolChanged signal
    item2.setSomeBool(True)
    assert model.someBool == Qt.PartiallyChecked
    assert someBoolChanged.callCount == 0

    # should convert the value before testing, but now resulting in
    # someBool == Qt.Checked and should emit the someBoolChanged signal
    item3.setSomeBool(True)
    assert model.someBool == Qt.Checked
    assert someBoolChanged.callCount == 1
