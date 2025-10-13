**Scene System**

This is the core data model / QGraphicsItem types (Person, Event, Marriage, etc.) with property system

- The Scene is the authoratative source for storing and querying Item objects.
However, Efficient diagram drawing requires caching references to Item
objects. Sometimes these references are circular.
- For example, sometimes Person needs to develop a dependency graph of
    ItemDetails, Emotion, etc for redraws when that Person is moved.
- Circular references are handled when loading the diagram file in two
    phases; 1) instantiate all the items with a map of their id's, then 2)
    resolve all dependencies via passing the map to each Item's read() method.
- There are two major ways that Person/Marriage/Emotion objects gets created,
which determines how instantiations and cascaded deletes work;
1) Drawing like a chalk board without an Event via Scene, where the scene
    "owns" the Item.
2) Created to represent a dated Event via EditForm, where the event "owns"
    the Item.
- When Emotion objects are associated with an event, they should never be
  created explicitly and then added to the scene because the scene creates them
  implicitly when an Event is created with `kind=EventKind.Shift` and
  `Event.relationship()` set.
- The Scene is the authoratitive source for querying Item relationships, e.g.
though eventsFor, emotionsFor, marriageFor, etc.
- Scene.find() takes special kwargs like `ids=`, `types=`, Scene.query
    matches Item property values.
- Item reference getters, e.g. `Event.spouse()`, that require `self.scene()`
    should never return None just because `self.scene()` is None, they should
    fail with an `AttributeError` on the return value of `self.scene()` and
    the calling code should be fixed to ensure the Item is added to the scene
    before using the getter.
- compat.py must set all Event.uniqueId's that are blank or 'CustomIndividual' to EventKind.VarableShift.value
- `Event` has mandatory `EventKind` as:
- `Bonded`, `Married`, `SeparatedBirth`, `Adopted`, `Moved`, `Separated`,
    `Divorced` are "PairBond" categories that reflect the pairbond/marriage's
    life cycle. All include a spouse and potentially a child.
- `Shift` category that indicates a change in the app's four key
    variables: (S)ymptom, (A)nxiety, (R)elationship and (F)unctioning.
    - R changes always occur in relation to one or more targets. 
    - R changes pertaining to triangles (`RelationShipKind.Inside`,
        `RelationshipKind.Outside`) also pertain to one or more other people
        to complete the triangle.
- `Death` only pertains to the Event's `person`.
- Item CRUD signals like personAdded, eventChanged, etc should only be added to
  the scene, not other Item classes.

## Separation of Concerns: Scene vs QUndoCommand

**Critical Architectural Rule**: The Scene object is the authoritative source for all logic required to maintain relationships between the Item objects it owns. QUndoCommand subclasses should ONLY:
1. Predict what changes Scene will make (for undo metadata)
2. Store any metadata required to undo/redo those changes
3. Execute the reversion of those changes

**What this means in practice**:
- Scene owns all cascade delete logic (e.g., removing Person cascades to Events, Emotions, Marriages)
- Scene owns all implicit item creation (e.g., creating Emotions when adding Events with relationships)
- Scene owns all relationship maintenance (e.g., updating references when items are added/removed)
- QUndoCommand classes (AddItem, RemoveItems, etc.) delegate to Scene._do_* methods
- QUndoCommand classes store metadata about what will change, NOT how to change it

**Example - Cascade Delete**:
- ❌ WRONG: RemoveItems.redo() implements cascade delete logic inline
- ✅ CORRECT: RemoveItems.redo() calls scene.removeItem(), which delegates to Scene._do_removeItem()
- ✅ CORRECT: Scene._do_removeItem() contains ALL cascade delete logic via helper functions:
  - Scene._removePerson() - cascades to events, emotions, marriages
  - Scene._removeEvent() - cascades to emotions
  - Scene._removeMarriage() - handles marriage cleanup
  - Scene._removeEmotion() - handles emotion removal

This separation ensures:
- Single source of truth for relationship logic (Scene)
- Consistent behavior whether changes are undoable or not
- QUndoCommand classes remain simple and focused on state capture/restore
- No duplicate logic between command classes and Scene