# Event Flattening Refactor - Master TODO

**Goal:** Make Events top-level Scene objects instead of children of Person/Marriage/Emotion, simplifying the object hierarchy and enabling better timeline/event management.

**Status:** In progress (progress commit: 235dc569)

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

## PHASE 2: Remove Event Reference Caching 🟡

Replace cached event lists with computed properties that query Scene.

### 2.1 Remove Person._events Cache
**File:** `pkdiagram/scene/person.py:787-789`

**Current Code:**
```python
class Person:
    def __init__(self):
        self._events = []  # Cache

    def events(self) -> list[Event]:
        return self._events

    def _onAddEvent(self, x):
        if x not in self._events:
            self._events.append(x)
            self.updateEvents()

    def _onRemoveEvent(self, x):
        if x in self._events:
            self._events.remove(x)
            self.updateEvents()
```

**New Code:**
```python
class Person:
    # Remove self._events

    def events(self) -> list[Event]:
        """Query scene for events pertaining to this person."""
        if not self.scene():
            return []
        return [e for e in self.scene()._events if e.person == self]

    def onEventAdded(self, event):
        """Called by Scene when event is added with person=self."""
        self.updateEvents()      # Recalc variables database
        self.updateDetails()     # Birth/death affect display
        self.updateGeometry()    # Adopted affects visuals

    def onEventRemoved(self, event):
        """Called by Scene when event is removed with person=self."""
        self.updateEvents()
        self.updateDetails()
        self.updateGeometry()

    def onEventChanged(self, event, prop):
        """Called when event property changes."""
        if prop.name() in ('dateTime', 'endDateTime'):
            self.updateEvents()
        if event.kind() in (EventKind.Birth, EventKind.Death, EventKind.Adopted):
            self.updateDetails()
            self.updateGeometry()
```

**Action Items:**
- [ ] Remove `Person._events` attribute
- [ ] Remove `Person._onAddEvent()` method
- [ ] Remove `Person._onRemoveEvent()` method
- [ ] Change `Person.events()` to computed property (query scene)
- [ ] Add `Person.onEventAdded(event)` callback method
- [ ] Add `Person.onEventRemoved(event)` callback method
- [ ] Add `Person.onEventChanged(event, prop)` callback method
- [ ] Update `Person.updateEvents()` to query `self.events()` instead of using cache

---

### 2.2 Remove Marriage._events Cache
**File:** `pkdiagram/scene/marriage.py:447-462`

**Current Code:**
```python
class Marriage:
    def __init__(self):
        self._events = []

    def events(self):
        return list(self._events)

    def _onAddEvent(self, x):
        if not x in self._events:
            self._events.append(x)
            self.updateDetails()
            self.updateEvents()

    def _onRemoveEvent(self, x):
        if x in self._events:
            self._events.remove(x)
            self.updateDetails()
            self.updateEvents()
```

**New Code:**
```python
class Marriage:
    # Remove self._events

    def events(self):
        """Query scene for events pertaining to this marriage."""
        if not self.scene():
            return []
        return [e for e in self.scene()._events if e.person == self]

    def onEventAdded(self, event):
        """Called by Scene when event is added with person=self."""
        self.updateDetails()
        self.updateGeometry()

    def onEventRemoved(self, event):
        """Called by Scene when event is removed."""
        self.updateDetails()
        self.updateGeometry()
```

**Action Items:**
- [ ] Remove `Marriage._events` attribute
- [ ] Remove `Marriage._onAddEvent()` method
- [ ] Remove `Marriage._onRemoveEvent()` method
- [ ] Remove `Marriage.updateEvents()` method (obsolete per user)
- [ ] Change `Marriage.events()` to computed property
- [ ] Add `Marriage.onEventAdded(event)` callback
- [ ] Add `Marriage.onEventRemoved(event)` callback

---

### 2.3 Simplify Event._do_setPerson()
**File:** `pkdiagram/scene/event.py:167-187`

**Current Code:** Still calls `person._onAddEvent()` which maintains cache.

