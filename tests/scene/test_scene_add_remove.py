import os.path

import pytest
import mock

from pkdiagram.pyqt import Qt, QGraphicsView, QPointF, QDateTime, QMessageBox
from pkdiagram import util
from pkdiagram.scene import (
    Scene,
    Person,
    Marriage,
    Emotion,
    Event,
    MultipleBirth,
    Layer,
    PathItem,
    ChildOf,
    Callout,
)

pytestmark = [
    pytest.mark.component("Scene"),
    pytest.mark.depends_on("Item"),
]


@pytest.fixture(params=[True, False])
def undo(request):
    return request.param


@pytest.mark.skip("Cant figure out how to store datetimes per undo command.")
def test_undoStackDateTimes(scene):
    assert scene._undoStackDateTimes == {}

    person = Person(name="person")
    scene.addItem(person, undo=True)
    assert scene._undoStack.index() == 1
    assert scene._undoStackDateTimes == {0: QDateTime()}

    event1 = Event(
        parent=person, description="First datetime", dateTime=util.Date(2001, 1, 1)
    )
    scene.addItem(event1, undo=True)
    assert scene._undoStack.index() == 2
    assert scene.currentDateTime() == event1.dateTime()
    assert scene._undoStackDateTimes == {0: QDateTime(), 1: QDateTime()}

    event2 = Event(
        parent=person, description="Second datetime", dateTime=util.Date(2002, 1, 1)
    )
    scene.addItem(event2, undo=True)
    assert scene._undoStack.index() == 3
    assert scene.currentDateTime() == event2.dateTime()
    assert scene._undoStackDateTimes == {
        0: QDateTime(),
        1: QDateTime(),
        2: event1.dateTime(),
    }

    scene.undo()
    assert scene.currentDateTime() == event1.dateTime()
    assert scene._undoStackDateTimes == {
        0: QDateTime(),
        1: QDateTime(),
        2: event1.dateTime(),
    }
    assert scene._undoStack.index() == 2


## Add items


def test_add_person(scene, undo):
    personAdded = util.Condition(scene.personAdded)
    personRemoved = util.Condition(scene.personRemoved)
    person = Person(name="person")
    scene.addItem(person, undo=undo)
    assert personAdded.callCount == 1
    assert scene.people() == [person]
    scene.undo()
    if undo:
        assert personRemoved.callCount == 1
        assert scene.people() == []
    else:
        assert personRemoved.callCount == 0
        assert scene.people() == [person]


def test_add_marriage(scene, undo):
    marriageAdded = util.Condition(scene.marriageAdded)
    marriageRemoved = util.Condition(scene.marriageRemoved)
    person1 = Person(name="person1")
    person2 = Person(name="person2")
    marriage = Marriage(person1, person2)
    scene.addItems(person1, person2, marriage, undo=undo)
    assert marriageAdded.callCount == 1
    assert scene.people() == [person1, person2]
    assert scene.marriages() == [marriage]
    scene.undo()
    if undo:
        assert marriageRemoved.callCount == 1
        assert scene.people() == []
        assert scene.marriages() == []
    else:
        assert marriageRemoved.callCount == 0
        assert scene.people() == [person1, person2]
        assert scene.marriages() == [marriage]


def test_add_emotion(scene, undo):
    emotionAdded = util.Condition(scene.emotionAdded)
    emotionRemoved = util.Condition(scene.emotionRemoved)
    person1 = Person(name="person1")
    person2 = Person(name="person2")
    emotion = Emotion(
        person1, person2, startDateTime=util.Date(2001, 1, 1), kind=util.ITEM_CONFLICT
    )
    scene.addItems(person1, person2)
    scene.addItem(emotion, undo=undo)
    assert emotionAdded.callCount == 1
    assert scene.people() == [person1, person2]
    assert scene.emotions() == [emotion]
    scene.undo()
    if undo:
        assert scene.currentDateTime() == QDateTime()
        assert emotionRemoved.callCount == 1
        assert scene.emotions() == []
    else:
        assert scene.currentDateTime() == emotion.startDateTime()
        assert emotionRemoved.callCount == 0
        assert scene.emotions() == [emotion]


def test_add_layer(scene, undo):
    layerAdded = util.Condition(scene.layerAdded)
    layerRemoved = util.Condition(scene.layerRemoved)
    layer = Layer(name="layer")
    scene.addItem(layer, undo=undo)
    assert layerAdded.callCount == 1
    assert scene.layers() == [layer]
    scene.undo()
    if undo:
        assert layerRemoved.callCount == 1
        assert scene.layers() == []
    else:
        assert layerRemoved.callCount == 0
        assert scene.layers() == [layer]


