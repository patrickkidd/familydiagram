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

### 1.2 Emotion Constructor Crash
**File:** `pkdiagram/scene/emotions.py:1206-1233`

**Problem:** `Emotion.__init__()` requires `event: Event` but `event` might be None during construction.

**Current Code:**
```python
def __init__(self, target: Person, event: Event | None = None, kind: RelationshipKind | None = None):
    self._event: Event | None = event
    # Later...
    if not self.isDyadic() and event.person():  # CRASH if event is None!
        self.setParentItem(event.person())
```

**Solution:**
```python
def __init__(self, target: Person, event: Event, kind: RelationshipKind, **kwargs):
    if not event:
        raise TypeError("Emotion() requires event= argument")
    if not kind:
        raise TypeError("Emotion() requires kind= argument")

    super().__init__(kind=kind.value, **kwargs)
    self._event = event
    self._target = target

    # Safe now:
    if not self.isDyadic() and self._event.person():
        self.setParentItem(self._event.person())
```

**Action Items:**
- [ ] Make `event` and `kind` required parameters in `Emotion.__init__()`
- [ ] Update all `Emotion()` calls to include both parameters
- [ ] Add assertions to validate event.kind() == EventKind.VariableShift

---

### 1.3 Scene Event Signal Wiring
**File:** `pkdiagram/scene/scene.py`

**Problem:** Scene declares `eventAdded/eventRemoved` signals but never emits them when events are added via `addItem()`.

**Current Code:**
```python
# Scene declares signals:
eventAdded = pyqtSignal(Event)
eventRemoved = pyqtSignal(Event)

# But addItem() doesn't emit them:
def addItem(self, item, undo=False):
    # ... adds to scene ...
    # Missing: if item.isEvent: self.eventAdded.emit(item)
```

**Solution:**
```python
def addItem(self, item, undo=False):
    # ... existing code ...

    # Add type-specific signals
    if item.isPerson:
        self._people.append(item)
        self.personAdded.emit(item)
    elif item.isEvent:
        self._events.append(item)
        # Notify person this event pertains to them
        if item.person and hasattr(item.person, 'onEventAdded'):
            item.person.onEventAdded(item)
        self.eventAdded.emit(item)
    elif item.isEmotion:
        self._emotions.append(item)
        self.emotionAdded.emit(item)
    # etc...
```

**Action Items:**
- [ ] Update `Scene.addItem()` to emit `eventAdded` signal
- [ ] Update `Scene.removeItem()` to emit `eventRemoved` signal
- [ ] Update `Scene.addItem()` to call `item.person.onEventAdded(item)`
- [ ] Update `Scene.removeItem()` to call `item.person.onEventRemoved(item)`
- [ ] Connect `TimelineModel` to `scene.eventAdded[Event]` signal

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
        event.kind() == EventKind.VariableShift
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
    kind=EventKind.VariableShift,
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
            chunk["kind"] = EventKind.VariableShift.value
        else:
            log.warning(f"Unknown uniqueId: {uid}, defaulting to VariableShift")
            chunk["kind"] = EventKind.VariableShift.value

        del chunk["uniqueId"]
```

**Action Items:**
- [ ] Implement uniqueId → kind migration in compat.py
- [ ] Map all old uniqueId strings to EventKind enums
- [ ] Set blank/CustomIndividual to EventKind.VariableShift (per CLAUDE.md)
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
            event_chunk["kind"] = EventKind.VariableShift.value
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
    kind=EventKind.VariableShift,
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
- Add link to edit Emotion if `kind == VariableShift`
- Show "Shift" instead of "VariableShift"

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

### 11.3 Update RemoveItems Command
**File:** `pkdiagram/scene/commands.py`

**Ensure:** RemoveItems properly removes events from Scene._events

**Action Items:**
- [ ] Verify RemoveItems calls Scene.removeItem() which handles events
- [ ] Test undo/redo with event removal

---

## PHASE 12: Edge Cases & Polish 🟢

### 12.1 Handle Orphaned Events
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

    elif self.kind() == EventKind.VariableShift:
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