**New Code:**
```python
def Event._do_setPerson(self, person):
    """Set the person this event pertains to."""
    was = self.person
    self.person = person

    # Notify old person this event no longer pertains to them
    if was and hasattr(was, 'onEventRemoved'):
        was.onEventRemoved(self)

    # Notify new person this event now pertains to them
    if person and hasattr(person, 'onEventAdded'):
        person.onEventAdded(self)

    # Update event's computed properties
    wasDescription = self.description()
    wasNotes = self.notes()
    wasParentName = self.personName()

    self.updateDescription()
    self.updateNotes()
    self.updateParentName()

    # Emit property changes for UI bindings
    if self.description() != wasDescription:
        self.onProperty(self.prop("description"))
    if self.notes() != wasNotes:
        self.onProperty(self.prop("notes"))
    if self.personName() != wasParentName:
        self.onProperty(self.prop("personName"))
```

**Action Items:**
- [ ] Update `Event._do_setPerson()` to call `onEventRemoved()/onEventAdded()` instead of `_onRemoveEvent()/_onAddEvent()`
- [ ] Ensure property change notifications are emitted

---

### 2.4 Update Event.onProperty() to Notify Person
**File:** `pkdiagram/scene/event.py:199-212`

**Current Code:**
```python
def onProperty(self, prop):
    # ... existing code ...
    super().onProperty(prop)
    if self.person:
        self.person.onEventProperty(prop)  # Exists but not used consistently
```

**New Code:**
```python
def onProperty(self, prop):
    # ... existing code ...
    super().onProperty(prop)

    # Notify person of property changes
    if self.person and hasattr(self.person, 'onEventChanged'):
        self.person.onEventChanged(self, prop)
```

**Action Items:**
- [ ] Update `Event.onProperty()` to call `person.onEventChanged(self, prop)`
- [ ] Remove obsolete `person.onEventProperty()` method if it exists

---

## PHASE 3: TimelineModel Refactor 🟡

Replace phantom Event objects with TimelineRow data class.

### 3.1 Create TimelineRow Data Class
**File:** `pkdiagram/models/timelinemodel.py`

**New Code:**
```python
from dataclasses import dataclass

@dataclass
class TimelineRow:
    """Presentation object for timeline - NOT a scene Event."""
    dateTime: QDateTime
    description: str
    source_event: Event | None
    is_end_marker: bool = False

    def kind(self) -> EventKind | None:
        return self.source_event.kind() if self.source_event else None

    def person(self):
        return self.source_event.person() if self.source_event else None

    def id(self):
        return self.source_event.id if self.source_event else None

    def __lt__(self, other):
        """Sort by dateTime."""
        if not self.dateTime or not other.dateTime:
            return False
        return self.dateTime < other.dateTime
```

**Action Items:**
- [ ] Create `TimelineRow` dataclass in `timelinemodel.py`
- [ ] Add accessor methods for common Event properties

---

### 3.2 Update TimelineModel to Use TimelineRow
**File:** `pkdiagram/models/timelinemodel.py:100-169`

**Current Code:**
```python
class TimelineModel:
    def __init__(self):
        self._events = SortedList()
        self._endEvents = {}  # Phantom events

    def _ensureEvent(self, event: Event):
        self._events.add(event)

        if event.endDateTime():
            endEvent = Event(dateTime=event.endDateTime(), ...)  # BAD: phantom event
            self._endEvents[event] = endEvent
            self._events.add(endEvent)
```

