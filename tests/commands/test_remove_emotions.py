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


class TestRemovePersonWithEmotions:

    def test_remove_person_as_emotion_subject(self, scene):
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
        emotion = scene.addItem(
            Emotion(kind=RelationshipKind.Conflict, event=event, target=person2)
        )

        assert len(scene.emotionsFor(person1)) == 1
        assert len(scene.emotionsFor(person2)) == 1

        scene.removeItem(person1, undo=True)

        assert len(scene.people()) == 1
        assert person2 in scene.people()
        assert len(scene.emotions()) == 0
        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.people()) == 2
        assert len(scene.emotions()) == 1
        assert len(scene.events()) == 1
        assert emotion in scene.emotions()
        assert event in scene.events()

    def test_remove_person_as_emotion_target(self, scene):
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        event = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Distance,
                relationshipTargets=[person2],
            )
        )
        emotion = scene.addItem(
            Emotion(kind=RelationshipKind.Distance, event=event, target=person2)
        )

        scene.removeItem(person2, undo=True)

        assert len(scene.people()) == 1
        assert person1 in scene.people()
        assert len(scene.emotions()) == 0

        scene.undo()

        assert len(scene.people()) == 2
        assert len(scene.emotions()) == 1
        assert emotion in scene.emotions()

    def test_remove_person_with_multiple_emotions(self, scene):
        person1, person2, person3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        event1 = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Conflict,
                relationshipTargets=[person2],
            )
        )
        emotion1 = scene.addItem(
            Emotion(kind=RelationshipKind.Conflict, event=event1, target=person2)
        )

        event2 = scene.addItem(
            Event(
                EventKind.Shift,
                person3,
                dateTime=util.Date(2020, 2, 1),
                relationship=RelationshipKind.Cutoff,
                relationshipTargets=[person1],
            )
        )
        emotion2 = scene.addItem(
            Emotion(kind=RelationshipKind.Cutoff, event=event2, target=person1)
        )

        assert len(scene.emotionsFor(person1)) == 2

        scene.removeItem(person1, undo=True)

        assert len(scene.people()) == 2
        assert len(scene.emotions()) == 0
        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.people()) == 3
        assert len(scene.emotions()) == 2
        assert len(scene.events()) == 2

    def test_remove_person_with_bidirectional_emotions(self, scene):
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
        emotion1 = scene.addItem(
            Emotion(kind=RelationshipKind.Conflict, event=event1, target=person2)
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
        emotion2 = scene.addItem(
            Emotion(kind=RelationshipKind.Conflict, event=event2, target=person1)
        )

        assert len(scene.emotions()) == 2

        scene.removeItem(person1, undo=True)

        assert len(scene.people()) == 1
        assert len(scene.emotions()) == 0
        assert len(scene.events()) == 0

        scene.undo()

        assert len(scene.people()) == 2
        assert len(scene.emotions()) == 2


class TestRemoveEventWithEmotions:

    def test_remove_event_deletes_emotions(self, scene):
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        event = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Fusion,
                relationshipTargets=[person2],
            )
        )
        emotion = scene.addItem(
            Emotion(kind=RelationshipKind.Fusion, event=event, target=person2)
        )

        assert len(scene.emotions()) == 1

        scene.removeItem(event, undo=True)

        assert len(scene.events()) == 0
        assert len(scene.emotions()) == 0
        assert len(scene.people()) == 2

        scene.undo()

        assert len(scene.events()) == 1
        assert len(scene.emotions()) == 1
        assert emotion in scene.emotions()

    def test_remove_event_with_multiple_emotions(self, scene):
        person1, person2, person3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        event = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Distance,
                relationshipTargets=[person2, person3],
            )
        )
        emotion1 = scene.addItem(
            Emotion(kind=RelationshipKind.Distance, event=event, target=person2)
        )
        emotion2 = scene.addItem(
            Emotion(kind=RelationshipKind.Distance, event=event, target=person3)
        )

        assert len(scene.emotions()) == 2
        assert len(scene.emotionsFor(event)) == 2

        scene.removeItem(event, undo=True)

        assert len(scene.events()) == 0
        assert len(scene.emotions()) == 0

        scene.undo()

        assert len(scene.events()) == 1
        assert len(scene.emotions()) == 2