def test_add_childof(scene, undo):
    person1 = Person(name="person1")
    person2 = Person(name="person2")
    marriage = Marriage(person1, person2)
    person3 = Person(name="person3")
    scene.addItems(person1, person2, marriage, person3)
    person3.setParents(marriage, undo=undo)
    assert person3.childOf._parents == marriage
    scene.undo()
    if undo:
        assert person3.childOf is None
    else:
        assert person3.childOf.parents() == marriage


def test_add_multipleBirth_read_file(scene):
    person1 = Person(name="person1")
    person2 = Person(name="person2")
    marriage = Marriage(person1, person2)
    person3 = Person(name="person3")
    person4 = Person(name="person4")
    scene.addItems(person1, person2, marriage, person3, person4)
    multipleBirth = MultipleBirth()
    scene.addItem(multipleBirth)
    multipleBirth._onSetParents(marriage)
    person3.setParents(multipleBirth)
    person4.setParents(multipleBirth)
    assert person3.childOf.multipleBirth == multipleBirth
    assert person4.childOf.multipleBirth == multipleBirth
    assert multipleBirth.children() == [person3, person4]


def test_add_multipleBirth_from_diagram(scene, undo):
    person1 = Person(name="person1")
    person2 = Person(name="person2")
    marriage = Marriage(person1, person2)
    person3 = Person(name="person3")
    person4 = Person(name="person4")
    scene.addItems(person1, person2, marriage, person3, person4)
    person3.setParents(marriage)
    person4.setParents(person3.childOf, undo=undo)
    multipleBirth = person3.childOf.multipleBirth
    assert person3.childOf.multipleBirth != None
    assert person4.childOf.multipleBirth is multipleBirth
    assert multipleBirth.children() == [person3, person4]
    scene.undo()
    if undo:
        assert person3.childOf is not None
        assert person4.childOf is None
        assert multipleBirth.children() == []
    else:
        assert person3.childOf.multipleBirth == multipleBirth
        assert person3.childOf.multipleBirth == multipleBirth
        assert multipleBirth.children() == [person3, person4]


def test_add_callout(scene, undo):
    layerItemAdded = util.Condition(scene.layerItemAdded)
    layerItemRemoved = util.Condition(scene.layerItemRemoved)
    layer = Layer(name="layer", active=True)
    scene.addItem(layer)
    callout = Callout(text="Hello, world")
    scene.addItem(callout, undo=undo)
    assert layerItemAdded.callCount == 1
    assert scene.layerItems() == [callout]
    scene.undo()
    if undo:
        assert layerItemRemoved.callCount == 1
        assert scene.layerItems() == []
    else:
        assert layerItemRemoved.callCount == 0
        assert scene.layerItems() == [callout]


## Remove items


def test_remove_person(scene, undo):
    personAdded = util.Condition(scene.personAdded)
    personRemoved = util.Condition(scene.personRemoved)
    person = Person(name="person")
    scene.addItem(person)
    scene.removeItem(person, undo=undo)
    assert personAdded.callCount == 1
    assert personRemoved.callCount == 1
    assert scene.people() == []
    scene.undo()
    if undo:
        assert personAdded.callCount == 2
        assert personRemoved.callCount == 1
        assert scene.people() == [person]
    else:
        assert personAdded.callCount == 1
        assert personRemoved.callCount == 1
        assert scene.people() == []


def test_remove_event(scene, undo):
    person = Person(name="person")
    scene.addItem(person)
    eventAdded = util.Condition(scene.eventAdded)
    eventRemoved = util.Condition(scene.eventRemoved)
    event = Event(
        parent=person, description="Something happened", dateTime=util.Date(2001, 1, 1)
    )
    scene.addItem(event)
    assert eventAdded.callCount == 1
    assert eventRemoved.callCount == 0
    assert scene.events(onlyDated=True) == [event]
    scene.removeItem(event, undo=undo)
    scene.undo()
    if undo:
        assert eventAdded.callCount == 2
        assert eventRemoved.callCount == 1
        assert scene.events(onlyDated=True) == [event]
    else:
        assert eventAdded.callCount == 1
        assert eventRemoved.callCount == 1
        assert scene.events(onlyDated=True) == []


def test_remove_event_with_events_remaining(scene):
    person = Person(name="person", birthDateTime=util.Date(2000, 1, 1))
    scene.addItem(person)
    eventRemoved = util.Condition(scene.eventRemoved)
    event = Event(
        parent=person, description="Something happened", dateTime=util.Date(2001, 1, 1)
    )
    scene.addItem(event)
    currentDateTime = scene.currentDateTime()
    scene.removeItem(event, undo=False)
    assert eventRemoved.callCount == 1
    assert scene.events(onlyDated=True) == [person.birthEvent]
    assert scene.currentDateTime() == currentDateTime


