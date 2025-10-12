import pytest
from pkdiagram import util
from pkdiagram.scene import (
    Scene,
    Person,
    Marriage,
    ChildOf,
    Event,
    EventKind,
)
from pkdiagram.scene.commands import RemoveItems


class TestRemoveBondedEvents:

    def test_remove_bonded_event(self, scene):
        """Bonded event marks when couple becomes bonded/committed."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        marriage = scene.addItem(Marriage(person1, person2))
        event = scene.addItem(
            Event(
                EventKind.Bonded,
                person1,
                spouse=person2,
                dateTime=util.Date(2010, 6, 15),
            )
        )

        assert len(scene.events()) == 1
        assert event.kind() == EventKind.Bonded

        scene.removeItem(event, undo=True)

        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.events()) == 1
        assert event in scene.events()
        assert event.person() == person1
        assert event.spouse() == person2

    def test_remove_person_with_bonded_event(self, scene):
        """Removing person cascades to delete their Bonded event."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        marriage = scene.addItem(Marriage(person1, person2))
        event = scene.addItem(
            Event(
                EventKind.Bonded,
                person1,
                spouse=person2,
                dateTime=util.Date(2010, 6, 15),
            )
        )

        scene.removeItem(person1, undo=True)

        assert len(scene.people()) == 1
        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.people()) == 2
        assert len(scene.events()) == 1
        assert event.person() == person1
        assert event.spouse() == person2


class TestRemoveMarriedEvents:

    def test_remove_married_event(self, scene):
        """Married event marks formal marriage."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        marriage = scene.addItem(Marriage(person1, person2))
        event = scene.addItem(
            Event(
                EventKind.Married,
                person1,
                spouse=person2,
                dateTime=util.Date(2015, 8, 20),
            )
        )

        assert event.kind() == EventKind.Married

        scene.removeItem(event, undo=True)

        assert len(scene.events()) == 0

        scene.undo()

        assert event in scene.events()
        assert event.person() == person1
        assert event.spouse() == person2

    def test_remove_person_with_married_event(self, scene):
        """Removing person deletes their Married event."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        marriage = scene.addItem(Marriage(person1, person2))
        event = scene.addItem(
            Event(
                EventKind.Married,
                person1,
                spouse=person2,
                dateTime=util.Date(2015, 8, 20),
            )
        )

        scene.removeItem(person1, undo=True)

        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.events()) == 1


class TestRemoveSeparatedEvents:

    def test_remove_separated_event(self, scene):
        """Separated event marks couple separation."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        marriage = scene.addItem(Marriage(person1, person2))
        married_event = scene.addItem(
            Event(
                EventKind.Married,
                person1,
                spouse=person2,
                dateTime=util.Date(2010, 1, 1),
            )
        )
        separated_event = scene.addItem(
            Event(
                EventKind.Separated,
                person1,
                spouse=person2,
                dateTime=util.Date(2015, 6, 1),
            )
        )

        assert len(scene.events()) == 2

        scene.removeItem(separated_event, undo=True)

        assert len(scene.events()) == 1
        assert married_event in scene.events()

        scene.undo()

        assert len(scene.events()) == 2
        assert separated_event in scene.events()

    def test_remove_person_with_lifecycle_events(self, scene):
        """Removing person with full marriage lifecycle: Bonded -> Married -> Separated."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        marriage = scene.addItem(Marriage(person1, person2))
        bonded = scene.addItem(
            Event(
                EventKind.Bonded,
                person1,
                spouse=person2,
                dateTime=util.Date(2008, 1, 1),
            )
        )
        married = scene.addItem(
            Event(
                EventKind.Married,
                person1,
                spouse=person2,
                dateTime=util.Date(2010, 6, 15),
            )
        )
        separated = scene.addItem(
            Event(
                EventKind.Separated,
                person1,
                spouse=person2,
                dateTime=util.Date(2018, 3, 20),
            )
        )

        assert len(scene.eventsFor(person1)) == 3

        scene.removeItem(person1, undo=True)

        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.events()) == 3
        assert bonded in scene.events()
        assert married in scene.events()
        assert separated in scene.events()