class TestRemoveEmotionDirectly:

    def test_remove_single_emotion(self, scene):
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        event = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Fusion,
                relationshipTargets=[person2],
            )
        )
        emotion = scene.addItem(
            Emotion(kind=RelationshipKind.Fusion, event=event, target=person2)
        )

        assert len(scene.emotions()) == 1

        scene.removeItem(emotion, undo=True)

        assert len(scene.people()) == 2
        assert len(scene.events()) == 1
        assert len(scene.emotions()) == 0

        scene.undo()

        assert len(scene.emotions()) == 1
        assert emotion in scene.emotions()

        scene.redo()

        assert len(scene.emotions()) == 0

    def test_remove_emotion_leaves_event_and_people(self, scene):
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
        emotion = scene.addItem(
            Emotion(kind=RelationshipKind.Cutoff, event=event, target=person2)
        )

        scene.removeItem(emotion, undo=True)

        assert len(scene.emotions()) == 0
        assert len(scene.events()) == 1
        assert event in scene.events()
        assert len(scene.people()) == 2

    def test_remove_one_emotion_of_multiple(self, scene):
        person1, person2, person3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        event = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Distance,
                relationshipTargets=[person2, person3],
            )
        )
        emotion1 = scene.addItem(
            Emotion(kind=RelationshipKind.Distance, event=event, target=person2)
        )
        emotion2 = scene.addItem(
            Emotion(kind=RelationshipKind.Distance, event=event, target=person3)
        )

        assert len(scene.emotions()) == 2

        scene.removeItem(emotion1, undo=True)

        assert len(scene.emotions()) == 1
        assert emotion2 in scene.emotions()
        assert emotion1 not in scene.emotions()

        scene.undo()

        assert len(scene.emotions()) == 2
        assert emotion1 in scene.emotions()


class TestRemoveMultipleEmotions:

    def test_remove_multiple_emotions_at_once(self, scene):
        person1, person2, person3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        event1 = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Conflict,
                relationshipTargets=[person2],
            )
        )
        emotion1 = scene.addItem(
            Emotion(kind=RelationshipKind.Conflict, event=event1, target=person2)
        )

        event2 = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 2, 1),
                relationship=RelationshipKind.Distance,
                relationshipTargets=[person3],
            )
        )
        emotion2 = scene.addItem(
            Emotion(kind=RelationshipKind.Distance, event=event2, target=person3)
        )

        assert len(scene.emotions()) == 2

        scene.push(RemoveItems(scene, [emotion1, emotion2]))

        assert len(scene.emotions()) == 0
        assert len(scene.events()) == 2
        assert len(scene.people()) == 3

        scene.undo()

        assert len(scene.emotions()) == 2


class TestComplexEmotionScenarios:

    def test_remove_person_with_events_emotions_and_triangles(self, scene):
        person1, person2, person3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        event = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Inside,
                relationshipTargets=[person2],
                relationshipTriangles=[person3],
            )
        )
        emotion = scene.addItem(
            Emotion(kind=RelationshipKind.Inside, event=event, target=person2)
        )

        initial_people = len(scene.people())
        initial_events = len(scene.events())
        initial_emotions = len(scene.emotions())

        scene.removeItem(person1, undo=True)

        assert len(scene.people()) == 2
        assert len(scene.events()) == 0
        assert len(scene.emotions()) == 0

        scene.undo()

        assert len(scene.people()) == initial_people
        assert len(scene.events()) == initial_events
        assert len(scene.emotions()) == initial_emotions

    def test_sequential_emotion_operations(self, scene):
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
        emotion1 = scene.addItem(
            Emotion(kind=RelationshipKind.Conflict, event=event1, target=person2)
        )

        event2 = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 2, 1),
                relationship=RelationshipKind.Distance,
                relationshipTargets=[person2],
            )
        )
        emotion2 = scene.addItem(
            Emotion(kind=RelationshipKind.Distance, event=event2, target=person2)
        )

        assert len(scene.emotions()) == 2

        scene.removeItem(emotion1, undo=True)
        assert len(scene.emotions()) == 1

        scene.removeItem(event2, undo=True)
        assert len(scene.emotions()) == 0

        scene.undo()
        assert len(scene.emotions()) == 1
        assert emotion2 in scene.emotions()

        scene.undo()
        assert len(scene.emotions()) == 2

    def test_remove_event_chain_with_emotions(self, scene):
        person1, person2, person3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        event1 = scene.addItem(
            Event(
                EventKind.Shift,
                person1,
                dateTime=util.Date(2020, 1, 1),
                relationship=RelationshipKind.Conflict,
                relationshipTargets=[person2],
            )
        )
        emotion1 = scene.addItem(
            Emotion(kind=RelationshipKind.Conflict, event=event1, target=person2)
        )

        event2 = scene.addItem(
            Event(
                EventKind.Shift,
                person2,
                dateTime=util.Date(2020, 2, 1),
                relationship=RelationshipKind.Cutoff,
                relationshipTargets=[person3],
            )
        )
        emotion2 = scene.addItem(
            Emotion(kind=RelationshipKind.Cutoff, event=event2, target=person3)
        )

        assert len(scene.events()) == 2
        assert len(scene.emotions()) == 2

        scene.push(RemoveItems(scene, [event1, event2]))

        assert len(scene.events()) == 0
        assert len(scene.emotions()) == 0
        assert len(scene.people()) == 3

        scene.undo()

        assert len(scene.events()) == 2
        assert len(scene.emotions()) == 2
