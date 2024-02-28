import pytest
import conftest
from test_marriage import noEvents
from pkdiagram.pyqt import Qt, QDate, QApplication, QDateTime
from pkdiagram import util, EventKinds, Person, Marriage, Event, Scene
from pkdiagram.qmldrawer import QmlDrawer


@pytest.fixture
def mp(qtbot, qmlScene, request):
    mp = QmlDrawer("qml/MarriageProperties.qml", propSheetModel="marriageModel")
    mp.checkInitQml()
    mp.scene = qmlScene
    mp.marriageModel = mp.rootProp("marriageModel")
    qtbot.addWidget(mp)
    mp.resize(600, 800)

    def cleanupMP():
        mp.rootProp("marriageModel").items = []

    request.addfinalizer(cleanupMP)
    return mp


@pytest.fixture
def marriageProps(qmlScene):
    return {"personAName": "", "personBName": ""}


def runMarriageProperties(mp, props):
    props = dict(props)
    props.update(updates)


def assertMarriageProperties(event, props, updates):
    assert mp.itemProp("titleLabel", "text") == props


def test_show_init(mp, qmlScene):
    m = qmlScene.marriages()[0]
    mp.marriageModel.items = [m]
    mp.marriageModel.scene = qmlScene

    assert mp.itemProp("itemTitle", "text") == "(Pair-Bond): %s & %s" % (
        m.personA().name(),
        m.personB().name(),
    )


def test_marriedBox(noEvents, mp):
    marriage = noEvents
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True

    mp.mouseClick("marriedBox")
    assert marriage.married() == False


def test_separatedBox(noEvents, mp):
    marriage = noEvents
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert marriage.separated() == False

    mp.mouseClick("separatedBox")
    assert marriage.married() == True
    assert marriage.separated() == True


def test_divorcedBox(noEvents, mp):
    marriage = noEvents
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert marriage.separated() == False
    assert marriage.divorced() == False

    mp.mouseClick("divorcedBox")
    assert marriage.married() == True
    assert marriage.separated() == True
    assert marriage.divorced() == True


def test_married_disabled_when_divorced(noEvents, mp):
    marriage = noEvents
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert mp.itemProp("marriedBox", "enabled") == True
    assert mp.itemProp("separatedBox", "enabled") == True
    assert mp.itemProp("divorcedBox", "checkState") == Qt.Unchecked

    mp.mouseClick("divorcedBox")
    assert marriage.divorced() == True
    assert mp.itemProp("marriedBox", "enabled") == False
    assert mp.itemProp("separatedBox", "enabled") == False


def test_divorced_disabled_when_divorce_events(noEvents, mp):
    marriage = noEvents
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert marriage.divorced() == False
    assert mp.itemProp("marriedBox", "enabled") == True
    assert mp.itemProp("separatedBox", "enabled") == True
    assert mp.itemProp("divorcedBox", "enabled") == True

    Event(
        parent=marriage,
        uniqueId=EventKinds.Divorced.value,
        dateTime=util.Date(2000, 1, 1),
    )
    assert mp.itemProp("marriedBox", "enabled") == False
    assert mp.itemProp("separatedBox", "enabled") == False
    assert mp.itemProp("divorcedBox", "enabled") == False


def test_married_becomes_enabled_after_delete_married_event(noEvents, mp):
    marriage = noEvents
    marriedEvent = Event(
        parent=marriage,
        uniqueId=EventKinds.Married.value,
        dateTime=util.Date(2000, 1, 1),
    )
    mp.rootProp("marriageModel").items = [marriage]
    assert mp.itemProp("marriedBox", "enabled") == False

    marriedEvent.setParent(None)
    assert mp.itemProp("marriedBox", "enabled") == True


def test_married_separated_divorced_disabled_with_events(noEvents, mp):
    marriage = noEvents
    mp.rootProp("marriageModel").items = [marriage]
    mp.itemProp("marriedBox", "enabled") == True
    mp.itemProp("separatedBox", "enabled") == True
    mp.itemProp("divorcedBox", "enabled") == True

    Event(parent=marriage, description="Something happened")
    mp.itemProp("marriedBox", "enabled") == False
    mp.itemProp("separatedBox", "enabled") == False
    mp.itemProp("divorcedBox", "enabled") == False


def test_married_separated_pen(noEvents, mp):
    marriage = noEvents
    scene = marriage.scene()
    mp.rootProp("marriageModel").items = [marriage]
    assert marriage.married() == True
    assert marriage.pen().style() == Qt.SolidLine

    marriage.setSeparated(True)
    assert marriage.pen().style() == Qt.SolidLine


def test_married_separated_divorced(noEvents, mp):
    marriage = noEvents
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
        == EventKinds.Separated.value
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
        == EventKinds.Divorced.value
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
        == EventKinds.Separated.value
    )
    assert marriage.separationIndicator.isVisible() == True
    assert marriage.pen().style() == Qt.SolidLine


# def test_add_marriage_event(noEvents, mp):
#     marriage = noEvents
#     mp.rootProp('marriageModel').items = [marriage]
#     mp.setCurrentTab('timeline')
#     assert len(marriage.events()) == 0

#     mp.mouseClick('addEventButton')
