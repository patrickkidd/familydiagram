import pytest
from pkdiagram.scene import (
    Scene,
    Person,
    Marriage,
    ChildOf,
    MultipleBirth,
)
from pkdiagram.scene.commands import RemoveItems


class TestRemoveChildOf:

    def test_remove_child_relationship(self, scene):
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        child = scene.addItem(Person(name="Charlie"))
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf = child.setParents(marriage)

        assert len(scene.find(types=ChildOf)) == 1
        assert child.childOf == childOf
        assert childOf.parents() == marriage

        scene.removeItem(childOf, undo=True)

        assert len(scene.find(types=ChildOf)) == 0
        assert child.childOf is None

        scene.undo()

        assert len(scene.find(types=ChildOf)) == 1
        assert child.childOf is not None

    def test_remove_marriage_deletes_children(self, scene):
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        child1, child2 = scene.addItems(Person(name="Charlie"), Person(name="Diana"))
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf1 = child1.setParents(marriage)
        childOf2 = child2.setParents(marriage)

        assert len(scene.find(types=ChildOf)) == 2

        scene.removeItem(marriage, undo=True)

        assert len(scene.marriages()) == 0
        assert len(scene.find(types=ChildOf)) == 0
        assert child1.childOf is None
        assert child2.childOf is None

        scene.undo()

        assert len(scene.marriages()) == 1
        assert len(scene.find(types=ChildOf)) == 2
        assert child1.childOf is not None
        assert child2.childOf is not None

    def test_remove_person_removes_childOf(self, scene):
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        child = scene.addItem(Person(name="Charlie"))
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf = child.setParents(marriage)

        assert len(scene.find(types=ChildOf)) == 1

        scene.removeItem(child, undo=True)

        assert len(scene.people()) == 2
        assert len(scene.find(types=ChildOf)) == 0

        scene.undo()

        assert len(scene.people()) == 3
        assert len(scene.find(types=ChildOf)) == 1

    def test_remove_parent_removes_marriage_and_children(self, scene):
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        child = scene.addItem(Person(name="Charlie"))
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf = child.setParents(marriage)

        scene.removeItem(parent1, undo=True)

        assert len(scene.people()) == 2
        assert len(scene.marriages()) == 0
        assert len(scene.find(types=ChildOf)) == 0

        scene.undo()

        assert len(scene.people()) == 3
        assert len(scene.marriages()) == 1
        assert len(scene.find(types=ChildOf)) == 1


