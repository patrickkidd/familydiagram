import pytest
import mock

from pkdiagram.pyqt import Qt, QDateTime
from pkdiagram.models import PersonPropertiesModel
from pkdiagram.scene import Scene, Person
from pkdiagram import util


pytestmark = [
    pytest.mark.component("PersonPropertiesModel"),
    pytest.mark.depends_on("Scene"),
]


@pytest.fixture
def model(scene):
    _model = PersonPropertiesModel()
    _model.scene = scene
    return _model


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


@pytest.mark.parametrize("deceasedDateTime", [QDateTime(), util.Date(1990, 1, 1)])
def test_set_age_on_deceased_one_person(scene, model, deceasedDateTime):
    personA = Person(deceased=True)
    personA.setDeceasedDateTime(deceasedDateTime)
    scene.addItems(personA)
    model.items = [personA]
    with mock.patch(
        "PyQt5.QtCore.QDateTime.currentDateTime", return_value=util.Date(2000, 1, 1)
    ):
        model.age = 10
    if deceasedDateTime:
        assert personA.birthDateTime() == model.deceasedDateTime.addYears(-10)
    else:
        assert personA.birthDateTime() == util.Date(1990, 1, 1)


@pytest.mark.parametrize("deceasedDateTime", [QDateTime(), util.Date(1990, 1, 1)])
def test_set_age_on_deceased_multiple_people(scene, model, deceasedDateTime):
    personA = Person(deceased=True)
    personB = Person(deceased=True)
    personA.setDeceasedDateTime(deceasedDateTime)
    personB.setDeceasedDateTime(deceasedDateTime)
    scene.addItems(personA, personB)
    model.items = [personA, personB]
    with mock.patch(
        "PyQt5.QtCore.QDateTime.currentDateTime", return_value=util.Date(2000, 1, 1)
    ):
        model.age = 10
    if deceasedDateTime:
        assert personA.birthDateTime() == model.deceasedDateTime.addYears(-10)
        assert personB.birthDateTime() == model.deceasedDateTime.addYears(-10)
    else:
        assert personA.birthDateTime() == util.Date(1990, 1, 1)
        assert personB.birthDateTime() == util.Date(1990, 1, 1)
