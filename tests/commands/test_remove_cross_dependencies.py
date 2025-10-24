import pytest

from btcopilot.schema import EventKind, RelationshipKind
from pkdiagram import util
from pkdiagram.scene import (
    Person,
    Marriage,
    ChildOf,
    MultipleBirth,
    Event,
    Layer,
)
from pkdiagram.scene.commands import RemoveItems


class TestRemovePersonWithEverything:

    def test_person_with_all_relationships(self, scene):
        """Remove person with marriages, children, events, emotions, and layer properties."""
        parent1, parent2, child = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        partner = scene.addItem(Person(name="Diana"))
        layer = scene.addItem(Layer(name="Layer 1"))

        # Alice marries Bob, has child Charlie
        marriage1 = scene.addItem(Marriage(parent1, parent2))
        childOf = child.setParents(marriage1)

        # Alice later marries Diana
        marriage2 = scene.addItem(Marriage(parent1, partner))

        # Alice has events
        event1 = scene.addItem(
            Event(EventKind.Shift, parent1, dateTime=util.Date(2010, 1, 1))
        )
        event2 = scene.addItem(
            Event(
                EventKind.Shift,
                parent1,
                dateTime=util.Date(2015, 1, 1),
                relationship=RelationshipKind.Conflict,
                relationshipTargets=[partner],
            )
        )

        # Alice has emotions (implicitly created by event2)
        emotion = scene.emotionsFor(event2)[0]

        # Alice has layer properties
        parent1.setLayers([layer.id])
        layer.setItemProperty(parent1.id, "bigFont", True)

        initial_people = len(scene.people())
        initial_marriages = len(scene.marriages())
        initial_children = len(scene.find(types=ChildOf))
        initial_events = len(scene.events())
        initial_emotions = len(scene.emotions())

        scene.removeItem(parent1, undo=True)

        # Everything cascades
        assert len(scene.people()) == 3  # Bob, Charlie, Diana remain
        assert len(scene.marriages()) == 0  # Both marriages deleted
        assert len(scene.find(types=ChildOf)) == 0  # Child relationship deleted
        assert len(scene.events()) == 0  # All Alice's events deleted
        assert len(scene.emotions()) == 0  # All emotions involving Alice deleted

        scene.undo()

        # Everything restored
        assert len(scene.people()) == initial_people
        assert len(scene.marriages()) == initial_marriages
        assert len(scene.find(types=ChildOf)) == initial_children
        assert len(scene.events()) == initial_events
        assert len(scene.emotions()) == initial_emotions
        assert parent1 in scene.people()
        assert marriage1 in scene.marriages()
        assert marriage2 in scene.marriages()
        assert event1 in scene.events()
        assert event2 in scene.events()
        assert emotion in scene.emotions()
        assert layer.getItemProperty(parent1.id, "bigFont") == (True, True)

    def test_marriage_with_everything(self, scene):
        """Remove marriage with children, events, and multiple births."""
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        child1, child2, twin1, twin2 = scene.addItems(
            Person(name="Charlie"),
            Person(name="Diana"),
            Person(name="Eve"),
            Person(name="Frank"),
        )

        marriage = scene.addItem(Marriage(parent1, parent2))

        # Regular children
        childOf1 = child1.setParents(marriage)
        childOf2 = child2.setParents(marriage)

        # Twins
        childOf3 = twin1.setParents(marriage)
        childOf4 = twin2.setParents(twin1.childOf)

        scene.removeItem(marriage, undo=True)

        assert len(scene.marriages()) == 0
        assert len(scene.find(types=ChildOf)) == 0
        assert len(scene.find(types=MultipleBirth)) == 0
        assert len(scene.people()) == 6  # Everyone remains

        scene.undo()

        assert len(scene.marriages()) == 1
        assert len(scene.find(types=ChildOf)) == 4
        assert len(scene.find(types=MultipleBirth)) == 1
        assert twin1.childOf.multipleBirth is not None
        assert twin2.childOf.multipleBirth is not None

    def test_complex_family_tree_removal(self, scene):
        """Complex family with multiple generations."""
        # Grandparents
        grandpa, grandma = scene.addItems(
            Person(name="Grandpa"), Person(name="Grandma")
        )
        grandparent_marriage = scene.addItem(Marriage(grandpa, grandma))

        # Parents (children of grandparents)
        parent1, parent2 = scene.addItems(Person(name="Mom"), Person(name="Dad"))
        childOf_parent1 = parent1.setParents(grandparent_marriage)

        # Parents marry
        parent_marriage = scene.addItem(Marriage(parent1, parent2))

        # Children
        child1, child2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        childOf1 = child1.setParents(parent_marriage)
        childOf2 = child2.setParents(parent_marriage)

        # Events
        event = scene.addItem(
            Event(
                EventKind.Shift,
                parent1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Distance,
                relationshipTargets=[parent2],
            )
        )

        # Remove middle generation (Mom)
        scene.removeItem(parent1, undo=True)

        # Cascading deletes
        assert len(scene.people()) == 5  # Everyone except Mom
        assert len(scene.marriages()) == 1  # Only grandparent marriage remains
        assert len(scene.find(types=ChildOf)) == 0  # All child relationships gone
        assert len(scene.events()) == 0
        assert len(scene.emotions()) == 0

        scene.undo()

        # Everything restored
        assert len(scene.people()) == 6
        assert len(scene.marriages()) == 2
        assert len(scene.find(types=ChildOf)) == 3