class TestRemoveBirthPartners:

    def test_remove_one_twin_reattach_to_existing_multiplebirth(self, scene):
        """When removing one twin, if other twins still exist, reattach on undo."""
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        twin1, twin2, twin3 = scene.addItems(
            Person(name="Charlie"), Person(name="Diana"), Person(name="Eve")
        )
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf1 = twin1.setParents(marriage)
        childOf2 = twin2.setParents(marriage)
        childOf3 = twin3.setParents(marriage)
        childOf3 = twin3.setParents(marriage)
        twin2.setParents(twin1.childOf)
        multipleBirth = twin2.childOf.multipleBirth
        twin3.setParents(multipleBirth)

        assert len(multipleBirth.children()) == 3

        scene.removeItem(twin1, undo=True)

        # twin1 removed, but twin2 and twin3 still have multipleBirth
        assert len(scene.people()) == 4
        assert twin2.childOf.multipleBirth is not None
        assert twin3.childOf.multipleBirth is not None

        scene.undo()

        # twin1 should reattach to existing multipleBirth
        assert len(scene.people()) == 5
        assert twin1.childOf.multipleBirth is not None
        assert twin2.childOf.multipleBirth is not None
        assert twin3.childOf.multipleBirth is not None
        assert len(multipleBirth.children()) == 3

    def test_remove_all_but_one_twin_recreate_multiplebirth(self, scene):
        """When only one twin remains, removing then restoring recreates MultipleBirth."""
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        twin1, twin2 = scene.addItems(Person(name="Charlie"), Person(name="Diana"))
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf1 = twin1.setParents(marriage)
        childOf2 = twin2.setParents(marriage)
        childOf2 = twin2.setParents(marriage)
        twin2.setParents(twin1.childOf)
        multipleBirth = twin2.childOf.multipleBirth

        # Remove twin1, now twin2 is alone
        scene.removeItem(twin1, undo=True)
        assert twin2.childOf.multipleBirth is not None

        # Remove twin2, multipleBirth should have no children
        scene.removeItem(twin2, undo=True)

        scene.undo()
        # twin2 restored

        scene.undo()
        # twin1 restored and should recreate multipleBirth connection
        assert twin1.childOf.multipleBirth is not None
        assert twin2.childOf.multipleBirth is not None
        assert twin1.childOf.multipleBirth == twin2.childOf.multipleBirth

    def test_remove_batch_birthpartners(self, scene):
        """Batch removal of multiple twins."""
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        twin1, twin2, twin3 = scene.addItems(
            Person(name="Charlie"), Person(name="Diana"), Person(name="Eve")
        )
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf1 = twin1.setParents(marriage)
        childOf2 = twin2.setParents(marriage)
        childOf3 = twin3.setParents(marriage)
        childOf3 = twin3.setParents(marriage)
        twin2.setParents(twin1.childOf)
        multipleBirth = twin2.childOf.multipleBirth
        twin3.setParents(multipleBirth)

        scene.push(RemoveItems(scene, [twin1, twin2]))

        assert len(scene.people()) == 3
        assert twin3.childOf.multipleBirth is not None

        scene.undo()

        assert len(scene.people()) == 5
        assert twin1.childOf.multipleBirth is not None
        assert twin2.childOf.multipleBirth is not None
        assert twin3.childOf.multipleBirth is not None

    def test_remove_non_twin_with_birthpartners_list(self, scene):
        """Person without birthPartners should restore normally."""
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        child = scene.addItem(Person(name="Charlie"))
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf = child.setParents(marriage)

        # No multipleBirth, no birthPartners
        assert childOf.multipleBirth is None

        scene.removeItem(child, undo=True)

        scene.undo()

        assert child.childOf is not None
        assert childOf.parents() == marriage
        assert childOf.multipleBirth is None


class TestRemoveMultipleBirth:

    def test_remove_multiple_birth_relationship(self, scene):
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        twin1, twin2 = scene.addItems(Person(name="Charlie"), Person(name="Diana"))
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf1 = twin1.setParents(marriage)
        childOf2 = twin2.setParents(marriage)
        childOf2 = twin2.setParents(marriage)
        twin2.setParents(twin1.childOf)
        multipleBirth = twin2.childOf.multipleBirth

        assert len(scene.find(types=MultipleBirth)) == 1
        assert twin1.childOf.multipleBirth is not None
        assert twin2.childOf.multipleBirth is not None

        scene.removeItem(multipleBirth, undo=True)

        assert len(scene.find(types=MultipleBirth)) == 0
        assert twin1.childOf.multipleBirth is None
        assert twin2.childOf.multipleBirth is None

        scene.undo()

        assert len(scene.find(types=MultipleBirth)) == 1
        assert twin1.childOf.multipleBirth is not None
        assert twin2.childOf.multipleBirth is not None

    def test_remove_marriage_deletes_multiple_birth(self, scene):
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        twin1, twin2 = scene.addItems(Person(name="Charlie"), Person(name="Diana"))
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf1 = twin1.setParents(marriage)
        childOf2 = twin2.setParents(marriage)
        childOf2 = twin2.setParents(marriage)
        twin2.setParents(twin1.childOf)
        multipleBirth = twin2.childOf.multipleBirth

        scene.removeItem(marriage, undo=True)

        assert len(scene.marriages()) == 0
        assert len(scene.find(types=MultipleBirth)) == 0
        assert len(scene.find(types=ChildOf)) == 0

        scene.undo()

        assert len(scene.marriages()) == 1
        assert len(scene.find(types=MultipleBirth)) == 1
        assert len(scene.find(types=ChildOf)) == 2

    def test_remove_one_twin_keeps_multiple_birth(self, scene):
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        twin1, twin2, twin3 = scene.addItems(
            Person(name="Charlie"), Person(name="Diana"), Person(name="Youngest")
        )
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf1 = twin1.setParents(marriage)
        childOf2 = twin2.setParents(marriage)
        childOf3 = twin3.setParents(marriage)
        twin2.setParents(twin1.childOf)
        twin3.setParents(twin1.childOf)
        multipleBirth = twin2.childOf.multipleBirth

        assert len(scene.people()) == 3
        assert len(scene.find(types=MultipleBirth)) == 1
        assert len(scene.find(types=ChildOf)) == 1

        scene.removeItem(twin1, undo=True)

        assert len(scene.people()) == 3
        assert len(scene.find(types=MultipleBirth)) == 1
        assert len(scene.find(types=ChildOf)) == 1
        assert twin2.childOf.multipleBirth is not None

        scene.undo()

        assert len(scene.people()) == 4
        assert len(scene.find(types=MultipleBirth)) == 1
        assert len(scene.find(types=ChildOf)) == 2

    def test_remove_triplets_multiple_birth(self, scene):
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        triplet1, triplet2, triplet3 = scene.addItems(
            Person(name="Charlie"), Person(name="Diana"), Person(name="Eve")
        )
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf1 = scene.addItem(ChildOf(triplet1, marriage))
        childOf2 = scene.addItem(ChildOf(triplet2, marriage))
        childOf3 = scene.addItem(ChildOf(triplet3, marriage))
        childOf3 = scene.addItem(ChildOf(triplet3, marriage))
        twin2.setParents(twin1.childOf)
        multipleBirth = twin2.childOf.multipleBirth
        twin3.setParents(multipleBirth)

        assert len(multipleBirth.children()) == 3

        scene.removeItem(multipleBirth, undo=True)

        assert len(scene.find(types=MultipleBirth)) == 0
        assert len(scene.find(types=ChildOf)) == 3

        scene.undo()

        assert len(scene.find(types=MultipleBirth)) == 1
        assert len(multipleBirth.children()) == 3


