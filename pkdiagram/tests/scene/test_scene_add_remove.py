import os.path

import pytest
import mock

from btcopilot.schema import RelationshipKind, EventKind
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
    ItemMode,
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

    person = scene.addItem(Person(name="person"), undo=True)
    assert scene._undoStack.index() == 1
    assert scene._undoStackDateTimes == {0: QDateTime()}

    event1 = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            description="First datetime",
            dateTime=util.Date(2001, 1, 1),
        ),
        undo=True,
    )
    assert scene._undoStack.index() == 2
    assert scene.currentDateTime() == event1.dateTime()
    assert scene._undoStackDateTimes == {0: QDateTime(), 1: QDateTime()}

    event2 = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            description="Second datetime",
            dateTime=util.Date(2002, 1, 1),
        ),
        undo=True,
    )
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


def test_add_pairbond_undo_redo(scene):
    person1 = Person(name="person1")
    person2 = Person(name="person2")
    scene.addItems(person1, person2)
    assert person1.marriages == []
    assert person2.marriages == []

    marriage = Marriage(person1, person2)
    scene.addItem(marriage, undo=True)
    assert person1.marriages == [marriage]

    scene.undo()
    assert person1.marriages == []

    scene.redo()
    assert person1.marriages == [marriage]


def test_add_emotion(scene, undo):
    person1, person2 = scene.addItems(Person(name="person1"), Person(name="person2"))
    eventAdded = util.Condition(scene.eventAdded)
    eventRemoved = util.Condition(scene.eventRemoved)
    emotionAdded = util.Condition(scene.emotionAdded)
    emotionRemoved = util.Condition(scene.emotionRemoved)
    event = scene.addItem(
        Event(
            EventKind.Shift,
            person1,
            dateTime=util.Date(2001, 1, 1),
            relationship=RelationshipKind.Conflict,
            relationshipTargets=[person2],
        ),
        undo=undo,
    )
    emotion = scene.emotionsFor(event)[0]
    assert eventAdded.callCount == 1
    assert emotionAdded.callCount == 1
    assert scene.people() == [person1, person2]
    assert scene.emotions() == [emotion]
    scene.undo()
    if undo:
        assert scene.currentDateTime() == QDateTime()
        assert eventRemoved.callCount == 1
        assert emotionRemoved.callCount == 1
        assert scene.emotions() == []
    else:
        assert scene.currentDateTime() == event.dateTime()
        assert eventRemoved.callCount == 0
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
    person1, person2, person3, person4 = scene.addItems(
        Person(name="person1"),
        Person(name="person2"),
        Person(name="person3"),
        Person(name="person4"),
    )
    marriage = scene.addItem(Marriage(person1, person2))
    person3.setParents(marriage)
    person4.setParents(person3.childOf)
    multipleBirth = person3.childOf.multipleBirth
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


def test_ensureParentsFor(scene):
    person = scene.addItem(Person(name="Hey", lastName="You"))
    event = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2001, 1, 1))
    )
    assert scene.currentDateTime() == event.dateTime()

    scene.ensureParentsFor(person, undo=True)
    assert person.childOf is not None
    assert person.parents() is not None
    assert len(person.parents().people) == 2
    assert scene.currentDateTime() == event.dateTime()  # doesn't change

    scene.undo()
    assert person.childOf is None
    assert person.parents() is None

    scene.redo()
    assert person.childOf is not None
    assert person.parents() is not None
    assert len(person.parents().people) == 2


## Remove items


def test_remove_person(scene, undo):
    personAdded = util.Condition(scene.personAdded)
    personRemoved = util.Condition(scene.personRemoved)
    person = scene.addItem(Person(name="person"))
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
    person = scene.addItem(Person(name="person"))
    eventAdded = util.Condition(scene.eventAdded)
    eventRemoved = util.Condition(scene.eventRemoved)
    event = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            description="Something happened",
            dateTime=util.Date(2001, 1, 1),
        )
    )
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
    person = scene.addItem(Person(name="person"))
    event1 = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 1))
    )
    eventRemoved = util.Condition(scene.eventRemoved)
    event2 = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            description="Something happened",
            dateTime=util.Date(2001, 1, 1),
        )
    )
    currentDateTime = scene.currentDateTime()
    scene.removeItem(event2, undo=False)
    assert eventRemoved.callCount == 1
    assert scene.events(onlyDated=True) == [event1]
    assert scene.currentDateTime() == currentDateTime


def test_remove_event_no_events_remaining(scene):
    person = scene.addItem(Person(name="person"))
    eventRemoved = util.Condition(scene.eventRemoved)
    event = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            description="Something happened",
            dateTime=util.Date(2001, 1, 1),
        )
    )
    scene.removeItem(event, undo=False)
    assert eventRemoved.callCount == 1
    assert scene.events(onlyDated=True) == []
    assert scene.currentDateTime() == QDateTime()


def test_remove_marriage(scene, undo):
    marriageAdded = util.Condition(scene.marriageAdded)
    marriageRemoved = util.Condition(scene.marriageRemoved)
    person1, person2 = scene.addItems(Person(name="person1"), Person(name="person2"))
    marriage = scene.addItem(Marriage(person1, person2))
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
    person1, person2 = scene.addItems(Person(name="person1"), Person(name="person2"))
    emotion = scene.addItem(Emotion(RelationshipKind.Conflict, person2, person=person1))
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

    person1, person2 = scene.addItems(Person(name="person1"), Person(name="person2"))
    marriage = scene.addItem(Marriage(person1, person2))
    person3 = scene.addItem(Person(name="person3"))
    person3.setParents(marriage)

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
    person = scene.addItem(Person(name="Hey", lastName="You"))
    event_1 = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2001, 1, 1))
    )
    assert scene.currentDateTime() == event_1.dateTime()

    event_2 = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2002, 1, 1))
    )
    assert scene.currentDateTime() == event_2.dateTime()


