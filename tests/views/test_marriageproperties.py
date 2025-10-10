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
def mp(qtbot, scene, qmlEngine):
    qmlEngine.setScene(scene)
    mp = QmlDrawer(
        qmlEngine, "qml/MarriageProperties.qml", propSheetModel="marriageModel"
    )
    mp.checkInitQml()
    mp.scene = scene
    mp.marriageModel = mp.rootProp("marriageModel")
    qtbot.addWidget(mp)
    mp.resize(600, 800)

    yield mp

    mp.deinit()


@pytest.fixture
def model(mp):
    return mp.rootProp("marriageModel")


def test_show_init(mp, scene, marriage):
    mp.marriageModel.items = [marriage]
    mp.marriageModel.scene = scene

    assert mp.itemProp("itemTitle", "text") == "(Pair-Bond): %s & %s" % (
        marriage.personA().name(),
        marriage.personB().name(),
    )


## Aggregate Properties


def test_anyMarriedEvents(scene, model, marriage):
    model.items = [marriage]
    assert model.anyMarriedEvents() == False

    scene.addItem(
        Event(
            EventKind.Married,
            marriage.personA(),
            spouse=marriage.personB(),
            dateTime=util.Date(1900, 1, 1),
        )
    )
    assert model.anyMarriedEvents() == True


def test_anySeparatedEvents(scene, model, marriage):
    model.items = [marriage]
    assert model.anySeparatedEvents() == False

    scene.addItem(
        Event(
            EventKind.Separated,
            marriage.personA(),
            spouse=marriage.personB(),
            dateTime=util.Date(1900, 1, 1),
        )
    )
    assert model.anySeparatedEvents() == True


def test_anyDivorcedEvents(scene, model, marriage):
    model.items = [marriage]
    assert model.anyDivorcedEvents() == False

    scene.addItem(
        Event(
            EventKind.Divorced,
            marriage.personA(),
            spouse=marriage.personB(),
            dateTime=util.Date(1900, 1, 1),
        )
    )
    assert model.anyDivorcedEvents() == True


def test_everMarried(scene, model, marriage):
    model.items = [marriage]
    assert model.everMarried() == True

    marriage.setMarried(False)
    assert model.everMarried() == False

    scene.addItem(
        Event(EventKind.Married, marriage.personA(), spouse=marriage.personB())
    )
    assert model.everMarried() == True

    marriage.setMarried(True)
    assert model.everMarried() == True


def test_everSeparated(scene, marriage, model):
    assert model.everSeparated() == False

    marriage.setSeparated(True)
    assert model.everSeparated() == True

    marriage.setSeparated(False)
    assert model.everSeparated() == False

    scene.addItem(
        Event(EventKind.Separated, marriage.personA(), spouse=marriage.personB())
    )
    assert model.everSeparated() == True

    marriage.setSeparated(True)
    assert model.everSeparated() == True


def test_everDivorced(scene, marriage, model):
    assert model.everDivorced() == False

    marriage.setDivorced(True)
    assert model.everDivorced() == True

    marriage.setDivorced(False)
    assert model.everDivorced() == False

    scene.addItem(
        Event(EventKind.Divorced, marriage.personA(), spouse=marriage.personB())
    )
    assert model.everDivorced() == True

    marriage.setDivorced(True)
    assert model.everDivorced() == True


## Properties


def test_marriedBox(marriage, mp):
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True

    mp.mouseClick("marriedBox")
    assert marriage.married() == False


def test_separatedBox(marriage, mp):
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert marriage.separated() == False

    mp.mouseClick("separatedBox")
    assert marriage.married() == True
    assert marriage.separated() == True


def test_divorcedBox(marriage, mp):
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert marriage.separated() == False
    assert marriage.divorced() == False

    mp.mouseClick("divorcedBox")
    assert marriage.married() == True
    assert marriage.separated() == True
    assert marriage.divorced() == True