class TestComplexChildScenarios:

    def test_sequential_child_operations(self, scene):
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        child1, child2 = scene.addItems(Person(name="Charlie"), Person(name="Diana"))
        marriage = scene.addItem(Marriage(parent1, parent2))
        child1.setParents(marriage)
        child2.setParents(marriage)

        scene.removeItem(child1.childOf, undo=True)
        assert len(scene.find(types=ChildOf)) == 1

        scene.removeItem(child2.childOf, undo=True)
        assert len(scene.find(types=ChildOf)) == 0

        scene.undo()
        assert len(scene.find(types=ChildOf)) == 1
        assert child2.childOf is not None

        scene.undo()
        assert len(scene.find(types=ChildOf)) == 2

    def test_remove_multiple_children_at_once(self, scene):
        parent1, parent2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        child1, child2, child3 = scene.addItems(
            Person(name="Charlie"), Person(name="Diana"), Person(name="Eve")
        )
        marriage = scene.addItem(Marriage(parent1, parent2))
        childOf1 = child1.setParents(marriage)
        childOf2 = child2.setParents(marriage)
        childOf3 = child3.setParents(marriage)

        assert len(scene.find(types=ChildOf)) == 3

        scene.push(RemoveItems(scene, [childOf1, childOf2]))

        assert len(scene.find(types=ChildOf)) == 1
        assert child3.childOf == childOf3

        scene.undo()

        assert len(scene.find(types=ChildOf)) == 3

    def test_remove_blended_family(self, scene):
        parent1, parent2, parent3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Carol")
        )
        child1, child2 = scene.addItems(Person(name="Charlie"), Person(name="Diana"))
        marriage1 = scene.addItem(Marriage(parent1, parent2))
        marriage2 = scene.addItem(Marriage(parent1, parent3))
        childOf1 = child1.setParents(marriage1)
        childOf2 = child2.setParents(marriage2)

        assert len(scene.people()) == 5
        assert len(scene.marriages()) == 2
        assert len(scene.find(types=ChildOf)) == 2

        scene.removeItem(parent1, undo=True)

        assert len(scene.people()) == 4
        assert len(scene.marriages()) == 0
        assert len(scene.find(types=ChildOf)) == 0

        scene.undo()

        assert len(scene.people()) == 5
        assert len(scene.marriages()) == 2
        assert len(scene.find(types=ChildOf)) == 2
