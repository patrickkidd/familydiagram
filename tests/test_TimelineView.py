import pytest

from pkdiagram.pyqt import *
from pkdiagram import util, QmlWidgetHelper, objects, Scene
from pkdiagram.objects import Person, Event
from pkdiagram.models import SceneModel


class TimelineViewTest(QWidget, QmlWidgetHelper):

    QmlWidgetHelper.registerQmlMethods([{"name": "test_getDelegates", "return": True}])

    def __init__(self, parent=None):
        super().__init__(parent)
        Layout = QVBoxLayout(self)
        scene = Scene()
        sceneModel = SceneModel()
        sceneModel.scene = scene
        self.initQmlWidgetHelper(
            "tests/qml/TimelineViewTest.qml", sceneModel=sceneModel
        )
        self.checkInitQml()
        self.setItemProp("timelineView", "model", scene.timelineModel)
        self.resize(600, 800)


@pytest.fixture
def tv(qtbot):

    tv = TimelineViewTest()
    qtbot.addWidget(tv)
    qtbot.waitActive(tv)
    tv.show()
    yield tv

    tv.hide()


def test_init(tv):
    scene = tv.rootProp("sceneModel").scene
    assert tv.itemProp("table", "visible") == False
    assert tv.itemProp("noEventsLabel", "visible") == True
    # delegates = tvt.test_getDelegates().toVariant()
    # assert tvt.itemProp('table', 'rows') == 1
    # print('asserting...')
    # assert delegates != []
    # delegates = []
    # table = tvt.findItem('table')
    # for child in table.childItems():
    #     if child.property('thisRow') is not None:
    #         delegates.append(child)
    # assert len(delegates) == 1


def test_some_events_shown(tv):
    scene = tv.rootProp("sceneModel").scene
    person = Person(name="Hey", lastName="There")
    event = Event(
        person, dateTime=util.Date(2001, 1, 1), description="Something happened"
    )
    scene.addItem(person, event)
    util.waitALittle()
    assert tv.itemProp("table", "visible") == True
    assert tv.itemProp("noEventsLabel", "visible") == False


def test_no_events(tv):
    assert tv.itemProp("noEventsLabel", "visible") == True
    assert tv.itemProp("noEventsLabel", "text") == util.S_NO_EVENTS_TEXT


def test_some_events_filtered_out(tv):
    scene = tv.rootProp("sceneModel").scene
    person = Person(name="Hey", lastName="You")
    events = [
        Event(
            parent=person,
            description="Something happened {i}".format(i=i),
            dateTime=util.Date(2010, 5, 1 + i),
        )
        for i in range(3)
    ]
    scene.addItems(person)
    scene.searchModel.startDateTime = util.Date(2020, 1, 1)
    util.waitALittle()
    assert tv.itemProp("noEventsLabel", "visible") == True
    assert tv.itemProp("noEventsLabel", "text") == util.S_NO_EVENTS_TEXT