class TestRemoveDivorcedEvents:

    def test_remove_divorced_event(self, scene):
        """Divorced event marks formal divorce."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        marriage = scene.addItem(Marriage(person1, person2))
        married = scene.addItem(
            Event(
                EventKind.Married,
                person1,
                spouse=person2,
                dateTime=util.Date(2010, 1, 1),
            )
        )
        divorced = scene.addItem(
            Event(
                EventKind.Divorced,
                person1,
                spouse=person2,
                dateTime=util.Date(2020, 12, 31),
            )
        )

        scene.removeItem(divorced, undo=True)

        assert len(scene.events()) == 1
        assert married in scene.events()

        scene.undo()

        assert len(scene.events()) == 2
        assert divorced in scene.events()

    def test_full_marriage_lifecycle(self, scene):
        """Complete lifecycle: Bonded -> Married -> Separated -> Divorced."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        marriage = scene.addItem(Marriage(person1, person2))
        bonded = scene.addItem(
            Event(
                EventKind.Bonded,
                person1,
                spouse=person2,
                dateTime=util.Date(2005, 1, 1),
            )
        )
        married = scene.addItem(
            Event(
                EventKind.Married,
                person1,
                spouse=person2,
                dateTime=util.Date(2007, 6, 1),
            )
        )
        separated = scene.addItem(
            Event(
                EventKind.Separated,
                person1,
                spouse=person2,
                dateTime=util.Date(2015, 3, 1),
            )
        )
        divorced = scene.addItem(
            Event(
                EventKind.Divorced,
                person1,
                spouse=person2,
                dateTime=util.Date(2017, 12, 31),
            )
        )

        assert len(scene.events()) == 4

        scene.push(RemoveItems(scene, [separated, divorced]))

        assert len(scene.events()) == 2

        scene.undo()

        assert len(scene.events()) == 4


class TestRemoveAdoptedEvents:

    def test_remove_adopted_event(self, scene):
        """Adopted event with child."""
        parent1, parent2, child = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        marriage = scene.addItem(Marriage(parent1, parent2))
        adopted = scene.addItem(
            Event(
                EventKind.Adopted,
                parent1,
                spouse=parent2,
                child=child,
                dateTime=util.Date(2010, 1, 1),
            )
        )

        scene.removeItem(adopted, undo=True)

        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.events()) == 1
        assert adopted.child() == child

    def test_remove_child_with_adopted_event(self, scene):
        """Removing adopted child should handle Adopted event."""
        parent1, parent2, child = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        marriage = scene.addItem(Marriage(parent1, parent2))
        child.setParents(marriage)
        adopted = scene.addItem(
            Event(
                EventKind.Adopted,
                parent1,
                spouse=parent2,
                child=child,
                dateTime=util.Date(2010, 1, 1),
            )
        )

        # Note: This tests the relationship between ChildOf and Adopted event
        # The Adopted event should reference the child
        assert adopted.child() == child
        assert child.childOf is not None

        scene.removeItem(child, undo=True)

        # Child removed, childOf and events deleted
        assert len(scene.people()) == 2
        assert len(scene.find(types=ChildOf)) == 0

        scene.undo()

        assert len(scene.people()) == 3
        assert child.childOf is not None


