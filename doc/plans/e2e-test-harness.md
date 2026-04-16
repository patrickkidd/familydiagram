# E2E Test Harness Plan

Status: Complete as of 2026-04-12

## Context

The MCP test harness (`familydiagram/mcpserver/`) was rebuilt to support multi-instance testing with ephemeral servers. This enables testing scenarios where both Pro and Personal apps must share a diagram without data loss.

During this work, three additional issues surfaced that need resolution.

## Architecture Changes (DONE)

### Multi-Instance MCP Harness

- `TestSession` singleton replaced with `TestInstance` registry (keyed by UUID)
- Dynamic port allocation for both bridge and Flask server (no more hardcoded 9876)
- `ephemeral_server.py`: standalone Flask+SQLite subprocess for isolated e2e testing
- `server_url` parameter on `launch_app` allows multiple apps to share one ephemeral server
- Orphan prevention: atexit + signal handlers + ppid watchdog thread
- New tools: `close_all_instances`, `seed_server_data`, `open_server_diagram`, `launch_app_in_simulator`
- Ephemeral server endpoints: `/test/seed`, `/test/reset`, `/test/health`, `/test/diagrams/<id>` (GET returns raw pickle, PUT accepts raw pickle), `/test/diagrams/seed_pickle` (POST raw pickle)

### Pro App Bridge Fix (DONE)

- `_getProAppState()` in `inspector.py` had unsafe attribute access (no null checks on session, fileManager, documentView, scene). Fixed with `getattr` + null guards.

### iOS Simulator Support (DONE, verified)

- `launch_app_in_simulator()` orchestrates boot -> install -> launch -> bridge connect
- Bridge auto-starts on port 9876 in simulator builds (`IS_IPHONE_SIMULATOR`)
- Verified: app state introspection, tab switching, screenshots all work through the bridge
- Pre-built `.app` at `build/ios/Debug-iphonesimulator/Family Diagram.app` is functional

### `open_server_diagram` Bridge Command (DONE)

- Added to bridge server + inspector + MCP tool
- Replicates the exact code path of clicking a diagram in the file manager: `syncDiagramFromServer` -> `onServerFileClicked` -> `setServerDiagram` -> `setDocument`
- Critical because `open_file` (local .fd path) bypasses the server/Legend/DocumentView initialization path

## Known Bug: Harness Error Capture (MUST FIX)

**The app logs errors to stdout, not stderr.** All previous error-checking used `_stderr_lines` which was always empty. This means every "OK" result reported before 2026-04-12 22:37 was a false positive.

Fix needed: all test scripts and any future automated checks must examine `_stdout_lines` for ERROR/Traceback patterns, not `_stderr_lines`.