@pytest.mark.parametrize("propName", ["hideDetails", "hideDates"])
def test_divorcedBox_extras(marriage, mp, propName):
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.prop(propName).get() == False

    mp.mouseClick(f"{propName}Box")
    assert marriage.prop(propName).get() == True

    mp.mouseClick(f"{propName}Box")
    assert marriage.prop(propName).get() == False


def test_married_disabled_when_divorced(marriage, mp):
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert mp.itemProp("marriedBox", "enabled") == True
    assert mp.itemProp("separatedBox", "enabled") == True
    assert mp.itemProp("divorcedBox", "checkState") == Qt.Unchecked

    mp.mouseClick("divorcedBox")
    assert marriage.divorced() == True
    assert mp.itemProp("marriedBox", "enabled") == False
    assert mp.itemProp("separatedBox", "enabled") == False


def test_divorced_disabled_when_divorce_events(scene, marriage, mp):
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert marriage.divorced() == False
    assert mp.itemProp("marriedBox", "enabled") == True
    assert mp.itemProp("separatedBox", "enabled") == True
    assert mp.itemProp("divorcedBox", "enabled") == True

    event = scene.addItem(
        Event(
            EventKind.Divorced,
            person=marriage.personA(),
            spouse=marriage.personB(),
            dateTime=util.Date(2000, 1, 1),
        )
    )
    scene.addItem(event)
    assert mp.itemProp("marriedBox", "enabled") == False
    assert mp.itemProp("separatedBox", "enabled") == False
    assert mp.itemProp("divorcedBox", "enabled") == False


def test_married_becomes_enabled_after_delete_married_event(scene, marriage, mp):
    married = scene.addItem(
        Event(
            EventKind.Married,
            person=marriage.personA(),
            spouse=marriage.personB(),
            dateTime=util.Date(2000, 1, 1),
        )
    )
    scene.addItem(married)
    mp.rootProp("marriageModel").items = [marriage]
    assert mp.itemProp("marriedBox", "enabled") == False

    married.setParent(None)
    assert mp.itemProp("marriedBox", "enabled") == True


def test_married_separated_divorced_disabled_with_events(scene, marriage, mp):
    mp.rootProp("marriageModel").items = [marriage]
    assert mp.itemProp("marriedBox", "enabled") == True
    assert mp.itemProp("separatedBox", "enabled") == True
    assert mp.itemProp("divorcedBox", "enabled") == True

    event = Event(
        EventKind.Shift,
        marriage.personA(),
        spouse=marriage.personB(),
        description="Something happened",
    )
    scene.addItem(event)
    assert mp.itemProp("marriedBox", "enabled") == False
    assert mp.itemProp("separatedBox", "enabled") == False
    assert mp.itemProp("divorcedBox", "enabled") == False


def test_married_separated_pen(marriage, mp):
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert marriage.pen().style() == Qt.SolidLine

    marriage.setSeparated(True)
    assert marriage.pen().style() == Qt.SolidLine


def test_married_separated_divorced(marriage, mp):
    scene = marriage.scene()
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True  # default
    assert marriage.isVisible() == True
    assert marriage.pen().style() == Qt.SolidLine
    assert marriage.separationStatusFor(scene.currentDateTime()) == None
    assert marriage.separationIndicator.isVisible() == False

    mp.mouseClick("marriedBox")
    assert marriage.married() == False
    assert marriage.separated() == False
    assert marriage.divorced() == False
    assert marriage.isVisible() == True
    assert marriage.pen().style() == Qt.DashLine
    assert marriage.separationStatusFor(scene.currentDateTime()) == None
    assert marriage.separationIndicator.isVisible() == False

    mp.mouseClick("separatedBox")
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

    mp.mouseClick("divorcedBox")
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

    mp.mouseClick("divorcedBox")
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


# def test_add_marriage_event(marriage, mp):
# #     mp.rootProp('marriageModel').items = [marriage]
#     mp.setCurrentTab('timeline')
#     assert len(marriage.events()) == 0

#     mp.mouseClick('addEventButton')
