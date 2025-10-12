import pytest
from pkdiagram.scene import (
    Scene,
    Person,
    Layer,
    LayerItem,
)
from pkdiagram.scene.commands import RemoveItems


class TestRemoveLayer:

    def test_remove_single_layer(self, scene):
        layer = scene.addItem(Layer(name="Layer 1"))

        assert len(scene.layers()) == 1

        scene.removeItem(layer, undo=True)

        assert len(scene.layers()) == 0

        scene.undo()

        assert len(scene.layers()) == 1
        assert layer in scene.layers()

    def test_remove_layer_with_items(self, scene):
        layer = scene.addItem(Layer(name="Layer 1"))
        person = scene.addItem(Person(name="Alice"))
        person.setLayers([layer.id])

        assert layer.id in person.layers()

        scene.removeItem(layer, undo=True)

        assert len(scene.layers()) == 0
        assert layer.id not in person.layers()

        scene.undo()

        assert len(scene.layers()) == 1
        assert layer.id in person.layers()

    def test_remove_multiple_layers(self, scene):
        layer1 = scene.addItem(Layer(name="Layer 1"))
        layer2 = scene.addItem(Layer(name="Layer 2"))
        layer3 = scene.addItem(Layer(name="Layer 3"))

        assert len(scene.layers()) == 3

        scene.push(RemoveItems(scene, [layer1, layer2]))

        assert len(scene.layers()) == 1
        assert layer3 in scene.layers()

        scene.undo()

        assert len(scene.layers()) == 3

    def test_sequential_layer_removal(self, scene):
        layer1 = scene.addItem(Layer(name="Layer 1"))
        layer2 = scene.addItem(Layer(name="Layer 2"))

        scene.removeItem(layer1, undo=True)
        assert len(scene.layers()) == 1

        scene.removeItem(layer2, undo=True)
        assert len(scene.layers()) == 0

        scene.undo()
        assert len(scene.layers()) == 1
        assert layer2 in scene.layers()

        scene.undo()
        assert len(scene.layers()) == 2


class TestRemoveLayerItem:

    def test_remove_layer_item(self, scene):
        layer = scene.addItem(Layer(name="Layer 1", active=True))
        layerItem = scene.addItem(LayerItem())
        # LayerItem auto-assigned to active layer

        assert len(scene.find(types=LayerItem)) == 1
        assert layer.id in layerItem.layers()

        scene.removeItem(layerItem, undo=True)

        assert len(scene.find(types=LayerItem)) == 0

        scene.undo()

        assert len(scene.find(types=LayerItem)) == 1
        assert layerItem in scene.find(types=LayerItem)

    def test_remove_layer_removes_layer_items(self, scene):
        layer = scene.addItem(Layer(name="Layer 1", active=True))
        layerItem1 = scene.addItem(LayerItem())
        layerItem2 = scene.addItem(LayerItem())
        # LayerItems auto-assigned to active layer

        assert len(scene.find(types=LayerItem)) == 2
        assert layer.id in layerItem1.layers()
        assert layer.id in layerItem2.layers()

        scene.removeItem(layer, undo=True)

        assert len(scene.layers()) == 0
        assert layer.id not in layerItem1.layers()
        assert layer.id not in layerItem2.layers()

        scene.undo()

        assert len(scene.layers()) == 1
        assert layer.id in layerItem1.layers()
        assert layer.id in layerItem2.layers()

    def test_orphaned_layer_item_auto_deleted(self, scene):
        """LayerItem with no layers should be auto-deleted when last layer removed."""
        layer = scene.addItem(Layer(name="Layer 1", active=True))
        layerItem = scene.addItem(LayerItem())
        # LayerItem auto-assigned to active layer

        assert len(scene.find(types=LayerItem)) == 1
        assert layer.id in layerItem.layers()

        scene.removeItem(layer, undo=True)

        # LayerItem should be auto-deleted since it has no layers
        assert len(scene.find(types=LayerItem)) == 0
        assert len(scene.layers()) == 0

        scene.undo()

        # Both should be restored
        assert len(scene.find(types=LayerItem)) == 1
        assert len(scene.layers()) == 1
        assert layer.id in layerItem.layers()

    def test_orphaned_layer_item_multiple_layers(self, scene):
        """LayerItem with multiple layers only deleted when all are removed."""
        layer1 = scene.addItem(Layer(name="Layer 1", active=True))
        layer2 = scene.addItem(Layer(name="Layer 2", active=True))
        layerItem = scene.addItem(LayerItem())
        # LayerItem auto-assigned to both active layers

        assert len(scene.find(types=LayerItem)) == 1
        assert layer1.id in layerItem.layers()
        assert layer2.id in layerItem.layers()

        scene.removeItem(layer1, undo=True)

        # LayerItem should still exist since it has layer2
        assert len(scene.find(types=LayerItem)) == 1
        assert layer2.id in layerItem.layers()
        assert layer1.id not in layerItem.layers()

        scene.removeItem(layer2, undo=True)

        # Now LayerItem should be orphaned and deleted
        assert len(scene.find(types=LayerItem)) == 0

        scene.undo()
        assert len(scene.find(types=LayerItem)) == 1

        scene.undo()
        assert layer1.id in layerItem.layers()
        assert layer2.id in layerItem.layers()

    def test_batch_layer_removal_orphans_items(self, scene):
        """Removing multiple layers at once orphans and deletes LayerItems."""
        layer1 = scene.addItem(Layer(name="Layer 1", active=True))
        layer2 = scene.addItem(Layer(name="Layer 2", active=True))
        layerItem = scene.addItem(LayerItem())
        # LayerItem auto-assigned to both active layers
        assert layer1.id in layerItem.layers()
        assert layer2.id in layerItem.layers()

        scene.push(RemoveItems(scene, [layer1, layer2]))

        assert len(scene.find(types=LayerItem)) == 0
        assert len(scene.layers()) == 0

        scene.undo()

        assert len(scene.find(types=LayerItem)) == 1
        assert len(scene.layers()) == 2


