# Personal App Data Synchronization Guide

This document provides comprehensive guidance for handling data synchronization between the frontend (PersonalAppController/Scene) and backend (DiagramData/PDP) in the personal app.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Data Structures](#data-structures)
- [Synchronization Patterns](#synchronization-patterns)
- [Best Practices by Scenario](#best-practices-by-scenario)
- [Preventing Race Conditions](#preventing-race-conditions)
- [Recommended Data Flow](#recommended-data-flow)
- [Current Issues and Solutions](#current-issues-and-solutions)
- [Action Items](#action-items)

---

## Architecture Overview

### Overall Structure

The personal app uses a **client-server architecture** with clear separation of concerns:

**Frontend (familydiagram/):**
- **PersonalAppController** (`familydiagram/pkdiagram/personal/personalappcontroller.py`) - Main controller coordinating frontend operations
- **Scene** (`familydiagram/pkdiagram/scene/scene.py`) - Core data model containing all diagram items (Person, Event, Marriage, Emotion, etc.)
- **EventForm** (`familydiagram/pkdiagram/views/eventform.py`) - UI form for adding/editing events
- **Frontend Models** (`familydiagram/pkdiagram/personal/models.py`) - QObject wrappers for Discussion, Statement, Speaker (QML binding)

**Backend (btcopilot/):**
- **Diagram Model** (`btcopilot/btcopilot/pro/models/diagram.py`) - SQLAlchemy model with PostgreSQL persistence
- **DiagramData** (`btcopilot/btcopilot/schema.py:264`) - Dataclass representing diagram state with PDP separation
- **PDP (Pending Data Pool)** (`btcopilot/btcopilot/schema.py:257`) - AI-extracted data awaiting user approval
- **Discussion/Statement Models** (`btcopilot/btcopilot/personal/models/`) - Chat conversation storage
- **Routes** (`btcopilot/btcopilot/personal/routes/`) - REST API endpoints

---

## Data Structures

### DiagramData Class

The `DiagramData` class (line 264 in `btcopilot/btcopilot/schema.py`) is the **central data structure** for synchronization:

```python
@dataclass
class DiagramData:
    people: list[dict] = field(default_factory=list)      # READ-ONLY from pickle
    events: list[dict] = field(default_factory=list)      # READ-ONLY from pickle
    pair_bonds: list[dict] = field(default_factory=list)  # READ-ONLY from pickle
    pdp: PDP = field(default_factory=PDP)                 # AI-managed pending data
    last_id: int = field(default=0)                        # ID generation
```

**Critical Design Decisions:**

1. **Separation of concerns**: Committed diagram data (people/events/pair_bonds) vs. pending data (pdp)
2. **Negative IDs for PDP items**: All PDP items have negative IDs to distinguish from committed items
3. **Read-only pickle data**: The outer people/events/pair_bonds lists may contain QtCore objects and are READ-ONLY for backend
4. **ID management**: `DiagramData` manages ID generation via `_next_id()` and `last_id`

### PDP (Pending Data Pool)

```python
@dataclass
class PDP:
    people: list[Person] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    pair_bonds: list[PairBond] = field(default_factory=list)
```

**Purpose**: AI extracts clinical data from chat conversations, storing it in a "pending" state until user approves/rejects.

**Key Features:**
- All items have **negative IDs** (e.g., -1, -2, -3)
- Items reference each other using these negative IDs
- When accepted, items get new positive IDs and move to committed data
- Transitive closure: accepting a person also accepts all their events

### Database Schema

**Diagrams Table** (`btcopilot/btcopilot/migrations/versions/cbc6ba6febe0_add_diagrams_table.py`):

```sql
CREATE TABLE diagrams (
    id INTEGER PRIMARY KEY,
    created_at DATETIME,
    updated_at DATETIME,
    user_id INTEGER,  -- Foreign key to users
    data LARGEBINARY, -- Pickled diagram data
    name VARCHAR,
    alias VARCHAR,
    use_real_names BOOLEAN,
    require_password_for_real_names BOOLEAN
)
```

**DiagramData Storage:**
- `DiagramData` is NOT a separate table
- Stored as pickled Python dict in `diagrams.data` column
- Structure: `{"people": [...], "events": [...], "pair_bonds": [...], "pdp": {...}, "last_id": N}`

---

## Synchronization Patterns

### Loading Data (Backend → Frontend)

**Flow:**

1. **Frontend initiates**: `PersonalAppController._refreshDiagram()` (line 155)
2. **HTTP GET request**: `GET /personal/diagrams/{diagram_id}`
3. **Backend route** (`btcopilot/btcopilot/personal/routes/diagrams.py:get()`, line 37):
   - Loads `Diagram` from PostgreSQL
   - Calls `diagram.get_diagram_data()` to unpickle diagram data
   - Returns JSON with `diagram_data` containing both committed data and PDP
4. **Frontend receives** (line 159-170):
   - Creates new `Scene()` object
   - Calls `scene.read(data)` to deserialize all items
   - Sets scene in controller

**Scene.read() Process** (`scene.py:972`):
- Two-phase loading:
  1. **Phase 1**: Create all items with IDs (events first, then people, marriages, emotions, etc.)
  2. **Phase 2**: Call `item.read(chunk, byId)` to resolve references using ID map
- Handles forward compatibility with `futureItems`
- Validates UUIDs and version compatibility

### Saving Data (Frontend → Backend)

**Flow:**

1. **Frontend triggers**: `PersonalAppController.saveDiagram()` (line 182)
2. **Serialize scene**: `data = self.scene.write()` (line 187)
3. **HTTP PUT request**: `PUT /personal/diagrams/{diagram_id}` with scene data
4. **Backend route** (`diagrams.py:update()`, line 60):
   - Calls `diagram.set_diagram_data(data)`
   - Commits to PostgreSQL via `db.session.commit()`

**Scene.write() Process** (`scene.py:1148`):
- Initializes typed arrays for each item type
- Iterates through `scene.itemRegistry`
- Calls `item.write(chunk)` for each item
- Returns structured dict with people, events, marriages, emotions, layers, etc.

**set_diagram_data() Behavior** (`diagram.py:61-81`):

```python
def set_diagram_data(self, diagram_data: DiagramData):
    data = pickle.loads(self.data) if self.data else {}
    data["pdp"] = asdict(diagram_data.pdp)  # Convert to dict for pickle
    data["last_id"] = diagram_data.last_id

    # Only update if provided (frontend controls these)
    if diagram_data.people:
        data["people"] = diagram_data.people
    if diagram_data.events:
        data["events"] = diagram_data.events
    if diagram_data.pair_bonds:
        data["pair_bonds"] = diagram_data.pair_bonds

    self.data = pickle.dumps(data)
```

---

## Best Practices by Scenario

### 1. Accepting/Rejecting PDP Items

**⚠️ CRITICAL ISSUE**: Current `acceptPDPItem()` (line 318) doesn't refresh the scene after acceptance! This causes data corruption.

**Why This is Critical:**

When backend accepts a PDP item, it:
1. Generates a new positive ID (was negative in PDP)
2. Moves item from `pdp.people/events/pair_bonds` to outer committed lists
3. Remaps all references to use new ID

If you don't refresh, your frontend Scene still has the old negative ID, and next `saveDiagram()` will overwrite the backend's work!

**Recommended Pattern:**

```python
def acceptPDPItem(self, pdpId: int):
    """Accept a PDP item and refresh scene to reflect committed data."""
    url = f"{self.apiUrl}/diagrams/{self.diagram['id']}/pdp/{pdpId}/accept"
    request = QNetworkRequest(QUrl(url))
    request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")

    def onFinished():
        reply = self.sender()
        if reply.error() == QNetworkReply.NoError:
            logging.info(f"Accepted PDP item: {pdpId}")
            # CRITICAL: Reload scene to get committed item with new positive ID
            self._refreshDiagram()  # <-- ADD THIS
        else:
            logging.error(f"Failed to accept PDP item: {reply.errorString()}")
        reply.deleteLater()

    reply = self.networkAccessManager.post(request, b'{}')
    reply.finished.connect(onFinished)
```

**Same applies to `rejectPDPItem()`** - refresh after rejection to ensure PDP state is consistent.

**Backend Accept Flow** (`diagrams.py:pdp_accept()`, line 104):

1. Frontend calls: `POST /personal/diagrams/{diagram_id}/pdp/{-pdp_id}/accept`
2. Backend:
   - Loads `DiagramData` via `diagram.get_diagram_data()`
   - Calls `database.commit_pdp_items([pdp_id])` (`schema.py:293`)
   - This:
     - Gets transitive closure of referenced items (if accepting person, include their events)
     - Generates new positive IDs via `_next_id()`
     - Remaps all IDs in items and references
     - Moves items from `pdp.*` to outer `people/events/pair_bonds` lists
     - Removes from PDP
   - Saves: `diagram.set_diagram_data(database)` + `db.session.commit()`

**Backend Reject Flow** (`diagrams.py:pdp_reject()`, line 130):

1. Frontend calls: `POST /personal/diagrams/{diagram_id}/pdp/{-pdp_id}/reject`
2. Backend:
   - Loads `DiagramData`
   - Finds item in PDP by ID
   - For persons: cascade deletes all events referencing that person
   - Removes item from PDP
   - Saves changes

### 2. Adding Events via EventForm

**Current Pattern** (works well):

```python
# In EventForm._save() - line 457
event = self.scene.addItem(Event(...), undo=True)  # Adds to frontend Scene only
```

**Best Practice:**
- ✅ EventForm operates purely on local Scene (no direct backend calls)
- ✅ Uses undo/redo macros for atomicity
- ⚠️ Must explicitly save afterwards

**Recommended Flow:**

1. User fills out EventForm
2. EventForm adds Event/People to Scene locally
3. **After form closes**: Call `PersonalAppController.saveDiagram()` to persist
4. Optionally debounce saves (wait 2-5 seconds) to batch multiple edits

**Example Integration** (add to EventForm):

```python
def _save(self):
    # ... existing event creation code ...

    # Notify controller to save after next event loop cycle
    QTimer.singleShot(2000, lambda: self.scene.controller.saveDiagram())  # 2-sec debounce
```

**EventForm Process** (`eventform.py:_save()`, line 457):

1. Validates form data (required fields, unsubmitted pickers)
2. Gathers person entries (person, spouse, child, targets, triangles)
3. Creates new Person objects for new people
4. Adds new people: `self.scene.addItems(*newPeople, undo=True)` (line 595)
5. Creates Marriage if needed for pair bond events
6. Creates Event: `event = self.scene.addItem(Event(...), undo=True)` (line 723)
7. Scene automatically creates Emotions for relationship events
8. Arranges people spatially based on event type
9. Updates timeline if needed

**Note**: All operations use `undo=True`, wrapping in `scene.macro()` for atomic undo/redo (line 452).

### 3. Scene Data Synchronization

**Current Pattern:**
- ✅ Scene loaded at startup: `_refreshDiagram()` (line 155)
- ✅ Scene saved explicitly: `saveDiagram()` (line 182)
- ⚠️ **Issue**: `onSuccess()` at line 124 calls `saveDiagram()` after various operations

**Recommended: Explicit Save Strategy**

```python
class PersonalAppController:
    def __init__(self):
        self._dirty = False  # Track unsaved changes
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._debouncedSave)

    def markDirty(self):
        """Mark scene as having unsaved changes."""
        self._dirty = True
        self._save_timer.start(5000)  # Auto-save after 5 seconds of inactivity

    def _debouncedSave(self):
        """Debounced auto-save."""
        if self._dirty:
            self.saveDiagram()
            self._dirty = False

    def saveDiagram(self):
        """Explicitly save scene to backend."""
        if not self.scene:
            return

        data = self.scene.write()  # Serialize Scene
        diagram_data = DiagramData(
            people=data.get('people', []),
            events=data.get('events', []),
            pair_bonds=data.get('pair_bonds', []),
            # Don't send PDP - backend manages it
        )

        # PUT to backend
        self._sendDiagramUpdate(diagram_data)
```

**Connect to Scene Changes:**

```python
# In Scene initialization
self.scene.changed.connect(self.controller.markDirty)  # Any scene change marks dirty
```

**Benefits:**
- **Immediate feedback**: User sees changes instantly in UI
- **Debounced saves**: Avoids hammering backend during rapid edits
- **Explicit control**: You decide when to save, not automatic

### 4. PDP-Specific Sync Strategy

**Key Insight**: Backend fully manages PDP through chat AI extraction. Frontend should:

1. **Never directly modify PDP** in `saveDiagram()`
2. **Always use dedicated endpoints** for accept/reject
3. **Always refresh after PDP operations** to get updated state

**Recommended: Make PDP Update Explicit**

Update `set_diagram_data()` (`diagram.py:61`) to make this explicit:

```python
def set_diagram_data(self, diagram_data: DiagramData, update_pdp: bool = False):
    """Set diagram data. By default, PDP is managed separately via chat/accept/reject."""
    data = pickle.loads(self.data) if self.data else {}

    # Always update committed data from frontend
    if diagram_data.people:
        data["people"] = diagram_data.people
    if diagram_data.events:
        data["events"] = diagram_data.events
    if diagram_data.pair_bonds:
        data["pair_bonds"] = diagram_data.pair_bonds

    # Only update PDP if explicitly requested (internal backend use only)
    if update_pdp:
        data["pdp"] = asdict(diagram_data.pdp)

    data["last_id"] = diagram_data.last_id
    self.data = pickle.dumps(data)
```

Then update routes:

```python
# In diagrams.py:update() - frontend saves
diagram.set_diagram_data(diagram_data, update_pdp=False)  # Explicit: don't touch PDP

# In discussions.py:chat() - AI extraction
diagram.set_diagram_data(diagram_data, update_pdp=True)  # Explicit: update PDP
```

**AI Chat Extraction Flow** (`discussions.py:chat()`, line 112):

1. User sends statement → `PersonalAppController._sendStatement()` (line 259)
2. Backend chat endpoint:
   - Calls `ask(discussion, statement)`
   - AI extracts `PDPDeltas` via `pdp.update()` (`btcopilot/btcopilot/pdp.py:179`)
   - Applies deltas to existing PDP: `new_pdp = apply_deltas(diagram_data.pdp, pdp_deltas)`
   - Saves updated PDP to diagram: `diagram.set_diagram_data(diagram_data)`
   - Returns PDP to frontend in response
3. Frontend updates (line 272):
   - Sets `self._pdp` with returned data
   - Emits `diagramChanged` signal

**PDP Delta Application** (`pdp.py:apply_deltas()`, line 238):
- Deep copies existing PDP
- Processes upserts (add new or update existing people/events/pair_bonds)
- Processes deletes
- Validates references between items

---

## Preventing Race Conditions

### Current State: No Concurrency Control

**Issues Identified:**

1. **No version tracking** on Diagram records
2. **No optimistic locking** (checking `updated_at` before writes)
3. **Pure last-write-wins** model
4. **ID generation not thread-safe** (`DiagramData._next_id()`)

### Race Condition Scenarios

#### Race Condition #1: Concurrent PDP Accept + Save

**Scenario:**
1. User clicks "Accept" on PDP item (async HTTP request starts)
2. User immediately adds an event via EventForm
3. Frontend saves diagram via `saveDiagram()`
4. Backend's accept endpoint completes, overwriting PDP changes

**Problem**: Last-write-wins, no conflict detection. The `saveDiagram()` could overwrite the accepted item or vice versa.

#### Race Condition #2: Concurrent Statement Submissions

**Scenario:**
1. User sends statement #1 (backend starts AI extraction)
2. User quickly sends statement #2 before #1 completes
3. Both extract deltas and call `apply_deltas()` on stale PDP state
4. Later statement overwrites earlier statement's extractions

**Problem**: No version tracking on PDP. Each statement loads current diagram, applies deltas, saves entire diagram.

#### Race Condition #3: Frontend Scene Desync

**Scenario:**
1. User accepts PDP item via HTTP request
2. Backend commits item, assigns new positive ID
3. Frontend doesn't reload Scene
4. Frontend Scene still has item with negative ID in PDP
5. User saves diagram → overwrites backend's committed item with stale PDP state

**Problem**: Frontend `acceptPDPItem()` doesn't refresh the scene after acceptance.

### Solution: Optimistic Locking with Version Tracking

#### Step 1: Add Version Column to Database

**Migration** (create new):

```python
def upgrade():
    op.add_column('diagrams', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))

def downgrade():
    op.drop_column('diagrams', 'version')
```

#### Step 2: Update Diagram Model

**Update** (`btcopilot/btcopilot/pro/models/diagram.py`):

```python
class Diagram(db.Model):
    __tablename__ = 'diagrams'

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.Integer, nullable=False, default=1)  # ADD THIS
    data = db.Column(db.LargeBinary)
    # ... other fields
```

#### Step 3: Update Routes with Version Checking

**Update** (`diagrams.py:update()`, line 60):

```python
@bp.route('/<int:diagram_id>', methods=['PUT'])
def update(diagram_id):
    diagram = Diagram.query.get_or_404(diagram_id)

    # Check version from client
    client_version = request.json.get('version')
    if client_version and diagram.version != client_version:
        return jsonify({
            'error': 'Conflict: diagram was modified by another process',
            'current_version': diagram.version
        }), 409  # HTTP 409 Conflict

    # Update data
    diagram_data = DiagramData.from_dict(request.json['diagram_data'])
    diagram.set_diagram_data(diagram_data)
    diagram.version += 1  # Increment version

    db.session.commit()
    return jsonify({
        'diagram': diagram.to_dict(),
        'version': diagram.version  # Return new version to client
    })
```

**Apply to all mutation endpoints:**
- `pdp_accept()` (line 104)
- `pdp_reject()` (line 130)
- `update()` (line 60)

#### Step 4: Handle Conflicts in Frontend

```python
class PersonalAppController:
    def __init__(self):
        self._current_version = None  # Track version

    def saveDiagram(self):
        """Save with conflict detection."""
        data = self.scene.write()

        payload = {
            'version': self._current_version,  # Send current version
            'diagram_data': data
        }

        reply = self.networkAccessManager.put(request, json.dumps(payload).encode())

        def onFinished():
            reply = self.sender()
            if reply.error() == QNetworkReply.NoError:
                response = json.loads(reply.readAll().data())
                self._current_version = response['version']  # Update version
                logging.info("Diagram saved successfully")
            elif reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 409:
                # Conflict detected - reload and prompt user
                logging.warning("Conflict detected - reloading diagram")
                self._handleSaveConflict()
            else:
                logging.error(f"Save failed: {reply.errorString()}")
            reply.deleteLater()

        reply.finished.connect(onFinished)

    def _handleSaveConflict(self):
        """Handle save conflict by reloading server data."""
        msgBox = QMessageBox()
        msgBox.setText("The diagram was modified by another process.")
        msgBox.setInformativeText("Reload the diagram? Your local changes will be lost.")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        if msgBox.exec() == QMessageBox.Yes:
            self._refreshDiagram()  # Reload from server
```

---

## Recommended Data Flow

### Startup

1. Frontend: `_refreshDiagram()` → `GET /diagrams/{id}`
2. Backend: Returns full DiagramData (committed + PDP)
3. Frontend: `scene.read(data)` - loads everything
4. Frontend: Stores `version` from response

### User Adds Event (EventForm)

1. Frontend: User fills form → `_save()` → `scene.addItem(Event(...))`
2. Frontend: Scene change triggers `markDirty()`
3. Frontend: 2-5 seconds later → debounce timer fires → `saveDiagram()`
4. Backend: `PUT /diagrams/{id}` with version check
5. Backend: If version matches → save committed data only → increment version → return new version
6. Frontend: Receives new version number, updates `_current_version`

### AI Chat Extraction

1. Frontend: `_sendStatement()` → `POST /discussions/{id}/chat`
2. Backend:
   - AI extracts deltas → `apply_deltas(pdp, deltas)`
   - Calls `set_diagram_data(..., update_pdp=True)`
   - Increments version
   - Commits to database
3. Backend: Returns updated PDP + new version in response
4. Frontend: Sets `self._pdp` (display in UI) + updates `_current_version`

### Accept PDP Item

1. Frontend: User clicks accept → `POST /diagrams/{id}/pdp/{-id}/accept`
2. Backend:
   - Version check (if implemented in accept endpoint)
   - `commit_pdp_items()` → assigns positive ID → moves to committed data
   - Increments version
   - Saves
3. Frontend: **CRITICAL** - `_refreshDiagram()` to reload scene with committed item
4. Result: Item now has positive ID in committed data, removed from PDP
5. Frontend: Updates `_current_version` from response

### Reject PDP Item

1. Frontend: User clicks reject → `POST /diagrams/{id}/pdp/{-id}/reject`
2. Backend:
   - Version check
   - Cascade deletes from PDP
   - Increments version
   - Saves
3. Frontend: **CRITICAL** - `_refreshDiagram()` to remove from scene
4. Frontend: Updates `_current_version` from response

---

## Current Issues and Solutions

### Critical Issues

| Issue | Impact | Solution | Priority |
|-------|--------|----------|----------|
| `acceptPDPItem()` doesn't refresh scene | Frontend scene becomes stale, subsequent saves overwrite backend changes | Add `self._refreshDiagram()` in `onFinished()` callback | 🔴 CRITICAL |
| `rejectPDPItem()` doesn't refresh scene | Frontend scene retains rejected items | Add `self._refreshDiagram()` in `onFinished()` callback | 🔴 CRITICAL |
| No concurrency control | Race conditions in multi-user or rapid operation scenarios | Add version tracking + optimistic locking | 🔴 HIGH |

### Medium Priority Issues

| Issue | Impact | Solution | Priority |
|-------|--------|----------|----------|
| Aggressive auto-saving | Excessive network traffic, potential conflicts | Implement debounced auto-save | 🟡 MEDIUM |
| No atomic PDP multi-step operations | Exception mid-cascade could leave inconsistent state | Validate entire operation before mutations | 🟡 MEDIUM |
| PDP update not explicit in `set_diagram_data()` | Frontend could accidentally overwrite PDP | Add `update_pdp` parameter (default False) | 🟡 MEDIUM |
| ID generation not thread-safe | Could generate duplicates in concurrent scenarios | Use PostgreSQL sequence or add locking | 🟡 MEDIUM |
| No validation of diagram data before save | Corrupted data could be saved | Add schema validation in routes | 🟡 LOW |

### Patterns That Work Well

✅ **PDP Separation**: Clean separation between committed data and AI-extracted pending data

✅ **Negative IDs**: Make PDP items easily distinguishable, prevent ID collisions

✅ **Transitive Closure**: `commit_pdp_items()` correctly handles accepting referenced items

✅ **Scene Two-Phase Loading**: Handles circular dependencies elegantly

✅ **Pickle Compatibility**: Backend never creates QtCore objects, clean separation

✅ **Undo/Redo System**: EventForm wraps operations atomically

✅ **Dataclass-Based Schema**: Type safety, clean serialization via `from_dict()`/`asdict()`

---

## Action Items

### Immediate (Fix Data Corruption Bugs)

1. **🔴 CRITICAL**: Fix `acceptPDPItem()` to call `_refreshDiagram()` after success
   - File: `familydiagram/pkdiagram/personal/personalappcontroller.py:318`
   - Add: `self._refreshDiagram()` in `onFinished()` callback

2. **🔴 CRITICAL**: Fix `rejectPDPItem()` to call `_refreshDiagram()` after success
   - File: `familydiagram/pkdiagram/personal/personalappcontroller.py:335`
   - Add: `self._refreshDiagram()` in `onFinished()` callback

### High Priority (Prevent Race Conditions)

3. **🔴 HIGH**: Add version tracking to diagrams table
   - Create migration: `op.add_column('diagrams', sa.Column('version', sa.Integer(), ...))`
   - Update model: `btcopilot/btcopilot/pro/models/diagram.py`

4. **🔴 HIGH**: Implement optimistic locking in routes
   - Update: `diagrams.py:update()`, `pdp_accept()`, `pdp_reject()`
   - Check version, return 409 on conflict, increment on success

5. **🔴 HIGH**: Handle 409 conflicts in frontend
   - Update: `PersonalAppController.saveDiagram()`
   - Add: `_handleSaveConflict()` method with user prompt

### Medium Priority (Improve User Experience)

6. **🟡 MEDIUM**: Implement debounced auto-save
   - Add: `_dirty` flag, `_save_timer`, `markDirty()`, `_debouncedSave()`
   - Connect: `scene.changed` signal to `markDirty()`

7. **🟡 MEDIUM**: Make PDP update explicit in `set_diagram_data()`
   - Add: `update_pdp: bool = False` parameter
   - Update routes to be explicit: `update_pdp=False` vs `update_pdp=True`

8. **🟡 MEDIUM**: Add schema validation before saving
   - Validate structure matches expected format
   - Reject invalid data with clear errors

### Low Priority (Code Quality)

9. **🟢 LOW**: Use PostgreSQL sequence for ID generation
   - Replace `_next_id()` with database-backed sequence
   - Ensures thread-safety in async/multi-worker scenarios

10. **🟢 LOW**: Add transaction-like validation for PDP cascade operations
    - Validate entire cascade before any mutations
    - Ensures atomicity of multi-step operations

---

## References

### Key Files

**Frontend:**
- `familydiagram/pkdiagram/personal/personalappcontroller.py` - Main controller
- `familydiagram/pkdiagram/scene/scene.py` - Scene data model
- `familydiagram/pkdiagram/views/eventform.py` - Event creation UI

**Backend:**
- `btcopilot/btcopilot/schema.py` - DiagramData, PDP, Person, Event dataclasses
- `btcopilot/btcopilot/pro/models/diagram.py` - Diagram SQLAlchemy model
- `btcopilot/btcopilot/personal/routes/diagrams.py` - Diagram REST API
- `btcopilot/btcopilot/personal/routes/discussions.py` - Chat/PDP extraction
- `btcopilot/btcopilot/pdp.py` - PDP delta application logic

### Related Documentation

- `btcopilot/doc/PDP.md` - Pending Data Pool architecture
- `familydiagram/doc/ARCHITECTURE.md` - Overall application architecture (if exists)
- `CLAUDE.md` - Development setup and testing procedures
