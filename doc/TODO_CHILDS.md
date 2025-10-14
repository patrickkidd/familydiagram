# TODO: Align ChildOf and MultipleBirth CRUD with Other Item Subclasses

This revised TODO incorporates your feedback: 
- No new signals unless directly used (omitted entirely here, as they're not specified as needed for your desktop app; add only if required for existing logic).
- Stick to instantiating objects and passing to `scene.addItem()` where possible, avoiding private convenience APIs like `_addChildOf` or `_addMultipleBirth`.
- Move `setParents` from `Person` to `Scene` as a public method (this acts as the entry point for creating/adding `ChildOf`, consistent with conventions like implicit `Emotion` creation in `addItem` for `Event`s).
- Remove all scattered APIs (e.g., `Person.children()`, `Person.parents()`, `MultipleBirth.members()` queries) to enforce `Scene` as the single source of truth.
- Keep `MultipleBirth` creation explicit (instantiate and `addItem`), but handle implicit linking/checks in `addItem` if siblings share parents (no auto-creation unless tied to rules).
- Ensure undo/redo reuses objects (store references in `QUndoCommand`s).
- Maintain separation: Cascades in `Scene._do_removeItem()`, queries in `Scene`, no duplication in commands.
- For loading, use `resolveDependencies` to handle circular refs.

Proceed sequentially. Update files like `pkdiagram/scene/scene.py`, `pkdiagram/scene/person.py`, `pkdiagram/scene/childof.py`, `pkdiagram/scene/multiplebirth.py`, and `pkdiagram/scene/commands.py`.

## Prerequisites
- Review existing `addItem()` logic (e.g., for `Event`, it implicitly creates `Emotion`s if `kind=EventKind.Shift`).
- Search codebase for calls to `Person.setParents()`, `Person.children()`, etc., and plan migrations.

## TODO Items

- [ ] **Step 1: Move setParents to Scene**  
  Remove `setParents` from `Person` in `person.py` (add a deprecation warning if needed for migration).  
  Add public `setParents` to `Scene` in `scene.py`, which instantiates `ChildOf` and calls `self.addItem(childOf)`. This adheres to the instantiation + `addItem` pattern while providing the moved API.  
  ```python:disable-run
  class Scene(...):
      def setParents(self, person, parents, adopted=False):
          if len(parents) != 2:
              raise ValueError("Exactly two parents required")
          if self.childOfFor(person):  # New query from Step 2; prevent duplicates
              raise ValueError("Person already has parents")
          childOf = ChildOf(child=person, parent1=parents[0], parent2=parents[1], adopted=adopted)
          self.addItem(childOf)  # Triggers any implicit logic in addItem (e.g., MB checks in later steps)
  ```  
  Migrate calls: Replace `person.setParents(parents)` with `person.scene().setParents(person, parents)`.

- [ ] **Step 2: Centralize Queries (Read) in Scene**  
  Add public query methods to `Scene` in `scene.py` for all ChildOf and MultipleBirth relationships. Use `self.query()` (assuming it exists for property matching).  
  Remove or deprecate scattered methods:  
  - In `person.py`: Remove `children()`, `parents()`, `siblings()` (or add warnings: `warnings.warn("Use scene.getChildren(self) instead")`).  
  - In `multiplebirth.py`: Remove direct `members()` access if it's a query; make it private if needed.  
  ```python
  class Scene(...):
      def childOfFor(self, person):
          return self.query(types=[ChildOf], child=person).first()
      
      def getParents(self, person):
          childOf = self.childOfFor(person)
          return [childOf.parent1, childOf.parent2] if childOf else []
      
      def getChildren(self, parent):
          childOfs = self.query(types=[ChildOf], parent1=parent) + self.query(types=[ChildOf], parent2=parent)
          return [co.child for co in childOfs]
      
      def getSiblings(self, person):
          childOf = self.childOfFor(person)
          if not childOf:
              return []
          childOfs = self.query(types=[ChildOf], parent1=childOf.parent1, parent2=childOf.parent2)
          return [co.child for co in childOfs if co.child != person]
      
      def multipleBirthFor(self, person):
          return self.query(types=[MultipleBirth], members__contains=person).first()
      
      def getMultipleBirthMembers(self, mb):
          return mb._members  # Private access if needed; or query self.query(types=[ChildOf], multipleBirth=mb) and map to children
      
      def multipleBirths(self):
          return self.query(types=[MultipleBirth])
  ```  
  Migrate codebase: Replace e.g., `person.children()` with `person.scene().getChildren(person)`.

- [ ] **Step 3: Enhance addItem for Implicit Logic**  
  Update `Scene.addItem()` in `scene.py` to handle ChildOf/MultipleBirth specifics (e.g., validate relationships, link to existing MultipleBirth if siblings share parents). No auto-creation of MultipleBirth; assume explicit instantiation.  
  ```python
  class Scene(...):
      def addItem(self, item):
          if isinstance(item, ChildOf):
              # Validate: Ensure child/parents exist in scene
              if not all([self.hasItem(item.child), self.hasItem(item.parent1), item.parent2 is None or self.hasItem(item.parent2)]):
                  raise ValueError("ChildOf relationships must reference existing scene items")
              # Check for existing MultipleBirth (implicit link, no create)
              siblings = self.getSiblings(item.child)
              if siblings:
                  mb = self.multipleBirthFor(siblings[0])
                  if mb:
                      item.setMultipleBirth(mb)  # Assume setter; add if needed
                      for sib in siblings:
                          sib_childOf = self.childOfFor(sib)
                          if sib_childOf:
                              sib_childOf.setMultipleBirth(mb)
          elif isinstance(item, MultipleBirth):
              # Validate members exist and share parents
              if not item.members:
                  raise ValueError("MultipleBirth requires members")
              first_childOf = self.childOfFor(item.members[0])
              if not first_childOf:
                  raise ValueError("MultipleBirth members must have ChildOf")
              for member in item.members[1:]:
                  childOf = self.childOfFor(member)
                  if not childOf or (childOf.parent1 != first_childOf.parent1 or childOf.parent2 != first_childOf.parent2):
                      raise ValueError("MultipleBirth members must share parents")
              # Link to ChildOfs
              for member in item.members:
                  childOf = self.childOfFor(member)
                  if childOf:
                      childOf.setMultipleBirth(item)
          super().addItem(item)  # Existing base logic
  ```

- [ ] **Step 4: Centralize Updates (Update)**  
  Keep setters on ChildOf/MultipleBirth (e.g., `setAdopted()`, `setOrder()`), but ensure they validate via Scene if needed (e.g., check scene() for relationships). No new signals.  
  For complex updates, add public Scene methods if used (e.g., `scene.updateMultipleBirthOrder(mb, new_order)`).  
  ```python
  # In childof.py
  class ChildOf(...):
      def setAdopted(self, value):
          super().setProperty('adopted', value)
          # No signal; add if used elsewhere
  
  # In multiplebirth.py
  class MultipleBirth(...):
      def setOrder(self, order):
          # Validate order matches members
          if len(order) != len(self.members):
              raise ValueError("Order must match members")
          super().setProperty('order', order)
  
  # In scene.py (if needed for complex update)
  class Scene(...):
      def updateMultipleBirthOrder(self, mb, new_order):
          mb.setOrder(new_order)
          # Any additional scene-level validation
  ```

- [ ] **Step 5: Centralize Deletion (Delete) with Cascades**  
  Extend `Scene._do_removeItem()` in `scene.py` for ChildOf/MultipleBirth. Update `_removePerson()` to integrate. Ensure reuse in undo/redo (commands store refs).  
  ```python
  class Scene(...):
      def _do_removeItem(self, item):
          if isinstance(item, Person):
              self._removePerson(item)  # Updated below
          elif isinstance(item, ChildOf):
              self._removeChildOf(item)
          elif isinstance(item, MultipleBirth):
              self._removeMultipleBirth(item)
          # ... other types
          super()._do_removeItem(item)  # Base removal
  
      def _removeChildOf(self, childOf):
          if childOf.multipleBirth:
              mb = childOf.multipleBirth
              mb._removeMember(childOf.child)  # Private; assume or add
              if not mb.members:
                  self._do_removeItem(mb)  # Cascade
          # Unlink any other refs
  
      def _removeMultipleBirth(self, mb):
          for member in mb.members:
              childOf = self.childOfFor(member)
              if childOf:
                  childOf.setMultipleBirth(None)
  
      # Update _removePerson
      def _removePerson(self, person):
          # ... existing (events, etc.)
          childOf = self.childOfFor(person)
          if childOf:
              self._removeChildOf(childOf)
          for co in [co for co in self.query(types=[ChildOf]) if co.parent1 == person or co.parent2 == person]:
              self._removeChildOf(co)
          mb = self.multipleBirthFor(person)
          if mb:
              self._removeMultipleBirth(mb)
          super()._removePerson(person)  # If exists
  ```

- [ ] **Step 6: Update QUndoCommand Subclasses for Object Reuse**  
  In `commands.py`, update `RemoveItems`, `AddItem` to store/reuse object refs (not recreate). Delegate to `Scene._do_removeItem()`.  
  ```python
  class RemoveItems(QUndoCommand):
      def __init__(self, items, ...):
          super().__init__()
          self.items = items
          self._affected_childofs = []
          self._affected_mbs = []
          # Predict and store refs
          scene = items[0].scene() if items else None
          for item in items:
              if isinstance(item, Person):
                  childOf = scene.childOfFor(item)
                  if childOf:
                      self._affected_childofs.append(childOf)
                  for co in [co for co in scene.query(types=[ChildOf]) if co.parent1 == item or co.parent2 == item]:
                      self._affected_childofs.append(co)
                  mb = scene.multipleBirthFor(item)
                  if mb:
                      self._affected_mbs.append(mb)
              elif isinstance(item, ChildOf):
                  self._affected_childofs.append(item)
                  if item.multipleBirth:
                      self._affected_mbs.append(item.multipleBirth)
              elif isinstance(item, MultipleBirth):
                  self._affected_mbs.append(item)
  
      def redo(self):
          for item in self.items:
              self.scene._do_removeItem(item)
  
      def undo(self):
          # Reuse stored objects
          for mb in reversed(self._affected_mbs):
              self.scene.addItem(mb)
          for childOf in reversed(self._affected_childofs):
              self.scene.addItem(childOf)
          for item in reversed(self.items):
              self.scene.addItem(item)
  ```  
  Similarly for `AddItem`: Store any affected (e.g., linked MB), reuse on undo.

- [ ] **Step 7: Handle Loading/Circular References**  
  Ensure `Scene.read()` in `scene.py` uses two phases. Add `resolveDependencies` to `ChildOf` and `MultipleBirth`.  
  ```python
  # In childof.py
  class ChildOf(...):
      def __init__(self, child=None, parent1=None, parent2=None, ...):
          self._child_id = child.id if child else None  # Temp
          self._parent1_id = parent1.id if parent1 else None
          self._parent2_id = parent2.id if parent2 else None
          self.child = child
          self.parent1 = parent1
          self.parent2 = parent2
  
      def resolveDependencies(self, id_map):
          if self._child_id and not self.child:
              self.child = id_map.get(self._child_id)
          if self._parent1_id and not self.parent1:
              self.parent1 = id_map.get(self._parent1_id)
          if self._parent2_id and not self.parent2:
              self.parent2 = id_map.get(self._parent2_id)
          if not all([self.child, self.parent1]):  # parent2 optional?
              raise ValueError("Unresolved ChildOf dependencies")
  
  # In multiplebirth.py (similar for members)
  class MultipleBirth(...):
      def __init__(self, members=None, ...):
          self._member_ids = [m.id for m in members] if members else []
          self.members = members or []
  
      def resolveDependencies(self, id_map):
          if self._member_ids and not self.members:
              self.members = [id_map.get(mid) for mid in self._member_ids if id_map.get(mid)]
          if not self.members:
              raise ValueError("Unresolved MultipleBirth members")
  ```  
  In `Scene.read()`:  
  ```python
  def read(self, data):
      id_map = {}
      # Phase 1: Instantiate without full deps
      for item_data in data.get('items', []):
          item_type = item_data['type']
          if item_type == 'ChildOf':
              item = ChildOf()  # Minimal init
          elif item_type == 'MultipleBirth':
              item = MultipleBirth()
          else:
              item = self._instantiateItem(item_data)  # Existing helper
          item.read(item_data)  # Load props, store temp IDs
          id_map[item.id] = item
      # Phase 2: Resolve
      for item in id_map.values():
          if hasattr(item, 'resolveDependencies'):
              item.resolveDependencies(id_map)
      # Add to scene
      for item in id_map.values():
          self.addItem(item)
  ```

- [ ] **Step 8: Integration with Events**  
  In `scene.py` or `event.py`, tie ChildOf to relevant `EventKind`s (e.g., `Adopted`, `SeparatedBirth`). Use `scene.setParents` internally.  
  ```python
  class Scene(...):
      def _addEventWithEmotions(self, event, ...):  # Existing; extend
          if event.kind in [EventKind.Adopted, EventKind.SeparatedBirth]:
              # Assume event.person is child, event.spouse is parent? Adjust based on schema
              parents = [event.spouse, ...]  # Fill based on event data
              adopted = (event.kind == EventKind.Adopted)
              self.setParents(event.person, parents, adopted=adopted)
  ```  
  For non-dated/drawing mode, use explicit instantiation + `addItem`.

- [ ] **Step 9: Testing/Migration**  
  - Add tests: Creation via `setParents` adds ChildOf, links MB if added explicitly; deletion cascades; queries work; undo/redo reuses objects.  
  - Migrate: Search/replace scattered APIs; test for regressions.  
  - If MultipleBirth needs implicit creation (e.g., on adding ChildOf with siblings), add to `addItem` logic (but keep explicit option).  
  - Update docs/CLAUDE.md if needed.
```