def test_remove_event_no_events_remaining(scene):
    person = Person(name="person")
    scene.addItem(person)
    eventRemoved = util.Condition(scene.eventRemoved)
    event = Event(
        parent=person, description="Something happened", dateTime=util.Date(2001, 1, 1)
    )
    scene.addItem(event)
    scene.removeItem(event, undo=False)
    assert eventRemoved.callCount == 1
    assert scene.events(onlyDated=True) == []
    assert scene.currentDateTime() == QDateTime()


def test_remove_marriage(scene, undo):
    marriageAdded = util.Condition(scene.marriageAdded)
    marriageRemoved = util.Condition(scene.marriageRemoved)
    person1 = Person(name="person1")
    person2 = Person(name="person2")
    marriage = Marriage(person1, person2)
    scene.addItems(person1, person2, marriage)
    scene.removeItem(marriage, undo=undo)
    assert marriageAdded.callCount == 1
    assert marriageRemoved.callCount == 1
    assert scene.people() == [person1, person2]
    assert scene.marriages() == []
    scene.undo()
    if undo:
        assert marriageAdded.callCount == 2
        assert marriageRemoved.callCount == 1
        assert scene.people() == [person1, person2]
        assert scene.marriages() == [marriage]
    else:
        assert marriageAdded.callCount == 1
        assert marriageRemoved.callCount == 1
        assert scene.people() == [person1, person2]
        assert scene.marriages() == []


def test_remove_emotion(scene, undo):
    emotionAdded = util.Condition(scene.emotionAdded)
    emotionRemoved = util.Condition(scene.emotionRemoved)
    person1 = Person(name="person1")
    person2 = Person(name="person2")
    emotion = Emotion(person1, person2, kind=util.ITEM_CONFLICT)
    scene.addItems(person1, person2)
    scene.addItem(emotion)
    scene.removeItem(emotion, undo=undo)
    assert emotionAdded.callCount == 1
    assert emotionRemoved.callCount == 1
    assert scene.people() == [person1, person2]
    assert scene.emotions() == []
    scene.undo()
    if undo:
        assert emotionAdded.callCount == 2
        assert emotionRemoved.callCount == 1
        assert scene.emotions() == [emotion]
    else:
        assert emotionAdded.callCount == 1
        assert emotionRemoved.callCount == 1
        assert scene.emotions() == []


def test_remove_layer(scene, undo):
    layerAdded = util.Condition(scene.layerAdded)
    layerRemoved = util.Condition(scene.layerRemoved)
    layer = Layer(name="layer")
    scene.addItem(layer)
    scene.removeItem(layer, undo=undo)
    assert layerAdded.callCount == 1
    assert layerRemoved.callCount == 1
    assert scene.layers() == []
    scene.undo()
    if undo:
        assert layerAdded.callCount == 2
        assert layerRemoved.callCount == 1
        assert scene.layers() == [layer]
    else:
        assert layerAdded.callCount == 1
        assert layerRemoved.callCount == 1
        assert scene.layers() == []


def test_remove_childof(scene, undo):
    person1 = Person(name="person1")
    person2 = Person(name="person2")
    marriage = Marriage(person1, person2)
    person3 = Person(name="person3")
    person3.setParents(marriage)
    scene.addItems(person1, person2, marriage, person3)
    scene.removeItem(person3.childOf, undo=undo)
    assert person3.childOf is None
    scene.undo()
    if undo:
        assert person3.childOf.parents() == marriage
    else:
        assert person3.childOf is None


def test_remove_multipleBirth(scene, undo):
    person1 = Person(name="person1")
    person2 = Person(name="person2")
    marriage = Marriage(person1, person2)
    person3 = Person(name="person3")
    person4 = Person(name="person4")
    scene.addItems(person1, person2, marriage, person3, person4)
    multipleBirth = MultipleBirth(marriage)
    scene.addItem(multipleBirth)
    person3.setParents(multipleBirth)
    person4.setParents(multipleBirth)
    with scene.macro("Remove multipleBirth", undo=undo):
        person3.setParents(None, undo=undo)
        person4.setParents(None, undo=undo)
    # scene.removeItem(multipleBirth, undo=undo)
    assert person3.childOf is None
    assert person4.childOf is None
    assert multipleBirth.children() == []
    scene.undo()
    if undo:
        assert person4 in person3.childOf.multipleBirth.children()
        assert person3 in person4.childOf.multipleBirth.children()
    else:
        assert person3.childOf is None
        assert person4.childOf is None
        assert multipleBirth.children() == []


