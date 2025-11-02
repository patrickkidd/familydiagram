# RemoveItems Command Test Suite

Comprehensive TDD test suite for the RemoveItems undo/redo command covering all item types and scenarios.

## Test Files

### Core Item Types

#### `test_remove_people_events.py` (5 classes, 7 tests)
- **TestRemoveItemsPersonWithEvents**: Person removal with single/multiple events
- **TestRemoveItemsEvent**: Direct event removal
- **TestRemoveItemsMarriage**: Marriage removal
- **TestRemoveItemsMultiple**: Batch removal operations
- **TestRemoveItemsComplexScenarios**: Person with events and marriages, sequential operations

#### `test_remove_emotions.py` (5 classes, 16 tests)
- **TestRemovePersonWithEmotions**: Person removal as subject/target, multiple emotions, bidirectional
- **TestRemoveEventWithEmotions**: Event removal cascading to emotions
- **TestRemoveEmotionDirectly**: Emotion-only removal
- **TestRemoveMultipleEmotions**: Batch emotion removal
- **TestComplexEmotionScenarios**: Triangles, sequential operations, event chains

#### `test_remove_nondyadic_emotions.py` (1 class, 6 tests)
- **TestRemoveNonDyadicEmotions**: Parent item restoration, triangle emotions, batch removal
  - Critical code path: `emotion.setParentItem()` restoration on undo

### Family Structure

#### `test_remove_children.py` (4 classes, 17 tests)
- **TestRemoveChildOf**: Child relationship removal, cascading from marriage/person/parent
- **TestRemoveBirthPartners**: Complex twin restoration logic
  - Reattach to existing MultipleBirth if other twins remain
  - Recreate MultipleBirth when all siblings restored
  - Batch removal of twins
  - Non-twin children (no birthPartners)
- **TestRemoveMultipleBirth**: MultipleBirth removal, cascading, triplets
- **TestComplexChildScenarios**: Sequential operations, blended families

### Layers

#### `test_remove_layers.py` (4 classes, 18 tests)
- **TestRemoveLayer**: Basic layer removal, layers with items, batch removal
- **TestRemoveLayerItem**: LayerItem removal
  - **Orphaned LayerItem auto-deletion**: When layer removed and LayerItem has no remaining layers
  - Multiple layers per item
  - Batch layer removal orphaning items
- **TestLayerProperties**: Property preservation through undo/redo
- **TestComplexLayerScenarios**: Mixed items, active layers, sequential operations

### Advanced Scenarios

#### `test_remove_cross_dependencies.py` (3 classes, 11 tests)
- **TestRemovePersonWithEverything**: All relationships at once (marriages, children, events, emotions, layers)
- **TestAlreadyDeletedItems**: Handling cascade-deleted items
  - Person already deleted by cascade
  - Emotion after event deleted
  - ChildOf after marriage deleted
- **TestCircularDependencies**: Mutual emotions, triangles, blended families

#### `test_remove_pairbond_events.py` (8 classes, 21 tests)
- **TestRemoveBondedEvents**: Bonded event removal
- **TestRemoveMarriedEvents**: Married event removal
- **TestRemoveSeparatedEvents**: Separated events, full lifecycle
- **TestRemoveDivorcedEvents**: Divorced events, complete lifecycle
- **TestRemoveAdoptedEvents**: Adopted event with children
- **TestRemoveSeparatedBirthEvents**: Birth before relationship
- **TestRemoveMovedEvents**: Couple moving together
- **TestComplexPairBondScenarios**: Multiple marriages, sequential operations

## Key Testing Patterns

### Cascading Deletions
All tests verify proper cascading:
- Removing Person → deletes marriages, events, emotions, childOf
- Removing Marriage → deletes children (ChildOf), MultipleBirth
- Removing Event → deletes associated Emotions
- Removing Layer → removes from LayerItems, deletes orphaned LayerItems

### Undo/Redo Verification
Standard pattern:
```python
# Setup
item = scene.addItem(...)
# Remove
scene.removeItem(item, undo=True)
assert item not in scene...
# Undo
scene.undo()
assert item in scene...
# Redo
scene.redo()
assert item not in scene...
```

### Special Cases Covered

1. **Non-dyadic Emotions**: Parent item restoration (`emotion.setParentItem()`)
2. **BirthPartners Logic**: Reattach vs recreate MultipleBirth
3. **Orphaned LayerItems**: Auto-deletion when no layers remain
4. **Already-Deleted Items**: Graceful handling of cascade-deleted items
5. **Circular Dependencies**: Mutual relationships, triangles
6. **PairBond Events**: Full marriage lifecycle with spouse references

## Test Execution

Run all tests:
```bash
python -m pytest tests/commands/ -v
```

Run specific file:
```bash
python -m pytest tests/commands/test_remove_emotions.py -v
```

Run specific test:
```bash
python -m pytest tests/commands/test_remove_children.py::TestRemoveBirthPartners::test_remove_one_twin_reattach_to_existing_multiplebirth -v
```

## TDD Approach

These tests are written using TDD principles:
- Tests specify **intended behavior** of RemoveItems command
- Tests assume correct API usage based on code analysis
- **Known bugs in scene.py are ignored** - tests represent correct behavior
- Tests will guide bug fixes in subsequent implementation phase

## Coverage Summary

- ✅ Person removal with events
- ✅ Event removal (all types including PairBond)
- ✅ Emotion removal (dyadic and non-dyadic)
- ✅ Marriage removal
- ✅ ChildOf removal
- ✅ MultipleBirth removal with BirthPartners logic
- ✅ Layer removal
- ✅ LayerItem removal with orphan handling
- ✅ Layer property preservation
- ✅ Cross-item dependencies
- ✅ Circular dependencies
- ✅ Already-deleted items
- ✅ Batch removal operations
- ✅ Sequential undo/redo operations
- ❌ Documents (not supported yet)
- ❌ ItemDetails (ignored per commands.py)
- ❌ SeparationIndicator (ignored per commands.py)