**New Code:**
```python
class TimelineModel:
    def __init__(self):
        self._rows = SortedList()  # TimelineRow objects, not Events

    def _ensureEvent(self, event: Event):
        """Add 1 or 2 rows for this event."""
        if not event.dateTime():
            return

        # Start row
        if not self._shouldHide(event):
            row = TimelineRow(
                dateTime=event.dateTime(),
                description=event.description(),
                source_event=event,
                is_end_marker=False,
            )
            newRowIndex = self._rows.bisect_right(row)
            if emit:
                self.beginInsertRows(QModelIndex(), newRowIndex, newRowIndex)
            self._rows.add(row)
            if emit:
                self.endInsertRows()

        # End row (if needed)
        if event.endDateTime():
            row = TimelineRow(
                dateTime=event.endDateTime(),
                description=f"{event.kind().name} ended",
                source_event=event,
                is_end_marker=True,
            )
            newRowIndex = self._rows.bisect_right(row)
            if emit:
                self.beginInsertRows(QModelIndex(), newRowIndex, newRowIndex)
            self._rows.add(row)
            if emit:
                self.endInsertRows()

    def _removeEvent(self, event):
        """Remove all rows for this event."""
        rows_to_remove = [r for r in self._rows if r.source_event == event]
        for row in rows_to_remove:
            index = self._rows.index(row)
            self.beginRemoveRows(QModelIndex(), index, index)
            self._rows.remove(row)
            self.endRemoveRows()
```

**Action Items:**
- [ ] Replace `self._events` with `self._rows` (SortedList of TimelineRow)
- [ ] Remove `self._endEvents` dict
- [ ] Update `_ensureEvent()` to create 1-2 TimelineRow objects
- [ ] Update `_removeEvent()` to remove all rows for an event
- [ ] Update `rowCount()` to return `len(self._rows)`
- [ ] Update `data()` method to work with TimelineRow objects
- [ ] Update `eventForRow()` to return `row.source_event`

---

### 3.3 Remove TimelineModel._shouldHide() Emotion Logic
**File:** `pkdiagram/models/timelinemodel.py:123-144`

**Current Code:**
```python
def _shouldHide(self, event):
    # ...
    elif (
        event.kind() == EventKind.Shift
        and event.relationship()
        and event.isEndEvent  # WRONG: Events don't have isEndEvent!
        and event.emotion().isSingularDate()
    ):
        hidden = True
```

**New Code:**
```python
def _shouldHide(self, event):
    """Determine if event should be hidden from timeline."""
    if event.dateTime() is None or event.dateTime().isNull():
        return True

    if not self._scene:  # SceneModel.nullTimelineModel
        return False

    # Don't hide end markers for singular-date relationships
    # (This is handled by not creating end TimelineRow in _ensureEvent)

    if self._searchModel and self._searchModel.shouldHide(event):
        return True

    return False
```

**Action Items:**
- [ ] Remove obsolete Emotion.endEvent logic from `_shouldHide()`
- [ ] Handle singular-date relationships in `_ensureEvent()` instead

---

## PHASE 4: Emotion-Event Relationship Cleanup 🟢

Clarify the Emotion ↔ Event relationship per Option 1 (Emotion owns Event reference).

### 4.1 Remove Event.emotions() Factory
**File:** `pkdiagram/scene/event.py:481-505`

**Current Code:**
```python
def Event.emotions(self) -> list[Emotion]:
    """Canonical constructor for emotions..."""
    if self.relationship():
        if not self._emotions:
            for target in self.relationshipTargets():
                emotion = self.scene.addItem(
                    Emotion(kind=self.relationship(), target=target, event=self, ...)
                )
                self._emotions.append(emotion)
        return self._emotions
    else:
        return []
```

**New Code:**
```python
def Event.emotions(self) -> list[Emotion]:
    """Find emotions that reference this event."""
    if not self.scene():
        return []
    return [e for e in self.scene()._emotions if e.event() == self]
```

**Emotion Creation:** Make explicit in Scene or calling code:
```python
# When creating a relationship event:
event = Event(
    kind=EventKind.Shift,
    person=person1,
    relationshipTargets=[person2, person3],
)
scene.addItem(event)

# Explicitly create emotions:
for target in event.relationshipTargets():
    emotion = Emotion(event=event, target=target, kind=event.relationship())
    scene.addItem(emotion)
```

**Action Items:**
- [ ] Remove `Event._emotions` cache attribute
- [ ] Change `Event.emotions()` to query `scene._emotions`
- [ ] Update all code that calls `Event.emotions()` to handle explicit creation
- [ ] Update `Scene.addItem()` to NOT auto-create emotions from events

