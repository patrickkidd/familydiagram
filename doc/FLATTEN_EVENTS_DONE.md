# Event Flattening Refactor - Completed Phases

**Archive of completed work. See TODO_FLATTEN_EVENTS.md for remaining tasks.**

---

## 📋 COMPLETED SECTIONS FROM TOC

### ✅ COMPLETED - Infrastructure & Architecture
- **[Phase 0](#phase-0-critical-infrastructure-blockers-)** - Critical Infrastructure Blockers
  - [0.1 ✅ Circular Import in marriage.py](#01-circular-import-in-marriagepy--completed)
  - [0.2 ✅ Scene.read() Missing Event Loading Code](#02-sceneread-missing-event-loading-code--completed)
  - [0.3 ✅ Scene.write() Not Separating Events](#03-scenewrite-not-separating-events--completed)
- **[Phase 1](#phase-1-fix-critical-blockers--urgent)** - Fix Critical Blockers
  - [1.1 ✅ Event.kind Property Initialization](#11-eventkind-property-initialization--notes-in-claudemd)
  - [1.2 ✅ Emotion Constructor Crash](#12-emotion-constructor-crash--completed)
  - [1.3 ✅ Scene Event Signal Wiring](#13-scene-event-signal-wiring--completed)
- **[Phase 2](#phase-2-remove-event-reference-caching-)** - Remove Event Reference Caching
  - [2.1 ✅ Remove Person._events Cache](#21-remove-person_events-cache--completed)
  - [2.2 ✅ Remove Marriage._events Cache](#22-remove-marriage_events-cache--completed)
  - [2.3 ✅ Simplify Event._do_setPerson()](#23-simplify-event_do_setperson--completed)
  - [2.4 ✅ Update Event.onProperty()](#24-update-eventonproperty-to-notify-person--completed)
- **[Phase 3](#phase-3-timelinemodel-refactor-)** - TimelineModel Refactor
  - [3.1 ✅ Create TimelineRow Data Class](#31-create-timelinerow-data-class--completed)
  - [3.2 ✅ Update TimelineModel to Use TimelineRow](#32-update-timelinemodel-to-use-timelinerow--completed)
  - [3.3 ✅ Remove TimelineModel._shouldHide() Emotion Logic](#33-remove-timelinemodel_shouldhide-emotion-logic--completed)
- **[Phase 4](#phase-4-emotion-event-relationship-cleanup-)** - Emotion-Event Relationship Cleanup
  - [4.1 ✅ Remove Event.emotions() Factory](#41-remove-eventemotions-factory--completed)
  - [4.2 ✅ Clarify Emotion.person() vs Emotion.target()](#42-clarify-emotionperson-vs-emotiontarget--completed)
  - [4.3 ✅ Emotion Property Delegation Pattern](#43-emotion-property-delegation-pattern--decision-keep-both)
- **[Phase 5](#phase-5-eventkind-enum-cleanup-)** - EventKind Enum Cleanup
  - [5.1 ✅ Fix String Comparisons](#51-fix-string-comparisons--completed)
  - [5.2 ✅ Update Marriage.separationStatusFor()](#52-update-marriageseparationstatusfor--completed)

### ✅ COMPLETED - Data & Compatibility
- **[Phase 6](#phase-6-data-compatibility-compatpy--completed)** - Data Compatibility (compat.py)
- **[Phase 7](#phase-7-test-fixes-partial-)** - Test Fixes (Partial)
  - [7.0 ✅ Fix Tests That Can Now Run](#70-fix-tests-that-can-now-run--completed)
  - [7.2 ✅ Fix event.uniqueId() Calls](#72-fix-eventuniqueId-calls--completed)
- **[Phase 8](#phase-8-modelview-updates-partial-)** - Model/View Updates (Partial)
  - [8.1 ✅ Update PersonPropertiesModel](#81-update-personpropertiesmodel-event-handling--completed)
  - [8.2 ✅ Update MarriagePropertiesModel](#82-update-marriagepropertiesmodel-event-handling--completed)
  - [8.3 ✅ Remove EmotionPropertiesModel Date Editors](#phase-83-remove-emotionpropertiesmodel-date-editors-)
  - [8.4 ✅ Update SearchModel](#phase-84-update-searchmodel-)
- **[Phase 9](#phase-9-scene-data-format--completed)** - Scene Data Format
  - [9.1 ✅ Update Scene.write()](#91-update-scenewrite--completed)
  - [9.2 ✅ Update Scene.read()](#92-update-sceneread--completed)
- **[Phase 10](#phase-10-qmlui-updates-)** - QML/UI Updates
  - [10.1 ✅ Update EventForm](#101-update-eventform-)
  - [10.2 ✅ Update EmotionProperties](#102-update-emotionproperties-)
  - [10.3 ✅ Update PersonProperties](#103-update-personproperties-)
- **[Phase 10.5](#phase-105-graphicaltimeline-timelinerow-refactor-)** - GraphicalTimeline TimelineRow Refactor
  - [10.5.1 ✅ Update GraphicalTimelineCanvas](#1051-update-graphicaltimelinecanvas)
  - [10.5.2 ✅ Update Event Drawing Logic](#1052-update-event-drawing-logic)
  - [10.5.3 ✅ Update Event Selection](#1053-update-event-selection)


---

## PHASE 0: Critical Infrastructure Blockers ✅

### 0.1 Circular Import in marriage.py ✅ COMPLETED
**File:** `pkdiagram/scene/marriage.py:26` (FIXED)

**Problem:** Production code was importing from test code:
```python
from tests.views.test_marriageproperties import marriage  # ← WRONG
```

**Impact:** Prevented ALL tests from running with circular import error.

**Resolution:** User removed the import. Tests can now run.

---

### 0.2 Scene.read() Missing Event Loading Code ✅ COMPLETED
**File:** `pkdiagram/scene/scene.py:676-755`

**Problem:** Scene.read() had NO code to load Event objects from saved files!

**Impact:** Saved diagrams could not be opened because events were never loaded from `data["events"]`.

**Resolution Implemented:**
- Scene.read() now implements two-phase loading (see Phase 9.2)
- Phase 1: Instantiate events with ID map
- Phase 2: Resolve event.person references via byId lookup

---

### 0.3 Scene.write() Not Separating Events ✅ COMPLETED
**File:** `pkdiagram/scene/scene.py:789-828`

**Problem:** Scene.write() output everything to `data["items"]` - didn't check for `isEvent` or create `data["events"]`.

**Impact:** Events were not being written to files correctly.

**Resolution Implemented:**
- Scene.write() now separates events into `data["events"]` array (see Phase 9.1)
- Events are written as top-level items separate from people/marriages

---

---

## PHASE 1: Fix Critical Blockers 🔴 URGENT

These issues prevent the app from running at all.

### 1.1 Event.kind Property Initialization ✅ NOTES IN CLAUDE.MD
**File:** `pkdiagram/scene/event.py:222`

**Problem:** `Event.kind()` crashes when property is `None`:
```python
def kind(self) -> EventKind:
    return EventKind(self.prop("kind").get())  # ValueError: None is not a valid EventKind
```

**Root Cause:** Event constructor always calls `updateDescription()` which calls `kind()` before kind is set.

**Solution:**
```python
# Option 1: Allow None (per CLAUDE.md - for TimelineModel dummy events)
def kind(self) -> EventKind | None:
    value = self.prop("kind").get()
    return EventKind(value) if value else None

# Option 2: Require kind in constructor
def __init__(self, kind: EventKind, **kwargs):
    if not kind:
        raise TypeError("Event() requires kind= argument")
    super().__init__(kind=kind.value, **kwargs)
```

**Decision:** Use Option 1 per CLAUDE.md note about TimelineModel dummy events.

**Action Items:**
- [ ] Change `Event.kind()` to return `EventKind | None`
- [ ] Update all `Event.__init__()` calls in tests to include `kind=`
- [ ] Add validation in `Event.updateDescription()` to handle `kind=None` case

---

### 1.2 Emotion Constructor Crash ✅ COMPLETED
**File:** `pkdiagram/scene/emotions.py:1206-1233`

**Problem:** `Emotion.__init__()` requires `event: Event` but `event` might be None during construction.

**Solution Implemented:**
- Constructor now accepts `kind`, `target`, and optional `event`
- Properties registered for `event` and `target` as IDs (lines 1177-1178)
- File loading updated to provide placeholder values (scene.py:713)
- All Emotion() constructor calls updated

**Action Items:**
- [x] Make `event` and `kind` required parameters in `Emotion.__init__()`
- [x] Update all `Emotion()` calls to include both parameters
- [x] Add assertions to validate event.kind() == EventKind.Shift

---

### 1.3 Scene Event Signal Wiring ✅ COMPLETED
**File:** `pkdiagram/scene/scene.py`

**Problem:** Scene declares `eventAdded/eventRemoved` signals but never emits them when events are added via `addItem()`.

**Solution Implemented:**
- Line 389: `item.person().onEventAdded()` called when event added
- Line 406: `self.eventAdded.emit(item)` emits signal when event added
- Line 540: `item.person().onEventRemoved()` called when event removed
- Line 542: `self.eventRemoved.emit(item)` emits signal when event removed
- TimelineModel connects to `scene.eventAdded[Event]` signal (line 348)

**Action Items:**
- [x] Update `Scene.addItem()` to emit `eventAdded` signal
- [x] Update `Scene.removeItem()` to emit `eventRemoved` signal
- [x] Update `Scene.addItem()` to call `item.person.onEventAdded(item)`
- [x] Update `Scene.removeItem()` to call `item.person.onEventRemoved(item)`
- [x] Connect `TimelineModel` to `scene.eventAdded[Event]` signal

---

---

## PHASE 2: Remove Event Reference Caching 🟡

Replace cached event lists with computed properties that query Scene.

### 2.1 Remove Person._events Cache ✅ COMPLETED
**File:** `pkdiagram/scene/person.py:787-789`

**Solution Implemented:**
- `Person._events` attribute removed
- `Person._onAddEvent()` and `Person._onRemoveEvent()` methods removed
- `Person.events()` now queries `self.scene()._events`
- Callback methods implemented: `onEventAdded()`, `onEventRemoved()`, `onEventChanged()`
- Scene calls these callbacks when events are added/removed/changed (see Phase 1.3)

**Action Items:**
- [x] Remove `Person._events` attribute
- [x] Remove `Person._onAddEvent()` method
- [x] Remove `Person._onRemoveEvent()` method
- [x] Change `Person.events()` to computed property (query scene)
- [x] Add `Person.onEventAdded(event)` callback method
- [x] Add `Person.onEventRemoved(event)` callback method
- [x] Add `Person.onEventChanged(event, prop)` callback method
- [x] Update `Person.updateEvents()` to query `self.events()` instead of using cache

---

### 2.2 Remove Marriage._events Cache ✅ COMPLETED
**File:** `pkdiagram/scene/marriage.py:387-395`

**Solution Implemented:**
- ✅ Marriage.events() correctly queries Scene by {person, spouse} pair (line 387-395)
- ✅ Marriage.onEventAdded() callback added (line 399-401)
- ✅ Marriage.onEventRemoved() callback added (line 403-405)
- ✅ Scene.addItem() notifies marriages when marriage events added
- ✅ Scene.removeItem() notifies marriages when marriage events removed

**Implementation:**
```python
# Line 387-395 - Query Scene for events
def events(self) -> list[Event]:
    if self.scene():
        return [
            x
            for x in self.scene().events()
            if {x.person(), x.spouse()} == {self.personA(), self.personB()}
        ]
    else:
        return []

# Line 399-405 - Callbacks for immediate visual feedback
def onEventAdded(self):
    self.updateDetails()  # Displays event dates (line 526-573)
    self.updateGeometry()  # Updates separation indicator

def onEventRemoved(self):
    self.updateDetails()
    self.updateGeometry()
```

**Action Items:**
- [x] Add `Marriage.onEventAdded(event)` callback method
- [x] Add `Marriage.onEventRemoved(event)` callback method
- [x] Update `Scene.addItem()` to detect `event.spouse()` and notify marriages
- [x] Update `Scene.removeItem()` to notify marriages before removing event
- [x] Note: Marriage.events() is ALREADY correctly implemented (no changes needed)

---

### 2.3 Simplify Event._do_setPerson() ✅ COMPLETED
**File:** `pkdiagram/scene/event.py:167-187`

**Solution Implemented:**
- Event._do_setPerson() updated to call new callback methods
- Calls `onEventRemoved()` on old person, `onEventAdded()` on new person
- Property change notifications emitted correctly

**Action Items:**
- [x] Update `Event._do_setPerson()` to call `onEventRemoved()/onEventAdded()` instead of `_onRemoveEvent()/_onAddEvent()`
- [x] Ensure property change notifications are emitted

---

### 2.4 Update Event.onProperty() to Notify Person ✅ COMPLETED
**File:** `pkdiagram/scene/event.py:199-212`

**Solution Implemented:**
- Event.onProperty() updated to call person.onEventChanged(self, prop)
- Person receives notifications for all event property changes
- Obsolete methods removed

**Action Items:**
- [x] Update `Event.onProperty()` to call `person.onEventChanged(self, prop)`
- [x] Remove obsolete `person.onEventProperty()` method if it exists

---


---

## PHASE 3: TimelineModel Refactor 🟡

Replace phantom Event objects with TimelineRow data class.

### 3.1 Create TimelineRow Data Class ✅ COMPLETED
**File:** `pkdiagram/models/timelinemodel.py`

**Solution Implemented:**
- TimelineRow dataclass created as presentation object
- Accessor methods for kind(), person(), id() added
- Proper sorting via __lt__ implementation

**Action Items:**
- [x] Create `TimelineRow` dataclass in `timelinemodel.py`
- [x] Add accessor methods for common Event properties

---

### 3.2 Update TimelineModel to Use TimelineRow ✅ COMPLETED
**File:** `pkdiagram/models/timelinemodel.py:100-169`

**Solution Implemented:**
- Replaced `self._events` with `self._rows` (SortedList of TimelineRow)
- Removed `self._endEvents` dict (phantom events eliminated)
- Updated `_ensureEvent()` to create 1-2 TimelineRow objects
- Updated `_removeEvent()` to remove all rows for an event
- Updated `rowCount()`, `data()`, and `eventForRow()` methods

**Action Items:**
- [x] Replace `self._events` with `self._rows` (SortedList of TimelineRow)
- [x] Remove `self._endEvents` dict
- [x] Update `_ensureEvent()` to create 1-2 TimelineRow objects
- [x] Update `_removeEvent()` to remove all rows for an event
- [x] Update `rowCount()` to return `len(self._rows)`
- [x] Update `data()` method to work with TimelineRow objects
- [x] Update `eventForRow()` to return `row.source_event`

---

### 3.3 Remove TimelineModel._shouldHide() Emotion Logic ✅ COMPLETED
**File:** `pkdiagram/models/timelinemodel.py:123-144`

**Solution Implemented:**
- Removed obsolete Emotion.endEvent logic from `_shouldHide()`
- Simplified logic to check dateTime validity and search model
- Singular-date relationship handling moved to `_ensureEvent()`

**Action Items:**
- [x] Remove obsolete Emotion.endEvent logic from `_shouldHide()`
- [x] Handle singular-date relationships in `_ensureEvent()` instead

---


---

## PHASE 4: Emotion-Event Relationship Cleanup 🟢

Clarify the Emotion ↔ Event relationship per Option 1 (Emotion owns Event reference).

### 4.1 Remove Event.emotions() Factory ✅ COMPLETED
**File:** `pkdiagram/scene/event.py:481-505`

**Solution Implemented:**
- Removed Event._emotions cache attribute
- Event.emotions() now queries scene._emotions for emotions referencing this event
- Emotion creation is now explicit (not auto-created by Event)
- Scene.addItem() no longer auto-creates emotions from events

**Action Items:**
- [x] Remove `Event._emotions` cache attribute
- [x] Change `Event.emotions()` to query `scene._emotions`
- [x] Update all code that calls `Event.emotions()` to handle explicit creation
- [x] Update `Scene.addItem()` to NOT auto-create emotions from events

---

### 4.2 Clarify Emotion.person() vs Emotion.target() ✅ COMPLETED
**File:** `pkdiagram/scene/emotions.py:1654-1658`

**Solution Implemented:**
- Emotion.person() delegates to event.person() (subject of relationship)
- Emotion.target() returns target person (object of relationship)
- Pattern is correct and documented

**Action Items:**
- [x] Add docstrings to clarify `person()` = subject, `target()` = object
- [x] Ensure all Emotion creation sets both `event` and `target`

---

### 4.3 Emotion Property Delegation Pattern ✅ DECISION: Keep Both
**File:** `pkdiagram/scene/emotions.py:1168-1180`

**Decision:** Keep BOTH Emotion and Event properties - they serve distinct use cases with no overlap.

**Use Case Architecture:**
1. **Dated Emotions (with Event)**: Properties stored on Event, Emotion getters delegate to Event
2. **Undated Emotions (manual drawing, no Event)**: Properties stored on Emotion directly

**Rationale:**
- User manually adds undated Emotions to diagram via EmotionProperties without dates
- These undated Emotions have no Event (event=None) and will NEVER get dates added later
- Dated Emotions always reference an Event, so properties live on Event
- No duplication because these are mutually exclusive cases

**Implementation Pattern:**
```python
PathItem.registerProperties([
    {"attr": "intensity", ...},  # Used for undated emotions
    {"attr": "notes"},           # Used for undated emotions
    {"attr": "color", ...},      # Used for undated emotions
    {"attr": "event", "type": int},  # Event ID reference
    {"attr": "target", "type": int}, # Target person ID
])

def notes(self) -> str:
    """Return notes from Event if exists, else from Emotion."""
    if self.event():
        return self.event().notes()
    return self.prop("notes").get()

def intensity(self) -> int:
    """Return intensity from Event if exists, else from Emotion."""
    if self.event():
        return self.event().relationshipIntensity()
    return self.prop("intensity").get()

def color(self) -> str:
    """Return color from Event if exists, else from Emotion."""
    if self.event():
        return self.event().color()
    return self.prop("color").get()
```

**Action Items:**
- [x] **DECIDED:** Keep both sets of properties for distinct use cases
- [x] Emotion properties serve undated manual diagram drawing
- [x] Event properties serve dated timeline events
- [x] Getters check if event exists and delegate appropriately
- [x] No migration path needed (undated emotions won't become dated)

---


---

## PHASE 5: EventKind Enum Cleanup 🟢

Fix string vs enum comparison issues.

### 5.1 Fix String Comparisons ✅ COMPLETED
**Files:** Multiple

**Solution Implemented:**
- Replaced all string comparisons with EventKind enum comparisons
- Replaced `uniqueId()` calls with `kind()` calls
- Updated all string literals to use EventKind enum

**Action Items:**
- [x] Search for `kind == "` and replace with `kind == EventKind.`
- [x] Search for `uniqueId() ==` and replace with `kind() ==`
- [x] Update all string literals to use EventKind enum

---

### 5.2 Update Marriage.separationStatusFor() ✅ COMPLETED
**File:** `pkdiagram/scene/marriage.py:64`

**Solution Implemented:**
- Replaced `.value` comparisons with direct enum comparisons
- Updated all separation status logic to use EventKind enums directly

**Action Items:**
- [x] Replace `.value` comparisons with direct enum comparisons
- [x] Update all separation status logic

**Note:** Event.getDescriptionForKind() was removed - event description is now computed differently.

---


---

### 7.0 Fix Tests That Can Now Run ✅ COMPLETED
**Blocker Removed:** Circular import in marriage.py:26 has been fixed.

**Tests can now run.** However, many will fail due to refactor changes.

**Git Diff Shows 35 Files Changed:**
- 18 test files modified
- Most common issues: Event() constructor calls, uniqueId() removal, Emotion() constructor

---


---

### 7.2 Fix event.uniqueId() Calls ✅ ALREADY DONE
**Result from grep:** NO files found with `uniqueId()` calls!

**Conclusion:** All uniqueId() calls have already been replaced with kind() calls.

**Action Items:**
- [x] Replace `event.uniqueId()` with `event.kind()` - DONE
- [x] Replace string comparisons with EventKind enums - DONE

---

---

## PHASE 6: Data Compatibility (compat.py) ✅ COMPLETED

Migrate old file format to new flattened Event structure. This must run in the `if UP_TO(data, "2.0.12b1"):` block.

### 6.1 Extract and Flatten Events from Items ✅ COMPLETED
**File:** `pkdiagram/models/compat.py:277-315` (IMPLEMENTED)

**Status:** Code is implemented and working.

**Step 1: Split data["items"] into separate arrays**
```python
# Split mixed items into separate top-level arrays
if "items" in data:
    data["people"] = []
    data["marriages"] = []
    data["emotions"] = []
    data["events"] = []
    data["layerItems"] = []
    data["layers"] = []
    data["multipleBirths"] = []

    remaining_items = []

    for chunk in data["items"]:
        kind = chunk.get("kind")
        if kind == "Person":
            data["people"].append(chunk)
        elif kind == "Marriage":
            data["marriages"].append(chunk)
        elif kind in Emotion.kindSlugs():  # All emotion types
            data["emotions"].append(chunk)
        elif kind == "Event":
            data["events"].append(chunk)
        elif kind == "Layer":
            data["layers"].append(chunk)
        elif kind in ("Callout", "PencilStroke"):
            data["layerItems"].append(chunk)
        elif kind == "MultipleBirth":
            data["multipleBirths"].append(chunk)
        else:
            remaining_items.append(chunk)

    if remaining_items:
        data["items"] = remaining_items
    else:
        del data["items"]
```

---

### 6.2 Migrate Event Properties ✅ COMPLETED
**File:** `pkdiagram/models/compat.py:317-534` (IMPLEMENTED)

**Status:** Code is implemented and working. Migrates all events from Person/Marriage/Emotion to top-level Scene.events array.

**IMPORTANT**: Old format has Person.birthEvent, Person.deathEvent, Person.adoptedEvent as separate properties (not in Person.events array). See tests/scene/data/UP_TO_2.0.12b1.json lines 88-159.

**Migration Logic:**
- Extracts Person.birthEvent/deathEvent/adoptedEvent to Scene.events with person reference
- Extracts Person.events to Scene.events with person reference
- Extracts Marriage.events to Scene.events with person/spouse references
- Extracts Emotion.startEvent/endEvent to single Event with endDateTime
- Migrates all uniqueId → kind mappings (EventKind enum values)
- Migrates Emotion properties to Event (intensity → relationshipIntensity, notes)
- Migrates Emotion.person_a/person_b to Event.person and Emotion.target
- Updates lastItemId for any newly created events
- Sets relationship field on emotion events

---

### 6.3 Emotion Kind Migration ✅ WON'T FIX
**Reason:** Legacy data already has Emotion.kind as string values (e.g., "Conflict", "Distance"), not int values. No migration needed.

**Verified:** Test file P-C-Timeline-Master.json shows Emotion.kind is already string format in old files.

---

### 6.4 Test Cases for compat.py ✅ COMPLETED
**File:** `tests/scene/test_compat.py` (IMPLEMENTED)

**Status:** All 11 test cases implemented and passing.

**Test Coverage:**
- `test_up_to_2_0_12b1` - Smoke test with real old diagram file
- `test_phase_6_2_extract_person_builtin_events` - Extract birthEvent/deathEvent/adoptedEvent
- `test_phase_6_1_split_items_into_separate_arrays` - Split items into typed arrays
- `test_phase_6_2_extract_person_custom_events` - Extract Person.events array
- `test_phase_6_2_extract_marriage_events` - Extract Marriage.events (bonded/married/moved/separated/divorced)
- `test_phase_6_2_extract_emotion_events_with_date_range` - Extract Emotion with startEvent/endEvent
- `test_phase_6_2_extract_emotion_events_singular_date` - Extract Emotion with single date
- `test_phase_6_2_migrate_uniqueid_to_kind` - Migrate Event.uniqueId to Event.kind
- `test_phase_6_2_assign_event_ids` - Assign IDs to events without IDs
- `test_phase_6_unknown_item_types_preserved` - Unknown types kept in items array
- `test_phase_6_empty_arrays_handling` - Handle empty events arrays correctly

**Action Items:**
- [x] Implement complete migration in compat.py `if UP_TO(data, "2.0.12b1"):` block
- [x] Split `data["items"]` into `data["people"]`, `data["marriages"]`, `data["emotions"]`, `data["events"]`, `data["multipleBirths"]`
- [x] Extract Person.birthEvent/deathEvent/adoptedEvent to Scene.events with person reference
- [x] Extract Person.events to Scene.events with person reference
- [x] Extract Marriage.events to Scene.events with person/spouse references
- [x] Extract Emotion.startEvent/endEvent to single Event with endDateTime
- [x] Migrate all uniqueId → kind mappings
- [x] Migrate Emotion properties to Event (intensity → relationshipIntensity, notes)
- [x] Migrate Emotion.person_a/person_b to Event.person and Emotion.target
- [x] Migrate Emotion.kind from int to RelationshipKind.value string (Won't Fix - already strings)
- [x] Update lastItemId for any newly created events
- [x] Add comprehensive test cases in test_compat.py (Phase 6.4)
- [x] Test with actual old diagram files (Phase 6.4)

---

### 6.5 Update Scene.read() and Scene.write() for New Data Format ✅ COMPLETED
**Files:** `pkdiagram/scene/scene.py:676-828`

**Problem:** After compat.py migration, the file format changes from single mixed `items[]` array to separate typed arrays. Scene.read() and Scene.write() must be updated to match this new structure.

#### Old Format (pre-2.0.12b1):
```json
{
  "items": [
    {"kind": "Person", "id": 1, "birthEvent": {...}, "events": [...]},
    {"kind": "Marriage", "id": 2, "events": [...]},
    {"kind": "Conflict", "id": 3, "startEvent": {...}, "endEvent": {...}},
    {"kind": "Layer", "id": 4},
    {"kind": "PencilStroke", "id": 5},
    {"kind": "MultipleBirth", "id": 6}
  ]
}
```

#### New Format (2.0.12b1+):
```json
{
  "people": [{"kind": "Person", "id": 1}],
  "marriages": [{"kind": "Marriage", "id": 2}],
  "emotions": [{"kind": "Conflict", "id": 3, "event": 10, "target": 2}],
  "events": [
    {"id": 7, "kind": "birth", "person": 1},
    {"id": 10, "kind": "shift", "person": 1, "relationshipTargets": [2]}
  ],
  "layers": [{"kind": "Layer", "id": 4}],
  "layerItems": [{"kind": "PencilStroke", "id": 5}],
  "multipleBirths": [{"kind": "MultipleBirth", "id": 6}],
  "items": []  // Empty or contains only unknown future types
}
```

#### Key Migrations Performed by compat.py:
- **Person**: `birthEvent`, `deathEvent`, `adoptedEvent` properties removed → moved to `events[]`
- **Person**: `events[]` array removed → moved to top-level `events[]`
- **Marriage**: `events[]` array removed → moved to top-level `events[]`
- **Emotion**: `startEvent`, `endEvent` properties removed → merged into single Event in `events[]`
- **Emotion**: `person_a` removed, `person_b` → `target`, `intensity` → moved to Event, added `event` reference
- **Emotion**: Added `relationship` field matching emotion kind (e.g., "conflict", "distance")
- **Event**: `uniqueId` string → `kind` enum value
- **Event**: Added `person`, `spouse`, `child`, `relationshipTargets`, `relationshipIntensity`, `relationship` fields

#### Scene.read() Updates (lines 704-775):

**Implemented:**
1. Load events from `data.get("events", [])` FIRST (before people)
2. Load people from `data.get("people", [])` (fallback to items for old format)
3. Load marriages from `data.get("marriages", [])` (fallback to items)
4. Load emotions from `data.get("emotions", [])` (fallback to items)
5. Load layers from `data.get("layers", [])` (fallback to items)
6. Load layerItems from `data.get("layerItems", [])` (fallback to items)
7. Load multipleBirths from `data.get("multipleBirths", [])` (fallback to items)
8. Keep `data.get("items", [])` for backward compatibility and unknown types

#### Scene.write() Updates (lines 789-828):

**Implemented:**
1. Initialize all typed arrays at start
2. Route each item type to its corresponding array
3. Events go to `data["events"][]` NOT `data["items"][]`
4. Emotion.kind written as RelationshipKind string value
5. Unknown types preserved in `data["items"][]`

**Action Items:**
- [x] Update Scene.read() to load from typed arrays (events, people, marriages, emotions, layers, layerItems, multipleBirths)
- [x] Add Event loading loop BEFORE Person loading (events must exist for person.events() queries)
- [x] Update Scene.write() to write to typed arrays instead of single items array
- [x] Ensure backward compatibility by keeping items array fallback in read()
- [x] Test round-trip: old file → compat → read → write → verify new format
- [x] Verify that emotion.kind is written as RelationshipKind string value (e.g., "conflict", "distance")
- [x] Add Emotion.kindSlugs() and Emotion.kindForKindSlug() methods
- [x] Add relationship field to emotion events in compat.py migration

---

## PHASE 7: Test Fixes (Partial) ✅

### 7.0 Fix Tests That Can Now Run ✅ COMPLETED
**Blocker Removed:** Circular import in marriage.py:26 has been fixed.

**Status:** Tests can now run. However, many failed initially due to refactor changes.

**Git Diff Showed 35 Files Changed:**
- 18 test files modified
- Most common issues: Event() constructor calls, uniqueId() removal, Emotion() constructor

**Completed Action Items:**
- ✅ Fixed circular import blocker (Phase 0.1)
- ✅ Tests can now execute without import errors
- ✅ Identified patterns that need fixing across test files

---

### 7.2 Fix event.uniqueId() Calls ✅ COMPLETED
**Files:** All test and production files

**Pattern Replaced:**
```python
# Old:
assert event.uniqueId() == "birth"

# New:
assert event.kind() == EventKind.Birth
```

**Status:** ✅ All uniqueId() calls have been replaced with kind() calls.

**Completed Action Items:**
- ✅ Replaced `event.uniqueId()` with `event.kind()` throughout codebase
- ✅ Replaced string comparisons with EventKind enums
- ✅ Verified no remaining uniqueId() calls via grep

---

## PHASE 8: Model/View Updates (Partial) ✅

### 8.1 Update PersonPropertiesModel Event Handling ✅ COMPLETED
**File:** `pkdiagram/models/personpropertiesmodel.py:78-106`

**Status:** ✅ Already using EventKind enums

**Implementation:**
```python
def onEventProperty(self, prop):
    if prop.name() == "dateTime":
        if prop.item.kind() == EventKind.Birth:
            self.refreshProperty("birthDateTime")
        elif prop.item.kind() == EventKind.Adopted:
            self.refreshProperty("adoptedDateTime")
        elif prop.item.kind() == EventKind.Death:
            self.refreshProperty("deceasedDateTime")
    # ... location handling uses same pattern
```

**Completed Action Items:**
- ✅ Replaced `uniqueId()` with `kind()` in PersonPropertiesModel (lines 80, 82, 84)
- ✅ Replaced string comparisons with EventKind enums (lines 80-92, 98-106)
- ✅ EventKind imported on line 9

---

### 8.2 Update MarriagePropertiesModel Event Handling ✅ COMPLETED
**File:** `pkdiagram/models/marriagepropertiesmodel.py:6-78`

**Status:** ✅ Already using EventKind enums

**Implementation:**
```python
def _anyMarriedEvents(marriage: Marriage):
    return any(x for x in marriage.events()
               if x.kind() == EventKind.Married
               and {x.person(), x.spouse()} == {marriage.personA(), marriage.personB()})

def onEventsChanged(self, event):
    if event.kind() == EventKind.Married:
        self.refreshProperty("anyMarriedEvents")
    elif event.kind() == EventKind.Separated:
        self.refreshProperty("anySeparatedEvents")
    elif event.kind() == EventKind.Divorced:
        self.refreshProperty("anyDivorcedEvents")
```

**Completed Action Items:**
- ✅ Replaced `uniqueId()` with `kind()` in MarriagePropertiesModel
- ✅ Replaced string comparisons with EventKind enums (lines 10, 19, 28, 68, 71, 74)
- ✅ EventKind imported on line 2

---

## PHASE 9: Scene Data Format ✅ COMPLETED

Update Scene serialization format. **Both sub-phases completed in Phase 6.5.**

### 9.1 Update Scene.write() ✅ COMPLETED
**File:** `pkdiagram/scene/scene.py:851-927`

**Status:** ✅ COMPLETED in Phase 6.5

**Implementation:**
Scene.write() has been fully updated to use typed arrays:

```python
# Initialize typed arrays (lines 858-866)
data["people"] = []
data["marriages"] = []
data["emotions"] = []
data["events"] = []  # NEW: top-level events array
data["layers"] = []
data["layerItems"] = []
data["multipleBirths"] = []
data["items"] = []  # For future unknown types

# Route items to appropriate arrays (lines 880-917)
if item.isEvent:
    chunk["kind"] = "Event"
    item.write(chunk)
    data["events"].append(chunk)
elif item.isPerson:
    chunk["kind"] = "Person"
    item.write(chunk)
    data["people"].append(chunk)
# ... etc
```

**Completed Action Items:**
- ✅ Updated `Scene.write()` to separate events from other items
- ✅ Created `data["events"]` array
- ✅ Removed events from `data["people"]` and `data["marriages"]`
- ✅ Unknown item types preserved in `data["items"]` for forward compatibility

---

### 9.2 Update Scene.read() ✅ COMPLETED
**File:** `pkdiagram/scene/scene.py:704-788`

**Status:** ✅ COMPLETED in Phase 6.5

**Implementation:**
Scene.read() implements two-phase loading with typed arrays:

```python
# Phase 1: Load events FIRST (lines 706-711)
for chunk in data.get("events", []):
    item = Event(kind=EventKind.Shift, person=None)  # Placeholder
    item.id = chunk["id"]
    items.append(item)
    itemChunks.append((item, chunk))

# Then load people, marriages, emotions... (lines 713-761)

# Phase 2: Resolve all dependencies via byId (lines 777-788)
for item, chunk in itemChunks:
    item.read(chunk, byId)  # Resolves event.person via byId lookup
```

**Completed Action Items:**
- ✅ Implemented two-phase loading in Scene.read()
- ✅ Events loaded FIRST in phase 1 (before people who query events)
- ✅ Event.person references resolved in phase 2
- ✅ Backward compatibility with `data.get("items", [])` fallback (lines 763-789)

---

## PHASE 8.3: Remove EmotionPropertiesModel Date Editors ✅

**File:** `pkdiagram/models/emotionpropertiesmodel.py`

**Goal:** Remove date/time properties that should be on Event

**Changes:**
```python
# Remove these properties (now on Event):
# - startDateTime
# - endDateTime
# - startDateUnsure
# - endDateUnsure

# Keep these:
# - personAId / personBId (or migrate to person/target?)
# - dyadic
# - itemName
```

**Completed Action Items:**
- ✅ Remove date/time properties from EmotionPropertiesModel
- ✅ Add link to edit Event instead
- ✅ Update QML to show Event properties via link

---

## PHASE 8.4: Update SearchModel ✅

**File:** `pkdiagram/models/searchmodel.py:118`

**Goal:** Add type hints to clarify SearchModel expects Event objects

**Previous Code:**
```python
def shouldHide(self, event):
    """Search kernel."""
    nullLoggedDate = bool(
        not event.loggedDateTime() or event.loggedDateTime().isNull()
    )
```

**Updated Code:**
```python
def shouldHide(self, event: Event) -> bool:
    """Determine if event should be hidden based on search criteria."""
    # ... existing logic ...
```

**Completed Action Items:**
- ✅ Add type hints to SearchModel.shouldHide()
- ✅ Ensure it works with Event objects (not TimelineRow)

---

## PHASE 10: QML/UI Updates ✅

Update QML interfaces to work with new structure.

### 10.1 Update EventForm ✅
**File:** `pkdiagram/resources/qml/EventForm.qml`

**Changes Made:**
- Added `event.color` picker widget
- Updated EventKind display labels (Shift → "Relationship Shift")
- Date range support via `isDateRange`, `startDateTime`, `endDateTime` properties
- Location, symptom, anxiety, functioning fields integrated

**Completed Action Items:**
- ✅ Add `color` picker widget to EventForm.qml
- ✅ Update EventKind display labels

---

### 10.2 Update EmotionProperties ✅
**File:** `pkdiagram/resources/qml/PK/EmotionProperties.qml`

**Changes Made:**
- Removed all date/time pickers from EmotionProperties.qml
- Removed `startDateTime`, `endDateTime` properties
- Added "Edit Event" link button that opens EventForm
- Passes `emotion.event()` to EventForm when link clicked
- Kept intensity, notes, kind, target editors for undated emotions

**Completed Action Items:**
- ✅ Remove all date/time pickers from EmotionProperties.qml
- ✅ Remove `startDateTime`, `endDateTime` properties
- ✅ Add "Edit Event" link button that opens EventForm
- ✅ Pass `emotion.event()` to EventForm when link clicked
- ✅ Keep intensity, notes, kind, target editors for undated emotions
- ✅ Update EmotionPropertiesDrawer.qml if needed

---

### 10.3 Update PersonProperties ✅
**File:** `pkdiagram/resources/qml/PersonProperties.qml`

**Changes Made:**
- Removed ~165 lines of date picker widgets (birth, adopted, deceased date pickers)
- Removed birthDatePicker, birthDateButtons, adoptedDateButtons, deceasedDateButtons properties
- Added "Edit Event" buttons for Birth and Death events
- Implemented button click handlers to find/create events and open EventForm
- Updated layout to remove DatePicker columns
- Birth/adopted/death dates still display correctly (read-only from model)

**Completed Action Items:**
- ✅ Remove ~165 lines of date picker widgets
- ✅ Remove birthDatePicker, birthDateButtons, adoptedDateButtons, deceasedDateButtons properties
- ✅ Add 2 "Edit Event" buttons for Birth, Death events
- ✅ Implement button click handlers to find/create events and open EventForm
- ✅ Update layout to remove DatePicker columns
- ✅ Test that birth/adopted/death dates still display correctly (read-only)

---

## PHASE 10.5: GraphicalTimeline TimelineRow Refactor 🟡

**Goal:** Refactor GraphicalTimeline to work with `TimelineRow` objects instead of raw `Event` objects, properly accounting for events with date ranges that create multiple timeline rows.

**Background:**
- `TimelineModel` stores `_rows` as a `SortedList` of `TimelineRow` objects
- Each `TimelineRow` has `.event` (the Event) and `.isEndMarker` (bool) properties
- Events with `endDateTime` create TWO rows: one for start, one for end
- **Current bug:** `graphicaltimelinecanvas.py:114` calls `self._timelineModel.events()` which doesn't exist
- GraphicalTimeline should display timeline rows, not just raw events

**Why This Matters:**
- Events with date ranges (e.g., relationship shifts with start/end dates) should display both markers
- Current code tries to access a non-existent `TimelineModel.events()` method
- Scene has become the canonical query interface, but TimelineModel provides filtered/sorted rows for UI

---

### 10.5.1 Update GraphicalTimelineCanvas
**File:** `pkdiagram/documentview/graphicaltimelinecanvas.py`

**Current Code (line 114):**
```python
self._events = self._timelineModel.events()  # ❌ DOES NOT EXIST
```

**Issue:**
- `TimelineModel.events()` method doesn't exist
- Need to work with `TimelineRow` objects from `_timelineModel._rows`

**New Approach:**
```python
# Get TimelineRow objects from TimelineModel
self._rows_data = []
for row_index in range(self._timelineModel.rowCount()):
    timeline_row = self._timelineModel._rows[row_index]
    self._rows_data.append(timeline_row)

# Or access via Scene for events, then match to TimelineRows
if self.scene:
    all_events = [e for e in self.scene.events() if e.dateTime() and not e.dateTime().isNull()]
    all_events.sort(key=lambda e: e.dateTime())
    # Build rows accounting for endDateTime
    self._rows_data = []
    for event in all_events:
        self._rows_data.append(TimelineRow(event=event, isEndMarker=False))
        if event.endDateTime():
            self._rows_data.append(TimelineRow(event=event, isEndMarker=True))
```

**Action Items:**
- [x] Remove call to non-existent `TimelineModel.events()` method
- [x] Decide: Access `TimelineModel._rows` directly OR reconstruct from `Scene.events()`
- [x] Update `self._events` to store `TimelineRow` objects or keep separate list
- [x] Update `dateTimeRange()` method to work with TimelineRow objects
- [x] Update tag filtering logic to work with TimelineRow objects (line 127)

---

### 10.5.2 Update Event Drawing Logic
**Files:**
- `pkdiagram/documentview/graphicaltimelinecanvas.py` (paint methods)
- `pkdiagram/documentview/graphicaltimeline.py` (if affected)

**Current State:** Drawing logic assumes `self._events` contains Event objects.

**Changes Needed:**
- Update drawing code to extract `.event` from TimelineRow
- Handle `.isEndMarker` flag to draw end markers differently
- Differentiate visual display between start markers and end markers

**Example:**
```python
# OLD:
for event in self._events:
    draw_event(event)

# NEW:
for timeline_row in self._rows_data:
    event = timeline_row.event
    if timeline_row.isEndMarker:
        draw_end_marker(event, event.endDateTime())
    else:
        draw_start_marker(event, event.dateTime())
```

**Action Items:**
- [x] Update paint methods to work with TimelineRow objects
- [ ] ~~Add visual distinction for end markers vs start markers~~
- [ ] ~~Ensure hover/tooltip shows correct dateTime (start vs end)~~

---

### 10.5.3 Update Event Selection
**Files:**
- `pkdiagram/documentview/graphicaltimelinecanvas.py` (selection logic)
- `pkdiagram/documentview/documentview.py` (if affected)

**Current State:** Selection logic works with Event objects.

**Changes Needed:**
- Clicking on an end marker should select the same underlying Event as the start marker
- Selection highlighting should show both start and end markers for an event with date range
- Rubber band selection should work with TimelineRow objects

**Example:**
```python
# When clicking on a timeline row:
clicked_row = find_row_at_position(click_pos)
event = clicked_row.event  # Get underlying event
# Select the event (both start and end markers will highlight)
select_event(event)
```

**Action Items:**
- [x] Update mouse click handlers to work with TimelineRow objects
- [x] Update selection visual to highlight both start/end markers
- [x] Test selection with rubber band on events with date ranges
- [x] Verify double-click to inspect works with both start/end markers


**END OF COMPLETED PHASES**
