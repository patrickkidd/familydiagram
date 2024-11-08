import pytest

from pkdiagram.pyqt import *
from pkdiagram import Person, Scene, PersonPropertiesModel


pytestmark = [
    pytest.mark.component("PersonPropertiesModel"),
    pytest.mark.depends_on("Scene"),
]


def test_checkStates(simpleScene):

    personA = Person(showMiddleName=False)
    personB = Person(showMiddleName=True)
    simpleScene.addItem(personA)
    simpleScene.addItem(personB)

    model = PersonPropertiesModel()
    model.items = [personA, personB]
    assert model.showMiddleName == Qt.PartiallyChecked

    personA.setShowMiddleName(True)
    assert model.showMiddleName == Qt.Checked


def _test_prop_returns():

    model = PersonPropertiesModel()

    def assertNoneAreNone():
        attrs = model.classProperties(PersonPropertiesModel)
        for kwargs in attrs:
            x = model._cachedPropGetter(kwargs)
            if x is None:
                Debug(kwargs)
                assert x == model.defaultFor(kwargs["attr"])

    assertNoneAreNone()

    personA = Person()
    personB = Person()
    scene = Scene()
    scene.addItems(personA, personB)
    model.items = [personA, personB]
    assertNoneAreNone()