---

### 4.2 Clarify Emotion.person() vs Emotion.target()
**File:** `pkdiagram/scene/emotions.py:1654-1658`

**Current Code:**
```python
def person(self) -> "Person":
    return self._event.person()  # Emotion delegates to event

def target(self) -> "Person":
    return self._target
```

**Clarification:** This is correct! Emotion always has:
- `.person()` - the "subject" of the relationship (from event)
- `.target()` - the "object" of the relationship (stored on Emotion)

**No changes needed** - just document the pattern.

**Action Items:**
- [ ] Add docstrings to clarify `person()` = subject, `target()` = object
- [ ] Ensure all Emotion creation sets both `event` and `target`

---

### 4.3 Remove Duplicate Properties
**File:** `pkdiagram/scene/emotions.py:1168-1180`

**Current Code:**
```python
PathItem.registerProperties([
    {"attr": "intensity", ...},  # DUPLICATE with Event.relationshipIntensity
    {"attr": "notes"},           # DUPLICATE with Event.notes
    {"attr": "color", ...},      # DUPLICATE with Event.color
])

def intensity(self) -> int:
    if self._event:
        return self._event.relationshipIntensity()  # Delegates
    else:
        return self.prop("intensity").get()  # Fallback?
```

**Decision Needed:** Should Emotion have its own intensity/notes/color, or always delegate to Event?

**Option A: Full Delegation (simpler)**
```python
# Remove Emotion properties, always delegate:
def intensity(self) -> int:
    return self._event.relationshipIntensity() if self._event else 1

def notes(self) -> str:
    return self._event.notes() if self._event else None

def color(self) -> str:
    return self._event.color() if self._event else None
```

**Option B: Emotion-Specific (more flexible)**
```python
# Keep Emotion properties, Event stores "default" values:
def intensity(self) -> int:
    # Emotion can override event's intensity
    if self.prop("intensity").isset():
        return self.prop("intensity").get()
    return self._event.relationshipIntensity() if self._event else 1
```

**Recommendation:** Use Option A (full delegation) unless you need per-target customization.

**Action Items:**
- [ ] **DECIDE:** Full delegation or emotion-specific properties?
- [ ] Remove duplicate properties if using full delegation
- [ ] Update getters to delegate to `self._event`
- [ ] Update setters to modify `self._event` properties

---

## PHASE 5: EventKind Enum Cleanup 🟢

Fix string vs enum comparison issues.

### 5.1 Fix String Comparisons
**Files:** Multiple

**Problem:** Code compares EventKind enum to strings:
```python
# Wrong:
if kind == "moved":
    ...

# Right:
if kind == EventKind.Moved:
    ...
```

**Action Items:**
- [ ] Search for `kind == "` and replace with `kind == EventKind.`
- [ ] Search for `uniqueId() ==` and replace with `kind() ==`
- [ ] Update all string literals to use EventKind enum

---

### 5.2 Update Event.getDescriptionForKind()
**File:** `pkdiagram/scene/event.py:308-349`

**Current Code:**
```python
def getDescriptionForKind(self, kind=None):
    # ...
    elif kind == "moved":  # STRING comparison!
        if self.location():
            ret = "Moved to %s" % self.location()
```

**New Code:**
```python
def getDescriptionForKind(self, kind: EventKind = None):
    if not kind:
        return None

    if self.person:
        if self.person.isPerson:
            if kind == EventKind.Birth:
                ret = util.BIRTH_TEXT
            elif kind == EventKind.Adopted:
                ret = util.ADOPTED_TEXT
            elif kind == EventKind.Death:
                ret = util.DEATH_TEXT
        elif self.person.isMarriage:
            if kind == EventKind.Bonded:
                ret = "Bonded"
            elif kind == EventKind.Married:
                ret = "Married"
            elif kind == EventKind.Divorced:
                ret = "Divorced"
            elif kind == EventKind.Separated:
                ret = "Separated"
            elif kind == EventKind.Moved:
                if self.location():
                    ret = "Moved to %s" % self.location()
                else:
                    ret = "Moved"
    return ret
```

