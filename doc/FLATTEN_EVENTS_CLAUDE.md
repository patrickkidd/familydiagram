I am in the middle of a major refactor of the fundamental data model and object
  hierarchy of this app. So this is an architecture-level change. I am
  flattening the relationship of Person/Marriage/Emotion and Event, making
  Events a top-level Item instead of always associating it with either a Person,
  Marriage, or Event. This refactor is so big and deep that it is hard to keep
  it all in my head. I have been taking notes in @doc/FLATTENING_EVENTS.md, but
  there are many changes all over the repo that are hard to keep track of. The
  last commit 235dc56934f025665f80134ff9d8beb62e393a7d is a progress commit, so
  it is incomplete. I expect many, many exceptions running this code and
  executing tests. In fact, many of the tests probably have logical errors now
  too that will need to be fixed.

  --------------------------------------------------------------------------

  Analyze the changes in the last commit to understand what is being attempted, and look and think very deeply about potential problems in the changes to speed up completing this massive change.
  Point out issues, don't actually make the changes on disk.

  Critical Architecture Issues in Event Flattening Refactor

  1. Event.kind Property Initialization (BLOCKER)

  File: pkdiagram/scene/event.py:222

  Problem: Event's kind() method tries to convert None to EventKind, causing immediate crashes:
  def kind(self) -> EventKind:
      return EventKind(self.prop("kind").get())  # Crashes when prop is None

  Root Cause: The kind property has no default value but Event.__init__() always calls updateDescription() → getDescriptionForKind(self.kind()) which fails when kind is None.

  Impact: Every Event creation without an explicit kind= argument fails immediately. Affects ~90% of test code.

  ---
  2. Dual Event Hierarchy Confusion

  Files: event.py, emotions.py, person.py, marriage.py

  Problem: Events now have TWO conflicting ownership models:
  1. Old model: event.person (Person/Marriage own the event via _events list)
  2. New model: Scene owns all events via scene._events

  Evidence:
  - Event._do_setPerson() still calls person._onAddEvent(self)
  - Person._events and Marriage._events still exist
  - But TimelineModel._refreshRows() now uses scene.events() instead
  - Scene has eventAdded/eventRemoved signals but Person/Marriage also track their own events

  Impact:
  - Data duplication/desync between Scene._events and Person._events
  - Events might exist in Scene but not in their person's list or vice versa
  - Undo/redo will break because old commands manipulate Person._events not Scene._events

  ---
  3. Emotion → Event Relationship Inversion

  Files: emotions.py:1270-1283, event.py:481-505

  Problem: Circular/confused relationship:
  - Emotion.__init__() expects an event: Event parameter and stores self._event
  - Emotion.person() returns self._event.person() (line 1655)
  - But Event.emotions() tries to CREATE emotions from relationship data (line 481-505)
  - Event.setEvent() asserts the event has matching kind/relationship (line 1280-1282)

  Architectural Confusion:
  - Is Emotion a wrapper around an Event (old way)?
  - Or is Event the primary object that spawns Emotions (new way)?
  - Code has BOTH patterns mixed together!

  ---
  4. Event.endDateTime vs Emotion Start/End Events

  Files: event.py:23, emotions.py, timelinemodel.py:142-153

  Problem: Events now have endDateTime property (line 23) but:
  - Emotions used to have separate startEvent and endEvent objects
  - TimelineModel._ensureEvent() tries to create synthetic "end events" from event.endDateTime() (line 142-153)
  - But there's no clear migration path from the old two-event model
  - Emotion code still references non-existent emotion.startEvent.dateTime() in multiple places

  Impact: All Emotion date range logic is broken. Tests referencing emotion start/end events will fail.

  ---
  5. Missing Scene Event Management

  File: scene.py

  Problem: Scene declares eventAdded/eventRemoved signals (line 135-137) but:
  - No visible Scene.addEvent() or Scene.removeEvent() methods
  - Events are added via generic Scene.addItem() which doesn't distinguish event types
  - No code connects events to Scene._events list during add/remove
  - TimelineModel expects scene.eventAdded[Event].connect() but Scene might not emit these

  Missing Infrastructure:
  # These should exist but don't:
  def Scene._onAddEvent(self, event):
      self._events.append(event)
      self.eventAdded.emit(event)

  def Scene._onRemoveEvent(self, event):
      self._events.remove(event)
      self.eventRemoved.emit(event)

  ---
  6. EventKind vs uniqueId Confusion

  Files: Multiple

  Problem: Massive search/replace changed:
  - event.uniqueId() → event.kind()
  - But uniqueId was a STRING like "birth", "married", "variable-shift"
  - While EventKind is an ENUM with values like EventKind.Birth
  - Code compares strings to enums in many places

  Examples:
  - event.py:327: elif kind == "moved": (string comparison with EventKind)
  - marriage.py:64: status in (EventKind.Separated.value, EventKind.Divorced.value) (mixing enum values with EventKind)

  ---
  7. Emotion Property Duplication

  Files: emotions.py:1273-1278, event.py:33-40

  Problem: Emotion intensity is stored in TWO places:
  # In Event:
  {"attr": "relationshipIntensity", "type": int, "default": util.DEFAULT_EMOTION_INTENSITY}

  # In Emotion:
  {"attr": "intensity", "type": int, "default": util.DEFAULT_EMOTION_INTENSITY}

  Then Emotion.intensity() returns self._event.relationshipIntensity() (line 1275), creating circular dependency.

  Similar duplications:
  - Emotion.notes vs Event.notes
  - Emotion.color vs Event.color
  - Emotion.kind vs Event.relationship()

  ---
  8. Test Infrastructure Breaks

  Problem: Tests create Events with old patterns:
  event = Event(person)  # Crashes - no kind specified
  event = Event(person, kind=EventKind.Birth)  # Works but person param is wrong position

  Required Changes:
  - All Event() calls need kind= parameter
  - Constructor signature changed: Event(person=None, ...) means person is now optional/keyword-only
  - Tests using event.uniqueId() need to change to event.kind().value

  ---
  9. Data Migration (Compatibility) Incomplete

  File: models/compat.py:291

  Problem: Comment says # Event. with no implementation. The TODO notes show many migrations needed:
  - Marriage.events → Scene.events
  - Person.Events → Scene.events
  - Emotion.events → Scene.events
  - Emotion.startEvent['emotionStartEvent'] → Emotion.startEvent['variable-shift']
  - Emotion.isDateRange → Event.endDateTime
  - Emotion.notes → Event.notes
  - etc.

  Impact: Old saved files will fail to load or corrupt data.

  ---
  10. TimelineModel Event Row Management

  File: timelinemodel.py:124-169

  Problem: _ensureEvent() creates phantom "end events":
  if event.endDateTime():
      endEvent = Event(dateTime=event.endDateTime(), description=f"{event.kind().name} ended")
      self._endEvents[event] = endEvent  # Not added to scene!
      self._events.append(endEvent)

  These synthetic events:
  - Are created outside the Scene
  - Have no scene() parent
  - Will break when code calls event.scene()
  - Duplicate the old Emotion.endEvent pattern

  ---
  Architectural Decision Needed

  The refactor is trying to do TWO incompatible things:

  Option A: Events are top-level Scene objects
  - Remove Person._events and Marriage._events
  - Move all event management to Scene
  - Events reference their person via event.person but Person doesn't own them

  Option B: Events are owned by Person/Marriage/Emotion
  - Keep the current _onAddEvent() infrastructure
  - Scene._events is just an index/cache
  - Events live and die with their owners

  Current code is stuck halfway between both, causing cascading failures.

  ---
  Immediate Blockers to Fix (In Order)

  1. Event.kind default value - Set to None and handle in kind() method
  2. Emotion.person() crash - _event might be None in constructor
  3. Scene event signals - Wire up Scene to actually emit eventAdded/eventRemoved
  4. TimelineModel synthetic events - Remove or properly integrate with Scene
  5. Test fixtures - Update all Event() calls to include kind=

  Would you like me to create an action plan to fix these issues systematically?


