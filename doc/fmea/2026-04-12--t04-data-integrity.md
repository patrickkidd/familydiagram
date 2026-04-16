# FMEA: Testing Session Data Integrity Findings

Date: 2026-04-12
Scope: Bugs, near-misses, and process failures discovered during T0-4/T0-5 testing session

## Context

This FMEA captures findings from the testing session that are NOT already covered in [2026-04-12--t04-concurrent-save-integrity.md](2026-04-12--t04-concurrent-save-integrity.md). That file covers the T0-4 fix itself (field ownership merge), diagram 1924 corruption, chat history loss, and the Scene.prune() gap.

## Failure Modes — Server-Side Data Loss

| # | Failure Mode | Trigger | Severity | Detection | Status |
|---|---|---|---|---|---|
| S1 | `Diagram.setDiagramData()` drops 38/43 DiagramData fields | `server_types.py` only writes 5 fields (people, pair_bonds, events, emotions, layers); all others silently dropped | Critical | FMEA analysis during T0-5 investigation | **OPEN** — `setDiagramData` in `btcopilot/btcopilot/pro/models/diagram.py` needs full field coverage or must be replaced with whole-blob write |
| S2 | `set_diagram_data()` drops clusters on write | btcopilot's `set_diagram_data` omits clusters field | High | FMEA analysis during T0-5 investigation | **OPEN** — field list in route handler incomplete |

### S1/S2 Blast Radius

Any code path that calls `setDiagramData()` or `set_diagram_data()` to persist changes will silently lose most DiagramData fields. The Pro app's normal save path (PUT with full blob) bypasses these methods, so the bug only triggers on server-side writes (admin tools, training app operations, migration scripts). If either method is ever used in a save-critical path, data loss is immediate and silent.

## Failure Modes — Desktop App Crashes

| # | Failure Mode | Trigger | Severity | Detection | Status |
|---|---|---|---|---|---|
| D1 | LegendView crash on `legendData.shown=True` | `AttributeError: 'LegendView' object has no attribute 'getVisibleSceneScaleRatio'` — LegendView inherits from wrong base or missing method | Medium | Test data seeding during manual testing | **OPEN** — `getVisibleSceneScaleRatio` exists on `View` (documentview/view.py) but not on `LegendView` |

### D1 Notes

LegendView calls a method that only exists on the document view hierarchy. Either LegendView needs its own implementation or the call site needs to route through the correct view object.

## Failure Modes — Test Infrastructure

| # | Failure Mode | Trigger | Severity | Detection | Status |
|---|---|---|---|---|---|
| T1 | Harness error capture is a false positive factory | App logs errors to stdout, not stderr. Harness checked stderr (always empty). Every previous "OK" result was unchecked. | Critical | Discovered when investigating why errors weren't caught | **OPEN** — harness must capture stdout or app must log to stderr. All prior test-log results are unreliable. |
| T2 | License modal blocks all test interactions | Beta builds strip features to LICENSE_BETA only. Ephemeral server seed created LICENSE_PROFESSIONAL, not LICENSE_BETA. Modal appears with no dismiss path in automated testing. | High | Manual testing session — all interactions silently failed | **FIXED** — seed updated to provide correct license type |

### T1 Blast Radius

Every AI-driven test session logged in `familydiagram/doc/test-logs/` that reported success based on absence of stderr errors is suspect. The harness was structurally incapable of detecting app errors. This is not a bug in any individual test — it's a systemic false-positive problem in the test infrastructure itself.

## Failure Modes — Documentation / Process

| # | Failure Mode | Trigger | Severity | Detection | Status |
|---|---|---|---|---|---|
| P1 | CLAUDE.md field sync rule would recreate T0-4 bug | Original rule said to update `applyChange` for ALL new DiagramData fields, without distinguishing Personal-owned fields. Future developer following the rule would add Personal fields to Pro's applyChange, re-enabling the overwrite bug. | High | Post-mortem analysis of T0-4 root cause | **FIXED** — CLAUDE.md updated to distinguish Scene-owned vs Personal-owned fields with explicit ownership guidance |

## Cross-References

- T0-4 fix, diagram 1924 corruption, chat history, prune gap: [2026-04-12--t04-concurrent-save-integrity.md](2026-04-12--t04-concurrent-save-integrity.md)
- T0-5 investigation: MVP Dashboard
- Chat history loss: MVP Dashboard (filed separately)
