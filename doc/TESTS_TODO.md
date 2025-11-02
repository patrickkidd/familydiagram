# Test Suite TODO



## Key rules
- using the new Event() constructor params, notably kind, person, relationship*.
- Creating Item objects in a scene.addItems call like `personA, personB = scene.addItems(Person(), Person())` instead of
- Add Person objects prior to adding other objects that reference them.
- understanding the new implicit Emotion creation modes creating the items and
then adding them later
- Not using composed special events like person.birthEvent and instead adding
  an event with the proper `EventKind` and then using `Scene.eventsFor(item,
  kinds=...)`
- Using `Scene.find(...)` api where possible, etc.
- Use the `scene` fixture instead of creating a new scene object for every test
  or referencing the same scene object through the view or model fixture.
- Do not correct app code to check if `Event.person()` is None or
  `Event.person()` is not in `scene.people()`, these values should always be
  valid. If they are not then that is a problem in the calling code or the test code.
- Replace composed special events, e.g. `birthEvent` or `setBirthDateTime`, with
  adding Event's of the correct kind
- See pkdiagram/scene/CLAUDE.md: Scene owns all Item relationship mutation
  logic. QUndoCommand subclasses only predict changes and store metadata for
  undo/redo.



## Key API Changes

### Event Constructor
- **Old**: `Event(EventKind.Birth, person=person)`
- **New**: `Event(EventKind.Birth, person, dateTime=...)`

### Item Creation
- **Old**: Create items e.g. `personA = Person()`, then `scene.addItem(item)`
- **New**: `personA, personB = scene.addItems(Person(), Person())`

### Event Queries
- **Old**: `person.birthEvent`, `person.deathEvent`
- **New**: `scene.eventsFor(person, kinds=EventKind.Birth)`

### Emotion Creation
- **Old**: `Emotion(kind, target, person=person)` then add separately
- **New**: Implicit via Event with relationship params or explicit add

### Scene Queries
- Prefer `Scene.find(ids=..., types=..., tags=...)` over manual iteration



## Patterns to Apply

### Pattern 1: Item Creation
```python
# Before
person = Person()
scene.addItem(person)

# After
person = scene.addItem(Person())
# or
personA, personB = scene.addItems(Person(), Person())
```

### Pattern 2: Event Creation
```python
# Before
event = Event(EventKind.Shift, person, dateTime=date)
scene.addItem(event)

# After
event = scene.addItem(Event(EventKind.Shift, person, dateTime=date))
```

### Pattern 3: Event Queries
```python
# Before
birth = person.birthEvent

# After
births = scene.eventsFor(person, kinds=EventKind.Birth)
birth = births[0] if births else None
```

### Pattern 4: Emotion with Event
```python
# Before
emotion = Emotion(RelationshipKind.Conflict, personB, person=personA)
scene.addItems(personA, personB, emotion)

# After
event = scene.addItem(Event(
    EventKind.Shift,
    personA,
    relationship=RelationshipKind.Conflict,
    relationshipTargets=[personB],
    dateTime=util.Date(2001, 1, 1)
))
emotion = scene.emotionsFor(event)[0]
```

### Pattern 5: Scene Queries
```python
# Before
people = [item for item in scene.items() if isinstance(item, Person)]

# After
people = scene.find(types=Person)
```

## Overview
**Current Status: 298 passed, 2 failed out of 300 tests (99.3% passing)**

## Remaining Test Failures

### 1. test_marriage.py::test_detailsText_lines
**Status:** ❌ FAILING
**Issue:** Event location not displayed in marriage detailsText
**Error:** Shows "None" instead of "Moved to Washington, DC"
**Location:** tests/scene/test_marriage.py:840
**Root Cause:** Marriage.detailsText() method not properly formatting Event location property

**Action Items:**
1. Check Marriage.detailsText() implementation in pkdiagram/scene/marriage.py
2. Verify Event.location property is being set correctly
3. Fix formatting logic to include location when present

### 2. test_scene_read_write.py::test_clean_stale_refs
**Status:** ❌ FAILING
**Issue:** Stale reference cleanup not working + AttributeError during scene read
**Error:**
- Assert 0 == 9 (no references pruned)
- AttributeError: 'NoneType' object has no attribute 'childOf' at pkdiagram/scene/multiplebirth.py:186
**Location:** tests/scene/test_scene_read_write.py:84
**Root Cause:** MultipleBirth.shouldShowFor() doesn't handle None person references properly

**Action Items:**
1. Fix None check in MultipleBirth.shouldShowFor() at pkdiagram/scene/multiplebirth.py:186
2. Add defensive check: `if person and person.childOf:`
3. Investigate why person references are becoming None during scene loading
4. Verify Scene.cleanStaleRefs() is properly removing orphaned references

## Fixed Tests (Now Passing) ✅

### Scene Tests
- **test_childof.py:** 18/18 tests passing (100%)
- **test_remove_children.py:** 15/15 tests passing (100%)
- **test_scene_add_remove.py::test_add_emotion:** Both parameterized tests now passing

### Model Tests
- **test_timelinemodel.py:** All previously failing tests now pass:
  - test_delete_emotion_date ✅
  - test_set_emotion_date ✅
  - test_showAliases_signals ✅

## Test Execution Notes

Some tests appear to hang indefinitely when running the full suite with `pytest`. For efficient testing:
- Run specific test files or functions individually
- Use timeout parameters when running larger test sets
- Consider investigating hanging tests separately

## Priority Fixes

1. **HIGH:** Fix MultipleBirth None reference handling (blocks scene loading)
2. **MEDIUM:** Fix Marriage.detailsText() location formatting

## Completed Work

### API Migration ✅ COMPLETE
- All test files successfully migrated to new Event/Scene API patterns
- Event constructor using new format: `Event(EventKind.X, person, dateTime=...)`
- Item creation using: `scene.addItems(Item(), Item())`
- No "create then add" anti-patterns remain

### ChildOf/MultipleBirth System ✅ COMPLETE
- Fixed ChildOf removal bug with undefined parents variable
- Fixed undo/redo for ChildOf/MultipleBirth objects
- Changed MultipleBirth removal to keep children attached
- All related tests now passing