class TestLayerProperties:

    def test_remove_person_preserves_layer_properties(self, scene):
        layer = scene.addItem(Layer(name="Layer 1"))
        person = scene.addItem(Person(name="Alice"))
        person.setLayers([layer.id])

        layer.setItemProperty(person.id, "hideLabel", True)
        assert layer.getItemProperty(person.id, "hideLabel") == (True, True)

        scene.removeItem(person, undo=True)

        assert len(scene.people()) == 0

        scene.undo()

        assert len(scene.people()) == 1
        assert layer.getItemProperty(person.id, "hideLabel") == (True, True)

    def test_remove_layer_clears_properties(self, scene):
        layer = scene.addItem(Layer(name="Layer 1"))
        person1, person2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
        person1.setLayers([layer.id])
        person2.setLayers([layer.id])

        layer.setItemProperty(person1.id, "hideLabel", True)
        layer.setItemProperty(person2.id, "hideLabel", False)

        scene.removeItem(layer, undo=True)

        assert len(scene.layers()) == 0

        scene.undo()

        assert len(scene.layers()) == 1
        assert layer.getItemProperty(person1.id, "hideLabel") == (True, True)
        assert layer.getItemProperty(person2.id, "hideLabel") == (False, True)

    def test_multiple_people_with_layer_properties(self, scene):
        layer1 = scene.addItem(Layer(name="Layer 1"))
        layer2 = scene.addItem(Layer(name="Layer 2"))
        person = scene.addItem(Person(name="Alice"))
        person.setLayers([layer1.id, layer2.id])

        layer1.setItemProperty(person.id, "hideLabel", True)
        layer2.setItemProperty(person.id, "hideLabel", False)

        scene.removeItem(person, undo=True)

        assert len(scene.people()) == 0

        scene.undo()

        assert len(scene.people()) == 1
        assert layer1.getItemProperty(person.id, "hideLabel") == (True, True)
        assert layer2.getItemProperty(person.id, "hideLabel") == (False, True)


class TestComplexLayerScenarios:

    def test_remove_multiple_people_with_layer_properties(self, scene):
        layer = scene.addItem(Layer(name="Layer 1"))
        person1, person2, person3 = scene.addItems(
            Person(name="Alice"), Person(name="Bob"), Person(name="Charlie")
        )
        person1.setLayers([layer.id])
        person2.setLayers([layer.id])
        person3.setLayers([layer.id])

        layer.setItemProperty(person1.id, "hideLabel", True)
        layer.setItemProperty(person2.id, "hideLabel", True)
        layer.setItemProperty(person3.id, "hideLabel", False)

        scene.push(RemoveItems(scene, [person1, person2]))

        assert len(scene.people()) == 1

        scene.undo()

        assert len(scene.people()) == 3
        assert layer.getItemProperty(person1.id, "hideLabel") == (True, True)
        assert layer.getItemProperty(person2.id, "hideLabel") == (True, True)
        assert layer.getItemProperty(person3.id, "hideLabel") == (False, True)

    def test_sequential_layer_operations(self, scene):
        layer1 = scene.addItem(Layer(name="Layer 1"))
        layer2 = scene.addItem(Layer(name="Layer 2"))
        person = scene.addItem(Person(name="Alice"))
        person.setLayers([layer1.id, layer2.id])

        layer1.setItemProperty(person.id, "hideLabel", True)
        layer2.setItemProperty(person.id, "hideLabel", False)

        assert len(scene.layers()) == 2
        assert layer1.getItemProperty(person.id, "hideLabel") == (True, True)

        scene.removeItem(layer1, undo=True)
        assert len(scene.layers()) == 1

        scene.removeItem(person, undo=True)
        assert len(scene.people()) == 0

        scene.undo()
        assert len(scene.people()) == 1
        assert layer2.getItemProperty(person.id, "hideLabel") == (False, True)

        scene.undo()
        assert len(scene.layers()) == 2
        assert layer1.getItemProperty(person.id, "hideLabel") == (True, True)

    def test_remove_layer_with_mixed_items(self, scene):
        layer = scene.addItem(Layer(name="Layer 1", active=True))
        person1 = scene.addItem(Person(name="Alice"))
        person2 = scene.addItem(Person(name="Bob"))
        layerItem = scene.addItem(LayerItem())
        # Persons and LayerItem auto-assigned to active layer

        assert layer.id in person1.layers()
        assert layer.id in person2.layers()
        assert layer.id in layerItem.layers()

        layer.setItemProperty(person1.id, "hideLabel", True)
        layer.setItemProperty(person2.id, "hideLabel", False)

        initial_people = len(scene.people())
        initial_layer_items = len(scene.find(types=LayerItem))

        scene.removeItem(layer, undo=True)

        assert len(scene.layers()) == 0
        assert len(scene.people()) == initial_people
        assert len(scene.find(types=LayerItem)) == 0

        scene.undo()

        assert len(scene.layers()) == 1
        assert len(scene.find(types=LayerItem)) == initial_layer_items
        assert len(scene.people()) == initial_people
        assert layer.getItemProperty(person1.id, "hideLabel") == (True, True)
        assert layer.getItemProperty(person2.id, "hideLabel") == (False, True)
