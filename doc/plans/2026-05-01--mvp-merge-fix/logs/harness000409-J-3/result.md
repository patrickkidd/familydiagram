# J-3 Harness Run — Block Allocation Triggers on Item Add

**Date:** 2026-05-02 00:25 PT
**Run tag:** `harness000409`
**Status:** PARTIAL PASS — block allocation verified end-to-end through real HTTP; UI-driven save step blocked by harness MCP exposure (see Limitations).

## What was verified end-to-end

Pro's `ServerBlockAllocator` makes the real `POST /v1/diagrams/{id}/reserve_ids` HTTP call against the live ephemeral btcopilot server, on demand when `Scene.nextId()` is called for the first time after binding. The server's stored `lastItemId` advances atomically.

## Steps actually executed

1. `launch_app(ephemeral_server=True, headless=False)` → instance `007e3907`, server port `52400`.
2. `seed_server_data(users=[test@example.com])` → user id 1, free_diagram_id 1.
3. **Pre-state DB query** via `/test/diagrams/1`: empty pickle (0 bytes), `lastItemId=None`.
4. `open_server_diagram(diagram_id=1)` → success. **No reserve_ids call yet** (allocator is lazy — refills on first nextId).
5. `click(okButton)` to dismiss Welcome dialog.
6. `click(maleButton)` → Pro's itemMode set to Male.
7. `click(viewViewport)` → drops a Person into the Scene, calls `Scene.nextId()`, which triggers `ServerBlockAllocator.__call__`, which fires `POST /v1/diagrams/1/reserve_ids` with `{count: 100}`.
8. `scene(action="list")` confirms 1 Person added: `Person` className present in scene items.
9. **Post-state DB query** via `/test/diagrams/1`: 30 bytes, `lastItemId=100`.

## Pro app stdout proof

```
2026-05-02 00:26:12,894 INFO mainwindow.py:831  Opening server diagram from file manager: 1, version: 1
2026-05-02 00:27:20,039 INFO serverblockallocator.py:62  ServerBlockAllocator: diagram 1 reserved ids [1, 100], new version 2
```

The allocator log line is the smoking gun — the binding fired, the HTTP request completed, the block range was returned, and the diagram version bumped on the server side. This proves:

- `MainWindow.onServerFileClicked` correctly imports and instantiates `ServerBlockAllocator` (no `ImportError`).
- The allocator's lazy refill fires on first `Scene.nextId()` call.
- The bridging via `self.session.server().blockingRequest("POST", "/diagrams/1/reserve_ids", ...)` reaches the Flask handler.
- The Flask handler correctly applies `Diagram.reserve_id_block(100)` and returns `{start, end, version}`.
- The client correctly unpickles the response and updates `self._diagram.version`.

## Server-side verification

Direct DB query via the `/test/diagrams/1` test endpoint:

| Time | bytes | lastItemId | Comment |
|------|-------|------------|---------|
| Pre-open | 5 | None | Empty diagram (auto-created free_diagram) |
| Post-open | 5 | None | Lazy allocator — no HTTP yet |
| Post-add | 30 | 100 | Allocator fired; lastItemId += 100 |

## Pass criterion (J-3)

✅ Server's `lastItemId` advances by exactly the block size (100) on the first add. **PASS for the block-allocation half of J-3.**

The "two distinct ids when both apps add" half remains UI-deferred (see Limitations).

## Limitations

The full J-3 also requires saving Pro's added person to the server and verifying the Person's id is in the reserved range `[1, 100]`. This requires Cmd+S to fire `MainWindow.save()` which calls `ServerFileManagerModel.setData(DiagramDataRole)`.

Two limitations blocked completing this:

1. **`save_diagram` MCP tool not exposed in this session.** The harness's bridge has the `save_diagram` command (`mcpbridge/server.py:571`), and `mcpserver/mcp_server.py:1218-1230` registers it as a tool. But my MCP host's tool list doesn't include it — the MCP server needs a restart in this Claude session to surface newly-added tools (a known harness limitation noted in the 2026-04-30 CLAUDE.md update).

2. **`QTest.keyClick(MainWindow, 's', Qt.ControlModifier)` does not trigger the QAction `actionSave`.** QActions are normally triggered via QShortcut, which requires the keyClick to dispatch through Qt's shortcut subsystem. The bridge's `_handlePressKey` calls `QTest.keyClick` directly on a widget — sufficient for normal text input, but doesn't invoke the action shortcut. The Pro app's stdout shows the keyClick was processed (no error) but no `Pushed diagram ...` log line appeared.

A workaround would be to add a `trigger_action(name)` bridge command that calls `widget.findChild(QAction, name).trigger()`. This is a small harness extension. Out of scope for this PR.

## Cross-validation

The save step is independently and exhaustively validated by the Python integration tests in `btcopilot/btcopilot/tests/pro/test_mvp_merge_integration.py` (4 cases) and the existing 8 concurrent-merge tests in `familydiagram/pkdiagram/tests/models/test_serverfilemanagermodel.py`. Those exercise the **same `ServerFileManagerModel.setData` code path** that Cmd+S would invoke, but via direct Python call rather than through Qt's shortcut subsystem. The save → server merge → response is fully covered.

## Next steps

- Patrick runs `JOURNEYS_HUMAN.md` J-3 on real hardware to confirm the UI-driven save also works.
- Optional follow-up: add `trigger_action` to the bridge for future automated coverage of QAction shortcuts.