class TestAlreadyDeletedItems:

    def test_remove_already_deleted_person(self, scene):
        """Attempting to remove a person already cascade-deleted."""
        parent1, parent2, child = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf = scene.addItem(ChildOf(child, marriage))

        # Remove parent1, which cascades to delete marriage
        scene.removeItem(parent1, undo=True)

        assert marriage not in scene.marriages()

        # Marriage already deleted by cascade - this should be handled gracefully
        # The scene should recognize marriage is not in the scene
        assert not marriage.scene()

    def test_remove_emotion_after_event_deleted(self, scene):
        """Emotion reference to deleted event."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        event = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Conflict,
                relationshipTargets=[person2],
            )
        )
        emotion = scene.emotionsFor(event)[0]

        # Remove event (cascades to emotion)
        scene.removeItem(event, undo=True)

        assert emotion not in scene.emotions()
        assert not emotion.scene()

    def test_remove_child_after_marriage_deleted(self, scene):
        """ChildOf reference to deleted marriage."""
        parent1, parent2, child = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf = child.setParents(marriage)

        # Remove marriage (cascades to childOf)
        scene.removeItem(marriage, undo=True)

        assert childOf not in scene.find(types=ChildOf)
        assert child.childOf is None


class TestCircularDependencies:

    def test_mutual_emotions(self, scene):
        """Two people with emotions toward each other."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        event1 = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Conflict,
                relationshipTargets=[person2],
            )
        )

        event2 = scene.addItem(
            Event(
                EventKind.Shift,
                person2,
                dateTime=util.Date(2020, 1, 15),
                relationship=RelationshipKind.Conflict,
                relationshipTargets=[person1],
            )
        )

        scene.removeItem(person1, undo=True)

        # Both emotions should be deleted (person1 involved in both)
        assert len(scene.emotions()) == 0
        assert len(scene.events()) == 0
        assert len(scene.people()) == 1

        scene.undo()

        assert len(scene.emotions()) == 2
        assert len(scene.events()) == 2
        assert len(scene.people()) == 2

    def test_triangle_relationships(self, scene):
        """Complex triangle with Inside/Outside emotions."""
        person1, person2, person3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )

        # Alice feels Inside with Bob, Outside Charlie
        event1 = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Inside,
                relationshipTargets=[person2],
                relationshipTriangles=[person3],
            )
        )

        # Bob feels Outside with Alice, Inside Charlie
        event2 = scene.addItem(
            Event(
                EventKind.Shift,
                person2,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Outside,
                relationshipTargets=[person1],
                relationshipTriangles=[person3],
            )
        )

        scene.removeItem(person1, undo=True)

        # Both events/emotions deleted (person1 involved)
        assert len(scene.events()) == 0
        assert len(scene.emotions()) == 0

        scene.undo()

        assert len(scene.events()) == 2
        assert len(scene.emotions()) == 2

    def test_blended_family_circular_refs(self, scene):
        """Blended family with children from multiple marriages."""
        parent1, parent2, parent3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Carol")
        )
        child1, child2 = scene.addItems(Person(name="Charlie"), Person(name="Diana"))

        # Alice + Bob = Charlie
        marriage1 = scene.addItem(Marriage(parent1, parent2))
        childOf1 = child1.setParents(marriage1)

        # Alice + Carol = Diana
        marriage2 = scene.addItem(Marriage(parent1, parent3))
        childOf2 = child2.setParents(marriage2)

        # Emotions between all family members (event creates 2 emotions implicitly)
        event = scene.addItem(
            Event(
                EventKind.Shift,
                parent1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Distance,
                relationshipTargets=[parent2, parent3],
            )
        )

        assert len(scene.marriages()) == 2
        assert len(scene.find(types=ChildOf)) == 2
        assert len(scene.emotions()) == 2
        assert len(scene.events()) == 1

        scene.removeItem(parent1, undo=True)

        # Both marriages, all child relationships, all emotions deleted
        assert len(scene.marriages()) == 0
        assert len(scene.find(types=ChildOf)) == 0
        assert len(scene.emotions()) == 0
        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.marriages()) == 2
        assert len(scene.find(types=ChildOf)) == 2
        assert len(scene.emotions()) == 2
        assert len(scene.events()) == 1
