import pytest
from pkdiagram import util
from pkdiagram.scene import (
    Scene,
    Person,
    Marriage,
    Event,
    EventKind,
)
from pkdiagram.scene.commands import RemoveItems


class TestRemoveItemsPersonWithEvents:

    def test_remove_person_with_single_event(self, scene):
        person = scene.addItem(Person(name="John"))
        event = scene.addItem(
            Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 1))
        )

        assert len(scene.people()) == 1
        assert len(scene.events()) == 1
        assert len(scene.eventsFor(person)) == 1

        scene.removeItem(person, undo=True)

        assert len(scene.people()) == 0
        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.people()) == 1
        assert len(scene.events()) == 1
        assert person in scene.people()
        assert event in scene.events()
        assert len(scene.eventsFor(person)) == 1

        scene.redo()

        assert len(scene.people()) == 0
        assert len(scene.events()) == 0

    def test_remove_person_with_multiple_events(self, scene):
        person = scene.addItem(Person(name="Jane"))
        event1 = scene.addItem(
            Event(EventKind.Shift, person, dateTime=util.Date(1990, 5, 15))
        )
        event2 = scene.addItem(
            Event(EventKind.Shift, person, dateTime=util.Date(2020, 10, 30))
        )
        event3 = scene.addItem(
            Event(EventKind.Shift, person, dateTime=util.Date(2010, 3, 20))
        )

        assert len(scene.eventsFor(person)) == 3

        scene.removeItem(person, undo=True)

        assert len(scene.people()) == 0
        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.people()) == 1
        assert len(scene.events()) == 3
        assert person in scene.people()
        assert event1 in scene.events()
        assert event2 in scene.events()
        assert event3 in scene.events()


class TestRemoveItemsEvent:

    def test_remove_event_directly(self, scene):
        person = scene.addItem(Person(name="John"))
        event = scene.addItem(
            Event(EventKind.Shift, person, dateTime=util.Date(2020, 5, 10))
        )

        assert len(scene.events()) == 1

        scene.removeItem(event, undo=True)

        assert len(scene.people()) == 1
        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.events()) == 1
        assert event in scene.events()

        scene.redo()

        assert len(scene.events()) == 0


class TestRemoveItemsMarriage:

    def test_remove_marriage(self, scene):
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        marriage = scene.addItem(Marriage(person1, person2))

        assert len(scene.marriages()) == 1

        scene.removeItem(marriage, undo=True)

        assert len(scene.marriages()) == 0
        assert len(scene.people()) == 2

        scene.undo()

        assert len(scene.marriages()) == 1
        assert marriage in scene.marriages()


class TestRemoveItemsMultiple:

    def test_remove_multiple_people(self, scene):
        person1, person2, person3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )

        assert len(scene.people()) == 3

        scene.push(RemoveItems(scene, [person1, person2]))

        assert len(scene.people()) == 1
        assert person3 in scene.people()

        scene.undo()

        assert len(scene.people()) == 3

        scene.redo()

        assert len(scene.people()) == 1

    def test_remove_person_and_their_events(self, scene):
        person = scene.addItem(Person(name="John"))
        event1, event2 = scene.addItems(
            Event(EventKind.Shift, person, dateTime=util.Date(1990, 1, 1)),
            Event(EventKind.Shift, person, dateTime=util.Date(2020, 1, 1)),
        )

        scene.removeItem(person, undo=True)

        assert len(scene.people()) == 0
        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.people()) == 1
        assert len(scene.events()) == 2


class TestRemoveItemsComplexScenarios:

    def test_remove_person_with_events_and_marriage(self, scene):
        person1, person2, person3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        marriage = scene.addItem(Marriage(person1, person2))
        event1 = scene.addItem(
            Event(EventKind.Shift, person1, dateTime=util.Date(1990, 1, 1))
        )
        event2 = scene.addItem(
            Event(EventKind.Shift, person1, dateTime=util.Date(2010, 6, 15))
        )

        initial_people = len(scene.people())
        initial_marriages = len(scene.marriages())
        initial_events = len(scene.events())

        scene.removeItem(person1, undo=True)

        assert len(scene.people()) == 2
        assert person1 not in scene.people()
        assert len(scene.marriages()) == 0
        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.people()) == initial_people
        assert len(scene.marriages()) == initial_marriages
        assert len(scene.events()) == initial_events
        assert person1 in scene.people()
        assert marriage in scene.marriages()

    def test_sequential_remove_and_undo(self, scene):
        personAdded = util.Condition(scene.personAdded)
        personRemoved = util.Condition(scene.personRemoved)
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        assert personAdded.callCount == 2
        assert personRemoved.callCount == 0

        scene.removeItem(person1, undo=True)
        assert personAdded.callCount == 2
        assert personRemoved.callCount == 1
        assert len(scene.people()) == 1

        scene.removeItem(person2, undo=True)
        assert personAdded.callCount == 2
        assert personRemoved.callCount == 2
        assert len(scene.people()) == 0

        scene.undo()
        assert personAdded.callCount == 3
        assert personRemoved.callCount == 2
        assert len(scene.people()) == 1
        assert person2 in scene.people()

        scene.undo()
        assert personAdded.callCount == 4
        assert personRemoved.callCount == 2
        assert len(scene.people()) == 2
        assert person1 in scene.people()
        assert person2 in scene.people()

        scene.redo()
        assert personAdded.callCount == 4
        assert personRemoved.callCount == 3
        assert len(scene.people()) == 1
        assert person2 in scene.people()

        scene.redo()
        assert personAdded.callCount == 4
        assert personRemoved.callCount == 4
        assert len(scene.people()) == 0