**Action Items:**
- [ ] Replace all string comparisons with EventKind enum
- [ ] Remove obsolete Emotion event description logic
- [ ] Add type hints: `kind: EventKind`

---

### 5.3 Update Marriage.separationStatusFor()
**File:** `pkdiagram/scene/marriage.py:64`

**Current Code:**
```python
status in (EventKind.Separated.value, EventKind.Divorced.value)  # Mixing enum values
```

**New Code:**
```python
status in (EventKind.Separated, EventKind.Divorced)  # Use enums directly
```

**Action Items:**
- [ ] Replace `.value` comparisons with direct enum comparisons
- [ ] Update all separation status logic

---

## PHASE 6: Data Compatibility (compat.py) 🔴 CRITICAL

Migrate old file format to new Event structure.

### 6.1 Migrate Event.uniqueId → Event.kind
**File:** `pkdiagram/models/compat.py:291`

**Current Code:**
```python
# Event.
# (empty!)
```

**New Code:**
```python
# Migrate Event.uniqueId to Event.kind
for chunk in data.get("events", []):
    if "uniqueId" in chunk:
        uid = chunk["uniqueId"]

        # Map old string IDs to EventKind values
        if uid == "birth":
            chunk["kind"] = EventKind.Birth.value
        elif uid == "adopted":
            chunk["kind"] = EventKind.Adopted.value
        elif uid == "death":
            chunk["kind"] = EventKind.Death.value
        elif uid == "married":
            chunk["kind"] = EventKind.Married.value
        elif uid == "bonded":
            chunk["kind"] = EventKind.Bonded.value
        elif uid == "separated":
            chunk["kind"] = EventKind.Separated.value
        elif uid == "divorced":
            chunk["kind"] = EventKind.Divorced.value
        elif uid == "moved":
            chunk["kind"] = EventKind.Moved.value
        elif uid == "emotionStartEvent" or uid == "emotionEndEvent" or uid == "CustomIndividual" or uid == "" or uid is None:
            chunk["kind"] = EventKind.Shift.value
        else:
            log.warning(f"Unknown uniqueId: {uid}, defaulting to Shift")
            chunk["kind"] = EventKind.Shift.value

        del chunk["uniqueId"]
```

**Action Items:**
- [ ] Implement uniqueId → kind migration in compat.py
- [ ] Map all old uniqueId strings to EventKind enums
- [ ] Set blank/CustomIndividual to EventKind.Shift (per CLAUDE.md)
- [ ] Delete uniqueId field after migration

---

### 6.2 Migrate Emotion Events to Scene
**File:** `pkdiagram/models/compat.py`

**Current Data Structure:**
```json
{
  "people": [
    {
      "id": 1,
      "events": [...]  // OLD: events stored in person
    }
  ],
  "marriages": [
    {
      "id": 2,
      "events": [...]  // OLD: events stored in marriage
    }
  ],
  "emotions": [
    {
      "id": 3,
      "startEvent": {...},  // OLD: event as child
      "endEvent": {...}     // OLD: event as child
    }
  ]
}
```

**New Data Structure:**
```json
{
  "events": [  // NEW: all events at top level
    {"id": 10, "kind": "birth", "person": 1, ...},
    {"id": 11, "kind": "variable-shift", "person": 1, "endDateTime": "...", ...}
  ],
  "people": [
    {"id": 1, ...}  // No more events array
  ],
  "marriages": [
    {"id": 2, ...}  // No more events array
  ],
  "emotions": [
    {"id": 3, "event": 11, "target": 2, ...}  // Reference to event ID
  ]
}
```