def test_remove_nuclear_family_with_MultipleBirth():
    scene = Scene()
    parentA = Person(name="parentA")
    parentB = Person(name="parentB")
    twinA = Person(name="twinA")
    twinB = Person(name="twinB")
    marriage = Marriage(parentA, parentB)
    scene.addItems(parentA, parentB, marriage, twinA, twinB)
    twinA.setParents(marriage)
    twinB.setParents(twinA.childOf)  # 0

    scene.selectAll()
    with mock.patch(
        "PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes
    ):
        scene.removeSelection()  # 1
    assert scene.find(types=PathItem) == []

    scene.undo()  # 0
    assert len(scene.find(types=MultipleBirth)) == 1
    assert len(scene.find(types=ChildOf)) == 2
    assert len(scene.find(types=Person)) == 4
    assert twinA.multipleBirth() != None
    assert twinA.multipleBirth() == twinB.multipleBirth()


def test_undo_remove_child_selected(scene):
    """People and pair-bond were selected but not child items after delete and undo."""

    person1 = Person(name="person1")
    person2 = Person(name="person2")
    marriage = Marriage(person1, person2)
    person3 = Person(name="person3")
    person3.setParents(marriage)
    scene.addItem(person1)
    scene.addItem(person2)
    scene.addItem(marriage)
    scene.addItem(person3)

    assert person3.childOf is not None

    marriage.setSelected(True)
    person3.setSelected(True)
    person1.setSelected(True)
    person2.setSelected(True)

    with mock.patch(
        "PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes
    ):
        scene.removeSelection()
    scene.undo()

    assert marriage.isSelected() == False
    assert person3.isSelected() == False
    assert person1.isSelected() == False
    assert person2.isSelected() == False
    assert person3.childOf.isSelected() == False


def test_add_events_sets_currentDateTime(scene):
    person = Person(name="Hey", lastName="You")
    scene.addItem(person)
    event_1 = Event(parent=person, dateTime=util.Date(2001, 1, 1))
    scene.addItem(event_1)
    assert scene.currentDateTime() == event_1.dateTime()

    event_2 = Event(parent=person, dateTime=util.Date(2002, 1, 1))
    scene.addItem(event_2)
    assert scene.currentDateTime() == event_2.dateTime()


def test_remove_last_event_sets_currentDateTime(scene):
    person = Person(name="p1")
    event = Event(parent=person, dateTime=util.Date(2001, 1, 1))
    scene.addItem(person)
    assert scene.currentDateTime() == event.dateTime()

    event.setDateTime(QDateTime())
    assert scene.currentDateTime() == QDateTime()


def test_addParentsToSelection_doesnt_reset_currentDateTime(scene):
    person = Person(name="Hey", lastName="You")
    scene.addItem(person)
    event = Event(parent=person, dateTime=util.Date(2001, 1, 1))
    scene.addItem(event)
    assert scene.currentDateTime() == event.dateTime()

    person.setSelected(True)
    scene.addParentsToSelection()
    assert scene.currentDateTime() == event.dateTime()


def test_remove_all_events_clears_currentDateTime(scene):
    person = Person(name="Hey", lastName="You")
    scene.addItem(person)
    event_1 = Event(parent=person, dateTime=util.Date(2001, 1, 1))
    scene.addItem(event_1)
    assert scene.currentDateTime() == event_1.dateTime()

    scene.removeItem(event_1)
    assert Scene().currentDateTime().isNull()


class View(QGraphicsView):
    def getVisibleSceneScaleRatio(self):
        return 1.0


def test_drag_create_emotion(qtbot):
    scene = Scene()
    view = View()
    view.resize(600, 800)
    view.show()
    view.setScene(scene)
    personA, personB = Person(name="A", pos=QPointF(50, 50)), Person(
        name="B", pos=QPointF(-50, 50)
    )
    scene.addItems(personA, personB)
    scene.setItemMode(util.ITEM_CONFLICT)
    qtbot.mousePress(
        view.viewport(), Qt.LeftButton, pos=view.mapFromScene(personA.pos())
    )
    qtbot.mouseMove(view.viewport(), view.mapFromScene(personA.pos() - personB.pos()))
    qtbot.mouseRelease(
        view.viewport(), Qt.LeftButton, pos=view.mapFromScene(personB.pos())
    )
    assert len(scene.emotions()) == 1
    emotion = scene.emotions()[0]
    assert emotion.personA() == personA
    assert emotion.personB() == personB
    assert emotion.kind() == util.ITEM_CONFLICT
