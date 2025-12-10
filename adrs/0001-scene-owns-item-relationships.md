# ADR-0001: Scene Owns Item Relationship Logic

**Status:** Accepted

**Date:** 2024 (formalized 2025-12-09)

**Deciders:** Patrick

## Context

The Family Diagram app has a complex data model with Person, Event, Marriage,
Emotion, and other Item types that have interdependencies. These items need:
- Cascade delete (removing Person removes their Events, Emotions, Marriages)
- Implicit item creation (creating Event with relationship creates Emotion)
- Reference resolution (circular references between items)

The question: where should this relationship logic live?

Two competing locations existed:
1. **QUndoCommand subclasses** (AddItem, RemoveItems, etc.) - where user actions originate
2. **Scene** - the authoritative container for all Items

## Decision

**Scene is the single source of truth for all Item relationship logic.**

QUndoCommand classes ONLY:
1. Predict what changes Scene will make (for undo metadata)
2. Store metadata required to undo/redo
3. Execute reversion of changes

Scene owns:
- All cascade delete logic via `_do_removeItem()` and helpers (`_removePerson`, `_removeEvent`, etc.)
- All implicit item creation
- All relationship maintenance
- Query methods (`eventsFor`, `emotionsFor`, `marriageFor`, etc.)

## Consequences

### Positive
- Single source of truth prevents logic duplication
- Consistent behavior whether changes are undoable or not
- QUndoCommand classes stay simple (state capture/restore only)
- Easier to reason about what happens when an item is added/removed

### Negative
- Scene becomes a large class with many responsibilities
- Must be careful that QUndoCommand predictions match Scene behavior

### Risks
- If Scene behavior changes, QUndoCommand undo metadata could become stale
- Tight coupling between Scene helpers and QUndoCommand classes

## Implementation Notes

Cascade delete helpers in Scene:
- `Scene._removePerson()` → cascades to events, emotions, marriages
- `Scene._removeEvent()` → cascades to emotions
- `Scene._removeMarriage()` → handles marriage cleanup
- `Scene._removeEmotion()` → handles emotion removal

Item reference getters (e.g. `Event.spouse()`) that require `self.scene()` should
fail with AttributeError if scene is None - calling code must ensure Item is
added to scene first.