def test_remove_last_event_sets_currentDateTime(scene):
    person = scene.addItem(Person(name="p1"))
    birthEvent = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2001, 1, 1))
    )
    assert scene.currentDateTime() == birthEvent.dateTime()

    birthEvent.setDateTime(QDateTime())
    assert scene.currentDateTime() == QDateTime()


def test_remove_all_events_clears_currentDateTime(scene):
    person = scene.addItem(Person(name="Hey", lastName="You"))
    event = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2001, 1, 1))
    )
    assert scene.currentDateTime() == event.dateTime()

    scene.removeItem(event)
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
    personA, personB = scene.addItems(
        Person(name="A", pos=QPointF(50, 50)), Person(name="B", pos=QPointF(-50, 50))
    )
    scene.setItemMode(ItemMode.Conflict)
    qtbot.mousePress(
        view.viewport(), Qt.LeftButton, pos=view.mapFromScene(personA.pos())
    )
    qtbot.mouseMove(view.viewport(), view.mapFromScene(personA.pos() - personB.pos()))
    qtbot.mouseRelease(
        view.viewport(), Qt.LeftButton, pos=view.mapFromScene(personB.pos())
    )
    assert len(scene.emotions()) == 1
    emotion = scene.emotions()[0]
    assert emotion.person() == personA
    assert emotion.target() == personB
    assert emotion.kind() == RelationshipKind.Conflict


def test_add_birth_event_not_removed_when_parent_has_birth(scene):
    """
    Regression test: A child's birth event should not be removed when adding
    a birth event for the parent. The duplicate detection should only match
    events where the person is the child, not where they are a parent.
    """
    father = scene.addItem(Person(name="Father"))
    mother = scene.addItem(Person(name="Mother"))
    marriage = scene.addItem(Marriage(father, mother))
    child = scene.addItem(Person(name="Child"))
    child.setParents(marriage)

    # Add birth event for child (father is the "person" on this event)
    childBirth = scene.addItem(
        Event(
            EventKind.Birth,
            person=father,
            spouse=mother,
            child=child,
            dateTime=util.Date(2000, 1, 1),
        )
    )
    assert child.birthEvent() == childBirth
    assert len(scene.eventsFor(child, kinds=EventKind.Birth)) == 1

    # Now add birth event for father (father is the "child" on this event)
    grandfather = scene.addItem(Person(name="Grandfather"))
    grandmother = scene.addItem(Person(name="Grandmother"))
    grandparentsMarriage = scene.addItem(Marriage(grandfather, grandmother))
    father.setParents(grandparentsMarriage)

    fatherBirth = scene.addItem(
        Event(
            EventKind.Birth,
            person=grandfather,
            spouse=grandmother,
            child=father,
            dateTime=util.Date(1970, 1, 1),
        )
    )

    # Child's birth event should still exist (the key regression test)
    assert child.birthEvent() == childBirth
    assert len(scene.eventsFor(child, kinds=EventKind.Birth)) == 1

    # Father's birth event should exist
    assert father.birthEvent() == fatherBirth
    # eventsFor returns all events involving father (as parent or child)
    fatherBirthEvents = [
        e for e in scene.eventsFor(father, kinds=EventKind.Birth) if e.child() == father
    ]
    assert len(fatherBirthEvents) == 1
    assert fatherBirthEvents[0] == fatherBirth


def test_add_duplicate_birth_event_replaces_first(scene):
    """Adding a second birth event for the same child replaces the first."""
    father = scene.addItem(Person(name="Father"))
    mother = scene.addItem(Person(name="Mother"))
    marriage = scene.addItem(Marriage(father, mother))
    child = scene.addItem(Person(name="Child"))
    child.setParents(marriage)

    birth1 = scene.addItem(
        Event(
            EventKind.Birth,
            person=father,
            spouse=mother,
            child=child,
            dateTime=util.Date(2000, 1, 1),
        )
    )
    assert child.birthEvent() == birth1

    birth2 = scene.addItem(
        Event(
            EventKind.Birth,
            person=father,
            spouse=mother,
            child=child,
            dateTime=util.Date(2000, 6, 15),
        )
    )

    # First birth should be replaced
    assert birth1 not in scene.events()
    assert child.birthEvent() == birth2
    assert len(scene.eventsFor(child, kinds=EventKind.Birth)) == 1


def test_add_duplicate_death_event_replaces_first(scene):
    """Adding a second death event for the same person replaces the first."""
    person = scene.addItem(Person(name="Person"))

    death1 = scene.addItem(
        Event(EventKind.Death, person=person, dateTime=util.Date(2020, 1, 1))
    )
    assert person.deathEvent() == death1

    death2 = scene.addItem(
        Event(EventKind.Death, person=person, dateTime=util.Date(2020, 6, 15))
    )

    # First death should be replaced
    assert death1 not in scene.events()
    assert person.deathEvent() == death2
    assert len(scene.eventsFor(person, kinds=EventKind.Death)) == 1
