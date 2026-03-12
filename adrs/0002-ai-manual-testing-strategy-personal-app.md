# ADR-0002: AI-Driven Manual Testing Strategy for the Personal App

**Status:** Accepted

**Date:** 2026-03-11

**Deciders:** Patrick

## Context

The Personal app targets iOS first. The existing `familydiagram-testing` MCP server
(TCP bridge at port 9876) was built for the desktop Pro app. iOS UI testing requires
a strategy that works without heavy third-party installs and without requiring a full
iOS build for every test cycle.

Three approaches were considered:

1. **iOS Simulator + xcrun simctl** — screenshots, lifecycle (boot/install/launch/terminate/log), but no touch injection without WDA or idb (download-heavy).
2. **Desktop as iOS proxy** — run the Personal app's QML codebase on macOS in an iPhone-sized window; interaction semantics differ but the render tree is identical.
3. **TCP bridge compiled into the iOS simulator build** — full semantic inspection (`get_app_state`, `inject_pdp_data`) reachable at localhost:9876 from host; requires an iOS build.

## Decision

Adopt a **layered approach**:

**Layer 1 — Desktop proxy (immediate, no downloads):** Run Personal app on macOS. Use
`resize_window(preset="iphone_14")` to constrain the window to iPhone viewport dimensions.
All existing bridge interactions (`click`, `scroll`, `long_press`, `hover`, `get_bounds`,
`get_text`) work. Semantic state (`get_app_state`, `personal_state`, `inject_pdp_data`)
is fully available. Vision-based correctness judgment uses Claude multimodal on screenshots.

**Layer 2 — iOS Simulator screenshots (immediate, no downloads):** `sim_list`, `sim_boot`,
`sim_screenshot` via `xcrun simctl` give GPU-accurate renders of the real iOS build.
No touch injection — use for visual regression only, or pair with Layer 1 for interaction.

**Layer 3 — TCP bridge in iOS simulator build (code-complete, pending iOS build verification):**
`main.py` auto-starts `TestBridgeServer` when `IS_IPHONE_SIMULATOR` is True (no CLI args
needed — iOS has none). `familydiagram.pdt` sets `mcpbridge` files to `included = true`.
iOS Simulator shares loopback with the host Mac, so localhost:9876 is reachable from Claude.
Guarded by `IS_IPHONE_SIMULATOR` (False on real devices) to prevent shipping the listener.

New MCP tools added to `familydiagram/mcpserver/mcp_server.py`:
- Bridge: `hover`, `scroll`, `long_press`, `get_text`, `get_bounds`, `resize_window`
- Simulator: `sim_list`, `sim_boot`, `sim_screenshot`, `sim_install`, `sim_launch`, `sim_terminate`, `sim_log`

New inspector/server methods in `familydiagram/pkdiagram/tests/mcpbridge/`:
- `inspector.py`: `hover`, `scroll`, `longPress`, `getText`, `getBounds`, `resizeWindow`
- `server.py`: corresponding handler registrations

## Consequences

### Positive
- Layer 1 is usable immediately with zero new dependencies; covers the majority of UX testing.
- Layer 2 produces pixel-accurate iOS screenshots for visual diff without any build tooling beyond Xcode.
- Claude's multimodal capability replaces brittle pixel-diff baselines for subjective UX judgment.
- `resize_window` presets make it easy to test multiple iPhone form factors in one session.

### Negative
- Desktop proxy doesn't exercise iOS-specific touch event routing, UIKit gesture recognizers, or Metal rendering pipeline.
- `xcrun simctl` cannot inject touch events; interactions on the simulator require Layer 3 (needs iOS build to verify).
- Layer 3 bundle inclusion (`familydiagram.pdt`) is unconditional — mcpbridge files are present in device builds, though never imported on device.

### Risks
- QML rendering differences between macOS and iOS (Metal vs. raster, font metrics, safe-area insets) may produce false passes on Layer 1 that fail on device.
- If `TestBridgeServer` is ever accidentally compiled into a production iOS build, it opens a local TCP listener in the shipped app.