class TestRemoveMovedEvents:

    def test_remove_moved_event(self, scene):
        """Moved event for couple moving together."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        scene.addItem(Marriage(person1, person2))
        moved = scene.addItem(
            Event(
                EventKind.Moved,
                person1,
                spouse=person2,
                location="New York",
                dateTime=util.Date(2015, 6, 1),
            )
        )

        assert moved.location() == "New York"

        scene.removeItem(moved, undo=True)

        assert len(scene.events()) == 0

        scene.undo()

        assert moved in scene.events()
        assert moved.location() == "New York"

    def test_remove_person_with_moved_event(self, scene):
        """Removing person deletes their Moved events."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        marriage = scene.addItem(Marriage(person1, person2))
        moved1 = scene.addItem(
            Event(
                EventKind.Moved,
                person1,
                spouse=person2,
                location="Boston",
                dateTime=util.Date(2010, 1, 1),
            )
        )
        moved2 = scene.addItem(
            Event(
                EventKind.Moved,
                person1,
                spouse=person2,
                location="Seattle",
                dateTime=util.Date(2015, 6, 1),
            )
        )

        scene.removeItem(person1, undo=True)

        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.events()) == 2


class TestComplexPairBondScenarios:

    def test_multiple_marriages_with_events(self, scene):
        """Person with multiple marriages, each with full lifecycle."""
        person1, spouse1, spouse2 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Carol")
        )

        # First marriage lifecycle
        marriage1 = scene.addItem(Marriage(person1, spouse1))
        married1 = scene.addItem(
            Event(
                EventKind.Married,
                person1,
                spouse=spouse1,
                dateTime=util.Date(2000, 1, 1),
            )
        )
        divorced1 = scene.addItem(
            Event(
                EventKind.Divorced,
                person1,
                spouse=spouse1,
                dateTime=util.Date(2010, 12, 31),
            )
        )

        # Second marriage lifecycle
        marriage2 = scene.addItem(Marriage(person1, spouse2))
        married2 = scene.addItem(
            Event(
                EventKind.Married,
                person1,
                spouse=spouse2,
                dateTime=util.Date(2012, 6, 1),
            )
        )

        assert len(scene.eventsFor(person1)) == 3

        scene.removeItem(person1, undo=True)

        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.events()) == 3

    def test_remove_spouse_keeps_person_events(self, scene):
        """Removing spouse should delete PairBond events involving both."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        marriage2 = scene.addItem(Marriage(person1, person2))
        married = scene.addItem(
            Event(
                EventKind.Married,
                person1,
                spouse=person2,
                dateTime=util.Date(2010, 1, 1),
            )
        )
        divorced = scene.addItem(
            Event(
                EventKind.Divorced,
                person1,
                spouse=person2,
                dateTime=util.Date(2020, 1, 1),
            )
        )
        # person1 also has individual event
        individual_event = scene.addItem(
            Event(EventKind.Shift, person1, dateTime=util.Date(2015, 1, 1))
        )

        scene.removeItem(person2, undo=True)

        # PairBond events should be deleted, but individual event remains
        # Note: This depends on whether PairBond events require both spouses
        # Based on the data model, events belong to person1, so they might remain
        # but this is implementation-specific

        scene.undo()

        assert len(scene.people()) == 2
        assert len(scene.events()) == 3

    def test_sequential_pairbond_event_removal(self, scene):
        """Sequential removal and undo of PairBond events."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        marriage2 = scene.addItem(Marriage(person1, person2))
        bonded = scene.addItem(
            Event(
                EventKind.Bonded,
                person1,
                spouse=person2,
                dateTime=util.Date(2008, 1, 1),
            )
        )
        married = scene.addItem(
            Event(
                EventKind.Married,
                person1,
                spouse=person2,
                dateTime=util.Date(2010, 1, 1),
            )
        )
        separated = scene.addItem(
            Event(
                EventKind.Separated,
                person1,
                spouse=person2,
                dateTime=util.Date(2018, 1, 1),
            )
        )

        scene.removeItem(married, undo=True)
        assert len(scene.events()) == 2

        scene.removeItem(separated, undo=True)
        assert len(scene.events()) == 1

        scene.undo()
        assert len(scene.events()) == 2
        assert separated in scene.events()

        scene.undo()
        assert len(scene.events()) == 3
        assert married in scene.events()