**Migration Code:**
```python
def update_data(data):
    # ... existing migrations ...

    # Collect all events from people/marriages/emotions
    all_events = []
    next_event_id = data.get("lastItemId", -1) + 1

    # Migrate person events
    for person_chunk in data.get("people", []):
        for event_chunk in person_chunk.pop("events", []):
            event_chunk["person"] = person_chunk["id"]
            if "id" not in event_chunk:
                event_chunk["id"] = next_event_id
                next_event_id += 1
            all_events.append(event_chunk)

    # Migrate marriage events
    for marriage_chunk in data.get("marriages", []):
        for event_chunk in marriage_chunk.pop("events", []):
            event_chunk["person"] = marriage_chunk["id"]  # Marriage is the "person"
            if "id" not in event_chunk:
                event_chunk["id"] = next_event_id
                next_event_id += 1
            all_events.append(event_chunk)

    # Migrate emotion events
    for emotion_chunk in data.get("emotions", []):
        # Convert start/end events to single event with endDateTime
        if "startEvent" in emotion_chunk:
            start = emotion_chunk.pop("startEvent")
            end = emotion_chunk.pop("endEvent", None)

            event_chunk = start
            event_chunk["kind"] = EventKind.Shift.value
            event_chunk["person"] = emotion_chunk.get("person_a")  # Subject

            # Migrate isDateRange to endDateTime
            if end and end.get("dateTime"):
                event_chunk["endDateTime"] = end["dateTime"]

            # Migrate emotion-specific properties
            if "intensity" in emotion_chunk:
                event_chunk["relationshipIntensity"] = emotion_chunk["intensity"]
            if "notes" in emotion_chunk:
                event_chunk["notes"] = emotion_chunk["notes"]

            # Set relationship targets
            if "person_b" in emotion_chunk:
                event_chunk["relationshipTargets"] = [emotion_chunk["person_b"]]

            if "id" not in event_chunk:
                event_chunk["id"] = next_event_id
                next_event_id += 1

            all_events.append(event_chunk)

            # Update emotion to reference event
            emotion_chunk["event"] = event_chunk["id"]
            emotion_chunk["target"] = emotion_chunk.pop("person_b", None)

            # Clean up old fields
            emotion_chunk.pop("person_a", None)
            emotion_chunk.pop("intensity", None)
            emotion_chunk.pop("notes", None)

    # Add all events to top-level
    data["events"] = all_events
    data["lastItemId"] = next_event_id - 1
```

**Action Items:**
- [ ] Implement full event migration in compat.py
- [ ] Migrate `Person.events` → `Scene.events`
- [ ] Migrate `Marriage.events` → `Scene.events`
- [ ] Migrate `Emotion.startEvent/endEvent` → single Event with `endDateTime`
- [ ] Update `Emotion` chunks to reference event ID
- [ ] Clean up old fields from person/marriage/emotion chunks
- [ ] Update `lastItemId` counter

---

### 6.3 Property Migrations
**File:** `pkdiagram/models/compat.py`

**Migrations Needed:**
```python
# Emotion property migrations
for emotion_chunk in data.get("emotions", []):
    # Emotion.kind (int) -> RelationshipKind enum value (str)
    if "kind" in emotion_chunk and isinstance(emotion_chunk["kind"], int):
        emotion_chunk["kind"] = RelationshipKind(emotion_chunk["kind"]).value

    # person_a -> event.person (handled in 6.2)
    # person_b -> target
    # intensity -> event.relationshipIntensity (handled in 6.2)
    # notes -> event.notes (handled in 6.2)
```

**Action Items:**
- [ ] Migrate `Emotion.kind` int → RelationshipKind.value string
- [ ] Migrate `Emotion.isDateRange` → `Event.endDateTime`
- [ ] Migrate `Emotion.person_a` → `Event.person`
- [ ] Migrate `Emotion.person_b` → `Emotion.target`
- [ ] Migrate `Emotion.intensity` → `Event.relationshipIntensity`
- [ ] Migrate `Emotion.notes` → `Event.notes`

---

## PHASE 7: Test Fixes 🟡

Update tests to work with new Event structure.

### 7.1 Fix Event() Constructor Calls
**Files:** All test files

**Current Pattern:**
```python
event = Event(person)  # FAILS: no kind
```

**New Pattern:**
```python
event = Event(person=person, kind=EventKind.Birth)
```

