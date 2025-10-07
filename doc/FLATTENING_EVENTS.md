Fix Event/Emotion relationship: https://alaskafamilysystems.atlassian.net/browse/FD-244
=====================================

Spec
---------------------------------------------
- Two major ways Emotions / Person gets created:
  - Drawing like a chalk board without an Event
  - Created to represent a dated Event
- Remove all Person/Marriage/Emotion event references for computer properties,
  Scene as single source of truth
  - Remove Person.onAddEvent, etc.
- Have Person.updateEvents() only listen for Shift since it only updates self.variablesDatabase?
- Add TimelineRow dataclass instead of dummy events; _ensureEvent(adds 1 or 2 for dateTime & endDateTime)
  ```
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
  ```
- Remove dateTime editors from PersonProperties in favor of a button to edit those singleton events, just like EmotionProperties.



Edit events with EventForm
------------------------------------
- event.includeOnDiagram
- Event.color
- Add link to edit emotion if kind == Shift
- Remove event field edits from EmotionProperties, just add links to start event
- Disable isDateRange when not editing Emotion's
- Legacy births, leave person/spouse empty if none exist if possible
- Shift -> Shift
- Storing EventKind on Event.uniqueId or new Event.kind?
  - Going to end up replacing `uniqueId` with `kind` anyway?
  - But still duplicates data?
- Update person geometry/details when birth/adopted/death events change
- delete commands.SetEmotionPerson
- Check that updating pairbond events update Marriage details (Marriage.onEventProperty removed)
- ITEM_MODE -> EventKind | RelationshipKind
  - Emotion
- Remove Emotion.notes and in EmotionProperties
- Double check undo/redo works for adding emotions from Scene.addItem
- Double check can delete event and emotion still remains, and vice-versa (is that even what we want?)
- Scene data:
  - data["items"] -> data["events"]
  - data["items"] -> data["people"]
- compat
  - CustomIndividual -> 'variable-shift' (kind can never be `None`)
  - [in &.read()] Marriage.events, Person.Events, Emotion.events -> Scene.events
  - Event.kind is None -> kind = Shift
  - Emotion.startEvent['emotionStartEvent'] -> Emotion.startEvent['variable-shift']
  - Emotion.isDateRange (isSingularDate()) -> Event.endEvent
  - Emotion.notes -> Emotion.event().notes
  - Emotion.kind -> RelationshipKind
  - Emotion.person_a -> Event.person
  - Emotion.person_b -> Emotion.target
  - Emotion.intensity -> Event.intensity


Create relationship field in add form
------------------------------------
- When setting R type, just change fields to match
- Re-use add form when editing event.
- Eliminate confusing R symbol event relationship
- Can add multiple events for different people, just choose how to show them
- Focus person field in PersonPicker on clear
- Event
  - Who
    - person
  - What
    - Bonded, Married, Separated, Divorced, Moved (isPairBond)
      - single (Spouse; optional=Moved)
    - Birth, Pregnancy, Adopted (isOffspring)
      - single (Spouse)
      - single (Child)
    - Shift
      - Summary
      - Symptom
      - Anxiety
      - Relationship (store emotion object, link events)
        - Conflict, Distance (Other(s))
        - Overfunctioning (Underfunctioner(s))
        - Underfunctioning (Overfunctioner(s))
        - Projection (Focused)
        - Cutoff (HIDDEN)
        - Triangle, to inside (Outside(s))
        - Triangle, to outside (Insides(s))
        - Toward (To)
        - Away (From)
        - DefinedSelf (Target(s))
      - Functioning
    - Death
  - When
    - Is Date Range (Disabled: isOffspring, isPairBond, Death)
  - Where
    - Location
  - How
    - Details
Testing
  - Make summary optional, default to "Variables: S,A,R" or something like that
- need labels or something for the symbols