--------------------------------------------------------------------------

  I have updated the `**Scene System**` section of CLAUDE.md with clarifications based on your last comments. Questions to continue this evalution:
- Should I abandon event reference caching like Person._events, Emotion._event, Marriage._events for efficient QGraphicsScene/View drawing and other UI speed, and instead focus on clear obejct
 ownership in Scene._itemCache and the cache Scene._events? If the performance difference would be negligable then I would certainly like to have a clear object model hierarchy.
- Event._do_setPerson() and person._onAddEvent(self) are there for when the person field of the event is changed. Or is this unnecessary?
- Right now I have the fields person, spouse, child, targets, and triangles on Event, but maybe there is a simpler way to store these attributes associated with an Event without such a 
categorical model? If not then just leave it.
- TimelineModel creates dummy Event's to show, select and delete Event.endDateTime() in a UI. I am open to ideas for a cleaner implementation. 
- Emotion is many-to-1 to Event, and Emotion always has a target person which is one of the Person references in Emotion.relationshipTargets. I tried to clean this relationship up by adding a 
canonical Emotion factory in the Event, especially since in the future I may lazily load emotions until Scene.currentDateTime requires that they be shown. But perhaps this causes confusion?

--------------------------------------------------------------------------


---
  1. Should you abandon reference caching (Person._events, etc.)?

  SHORT ANSWER: Yes, abandon the caches. Performance will be negligible.

  ANALYSIS:

  Current Caching Pattern:
  - Person._events - list of events
  - Marriage._events - list of events
  - Emotion._event - single event reference

  Performance Concerns:
  # With cache:
  person.events()  # O(1) - just return self._events

  # Without cache (query Scene):
  def events(self):
      return self.scene().find(lambda e: e.person == self, types=Event)  # O(n)

  But consider:
  1. How often is this called per frame? Looking at your code:
    - Person.updateEvents() - called on event add/remove (rare)
    - TimelineModel._refreshRows() - already uses scene.events() in new code
    - Most UI doesn't iterate all person events frequently
  2. Scene._events is already indexed: You have Scene._events = [], so:
  # Efficient O(n) where n = total events, with early exit:
  def Person.events(self):
      return [e for e in self.scene()._events if e.person == self]
  3. PyQt/QGraphicsScene already caches items internally via spatial indexing. Adding your own cache on top creates synchronization bugs.

  RECOMMENDATION:
  # In Person:
  def events(self) -> list[Event]:
      """Query scene for events owned by this person."""
      if not self.scene():
          return []
      return [e for e in self.scene()._events if e.person == self]

  # Remove:
  # - Person._events
  # - Person._onAddEvent()  
  # - Person._onRemoveEvent()
  # - Same for Marriage

  # Keep Scene._events as the SINGLE source of truth

  Migration path:
  - Scene already has _events, _people, _marriages, _emotions as authoritative lists
  - When deserializing: Scene.read() populates Scene._events, then each Event.read() sets event.person
  - No duplicate tracking needed

  ---
  2. Is Event._do_setPerson() and person._onAddEvent(self) necessary?

  SHORT ANSWER: Only if you keep the cache. If you remove Person._events, you can simplify.

  CURRENT FLOW:
  Event._do_setPerson(person):
      was = self.person
      self.person = person
      if was:
          was._onRemoveEvent(self)  # Update old person's cache
      if person:
          person._onAddEvent(self)  # Update new person's cache

  SIMPLIFIED FLOW (no cache):
  Event._do_setPerson(person):
      was = self.person
      self.person = person
      # Notify person for geometry updates
      if was:
          was.updateEvents()  # Recalc variables database
      if person:
          person.updateEvents()
      # Notify scene
      if self.scene():
          self.scene().eventChanged.emit(self)

  KEEP THIS PATTERN: Even without caching, Person needs to know when events change for:
  - Person.updateEvents() - updates variables database (anxiety, functioning, etc.)
  - Person.updateDetails() - birth/death dates affect name display
  - Person.updateGeometry() - adopted status affects visual

  RECOMMENDATION:
  # Keep setPerson() for notifications, but remove _onAddEvent caching:
  def Event._do_setPerson(self, person):
      was = self.person
      self.person = person

      # Update geometry/details on affected people
      if was and hasattr(was, 'updateEvents'):  # Person or Marriage
          was.updateEvents()
          was.updateGeometry()
      if person and hasattr(person, 'updateEvents'):
          person.updateEvents()
          person.updateGeometry()

      # Standard property change notifications
      self.updateDescription()
      self.updateNotes()
      self.updateParentName()

  ---
  3. Simplify Event's person fields (person, spouse, child, targets, triangles)?

  CURRENT MODEL:
  Event.registerProperties([
      {"attr": "personName"},          # Display name
      {"attr": "spouse", "type": int},  # ID for pair-bond events
      {"attr": "child", "type": int},   # ID for birth/adoption events
      {"attr": "relationshipTargets", "type": list},  # IDs for emotion targets
      {"attr": "relationshipTriangles", "type": list}, # IDs for triangles
  ])

  # Plus:
  self.person  # Main person (not a property!)

  PROBLEMS:
  1. Redundancy: person vs personName (one is ref, one is cached string)
  2. Categorical rigidity: Why is spouse special vs relationshipTargets[0]?
  3. Marriage events are weird: Do they set person to Marriage object? Or to one of the spouses?

  ANALYSIS OF USE CASES:

  | Event Type              | Person          | Spouse | Child | Targets   | Triangles   |
  |-------------------------|-----------------|--------|-------|-----------|-------------|
  | Birth                   | mother/father?  | -      | baby  | -         | -           |
  | Adopted                 | adoptive parent | -      | child | -         | -           |
  | Death                   | deceased        | -      | -     | -         | -           |
  | Married                 | -               | -      | -     | -         | -           |
  | Shift (Emotion) | subject         | -      | -     | target(s) | triangle(s) |

  THE CONFUSION: Marriage events don't have a single "person" - they have TWO people!

  RECOMMENDATION - OPTION A (Keep categorical):
  # If event types truly have different semantics:
  Event.registerProperties([
      # Generic fields:
      {"attr": "people", "type": list},  # List of ALL person IDs involved

      # Semantic helpers (computed properties):
      def person(self):
          """Primary person for this event."""
          people = self.people()
          return people[0] if people else None

      def targets(self):
          """For relationship events, the non-primary people."""
          people = self.people()
          return people[1:] if len(people) > 1 else []
  ])

  RECOMMENDATION - OPTION B (Fully generic):
  # Store roles explicitly:
  Event.registerProperties([
      {"attr": "participants", "type": list},
      # Format: [{"role": "subject", "id": 123}, {"role": "target", "id": 456}]
  ])

  # Access via:
  def person(self):
      """Get person with role='subject'."""
      for p in self.participants():
          if p["role"] == "subject":
              return self.scene().find(id=p["id"])
      return None

  MY PREFERENCE: Option A - keeps code readable without over-engineering. Marriage events can set people=[spouse1_id, spouse2_id].

  ---
  4. TimelineModel dummy Events for endDateTime - cleaner solution?

  CURRENT APPROACH:
  def TimelineModel._ensureEvent(event: Event):
      self._events.add(event)

      if event.endDateTime():
          # Create phantom event!
          endEvent = Event(
              dateTime=event.endDateTime(),
              description=f"{event.kind().name} ended"
          )
          self._endEvents[event] = endEvent
          self._events.add(endEvent)  # Not in scene!

  PROBLEMS:
  - Phantom events have no scene()
  - Phantom events aren't in Scene._events
  - Selecting phantom event in timeline UI breaks
  - Deleting phantom event tries to remove from scene (crash)

  CLEANER OPTION 1: Timeline-specific data class
  @dataclass
  class TimelineRow:
      """Presentation object for timeline - NOT a scene Event."""
      dateTime: QDateTime
      description: str
      source_event: Event | None  # Reference to real event
      is_end_marker: bool = False

      def kind(self):
          return self.source_event.kind() if self.source_event else None

      def person(self):
          return self.source_event.person() if self.source_event else None

  # In TimelineModel:
  self._rows = SortedList()  # TimelineRow objects, not Events

  def _ensureEvent(self, event: Event):
      # Start row
      self._rows.add(TimelineRow(
          dateTime=event.dateTime(),
          description=event.description(),
          source_event=event,
      ))

      # End row (if needed)
      if event.endDateTime():
          self._rows.add(TimelineRow(
              dateTime=event.endDateTime(),
              description=f"{event.kind().name} ended",
              source_event=event,
              is_end_marker=True,
          ))

  CLEANER OPTION 2: Virtual rows via index math
  # Keep events, calculate end rows on-the-fly:
  def rowCount(self):
      count = len(self._events)
      for event in self._events:
          if event.endDateTime():
              count += 1  # Phantom row
      return count

  def eventForRow(self, row):
      real_index = row
      for i, event in enumerate(self._events[:row]):
          if event.endDateTime():
              real_index -= 1  # Adjust for phantom rows before this

      event = self._events[real_index]
      # If this row is the "end" phantom...
      if self._isEndRow(row):
          return None  # Signal to show end date
      return event

  MY RECOMMENDATION: Option 1 (TimelineRow wrapper class)
  - Clean separation: Timeline is a VIEW on Events, not the events themselves
  - Easy to handle selection (check row.source_event)
  - Easy to handle deletion (delete row.source_event, let timeline refresh)
  - No phantom objects polluting the data model

  ---
  5. Emotion many-to-1 Event relationship - is the factory pattern confusing?

  CURRENT DESIGN:
  # Emotion.__init__:
  def __init__(self, target: Person, event: Event, kind: RelationshipKind):
      self._event = event
      self._target = target
      # Emotion delegates to event for dateTime, intensity, etc.

  # Event.emotions() factory:
  def Event.emotions(self) -> list[Emotion]:
      if self.relationship():
          for target in self.relationshipTargets():
              emotion = Emotion(kind=self.relationship(), target=target, event=self)
              self._emotions.append(emotion)
      return self._emotions

  CONFUSION POINTS:
  1. Who owns whom? Is Emotion a wrapper around Event, or Event a data bag for Emotions?
  2. Lazy loading: If emotions are created on-demand via Event.emotions(), when do they get added to Scene?
  3. Multiple targets: If one Event has 3 targets, do you create 3 Emotion objects? Are they all in Scene._emotions?

  CLEARER MODEL - OPTION A (Emotion owns Event):
  # Event is just data:
  event = Event(
      kind=EventKind.Shift,
      dateTime=...,
      relationship=RelationshipKind.Conflict,
      relationshipTargets=[person2, person3],
  )
  scene.addItem(event)  # Just stores data, no visuals

  # Emotion is the visual/interactive object:
  for target in event.relationshipTargets():
      emotion = Emotion(event=event, target=target)
      scene.addItem(emotion)  # Adds to scene, creates visuals

  # Query:
  def Event.emotions(self):
      """Find emotions that reference this event."""
      return [e for e in self.scene()._emotions if e.event() == self]

  CLEARER MODEL - OPTION B (Event-centric, no Emotion objects):
  # Event stores everything, Emotion is just a QGraphicsItem view:
  event = Event(
      kind=EventKind.Shift,
      relationship=RelationshipKind.Conflict,
      person=person1,
      relationshipTargets=[person2, person3],
  )

  # Scene creates visuals on-demand:
  def Scene.emotionItemsFor(event: Event):
      """Create QGraphicsPathItems for each emotion in this event."""
      items = []
      for target in event.relationshipTargets():
          item = EmotionGraphicsItem(event, target)  # Just a view
          items.append(item)
      return items

  MY RECOMMENDATION: Option A - keeps Emotion as a first-class object because:
  - Emotions have their own selection state, hover state, fanned-out state
  - Emotions have notes/color that might be per-relationship, not per-event
  - Your existing Scene._emotions infrastructure expects Emotion objects

  CLARIFICATION NEEDED:
  # Should this:
  event = Event(
      kind=EventKind.Shift,
      relationship=RelationshipKind.Conflict,
      relationshipTargets=[alice, bob, charlie],
  )

  # Create 3 emotions automatically when added to scene?
  # Or require explicit creation:
  scene.addItem(event)
  for target in [alice, bob, charlie]:
      scene.addItem(Emotion(event=event, target=target))

  I suggest explicit creation to avoid surprises, and remove the Event.emotions() factory.

  ---
  SUMMARY & RECOMMENDATIONS

  | Question                   | Recommendation             | Rationale                                    |
  |----------------------------|----------------------------|----------------------------------------------|
  | 1. Abandon caches?         | YES                        | Negligible perf cost, massive simplification |
  | 2. Keep setPerson()?       | YES (but simplify)         | Needed for updateEvents/updateGeometry       |
  | 3. Simplify person fields? | YES - use people: list     | More flexible, handles Marriage events       |
  | 4. TimelineRow wrapper?    | YES - separate data class  | Clean separation of concerns                 |
  | 5. Emotion factory?        | REMOVE - explicit creation | Clearer ownership, no surprises              |

  ARCHITECTURAL DECISION:

  ✅ Scene is authoritative for all items (_events, _people, _emotions, etc.)✅ Items reference each other via properties (event.person, emotion.target)✅ No duplicate caching (except
  read-only computed properties)✅ Views create presentation objects (TimelineRow) without polluting model

  This gives you a clear ownership hierarchy and makes undo/redo trivial (just mutate Scene lists).

  Would you like me to draft code snippets showing how to implement these recommendations?