**Action Items:**
- [ ] Search all test files for `Event(` calls
- [ ] Add `kind=` parameter to all Event() constructors
- [ ] Update positional arguments to keyword arguments

---

### 7.2 Fix event.uniqueId() Calls
**Files:** All test files

**Pattern:**
```python
# Old:
assert event.uniqueId() == "birth"

# New:
assert event.kind() == EventKind.Birth
```

**Action Items:**
- [ ] Replace `event.uniqueId()` with `event.kind()`
- [ ] Replace string comparisons with EventKind enums

---

### 7.3 Fix Emotion Construction
**Files:** Test files using Emotion

**Current Pattern:**
```python
emotion = Emotion(kind=RelationshipKind.Conflict, ...)  # Missing event?
```

**New Pattern:**
```python
event = Event(
    person=person1,
    kind=EventKind.Shift,
    relationshipTargets=[person2],
)
scene.addItem(event)

emotion = Emotion(event=event, target=person2, kind=RelationshipKind.Conflict)
scene.addItem(emotion)
```

**Action Items:**
- [ ] Update all Emotion() calls to include `event=` parameter
- [ ] Create corresponding Event objects for emotions
- [ ] Add both event and emotion to scene explicitly

---

## PHASE 8: Model/View Updates 🟢

Update models to work with new structure.

### 8.1 Update PersonPropertiesModel Event Handling
**File:** `pkdiagram/models/personpropertiesmodel.py:77-106`

**Current Code:** Uses `event.uniqueId()` strings

**New Code:**
```python
def onEventProperty(self, prop):
    if prop.name() == "dateTime":
        if prop.item.kind() == EventKind.Birth:
            self.refreshProperty("birthDateTime")
        elif prop.item.kind() == EventKind.Adopted:
            self.refreshProperty("adoptedDateTime")
        elif prop.item.kind() == EventKind.Death:
            self.refreshProperty("deceasedDateTime")
    # ... etc
```

**Action Items:**
- [ ] Replace `uniqueId()` with `kind()` in PersonPropertiesModel
- [ ] Replace string comparisons with EventKind enums

---

### 8.2 Update MarriagePropertiesModel Event Handling
**File:** `pkdiagram/models/marriagepropertiesmodel.py:40-50`

**Current Code:** Uses `event.uniqueId()` strings

**Action Items:**
- [ ] Replace `uniqueId()` with `kind()` in MarriagePropertiesModel
- [ ] Replace string comparisons with EventKind enums

---

### 8.3 Remove EmotionPropertiesModel Date Editors
**File:** `pkdiagram/models/emotionpropertiesmodel.py`

**Current Code:** Has date/time properties that should be on Event

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

**Action Items:**
- [ ] Remove date/time properties from EmotionPropertiesModel
- [ ] Add link to edit Event instead
- [ ] Update QML to show Event properties via link

---

### 8.4 Update SearchModel
**File:** `pkdiagram/models/searchmodel.py:118`

**Current Code:**
```python
def shouldHide(self, event):
    """Search kernel."""
    nullLoggedDate = bool(
        not event.loggedDateTime() or event.loggedDateTime().isNull()
    )
```

**Ensure:** Type hint shows this expects Event, not TimelineRow:
```python
def shouldHide(self, event: Event) -> bool:
    """Determine if event should be hidden based on search criteria."""
    # ... existing logic ...
```

**Action Items:**
- [ ] Add type hints to SearchModel.shouldHide()
- [ ] Ensure it works with Event objects (not TimelineRow)

---

## PHASE 9: Scene Data Format 🟢

Update Scene serialization format.

### 9.1 Update Scene.write()
**File:** `pkdiagram/scene/scene.py`

**Current Format:**
```json
{
  "items": [...]  // Mixed people, marriages, emotions
}
```

**New Format:**
```json
{
  "people": [...],
  "events": [...],  // NEW: top-level events
  "marriages": [...],
  "emotions": [...],
  "layerItems": [...],
  "layers": [...]
}
```

