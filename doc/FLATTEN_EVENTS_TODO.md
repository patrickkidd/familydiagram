# Event Flattening Refactor - Master TODO

**Goal:** Make Events top-level Scene objects instead of children of Person/Marriage/Emotion, simplifying the object hierarchy and enabling better timeline/event management.

**Status:** In progress (progress commit: 235dc569)

**Archive:** Completed phases moved to [FLATTEN_EVENTS_DONE.md](./FLATTEN_EVENTS_DONE.md)

---

## 📋 TABLE OF CONTENTS


### Phase 11: Commands/Undo 🟡
- **[Phase 11](#phase-11-commandsundo-)** - Commands/Undo
  - [11.1 ⬜ Remove commands.SetEmotionPerson](#111-remove-commandssetemotionperson)
  - [11.2 ⬜ Update AddItem Command](#112-update-additem-command)
  - [11.3 ⬜ Update RemoveItems Command](#113-update-removeitems-command---critical-refactor-needed-) (CRITICAL REFACTOR)

### Phase 12: Clone/Remap Refactor 🟡
- **[Phase 12](#phase-12-cloneremap-refactor-)** - Clone/Remap Refactor
  - [12.1 ⬜ Add Event.clone() Method](#121-add-eventclone-method)
  - [12.2 ⬜ Update Emotion.clone() and Emotion.remap()](#122-update-emotionclone-and-emotionremap)
  - [12.3 ⬜ Update Marriage.clone()](#123-update-marriageclone---events-handling)
  - [12.4 ⬜ Test Clone/Paste Workflow](#124-test-clonepaste-workflow)

### Phase 7: Test Fixes 🟡
- **[Phase 7](#phase-7-test-fixes-)** - Test Fixes
  - [7.1 ⬜ Fix Event() Constructor Calls](#71-fix-event-constructor-calls) (18 test files)
  - [7.3 ⬜ Fix Emotion Construction](#73-fix-emotion-construction) (13 files)
  - [7.4 ⬜ Graphical timeline tests](#75-graphical-timeline-tests)
  - [7.5 ⬜ Run Full Test Suite and Fix Failures](#74-run-full-test-suite-and-fix-failures)

### Phase 13: Documentation 🟡
- **[Phase 13](#phase-13-documentation-)** - Documentation
  - [13.1 ⬜ Update CLAUDE.md](#131-update-claudemd)
  - [13.2 ⬜ Add Architecture Diagram](#132-add-architecture-diagram)

### Phase 14: File Format Version Bump 🔴
- **[Phase 14](#phase-14-file-format-version-bump--critical)** - File Format Version Bump
  - [14.1 ⬜ Update VERSION_COMPAT](#141-update-version_compat)
  - [14.2 ⬜ Add Migration Test Cases](#142-add-migration-test-cases)
  - [14.3 ⬜ Backward Compatibility Strategy](#143-backward-compatibility-strategy)

### 📚 Reference
- **[Appendix](#appendix-original-analysis-issues)** - Original Analysis Issues
- **[Appendix](#appendix-user-decisions--clarifications)** - User Decisions & Clarifications

---

## 🚨 QUICK START - Critical Path

**Priority order:** Phase 11 → 12 → 7 → 13 → 14

**Next Steps:**
1. Fix Commands/Undo and Clone (Phases 11, 12)
2. Fix remaining test failures (Phase 7)
3. Polish and release (Phases 13, 14)

**Completed:**
- ✅ Phases 0.1, 1, 2, 3, 4, 5, 6, 7.0, 7.2, 10, 10.5, 15 (see [FLATTEN_EVENTS_DONE.md](./FLATTEN_EVENTS_DONE.md))
- ✅ Phases 0.2, 0.3, 8.1, 8.2, 8.3, 8.4, 9.1, 9.2 (completed in Phase 6.5 or Phase 8)

**Estimated Effort Remaining:**
- Phases 11, 12: 4 hours (commands and clone)
- Phase 7: 4 hours (test fixes)
- Phase 13: 1 hour (documentation)
- Phase 14: 2 hours (version bump)
- **Total: ~11 hours of focused work**

**Testing Strategy:**
After each phase:
1. Run unit tests: `python -m pytest tests/scene/test_event.py -v`
2. Run model tests: `python -m pytest tests/models/ -v`
3. Run integration tests: `python -m pytest tests/views/ -v`
4. Smoke test UI: Open app, create events, timeline, undo/redo

Before final commit:
1. Full test suite: `python -m pytest -vv`
2. Load old diagram files (test compat.py)
3. Create new diagram, save, reload
4. Test all event types
5. Test timeline interactions
6. Test undo/redo thoroughly



---

## PHASE 15: ItemMode Enum Migration 🟢

**Goal:** Replace integer constants (`util.ITEM_*`) with an `ItemMode` enum for type safety and clarity. This is a code quality improvement, not a functional requirement.

**Priority:** MEDIUM - This refactor improves code maintainability and should be done before Commands/Undo work to avoid confusion with ITEM_* vs ItemMode in that code.

**Background:**
- `util.ITEM_*` constants (e.g., `ITEM_MALE=0`, `ITEM_FEMALE=1`, `ITEM_MARRY=2`) are used when drawing items onto the diagram via toolbar buttons (chalkboard mode)
- These are separate from `EventKind` enum which is used for dated events (timeline mode)
- `RelationshipKind` already has `.itemMode()` and `.fromItemMode()` methods for bidirectional conversion
- Current implementation uses raw integers, which lacks type safety

**Current ITEM_* Constants (util.py:248-267):**
```python
ITEM_NONE = None
ITEM_MALE = 0
ITEM_FEMALE = 1
ITEM_MARRY = 2
ITEM_CHILD = 3
ITEM_PENCIL = 4
ITEM_ERASER = 5
ITEM_FUSION = 6
ITEM_CUTOFF = 7
ITEM_CONFLICT = 8
ITEM_PROJECTION = 9
ITEM_DISTANCE = 10
ITEM_TOWARD = 11
ITEM_AWAY = 12
ITEM_DEFINED_SELF = 13
ITEM_CALLOUT = 14
ITEM_RECIPROCITY = 15
ITEM_INSIDE = 16
ITEM_OUTSIDE = 17
```

**Key Usage Files:**
- `pkdiagram/scene/scene.py` - Scene._itemMode, mouse event handlers
- `pkdiagram/documentview/documentcontroller.py` - QAction.setData() mappings
- `pkdiagram/scene/relationshipkind.py` - itemMode() and fromItemMode() conversions
- `pkdiagram/app/qmlutil.py` - QML property exposure
- `pkdiagram/scene/emotions.py` - Emotion.KIND_MAP indirectly uses via RelationshipKind

---

### 15.1 Create ItemMode Enum
**File:** `pkdiagram/scene/itemmode.py` (NEW)

**Create enum matching existing constants:**
```python
import enum


class ItemMode(enum.Enum):
    """Drawing modes for creating items on the diagram."""

    # Special
    NONE = None

    # People
    MALE = "male"
    FEMALE = "female"

    # Relationships
    MARRY = "marry"
    CHILD = "child"

    # Emotions (relationships)
    FUSION = "fusion"
    CUTOFF = "cutoff"
    CONFLICT = "conflict"
    PROJECTION = "projection"
    DISTANCE = "distance"
    TOWARD = "toward"
    AWAY = "away"
    DEFINED_SELF = "defined-self"
    RECIPROCITY = "reciprocity"
    INSIDE = "inside"
    OUTSIDE = "outside"

    # UI Tools
    PENCIL = "pencil"
    ERASER = "eraser"
    CALLOUT = "callout"

    def isEmotion(self) -> bool:
        """Check if this mode creates an emotion."""
        return self in [
            self.PROJECTION,
            self.CONFLICT,
            self.CUTOFF,
            self.DISTANCE,
            self.TOWARD,
            self.AWAY,
            self.DEFINED_SELF,
            self.RECIPROCITY,
            self.INSIDE,
            self.OUTSIDE,
        ]

    def isPerson(self) -> bool:
        """Check if this mode creates a person."""
        return self in [self.MALE, self.FEMALE]

    def isRelationship(self) -> bool:
        """Check if this mode creates a marriage or child relationship."""
        return self in [self.MARRY, self.CHILD]
```

**Action Items:**
- [ ] Create `pkdiagram/scene/itemmode.py` with ItemMode enum
- [ ] Add helper methods (isEmotion, isPerson, isRelationship)
- [ ] Use string values (like EventKind) instead of integers
- [ ] Add migration logic to compat.py to convert old int's to enum value

---

### 15.2 Update Scene and Mouse Handlers
**File:** `pkdiagram/scene/scene.py`

**Current Code:**
```python
self._itemMode = util.ITEM_NONE  # line 222

if self.itemMode() == util.ITEM_CALLOUT:  # line 1107
    ...
elif self.itemMode() in [util.ITEM_MALE, util.ITEM_FEMALE]:  # line 1113
    ...
elif self.itemMode() in [  # line 1121
    util.ITEM_MARRY,
    util.ITEM_CHILD,
    util.ITEM_CONFLICT,
    ...
]:
```

**New Code:**
```python
from pkdiagram.scene import ItemMode

self._itemMode = ItemMode.NONE

if self.itemMode() == ItemMode.CALLOUT:
    ...
elif self.itemMode().isPerson():
    ...
elif self.itemMode().isRelationship() or self.itemMode().isEmotion():
    ...
```

**Changes Needed:**
- Replace `util.ITEM_*` with `ItemMode.*`
- Replace list checks with helper methods
- Update `Scene.setItemMode()` signature: `def setItemMode(self, mode: ItemMode)`
- Update `Scene.itemMode()` return type: `def itemMode(self) -> ItemMode`

**Action Items:**
- [ ] Replace all `util.ITEM_*` references with `ItemMode.*` in scene.py
- [ ] Update method signatures with ItemMode type hints
- [ ] Use `itemMode().isPerson()` instead of `itemMode() in [ITEM_MALE, ITEM_FEMALE]`
- [ ] Use `itemMode().isEmotion()` instead of `itemMode() in emotionItemModes()`
- [ ] Remove `util.emotionItemModes()` function (replaced by ItemMode.isEmotion())

---

### 15.3 Update DocumentController
**File:** `pkdiagram/documentview/documentcontroller.py`

**Current Code:**
```python
self.ui.actionMale.setData(util.ITEM_MALE)  # line 127
self.ui.actionFemale.setData(util.ITEM_FEMALE)
self.ui.actionMarriage.setData(util.ITEM_MARRY)
...

def onSceneItemMode(self):  # line 745
    if self.scene.itemMode() is util.ITEM_NONE:
        ...
```

**New Code:**
```python
from pkdiagram.scene import ItemMode

self.ui.actionMale.setData(ItemMode.MALE)
self.ui.actionFemale.setData(ItemMode.FEMALE)
self.ui.actionMarriage.setData(ItemMode.MARRY)
...

def onSceneItemMode(self):
    if self.scene.itemMode() == ItemMode.NONE:
        ...
```

**Action Items:**
- [ ] Replace all `util.ITEM_*` with `ItemMode.*` in documentcontroller.py
- [ ] Update `onSceneItemMode()` to use ItemMode enum

---

### 15.4 Update QML Exposure
**File:** `pkdiagram/app/qmlutil.py`

**Current Code:**
```python
UTIL_CONST_NAMES = [
    ...
    "ITEM_CUTOFF",
    "ITEM_FUSION",
    "ITEM_CONFLICT",
    ...
]
```

**Issue:** QML currently accesses emotion item modes as integers via `Util.ITEM_CUTOFF`.

**Options:**

**Option A: Keep integer constants for QML (RECOMMENDED)**
- Keep `util.ITEM_*` constants for QML compatibility
- Use `ItemMode` enum in Python code only
- Add conversion: `ItemMode.CUTOFF.toInt()` → returns old integer value
- QML continues to use `Util.ITEM_CUTOFF` without changes

**Option B: Expose ItemMode enum to QML**
- Register ItemMode as QEnum
- Update QML to use `ItemMode.CUTOFF` instead of `Util.ITEM_CUTOFF`
- More complex, requires QML changes

**Recommendation:** Use Option A to avoid QML changes. The integer constants can coexist with the enum for backwards compatibility.

**Action Items:**
- [ ] **DECIDE:** Keep integer constants for QML vs expose enum to QML
- [ ] If Option A: Keep util.ITEM_* constants, add ItemMode ↔ int conversion
- [ ] If Option B: Register ItemMode as QEnum, update QML files

---

### 15.5 Update RelationshipKind Conversions
**File:** `pkdiagram/scene/relationshipkind.py`

**Current Code:**
```python
def itemMode(self) -> int:
    if self == self.Cutoff:
        return util.ITEM_CUTOFF
    elif self == self.Conflict:
        return util.ITEM_CONFLICT
    ...

@staticmethod
def fromItemMode(itemMode: int) -> "RelationshipKind":
    mapping = {
        util.ITEM_CONFLICT: RelationshipKind.Conflict,
        ...
    }
```

**New Code:**
```python
def itemMode(self) -> ItemMode:
    if self == self.Cutoff:
        return ItemMode.CUTOFF
    elif self == self.Conflict:
        return ItemMode.CONFLICT
    ...

@staticmethod
def fromItemMode(itemMode: ItemMode) -> "RelationshipKind":
    mapping = {
        ItemMode.CONFLICT: RelationshipKind.Conflict,
        ...
    }
```

**Action Items:**
- [ ] Update RelationshipKind.itemMode() return type to ItemMode
- [ ] Update RelationshipKind.fromItemMode() parameter type to ItemMode
- [ ] Update mapping dictionary keys from util.ITEM_* to ItemMode.*

---

### 15.6 Testing
**Files:** Test files that use ITEM_* constants

**Test Changes Needed:**
```python
# Old
scene.setItemMode(util.ITEM_MALE)

# New
from pkdiagram.scene import ItemMode
scene.setItemMode(ItemMode.MALE)
```

**Action Items:**
- [ ] Update test files that reference util.ITEM_* constants
- [ ] Run full test suite to verify drawing functionality
- [ ] Manual test: Click toolbar buttons to draw people, emotions, relationships

---

## PHASE 11: Commands/Undo 🟢

Update undo commands to work with Scene-owned events.

### 11.1 Remove commands.SetEmotionPerson
**File:** `pkdiagram/scene/commands.py`

**Rationale:** Emotion.person is now computed from Emotion.event.person, so can't be set directly.

**Action Items:**
- [ ] Delete `SetEmotionPerson` command class
- [ ] Update code that used it to use `SetProperty` on Event instead

---

### 11.2 Update AddItem Command
**File:** `pkdiagram/scene/commands.py`

**Ensure:** AddItem properly adds events to Scene._events

**Action Items:**
- [ ] Verify AddItem calls Scene.addItem() which handles events
- [ ] Test undo/redo with events

---

### 11.3 Update RemoveItems Command - CRITICAL REFACTOR NEEDED 🔴
**File:** `pkdiagram/scene/commands.py:47-347`

**Problem:** `RemoveItems` has deep coupling to OLD event/emotion ownership model. The refactor breaks this command in multiple ways.

#### Current Issues:

**Issue 1: Event Ownership Confusion**
```python
# Line 154-155: Assumes person owns events
for event in list(item.events()):  # Now queries Scene, not cache
    mapEvent(event)
```

After refactor, `person.events()` returns scene-queried events, not owned events. The mapping is fine, but the redo/undo logic assumes wrong ownership.

**Issue 2: Event Person Restoration (Line 307-311)**
```python
for entry in self._unmapped["events"]:
    if entry["dateTime"]:
        entry["event"].setDateTime(entry["dateTime"])
    else:
        entry["event"].setPerson(entry["person"])  # WRONG: person may not exist yet!
```

**Problem:** Events might get restored BEFORE their person is restored, causing crash when trying to call `person.onEventAdded()`.

**Issue 3: Emotion Person Cache Calls (Lines 200, 240, 314, 317)**
```python
# Line 200 (redo):
person._onRemoveEmotion(emotion)  # No longer exists after Phase 2

# Line 314-318 (undo):
entry["people"][0]._onAddEmotion(entry["emotion"])  # No longer exists
entry["emotion"].setPersonA(entry["people"][0])     # Obsolete - uses event.person now
entry["people"][1]._onAddEmotion(entry["emotion"])  # No longer exists
entry["emotion"].setPersonB(entry["people"][1])     # Obsolete - uses emotion.target now
```

**Problem:** All `_onAddEmotion()` and `_onRemoveEmotion()` calls will break after Phase 2 removes emotion caching.

**Issue 4: Event Mapping Stores Wrong Data (Line 109-115)**
```python
def mapEvent(item):
    self._unmapped["events"].append(
        {"event": item, "person": item.person, "dateTime": item.dateTime()}
    )
```

**Problem:**
- Stores `person` object reference, but person might be deleted/recreated
- Should store `person.id` instead
- Missing `spouse`, `child`, `relationshipTargets`, `relationshipTriangles` IDs

**Issue 5: Emotion Mapping Obsolete (Line 117-126)**
```python
def mapEmotion(item):
    self._unmapped["emotions"].append({
        "emotion": item,
        "people": list(item.people),  # WRONG: emotion.people no longer exists
    })
```

**Problem:** `emotion.people` is obsolete. Should map `emotion.event.id` and `emotion.target.id`.

**Issue 6: Person Deletion Removes Events/Emotions (Lines 189-201)**
```python
if item.isPerson:
    for emotion in list(item.emotions()):  # Queries all scene emotions
        for person in list(emotion.people):  # Obsolete
            person._onRemoveEmotion(emotion)  # Obsolete
        self.scene.removeItem(emotion)  # DELETES emotion when person deleted!
```

**Problem:** Currently deletes ALL emotions when person is deleted. With new model, should emotions survive person deletion? Need policy decision.

#### Required Changes:

**CHANGE 1: Update Event Mapping**
```python
def mapEvent(item):
    for entry in self._unmapped["events"]:
        if entry["event"] is item:
            return

    # Store IDs, not object references
    mapping = {
        "event": item,
        "personId": item.person().id if item.person() else None,
        "spouseId": item.spouse().id if item.spouse() else None,
        "childId": item.child().id if item.child() else None,
        "targetIds": [p.id for p in item.relationshipTargets()],
        "triangleIds": [p.id for p in item.relationshipTriangles()],
        "dateTime": item.dateTime(),
    }
    self._unmapped["events"].append(mapping)
```

**CHANGE 2: Update Event Undo Restoration**
```python
# MUST restore events AFTER people are restored
for entry in self._unmapped["events"]:
    # Don't try to restore person reference yet - it happens in event.read()
    # Just ensure event is in scene
    if not entry["event"].scene():
        self.scene.addItem(entry["event"])
```

**CHANGE 3: Update Emotion Mapping**
```python
def mapEmotion(item):
    for entry in self._unmapped["emotions"]:
        if entry["emotion"] is item:
            return

    mapping = {
        "emotion": item,
        "eventId": item.event().id if item.event() else None,
        "targetId": item.target().id if item.target() else None,
    }
    self._unmapped["emotions"].append(mapping)
```

**CHANGE 4: Remove Obsolete Emotion Cache Calls**
```python
# DELETE all of these:
# person._onAddEmotion()
# person._onRemoveEmotion()
# emotion.setPersonA()
# emotion.setPersonB()
# emotion.people

# REPLACE with simple scene add/remove:
elif item.isEmotion:
    self.scene.removeItem(item)  # Scene handles notification
```

**CHANGE 5: Update Emotion Undo Restoration**
```python
for entry in self._unmapped["emotions"]:
    # Emotion references are via event, not direct person
    if not entry["emotion"].scene():
        self.scene.addItem(entry["emotion"])
```

**CHANGE 6: Decide Person Deletion Policy**

**Option A: Keep current behavior (delete events/emotions with person)**
```python
if item.isPerson:
    # Delete all events for this person
    for event in list(self.scene.events()):
        if event.person() == item:
            self.scene.removeItem(event)

    # Delete all emotions involving this person
    for emotion in list(self.scene.emotions()):
        if emotion.person() == item or emotion.target() == item:
            self.scene.removeItem(emotion)
```

**Option B: Allow orphaned events (just remove person reference)**
```python
if item.isPerson:
    # Orphan events - they remain in scene but lose person reference
    for event in list(self.scene.events()):
        if event.person() == item:
            event.prop("person").set(None)  # Orphan it

    # Delete only emotions where this person is the subject
    # Keep emotions where they're just a target? Or orphan those too?
```

**Recommendation:** Use Option A for now (delete with person), add Option B as future enhancement if needed.

#### Action Items:

- [ ] **DECIDE:** Delete events/emotions when person deleted, or orphan them?
- [ ] Update `mapEvent()` to store person/spouse/child/target/triangle IDs, not objects
- [ ] Update `mapEmotion()` to store event ID and target ID, not people list
- [ ] Remove all `_onAddEmotion()` and `_onRemoveEmotion()` calls
- [ ] Remove all `emotion.setPersonA()` and `emotion.setPersonB()` calls
- [ ] Fix event restoration order - events AFTER people in undo()
- [ ] Fix emotion restoration order - emotions AFTER events in undo()
- [ ] Update person deletion logic (lines 189-201) per chosen policy
- [ ] Update emotion deletion logic (lines 237-241)
- [ ] Add test: delete person with events, undo, verify events restored
- [ ] Add test: delete emotion, undo, verify emotion + event restored
- [ ] Add test: delete event, verify emotion stays but is orphaned (or deleted?)

---

## PHASE 12: Clone/Remap Refactor 🟡

**Overview:** The clone/remap system is used for copy/paste operations. Items are cloned with temporary `_cloned_*_id` attributes, then remapped to resolve references between clones.

### 12.1 Add Event.clone() Method
**File:** `pkdiagram/scene/event.py` (NEW)

**Problem:** Event doesn't have a clone() method, but Person.clone() calls `event.clone(scene)`!

**Current:** Event inherits default `Item.clone()` which copies properties, but doesn't handle:
- Dynamic properties (symptom, anxiety, relationship, functioning)
- Person references need remapping (person, spouse, child, targets, triangles)

**New Code:**
```python
def Event.clone(self, scene):
    """Clone this event for copy/paste."""
    x = super().clone(scene)  # Copies all properties including person ID

    # Clone dynamic properties
    for prop in self.dynamicProperties:
        newProp = x.addDynamicProperty(prop.attr)
        newProp.set(prop.get(), notify=False)

    # Store original IDs for remapping phase
    x._cloned_person_id = self.prop("person").get()
    x._cloned_spouse_id = self.prop("spouse").get()
    x._cloned_child_id = self.prop("child").get()
    x._cloned_target_ids = list(self.prop("relationshipTargets").get() or [])
    x._cloned_triangle_ids = list(self.prop("relationshipTriangles").get() or [])

    return x

def Event.remap(self, map):
    """Remap person references after cloning."""
    # Remap person reference
    if hasattr(self, "_cloned_person_id") and self._cloned_person_id:
        person = map.find(self._cloned_person_id)
        if person:
            self.prop("person").set(person.id, notify=False)
        delattr(self, "_cloned_person_id")

    # Remap spouse
    if hasattr(self, "_cloned_spouse_id") and self._cloned_spouse_id:
        spouse = map.find(self._cloned_spouse_id)
        if spouse:
            self.prop("spouse").set(spouse.id, notify=False)
        else:
            self.prop("spouse").set(None, notify=False)
        delattr(self, "_cloned_spouse_id")

    # Remap child
    if hasattr(self, "_cloned_child_id") and self._cloned_child_id:
        child = map.find(self._cloned_child_id)
        if child:
            self.prop("child").set(child.id, notify=False)
        else:
            self.prop("child").set(None, notify=False)
        delattr(self, "_cloned_child_id")

    # Remap relationship targets
    if hasattr(self, "_cloned_target_ids"):
        new_target_ids = []
        for id in self._cloned_target_ids:
            target = map.find(id)
            if target:
                new_target_ids.append(target.id)
        self.prop("relationshipTargets").set(new_target_ids, notify=False)
        delattr(self, "_cloned_target_ids")

    # Remap relationship triangles
    if hasattr(self, "_cloned_triangle_ids"):
        new_triangle_ids = []
        for id in self._cloned_triangle_ids:
            triangle = map.find(id)
            if triangle:
                new_triangle_ids.append(triangle.id)
        self.prop("relationshipTriangles").set(new_triangle_ids, notify=False)
        delattr(self, "_cloned_triangle_ids")

    return True  # Success
```

**Action Items:**
- [ ] Add `Event.clone()` method to handle dynamic properties
- [ ] Add `Event.remap()` method to remap all person references (person, spouse, child, targets, triangles)
- [ ] Store `_cloned_*_id` attributes for remap phase
- [ ] Handle None values gracefully when references don't exist in clipboard

---

### 12.2 Update Emotion.clone() and Emotion.remap()
**File:** `pkdiagram/scene/emotions.py:1358-1379`

**Current Code:**
```python
def clone(self, scene):
    raise NotImplementedError("Emotion.clone() is not implemented.")
    x = super().clone(scene)
    if self.isDyadic():
        x._cloned_people_ids = []
        for p in self.people:  # WRONG: emotion.people removed in refactor
            x._cloned_people_ids.append(p.id)
    else:
        x._cloned_person_id = self.people[0].id  # WRONG
    return x

def remap(self, map):
    raise NotImplementedError("Emotion.remap() is not implemented.")
    if self.isDyadic():
        self.people = [map.find(id) for id in self._cloned_people_ids]  # WRONG
        # ...
```

**New Code:**
```python
def clone(self, scene):
    """Clone this emotion for copy/paste."""
    x = super().clone(scene)

    # Store IDs for remapping (emotion references event + target)
    x._cloned_event_id = self._event.id if self._event else None
    x._cloned_target_id = self._target.id if self._target else None

    return x

def remap(self, map):
    """Remap event and target references after cloning."""
    # Remap event reference
    if hasattr(self, "_cloned_event_id"):
        event_id = self._cloned_event_id
        delattr(self, "_cloned_event_id")

        if event_id:
            self._event = map.find(event_id)
            if not self._event:
                return False  # Can't clone emotion without event

    # Remap target reference
    if hasattr(self, "_cloned_target_id"):
        target_id = self._cloned_target_id
        delattr(self, "_cloned_target_id")

        if target_id:
            self._target = map.find(target_id)
            if not self._target:
                return False  # Can't clone emotion without target

    # Update parent item (emotion is child of person in scene graph)
    if not self.isDyadic() and self._event and self._event.person():
        self.setParentItem(self._event.person())

    return True
```

**Action Items:**
- [ ] Remove `NotImplementedError` from Emotion.clone()
- [ ] Remove `NotImplementedError` from Emotion.remap()
- [ ] Remove references to obsolete `emotion.people` list
- [ ] Store `_cloned_event_id` and `_cloned_target_id` for remapping
- [ ] Remap using `map.find()`
- [ ] Return False if event or target not found in clipboard (incomplete clone)

---

### 12.3 Update Marriage.clone() - Events Handling
**File:** `pkdiagram/scene/marriage.py:241-246`

**Current Code:**
```python
def clone(self, scene):
    x = super().clone(scene)
    x._cloned_people_ids = [p.id for p in self.people]
    x._cloned_children_ids = [p.id for p in self.children]
    x._cloned_custody_id = self.custody()
    return x
```

**Issue:** Marriage doesn't clone its events, but Marriage has events after refactor!

**Question:** Should Marriage.clone() also clone its events like Person does?

**Option A: Clone marriage events**
```python
def clone(self, scene):
    x = super().clone(scene)
    x._cloned_people_ids = [p.id for p in self.people]
    x._cloned_children_ids = [p.id for p in self.children]
    x._cloned_custody_id = self.custody()

    # Clone events
    x._cloned_event_ids = []
    for event in self.events():
        newEvent = event.clone(scene)
        newEvent._cloned_person_id = self.id  # Marriage is the "person"
        x._cloned_event_ids.append(newEvent.id)

    return x
```

**Option B: Don't clone marriage events (current behavior)**
- Simpler, events stay with original marriage
- User can copy events separately if needed

**Action Items:**
- [ ] **DECIDE:** Should cloning a marriage also clone its events?
- [ ] If yes, update Marriage.clone() to clone events
- [ ] If yes, update Marriage.remap() to remap cloned events

---

### 12.4 Test Clone/Paste Workflow
**Files:** New tests needed

**Test Scenarios:**
1. **Copy/paste person with events**
   - Create person with birth/death events
   - Copy person
   - Paste person
   - Verify cloned person has cloned events
   - Verify events point to cloned person, not original

2. **Copy/paste person with emotions**
   - Create person with relationship to another person
   - Create emotion with event
   - Copy first person only
   - Paste - emotion should fail to remap (target not in clipboard)
   - Copy BOTH people
   - Paste - should paste emotion with remapped event and target

3. **Copy/paste marriage (if events cloned)**
   - Create marriage with married/divorced events
   - Copy marriage
   - Paste marriage
   - Verify events remapped to cloned marriage

4. **Copy/paste event with multiple targets**
   - Create VariableShift event with relationship targets
   - Create emotion
   - Copy person
   - Paste - verify targets that aren't in clipboard are cleared

**Action Items:**
- [ ] Write test: copy/paste person with events
- [ ] Write test: copy/paste person with emotions (partial selection fails)
- [ ] Write test: copy/paste multiple people with shared emotions (full selection works)
- [ ] Write test: copy/paste marriage with events (if decided)
- [ ] Write test: event targets remapping with partial clipboard
- [ ] Test clipboard.py integration with new event/emotion clone methods

---

## PHASE 7: Test Fixes 🟡

Update tests to work with new Event structure.

### 7.1 Fix Event() Constructor Calls
**Files Changed (from git diff):**
- tests/scene/test_event.py (77 lines changed)
- tests/scene/test_marriage.py (81 lines deleted - needs investigation)
- tests/views/eventform/*.py (multiple files)
- tests/views/test_emotionproperties.py (8 lines changed)
- tests/views/test_marriageproperties.py (185 lines changed)
- tests/models/test_copilotengine.py (8 lines changed)
- tests/models/test_searchmodel.py (3 lines changed)
- tests/models/test_timelinemodel.py (26 lines changed)

**Old Pattern:**
```python
event = Event(person)  # FAILS: missing kind argument
```

**New Pattern (from test_event.py:10):**
```python
event = Event(EventKind.Shift, person)  # Positional
```

**Action Items:**
- [ ] tests/scene/test_event.py - update all Event() calls (mostly done, check line 24 logic error)
- [ ] tests/scene/test_marriage.py - 81 lines deleted, verify tests still valid
- [ ] tests/views/eventform/ - 6 test files with Event() calls
- [ ] tests/views/test_emotionproperties.py - update Event() calls
- [ ] tests/views/test_marriageproperties.py - 185 lines changed, needs review
- [ ] tests/models/*.py - update Event() calls in model tests
- [ ] Search for remaining `Event\(` patterns and update

**Known Logic Error:**
**File:** tests/scene/test_event.py:24
```python
# Line 21-33 - LOGIC ERROR
event = Event(EventKind.Shift, personB)  # ← Event added to personB
event.setPerson(personB, undo=undo)  # ← Still personB! Not personA!
assert event in personA.events()  # ← WRONG: event is still in personB
assert event not in personB.events()  # ← WRONG: should be in personB
```

Should probably be:
```python
event = Event(EventKind.Shift, personA)  # Start with personA
event.setPerson(personB, undo=undo)  # Switch to personB
assert event not in personA.events()  # No longer in personA
assert event in personB.events()  # Now in personB
```

---

### 7.3 Fix Emotion Construction
**Files with Emotion() calls (from grep):**
- pkdiagram/scene/scene.py
- pkdiagram/scene/emotions.py
- tests/views/eventform/test_edit.py
- tests/views/test_emotionproperties.py
- tests/scene/test_scene_add_remove.py
- tests/models/test_timelinemodel.py
- tests/models/test_searchmodel.py
- pkdiagram/scene/commands.py
- tests/test_documentview.py
- tests/mainwindow/test_mw_kb_shortcuts.py
- tests/scene/test_scene_show_hide.py
- tests/scene/test_scene_read_write.py
- tests/scene/test_emotions.py

**Old Pattern:**
```python
emotion = Emotion(kind=RelationshipKind.Conflict, ...)  # Missing event?
```

**New Pattern (from scene.py:720):**
```python
# Scene.read() pattern:
kind = Emotion.kindForKindSlug(chunk["kind"])
item = Emotion(kind=kind, target=None, event=None)  # Placeholder values

# Test pattern:
event = Event(
    kind=EventKind.Shift,
    person=person1,
    relationshipTargets=[person2],
)
scene.addItem(event)

emotion = Emotion(event=event, target=person2, kind=RelationshipKind.Conflict)
scene.addItem(emotion)
```

**Action Items:**
- [ ] Update all Emotion() calls in tests to include `event=` and `target=`
- [ ] Create corresponding Event objects for dated emotions
- [ ] For undated emotions (manual drawing), use event=None
- [ ] Add both event and emotion to scene explicitly
- [ ] Verify scene.py:720 Emotion loading works with event=None placeholder

### 7.4 Graphical Timeline Tests
- [ ] Add prelim test suite
- [ ] Test rendering with events that have date ranges
- [ ] Ensure selecting an end marker selects the underlying Event

---

### 7.5 Run Full Test Suite and Fix Failures
**Action Items:**
- [ ] Run `python -m pytest -vv` and collect all failures
- [ ] Fix test failures by category (Event, Emotion, Marriage, Scene, etc.)
- [ ] Verify Scene.read()/write() tests pass after Phase 0.2/0.3 implemented
- [ ] Verify compat.py tests pass after Phase 6 implemented
- [ ] Verify clone/paste tests pass after Phase 12 implemented
- [ ] Verify age calculation still works (should read from personModel.birthDateTime)

---

## PHASE 13: Edge Cases & Polish 🟢

### 13.1 Handle Orphaned Events
**Scenario:** Event.person is deleted

**Current Behavior:** ?

**Desired Behavior:**
- Option A: Delete event when person is deleted
- Option B: Allow orphaned events, show as "(deleted person)"

**Action Items:**
- [ ] **DECIDE:** Delete orphaned events or allow them?
- [ ] Implement chosen behavior in RemoveItems command
- [ ] Add tests for orphaned events

---

### 13.2 Handle Marriage Events
**Question:** How does Event.person work for Marriage events?

**Current Code:** Marriage events set `event.person = marriage`

**Is this correct?** Or should they:
- Set `event.spouse` to one spouse and leave `event.person` empty?
- Have a separate `event.marriage` field?

**Action Items:**
- [ ] **CLARIFY:** How should marriage events reference the marriage?
- [ ] Document the pattern in CLAUDE.md
- [ ] Ensure consistency across codebase

---

### 13.3 Event Validation
**Add validation to catch errors early:**

```python
def Event.validate(self):
    """Ensure event fields match its kind."""
    if self.kind() in (EventKind.Bonded, EventKind.Married, EventKind.Separated,
                       EventKind.Divorced, EventKind.Moved):
        assert self.spouse(), f"{self.kind()} requires spouse"
        assert not self.relationshipTargets(), f"{self.kind()} cannot have targets"

    elif self.kind() in (EventKind.Birth, EventKind.Adopted):
        assert self.spouse(), f"{self.kind()} requires spouse (other parent)"
        assert self.child(), f"{self.kind()} requires child"

    elif self.kind() == EventKind.Shift:
        if self.relationship():  # R variable
            assert self.relationshipTargets(), "Relationship shift requires targets"
        else:  # S, A, or F variable
            assert not self.relationshipTargets(), "Non-relationship shift cannot have targets"

    elif self.kind() == EventKind.Death:
        assert self.person, "Death requires person"
        assert not self.spouse(), "Death cannot have spouse field"
```

**Action Items:**
- [ ] Add `Event.validate()` method
- [ ] Call during Event.write() or in tests
- [ ] Add tests for invalid events

---

## PHASE 13: Documentation 📝

### 13.1 Update CLAUDE.md
**Status:** ✅ Already updated with architecture notes

**Remaining:**
- [ ] Add Event.kind validation rules
- [ ] Document Event-Emotion relationship
- [ ] Document TimelineRow pattern

---

### 13.2 Add Architecture Diagram
**Create:** Visual diagram showing:
- Scene owns Events, People, Marriages, Emotions
- Events reference Person via `event.person`
- Emotions reference Event via `emotion.event`
- Emotions reference target Person via `emotion.target`

**Action Items:**
- [ ] Create architecture diagram (ASCII or image)
- [ ] Add to doc/FLATTENING_EVENTS.md or CLAUDE.md

---

## PHASE 14: File Format Version Bump 🔴 CRITICAL

**Purpose:** The event flattening refactor introduces breaking changes to the file format. Files saved in the new format cannot be opened by older versions.

### 14.1 Update VERSION_COMPAT
**File:** `pkdiagram/version.py`

**Current Values (need to check):**
```python
VERSION = "2.0.12"  # Current release version
VERSION_COMPAT = "2.0.0"  # Oldest version that can read this file format
```

**Required Change:**
When the new format is released, bump `VERSION_COMPAT` to prevent older versions from trying to open incompatible files:
```python
VERSION = "2.1.0"  # New version with flattened events
VERSION_COMPAT = "2.1.0"  # Files created with 2.1.0+ cannot be opened by 2.0.x
```

**Rationale:**
- Old versions (2.0.x) expect events in `data["items"]` nested under people/marriages/emotions
- New version (2.1.0) writes events to `data["events"]` as top-level items
- Old versions will crash trying to load new files if we don't block them

**Action Items:**
- [ ] Check current VERSION and VERSION_COMPAT in version.py
- [ ] Decide on version number for flattened events release (2.1.0 or 3.0.0?)
- [ ] Update VERSION_COMPAT when deploying new format
- [ ] Add migration guide to release notes

---

### 14.2 Add Migration Test Cases
**File:** `tests/scene/test_compat.py` (or new test file)

**Purpose:** Verify that old file format can be loaded and migrated by compat.py.

**Test Cases Needed:**
```python
def test_migrate_old_person_events_to_scene():
    """Test that Person.events are migrated to Scene.events."""
    old_data = {
        "version": "2.0.12",
        "people": [
            {
                "id": 1,
                "events": [  # OLD: events nested under person
                    {"id": 10, "uniqueId": "birth", "dateTime": "..."}
                ]
            }
        ]
    }
    compat.update_data(old_data)
    assert old_data.get("events") == [  # NEW: events at top level
        {"id": 10, "kind": EventKind.Birth.value, "person": 1, "dateTime": "..."}
    ]
    assert "events" not in old_data["people"][0]  # Removed from person

def test_migrate_emotion_start_end_events_to_single_event():
    """Test Emotion.startEvent/endEvent merged into single Event with endDateTime."""
    old_data = {
        "emotions": [
            {
                "id": 20,
                "startEvent": {"id": 30, "dateTime": "2020-01-01"},
                "endEvent": {"id": 31, "dateTime": "2020-12-31"},
                "person_a": 1,
                "person_b": 2,
            }
        ]
    }
    compat.update_data(old_data)
    assert old_data.get("events") == [
        {
            "id": 30,
            "kind": EventKind.Shift.value,
            "person": 1,
            "dateTime": "2020-01-01",
            "endDateTime": "2020-12-31",
            "relationshipTargets": [2],
        }
    ]
    assert old_data["emotions"][0]["event"] == 30  # References event ID
    assert "startEvent" not in old_data["emotions"][0]
    assert "endEvent" not in old_data["emotions"][0]

def test_migrate_uniqueId_to_kind():
    """Test Event.uniqueId string → Event.kind enum."""
    old_data = {
        "events": [
            {"id": 10, "uniqueId": "birth"},
            {"id": 11, "uniqueId": "CustomIndividual"},  # Edge case
        ]
    }
    compat.update_data(old_data)
    assert old_data["events"][0]["kind"] == EventKind.Birth.value
    assert old_data["events"][1]["kind"] == EventKind.Shift.value
    assert "uniqueId" not in old_data["events"][0]
```

**Action Items:**
- [ ] Create comprehensive test cases for compat.py migrations
- [ ] Test loading actual saved diagram files from version 2.0.x
- [ ] Verify round-trip: old format → migrate → save → load → works
- [ ] Test edge cases: empty events, None uniqueId, missing fields

---

### 14.3 Backward Compatibility Strategy
**Question:** Should new version be able to SAVE in old format for compatibility?

**Option A: One-way upgrade (RECOMMENDED)**
- New version can READ old format (via compat.py)
- New version always SAVES in new format
- Users cannot downgrade after upgrading
- Simpler implementation

**Option B: Dual-format support**
- New version can READ and WRITE both formats
- "Save As..." dialog lets user choose format
- More complex, requires maintaining two code paths

**Recommendation:** Use Option A (one-way upgrade) because:
- Event flattening is fundamental architecture change
- Maintaining dual format is complex and error-prone
- VERSION_COMPAT will block old versions from opening new files
- Users can keep old version installed if needed

**Action Items:**
- [ ] **DECIDE:** One-way upgrade vs dual-format support
- [ ] Document upgrade path in release notes
- [ ] Warn users to backup files before upgrading
- [ ] Consider "Export to 2.0.x format" feature for emergencies

---

## APPENDIX: Original Analysis Issues

### Issue Summary from Initial Analysis

**From First Response:**

1. ✅ Event.kind initialization - **Addressed in Phase 1.1** (archived in FLATTEN_EVENTS_DONE.md)
2. ✅ Dual event hierarchy (Person._events vs Scene._events) - **Addressed in Phase 2** (archived)
3. ✅ Emotion-Event relationship confusion - **Addressed in Phase 4** (archived)
4. ✅ Event.endDateTime vs Emotion start/end - **Addressed in Phase 3 (TimelineRow)** (archived)
5. ✅ Missing Scene event management - **Addressed in Phase 1.3** (archived)
6. ✅ EventKind vs uniqueId - **Addressed in Phase 5** (archived)
7. ✅ Emotion property duplication - **Addressed in Phase 4.3** (archived)
8. ✅ Test infrastructure breaks - **Addressed in Phase 7.0, 7.2** (archived)
9. ⬜ Data migration incomplete - **Addressed in Phase 6** (in progress)
10. ✅ TimelineModel phantom events - **Addressed in Phase 3** (archived)

---

## APPENDIX: User Decisions & Clarifications

### From Follow-up Discussion:

**#1: Remove Caches**
- ✅ CONFIRMED: Remove Person._events, Marriage._events, Emotion._event caches
- ✅ Use computed properties querying Scene
- Performance negligible per user

**#2: Event Change Notifications**
- ✅ DECIDED: Use direct callbacks (onEventAdded/onEventRemoved/onEventChanged)
- ✅ NOT using Qt signals
- Scene calls person.onEventAdded() when event.person is set

**#3: Event Person Fields**
- ✅ CONFIRMED: Keep categorical fields (spouse, child, relationshipTargets, relationshipTriangles)
- ✅ They serve different semantic purposes per EventKind
- See updated requirements table in Phase 5 based on CLAUDE.md

**#4: TimelineModel Dummy Events**
- ✅ DECIDED: Use TimelineRow dataclass (Option 1)
- Clean separation of view from model
- See Phase 3

**#5: Emotion-Event Relationship**
- ✅ DECIDED: Use Option 1 (Emotion owns Event reference)
- Remove Event.emotions() factory
- Explicit creation: create Event, then create Emotion(s) referencing it
- See Phase 4

---

**END OF TODO**
