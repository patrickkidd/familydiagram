import pytest

from pkdiagram.pyqt import Qt
from pkdiagram import util
from pkdiagram.scene import EventKind, Person, Marriage, Event, marriage
from pkdiagram.views import QmlDrawer


pytestmark = [pytest.mark.component("MarriageProperties")]


@pytest.fixture
def marriage(scene):
    personA, personB = Person(name="personA"), Person(name="personB")
    marriage = Marriage(personA=personA, personB=personB)
    scene.addItems(personA, personB, marriage)
    return marriage


@pytest.fixture
def view(qtbot, scene, qmlEngine):
    qmlEngine.setScene(scene)
    _view = QmlDrawer(
        qmlEngine, "qml/MarriageProperties.qml", propSheetModel="marriageModel"
    )
    _view.checkInitQml()
    _view.scene = scene
    _view.marriageModel = _view.rootProp("marriageModel")
    qtbot.addWidget(_view)
    _view.resize(600, 800)

    yield _view

    _view.deinit()


@pytest.fixture
def model(view):
    return view.rootProp("marriageModel")


def test_show_init(view, scene, marriage):
    view.marriageModel.items = [marriage]
    view.marriageModel.scene = scene

    assert view.itemProp("itemTitle", "text") == "(Pair-Bond): %s & %s" % (
        marriage.personA().name(),
        marriage.personB().name(),
    )


## Aggregate Properties


def test_aggregate_properties(scene, model, marriage):
    model.items = [marriage]
    assert model.anyMarriedEvents == False
    assert model.anySeparatedEvents == False
    assert model.anyDivorcedEvents == False


def test_anyMarriedEvents(scene, model, marriage):
    model.items = [marriage]
    assert model.anyMarriedEvents == False
    assert model.anySeparatedEvents == False
    assert model.anyDivorcedEvents == False

    scene.addItems(
        Event(
            EventKind.Married,
            marriage.personA(),
            spouse=marriage.personB(),
            dateTime=util.Date(1900, 1, 1),
        ),
        Event(
            EventKind.Separated,
            marriage.personA(),
            spouse=marriage.personB(),
            dateTime=util.Date(1910, 1, 1),
        ),
        Event(
            EventKind.Divorced,
            marriage.personA(),
            spouse=marriage.personB(),
            dateTime=util.Date(1920, 1, 1),
        ),
        batch=False,
    )
    assert model.anyMarriedEvents == True
    assert model.anySeparatedEvents == True
    assert model.anyDivorcedEvents == True


## Properties


def test_marriedBox(marriage, view):
    view.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True

    view.mouseClick("marriedBox")
    assert marriage.married() == False


def test_separatedBox(marriage, view):
    view.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert marriage.separated() == False

    view.mouseClick("separatedBox")
    assert marriage.married() == True
    assert marriage.separated() == True


def test_divorcedBox(marriage, view):
    view.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert marriage.separated() == False
    assert marriage.divorced() == False

    view.mouseClick("divorcedBox")
    assert marriage.married() == True
    assert marriage.separated() == True
    assert marriage.divorced() == True


@pytest.mark.parametrize("propName", ["hideDetails", "hideDates"])
def test_divorcedBox_extras(marriage, mp, propName):
    view.rootProp("marriageModel").items = [marriage]
    assert marriage.prop(propName).get() == False

    view.mouseClick(f"{propName}Box")
    assert marriage.prop(propName).get() == True

    view.mouseClick(f"{propName}Box")
    assert marriage.prop(propName).get() == False


def test_married_disabled_when_divorced(marriage, view):
    view.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert view.itemProp("marriedBox", "enabled") == True
    assert view.itemProp("separatedBox", "enabled") == True
    assert view.itemProp("divorcedBox", "checkState") == Qt.Unchecked

    view.mouseClick("divorcedBox")
    assert marriage.divorced() == True
    assert view.itemProp("marriedBox", "enabled") == False
    assert view.itemProp("separatedBox", "enabled") == False