**Action Items:**
- [ ] Update `Scene.write()` to separate events from other items
- [ ] Create `data["events"]` array
- [ ] Remove events from `data["people"]` and `data["marriages"]`

---

### 9.2 Update Scene.read()
**File:** `pkdiagram/scene/scene.py`

**Two-Phase Loading (per CLAUDE.md):**
```python
def read(self, data, byId):
    # Phase 1: Instantiate all items with ID map
    for event_chunk in data.get("events", []):
        event = Event(id=event_chunk["id"])
        byId[event.id] = event
        self._events.append(event)

    # ... instantiate people, marriages, emotions ...

    # Phase 2: Resolve dependencies
    for event in self._events:
        event.read(event_chunk, byId)  # Sets event.person via byId lookup
```

**Action Items:**
- [ ] Implement two-phase loading in Scene.read()
- [ ] Load events in phase 1
- [ ] Resolve event.person references in phase 2
- [ ] Handle backward compatibility with compat.py

---

## PHASE 10: QML/UI Updates 🟢

Update QML interfaces to work with new structure.

### 10.1 Update EventForm
**File:** `pkdiagram/resources/qml/EventForm.qml`

**Changes:**
- Add `event.includeOnDiagram` checkbox
- Add `event.color` picker
- Add link to edit Emotion if `kind == Shift`
- Show "Shift" instead of "Shift"

**Action Items:**
- [ ] Add UI controls for new Event properties
- [ ] Add conditional link to EmotionProperties
- [ ] Update kind labels

---

### 10.2 Update EmotionProperties
**File:** `pkdiagram/resources/qml/PK/EmotionProperties.qml`

**Changes:**
- Remove date/time editors (now on Event)
- Add link to edit start Event
- Disable isDateRange when not editing Emotion

**Action Items:**
- [ ] Remove date editors from EmotionProperties.qml
- [ ] Add "Edit Event" link button
- [ ] Update logic for isDateRange

---

### 10.3 Update PersonProperties
**File:** Per FLATTENING_EVENTS.md

**Changes:**
- Remove dateTime editors (now on Event, edited via Timeline or EventForm)

**Action Items:**
- [ ] Remove birth/death/adopted date editors from PersonProperties
- [ ] Add links to edit events via Timeline or EventForm

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

### 12.2 Handle Marriage Events
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

### 12.3 Event Validation
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

## APPENDIX: Original Analysis Issues

### Issue Summary from Initial Analysis

**From First Response:**

1. ✅ Event.kind initialization - **Addressed in Phase 1.1**
2. ✅ Dual event hierarchy (Person._events vs Scene._events) - **Addressed in Phase 2**
3. ✅ Emotion-Event relationship confusion - **Addressed in Phase 4**
4. ✅ Event.endDateTime vs Emotion start/end - **Addressed in Phase 3 (TimelineRow)**
5. ✅ Missing Scene event management - **Addressed in Phase 1.3**
6. ✅ EventKind vs uniqueId - **Addressed in Phase 5**
7. ✅ Emotion property duplication - **Addressed in Phase 4.3**
8. ✅ Test infrastructure breaks - **Addressed in Phase 7**
9. ✅ Data migration incomplete - **Addressed in Phase 6**
10. ✅ TimelineModel phantom events - **Addressed in Phase 3**

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

## Progress Tracking

**Current Status:** Planning phase complete, ready for implementation

**Next Steps:**
1. Start with Phase 1 (Critical Blockers)
2. Run tests after each phase
3. Commit working state after each phase completes

**Estimated Effort:**
- Phase 1: 4 hours (blockers)
- Phase 2: 6 hours (remove caches)
- Phase 3: 4 hours (TimelineRow)
- Phase 4: 3 hours (Emotion cleanup)
- Phase 5: 2 hours (EventKind)
- Phase 6: 8 hours (compat.py - CRITICAL)
- Phase 7: 4 hours (tests)
- Phase 8-13: 10 hours (polish)

**Total:** ~40 hours of focused work

---

## Testing Strategy

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

**END OF TODO**
