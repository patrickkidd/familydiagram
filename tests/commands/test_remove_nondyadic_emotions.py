import pytest
from pkdiagram import util
from pkdiagram.scene import (
    Scene,
    Person,
    Event,
    EventKind,
    Emotion,
    RelationshipKind,
)
from pkdiagram.scene.commands import RemoveItems


class TestRemoveNonDyadicEmotions:

    def test_remove_nondyadic_emotion_parent_item(self, scene):
        """Non-dyadic emotions have special parent item handling on undo."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        event = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Cutoff,
                relationshipTargets=[person2],
            )
        )
        emotion = scene.emotionsFor(event)[0]

        # Verify it's non-dyadic
        assert not emotion.isDyadic()
        assert emotion.parentItem() == person1

        scene.removeItem(emotion, undo=True)

        assert len(scene.emotions()) == 0

        scene.undo()

        assert len(scene.emotions()) == 1
        assert emotion in scene.emotions()
        # Critical: parent item should be restored
        assert emotion.parentItem() == person1
        assert emotion.event() == event
        assert emotion.target() == person2

    def test_remove_person_with_nondyadic_emotions(self, scene):
        """Removing person with non-dyadic emotions restores parent item correctly."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        event = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Cutoff,
                relationshipTargets=[person2],
            )
        )
        emotion = scene.emotionsFor(event)[0]

        assert not emotion.isDyadic()

        scene.removeItem(person1, undo=True)

        assert len(scene.people()) == 1
        assert len(scene.emotions()) == 0
        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.people()) == 2
        assert len(scene.emotions()) == 1
        assert len(scene.events()) == 1
        # Parent item restored correctly
        assert emotion.parentItem() == person1

    def test_remove_event_with_nondyadic_emotion(self, scene):
        """Event removal with non-dyadic emotion should restore parent item on undo."""
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        event = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Cutoff,
                relationshipTargets=[person2],
            )
        )
        emotion = scene.emotionsFor(event)[0]

        original_parent = emotion.parentItem()

        scene.removeItem(event, undo=True)

        assert len(scene.events()) == 0
        assert len(scene.emotions()) == 0

        scene.undo()

        assert len(scene.events()) == 1
        assert len(scene.emotions()) == 1
        assert emotion.parentItem() == original_parent

    def test_multiple_nondyadic_emotions_same_person(self, scene):
        """Multiple non-dyadic emotions from same person."""
        person1, person2, person3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        event1 = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Cutoff,
                relationshipTargets=[person2],
            )
        )
        emotion1 = scene.emotionsFor(event1)[0]

        event2 = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 2, 1),
                relationship=RelationshipKind.Cutoff,
                relationshipTargets=[person3],
            )
        )
        emotion2 = scene.emotionsFor(event2)[0]

        assert emotion1.parentItem() == person1
        assert emotion2.parentItem() == person1

        scene.removeItem(person1, undo=True)

        assert len(scene.emotions()) == 0

        scene.undo()

        assert len(scene.emotions()) == 2
        assert emotion1.parentItem() == person1
        assert emotion2.parentItem() == person1

    def test_nondyadic_triangle_emotion(self, scene):
        """Non-dyadic emotions with triangle relationships (Inside/Outside)."""
        person1, person2, person3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        event = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Cutoff,
                relationshipTargets=[person2],
                relationshipTriangles=[person3],
            )
        )
        emotion = scene.emotionsFor(event)[0]

        assert not emotion.isDyadic()
        assert emotion.parentItem() == person1

        scene.removeItem(emotion, undo=True)

        scene.undo()

        assert emotion.parentItem() == person1
        assert emotion.event() == event
        assert emotion.target() == person2

    def test_remove_batch_nondyadic_emotions(self, scene):
        """Batch removal of multiple non-dyadic emotions."""
        person1, person2, person3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        event1 = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Cutoff,
                relationshipTargets=[person2],
            )
        )
        emotion1 = scene.emotionsFor(event1)[0]

        event2 = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 2, 1),
                relationship=RelationshipKind.Cutoff,
                relationshipTargets=[person3],
            )
        )
        emotion2 = scene.emotionsFor(event2)[0]

        scene.push(RemoveItems(scene, [emotion1, emotion2]))

        assert len(scene.emotions()) == 0

        scene.undo()

        assert len(scene.emotions()) == 2
        assert emotion1.parentItem() == person1
        assert emotion2.parentItem() == person1