def test_divorced_disabled_when_divorce_events(scene, marriage, view):
    view.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert marriage.divorced() == False
    assert view.itemProp("marriedBox", "enabled") == True
    assert view.itemProp("separatedBox", "enabled") == True
    assert view.itemProp("divorcedBox", "enabled") == True

    event = scene.addItem(
        Event(
            EventKind.Divorced,
            person=marriage.personA(),
            spouse=marriage.personB(),
            dateTime=util.Date(2000, 1, 1),
        )
    )
    scene.addItem(event)
    assert view.itemProp("marriedBox", "enabled") == False
    assert view.itemProp("separatedBox", "enabled") == False
    assert view.itemProp("divorcedBox", "enabled") == False


def test_married_becomes_enabled_after_delete_married_event(scene, marriage, view):
    married = scene.addItem(
        Event(
            EventKind.Married,
            person=marriage.personA(),
            spouse=marriage.personB(),
            dateTime=util.Date(2000, 1, 1),
        )
    )
    scene.addItem(married)
    view.rootProp("marriageModel").items = [marriage]
    assert view.itemProp("marriedBox", "enabled") == False

    married.setParent(None)
    assert view.itemProp("marriedBox", "enabled") == True


def test_married_separated_divorced_disabled_with_events(scene, marriage, view):
    view.rootProp("marriageModel").items = [marriage]
    assert view.itemProp("marriedBox", "enabled") == True
    assert view.itemProp("separatedBox", "enabled") == True
    assert view.itemProp("divorcedBox", "enabled") == True

    event = Event(
        EventKind.Shift,
        marriage.personA(),
        spouse=marriage.personB(),
        description="Something happened",
    )
    scene.addItem(event)
    assert view.itemProp("marriedBox", "enabled") == False
    assert view.itemProp("separatedBox", "enabled") == False
    assert view.itemProp("divorcedBox", "enabled") == False


def test_married_separated_pen(marriage, view):
    view.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert marriage.pen().style() == Qt.SolidLine

    marriage.setSeparated(True)
    assert marriage.pen().style() == Qt.SolidLine


def test_married_separated_divorced(marriage, view):
    scene = marriage.scene()
    view.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True  # default
    assert marriage.isVisible() == True
    assert marriage.pen().style() == Qt.SolidLine
    assert marriage.separationStatusFor(scene.currentDateTime()) == None
    assert marriage.separationIndicator.isVisible() == False

    view.mouseClick("marriedBox")
    assert marriage.married() == False
    assert marriage.separated() == False
    assert marriage.divorced() == False
    assert marriage.isVisible() == True
    assert marriage.pen().style() == Qt.DashLine
    assert marriage.separationStatusFor(scene.currentDateTime()) == None
    assert marriage.separationIndicator.isVisible() == False

    view.mouseClick("separatedBox")
    assert marriage.married() == False
    assert marriage.separated() == True
    assert marriage.divorced() == False
    assert marriage.isVisible() == True
    assert (
        marriage.separationStatusFor(scene.currentDateTime())
        == EventKind.Separated.value
    )
    assert marriage.separationIndicator.isVisible() == True
    assert marriage.pen().style() == Qt.DashLine

    view.mouseClick("divorcedBox")
    assert marriage.married() == True
    assert marriage.separated() == True
    assert marriage.divorced() == True
    assert marriage.isVisible() == True
    assert (
        marriage.separationStatusFor(scene.currentDateTime())
        == EventKind.Divorced.value
    )
    assert marriage.separationIndicator.isVisible() == True
    assert marriage.pen().style() == Qt.SolidLine

    view.mouseClick("divorcedBox")
    assert marriage.married() == True
    assert marriage.separated() == True
    assert marriage.divorced() == False
    assert marriage.isVisible() == True
    assert (
        marriage.separationStatusFor(scene.currentDateTime())
        == EventKind.Separated.value
    )
    assert marriage.separationIndicator.isVisible() == True
    assert marriage.pen().style() == Qt.SolidLine


# def test_add_marriage_event(marriage, view):
# #     view.rootProp('marriageModel').items = [marriage]
#     view.setCurrentTab('timeline')
#     assert len(marriage.events()) == 0

#     view.mouseClick('addEventButton')
