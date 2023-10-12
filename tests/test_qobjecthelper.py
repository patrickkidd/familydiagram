import pytest
from pkdiagram.pyqt import QObject, QVariant
from pkdiagram import util, QObjectHelper


class SomeQObject(QObject):
    pass

class SomeModel(QObject, QObjectHelper):

    QObjectHelper.registerQtProperties([
        { 'attr': 'someQObject', 'type': QVariant },
        { 'attr': 'someUnimplementedObejct' }
    ])

    def __init__(self, parent=None, initQObjectHelper=True):
        super().__init__(parent)
        self._someQObject = None
        if initQObjectHelper:
            self.initQObjectHelper()

    def get(self, attr):
        if attr == 'someQObject':
            ret = self._someQObject
        else:
            ret = super().get(attr)
        return ret

    def set(self, attr, value):
        if attr == 'someQObject':
            self._someQObject = value
        else:
            super().set(attr, value)

    def reset(self, attr):
        if attr == 'someQObject':
            self._someQObject = None
            self.refreshProperty(attr)
    

def test_python_property():
    
    model = SomeModel()
    assert model.someQObject == None
    
    someQObject = SomeQObject()
    model.someQObject = someQObject
    assert model.someQObject == someQObject

    model.resetSomeQObject()
    assert model.someQObject == None


def test_unimplemented_python_property():
    
    model = SomeModel()

    with pytest.raises(AttributeError) as e:
        model.someUnimplementedObject == None
    

def test_reset_emits_changed_signal():

    model = SomeModel()
    someQObjectChanged = util.Condition(model.someQObjectChanged)
    
    model.someQObject = SomeQObject()
    assert someQObjectChanged.callCount == 1
    
    model.resetSomeQObject()
    assert someQObjectChanged.callCount == 2

    
def test_global_context():
    SOME_CONSTANT = 'blah'
    # SOME_SETTING = 'blue'

    _globalContext = locals()

    class Model(QObject, QObjectHelper):

        QObjectHelper.registerQtProperties([
            { 'attr': 'SOME_CONSTANT', 'constant': True, 'global': True }
            # { 'attr': 'SOME_CONSTANT', 'constant': False, 'global': True }
        ], globalContext=_globalContext)

        def __init__(self):
            super().__init__()
            self.initQObjectHelper()

    model = Model()
    assert model.SOME_CONSTANT == SOME_CONSTANT

    ## Setting globals doesn't work yet.
    ## Can't set attr on locals()/globalContext even though they ref same dict object
    
    # assert model.SOME_SETTING == 'blue'
    # Debug('>>>', id(locals()), locals()['SOME_SETTING'])
    # model.SOME_SETTING = 'yellow'
    # Debug('<<<', id(locals()), locals()['SOME_SETTING'])
    # assert SOME_SETTING == 'yellow'

class SomeOtherModel(SomeModel):

    QObjectHelper.registerQtProperties([
        { 'attr': 'someOtherQObject', 'type': QVariant },
    ])

    def __init__(self, parent=None):
        super().__init__(parent, initQObjectHelper=False)
        self._someOtherQObject = None
        self.initQObjectHelper()

    def get(self, attr):
        if attr == 'someOtherQObject':
            return self._someOtherQObject
        else:
            return super().get(attr)

    def set(self, attr, value):
        if attr == 'someOtherQObject':
            self._someOtherQObject = value
        else:
            super().set(attr, value)

    def reset(self, attr):
        if attr == 'someOtherQObject':
            self._someOtherQObject = None
        super().reset(attr)


class SomeOtherQObject(QObject):
    pass

def test_inheritance():
    model = SomeOtherModel()

    # make sure inherited properties still work

    assert model.someQObject == None
    
    someQObject = SomeQObject()
    model.someQObject = someQObject
    assert model.someQObject == someQObject

    model.resetSomeQObject()
    assert model.someQObject == None

    # make sure new properties still work

    assert model.someOtherQObject == None
    
    someOtherQObject = SomeOtherQObject()
    model.someOtherQObject = someOtherQObject
    assert model.someOtherQObject == someOtherQObject

    model.resetSomeOtherQObject()
    assert model.someOtherQObject == None


    
