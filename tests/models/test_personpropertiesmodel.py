import pytest

from pkdiagram.pyqt import Qt
from pkdiagram.models import PersonPropertiesModel
from pkdiagram.scene import Scene, Person


pytestmark = [
    pytest.mark.component("PersonPropertiesModel"),
    pytest.mark.depends_on("Scene"),
]


def test_read_checkStates(simpleScene):

    personA = Person(showMiddleName=False)
    personB = Person(showMiddleName=True)
    simpleScene.addItem(personA)
    simpleScene.addItem(personB)

    model = PersonPropertiesModel()
    model.items = [personA, personB]
    assert model.showMiddleName == Qt.PartiallyChecked

    #

    personA.setShowMiddleName(True)
    assert model.showMiddleName == Qt.Checked

    personA.setHideDetails(True)
    assert model.hideDetails == Qt.PartiallyChecked

    personA.setHideDates(True)
    assert model.hideDates == Qt.PartiallyChecked

    personA.setHideVariables(True)
    assert model.hideDates == Qt.PartiallyChecked

    #

    personB.setHideDetails(True)
    assert model.hideDetails == Qt.Checked

    personB.setHideDates(True)
    assert model.hideDates == Qt.Checked

    personB.setHideVariables(True)
    assert model.hideVariables == Qt.Checked


def _test_prop_returns():

    model = PersonPropertiesModel()

    def assertNoneAreNone():
        attrs = model.classProperties(PersonPropertiesModel)
        for kwargs in attrs:
            x = model._cachedPropGetter(kwargs)
            if x is None:
                log.info(kwargs)
                assert x == model.defaultFor(kwargs["attr"])

    assertNoneAreNone()

    personA = Person()
    personB = Person()
    scene = Scene()
    scene.addItems(personA, personB)
    model.items = [personA, personB]
    assertNoneAreNone()
