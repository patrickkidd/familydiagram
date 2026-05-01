# Harness: Multi-Instance Concurrent Testing

**Branch**: `harness-multi-instance` (worktree at `familydiagram/.claude/worktrees/harness-multi-instance`)  
**Goal**: Enable running N concurrent Pro and Personal app instances against a single ephemeral server, with deterministic coordination for save-ordering and observable outcomes.  
**NOT in scope**: fixing app-level bugs (applyChange merge logic, QMessageBox in headless, assert in personalappcontroller, etc.). Those belong to Patrick's parallel work in the main clone.

---

## What's Done

### Infrastructure (mcp_server.py)
- `TestInstance` gets dynamic bridge port (no hardcoded 9876)
- Sandboxed filesystem per instance (temp dir, auto-cleaned)
- `UUID`-based `instance_id`
- Background drain threads for app subprocess pipes (stdout/stderr) — prevents pipe buffer exhaustion from blocking the Qt main thread
- Background drain threads for ephemeral Flask server subprocess pipes — same fix
- `ephemeral_server=True` / `server_url=...` options so Personal can share Pro's server
- `close(force=True)` teardown; atexit + signal handlers prevent orphans

### Ephemeral Server (ephemeral_server.py)
- `threaded=True` on Flask so concurrent connections from Pro + Personal don't serialize
- `/test/seed` endpoint (idempotent — returns existing user if present)
- `/test/diagrams/<id>` GET/PUT raw pickle endpoints
- `/test/health` endpoint

### Bridge Server (pkdiagram/mcpbridge/server.py)
- Dynamic port binding
- Long-running timeout (120s) for `save_diagram`, `open_server_diagram`, `open_file`
- `wait_until_idle` command: no-op dispatched to Qt main thread; returns when thread is free

### Bridge Commands (pkdiagram/mcpbridge/inspector.py)
- `open_server_diagram`: **blocks until fully loaded** (Pro: sync; Personal: nested QEventLoop on `diagramChanged`)
- `save_diagram`: **blocks until complete including 409 retries**; returns `{success, conflicts}` where `conflicts > 0` confirms applyChange fired
- `get_status`: lightweight `{appType, serverDiagramId, sceneLoaded}`
- `wait_until_idle`: dispatched to Qt main thread; returns when free
- `get_scene_items`: works for both Pro (QGraphicsView) and Personal (controller.scene)

### Test (mcpserver/tests/test_concurrent_save.py)
- Self-contained: seeds its own user + diagram via `/test/seed`
- Journey-1A: Pro saves first (V→V+1), Personal (stale V) saves second, gets 409
- Asserts `conflicts >= 1` on Personal's save (409 path fired)
- Step 5 (re-open + scene check) intentionally omitted — requires app bug fixes out of scope for this branch
- **Status**: PASSES 10/10 at ~16s/run

---

## Known Blockers / Bugs Hit During Harness Work

These are **app bugs**, not harness bugs. Do NOT fix here — report to Patrick:

1. **`handleDiagramConflict` QMessageBox in headless mode** (`serverfilemanagermodel.py:handleDiagramConflict`): When `syncDiagramFromServer` downloads a newer diagram, `dataChanged` fires → `onServerFileModelDataChanged` → `QMessageBox.exec_()` blocks forever headless. Workaround used in harness test: none currently — the test works because the timing avoids it, OR the `_savingServerFile` flag happens to be set. **Needs investigation.**

2. **Personal's `applyChange` overwrites scene-owned fields** (`personalappcontroller.py:saveDiagram`): On 409 retry, Personal writes its stale empty scene onto server version, losing Pro's people. This is a data integrity bug Patrick is working on.

3. **`assert self.scene is None` in `personalappcontroller.py:_refreshDiagram`**: Prevents re-loading a diagram when scene is already set. Causes second `open_server_diagram` on Personal to silently return stale scene data. App bug, not harness bug.

---

## Next Steps for Harness (in scope)

- [ ] Add a second test scenario: Two Personal instances concurrent (different session tokens, same diagram)  
- [ ] Add `get_scene_items` result to the `get_status` response so callers can check without a separate round-trip  
- [ ] Stress test: launch 4 instances (2 Pro + 2 Personal) and verify all bridge commands work without interference  
- [ ] Confirm harness teardown leaves no orphan processes (`lsof` / `ps` check after close)  
- [ ] Document the bridge command contract (timeout behavior, what `conflicts` means)

## Out of Scope (report to Patrick)

- applyChange 3-way merge logic  
- QMessageBox in headless mode  
- Personal scene reload assert  
- Any data integrity fixes in production app code
