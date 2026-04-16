# Diagram Data Integrity Test Plan

Status: In progress as of 2026-04-12

Covers all test scenarios for ensuring neither app loses the other's data when saving — today (two separate apps) and future (Personal embedded in Pro).

## T0-4: FR-2 Fix Summary

File: `familydiagram/pkdiagram/models/serverfilemanagermodel.py` (applyChange at ~line 538)

Old behavior: Pro app's `applyChange` replaced the entire DiagramData blob, destroying Personal-app-owned fields (pdp, clusters, clusterCacheKey).

New behavior: Explicit field-by-field assignment. Pro app's `applyChange` sets only Scene-owned fields, leaving Personal-owned fields untouched. Same pattern as PersonalAppController.saveDiagram().

Also fixed: `Scene.diagramData()` in `scene.py` now includes `hideSARFGraphics` (was missing).

### Adversarial FMEA (independent sub-agent)

9 failure modes tested, all 43 DiagramData fields accounted for. Key findings:

- The fix itself is correct and complete for the Pro app save path
- Pre-existing bugs found in adjacent code paths (filed as T0-5 in dashboard):
  - `Diagram.setDiagramData()` (familydiagram `server_types.py`) only writes 5/43 fields — drops emotions, layers, UI flags on local writes (affects PDP undo)
  - Server-side `Diagram.set_diagram_data()` (btcopilot `pro/models/diagram.py`) drops clusters and clusterCacheKey
- CLAUDE.md DiagramData field sync rule added

## Automated Tests (5/5 PASS)

Run: `uv run pytest familydiagram/pkdiagram/tests/models/test_serverfilemanagermodel.py -v -k "preserve or merge or roundtrip or empty_pdp"`

1. `test_save_preserves_server_pdp` - PDP survives Pro save
2. `test_save_preserves_server_clusters` - Clusters survive Pro save
3. `test_save_merges_correctly_on_409_retry` - Merge logic on conflict replay
4. `test_save_scene_roundtrip_fidelity` - All Pro fields survive unchanged
5. `test_save_empty_pdp_stays_empty` - No phantom PDP introduced

## Test Diagrams (seeded on dev server, ids 1973-1979)

All built from real diagram data (cloned from diagram 723 to ensure valid Scene format). All 7 open clean in Pro app via `open_server_diagram` (verified with stdout error checking).

| ID | Name | Contents | Test Purpose |
|----|------|----------|-------------|
| 1973 | T04-01-rich-pdp-minimal-scene | 1 person, 3 PDP people, 3 PDP events, 1 cluster | Pro edits scene, PDP must survive |
| 1974 | T04-02-rich-scene-no-pdp | 68 people (full real diagram), emotions, no PDP | Personal extracts PDP, scene must survive |
| 1975 | T04-03-all-ui-flags-toggled | 1 person, every UI flag set to non-default | Personal saves, all flags must survive |
| 1976 | T04-04-kitchen-sink-both-apps | Full real diagram + PDP + clusters + tags + legendData | Either app edits, nothing lost |
| 1977 | T04-05-empty-new-diagram | Empty | No phantom data introduced |
| 1978 | T04-06-pdp-only-no-scene | No scene items, PDP with 1 person + 1 event, 1 cluster | Pro adds person, PDP survives |
| 1979 | T04-07-layers-and-pruned | 2 people (real format), pruned items, storePositionsInLayers | Personal saves, pruned/layers survive |

---

## Current Architecture: Two Separate Apps

### Manual Test Script

Full round-trip test for each diagram:

| # | Diagram | Step 1: Open in Pro | Step 2: Pro edit + save | Step 3: Open in Personal | Step 4: Personal edit + save | Step 5: Reopen in Pro | Pass criteria |
|---|---------|--------------------|-----------------------|------------------------|-----------------------------|----------------------|---------------|
| 1 | T04-01 | Verify 1 person "Mom" | Add person "Dad", save | Verify scene + PDP shows Alice/Bob/Carol + cluster | Send chat message, save | Verify "Mom"+"Dad", PDP 3 people, cluster | PDP survives Pro; scene survives Personal |
| 2 | T04-02 | Verify 68 people, emotions | Drag a person, save | Verify people/positions/emotions; extract PDP | Accept PDP item, save | Verify positions held, emotions intact, PDP present | Scene survives Personal extraction |
| 3 | T04-03 | Verify all flags non-default | Toggle Hide Names, save | Open, do anything, save | - | All flags still non-default except Hide Names | UI flags survive Personal pass-through |
| 4 | T04-04 | Verify everything present | Add event to a person, save | Verify event + PDP + clusters + tags | Extract PDP, save | Event, layers, pruned, legendData intact | Full round-trip, nothing lost |
| 5 | T04-05 | Verify empty | Add 1 person, save | Verify 1 person, no phantom PDP | Send chat, save | 1 person, no phantom clusters | Empty stays clean |
| 6 | T04-06 | Verify no scene, PDP has "OnlyInPDP" | Add person, save | Verify scene person + PDP person | Accept PDP item, save | Both present | PDP survives first Pro touch |
| 7 | T04-07 | Verify 2 people, pruned items | Move a person, save | Open, save | - | Pruned items intact | Pruned survives Personal pass-through |
| 8 | T04-04 | Both apps open simultaneously | Pro: add event, save | Personal (already open): send chat, save | Reopen in Personal | Pro's event present, Personal's chat history present | Concurrent edits merge via 409; neither app's data lost |

Failure indicators: PDP tab shows "no data" after Pro save, layers gone after Personal save, positions reset to (0,0), UI flags reverted to defaults.

### Test Results

**Legend**: "Human verified" = Patrick manually ran the test and confirmed. "Agentic" = automated harness ran the scenario with no data loss detected. Only human verification counts as DONE.

| # | Result | Verification | Date | Notes |
|---|--------|-------------|------|-------|
| 1 | PASS | Human verified | 2026-04-12 | |
| 2 | PASS | Human verified | 2026-04-12 | |
| 3 | PASS | Human verified | 2026-04-12 | Used Hide Names toggle (scale is ephemeral) |
| 4 | PASS (partial) | Human verified | 2026-04-12 | Patrick ran concurrent variant: opened in Personal, opened in Pro, added event in Pro, sent "ping" in Personal chat, closed+reopened Personal — event survived but chat message+response was gone. **Chat loss is NOT a T0-4 issue** — chat statements are in the Discussion DB table, not DiagramData. Filed in MVP dashboard. |
| 5 | PASS (agentic) | Agentic only | 2026-04-12 | Can't verify person in Personal UI (no diagram view). Used chat + reopen in Pro to confirm person persisted. Needs human verification. |
| 6 | PASS (agentic) | Agentic only | 2026-04-12 | Needs human verification. |
| 7 | PASS (agentic) | Agentic only | 2026-04-12 | Diagram data (people, pruned, event) survived. Chat "ping" lost on reopen — same known bug as #4. Needs human verification. |
| 8 | PASS (agentic) | Agentic only | 2026-04-12 | Pro's event survived in Personal. Chat history lost on Personal reopen — same known bug. Needs human verification. |

---

## Future Architecture: Personal Embedded in Pro

When the Personal app is embedded as a right drawer in the Pro app, both views share one process, one Scene, one Diagram. The save path changes: one `applyChange` must capture both Pro and Personal state. The 409 mechanism still applies for multi-user concurrent access.

### Category 1: Single-user, in-process (shared Scene and DiagramData)

Pro scene and Personal drawer share one process, one Scene object, one Diagram. No server round-trip between them.

| # | Scenario | Steps | Pass criteria | What could break |
|---|----------|-------|---------------|------------------|
| E1 | Pro edit visible to Personal | Open diagram, open Personal drawer, add person in Pro | Personal drawer sees the new person | Shared Scene not wired to Personal's models |
| E2 | Personal chat doesn't corrupt scene | Send chat in Personal drawer | Pro scene unchanged, chat persisted | Chat path accidentally mutates DiagramData |
| E3 | PDP extraction with unsaved Pro edits | Make Pro edit (don't save), trigger extraction | Both Pro edit and extracted PDP present after save | Extraction overwrites in-memory Scene state |
| E4 | PDP accept appears in Pro scene | Accept PDP item in drawer | Committed item visible in Pro scene immediately | `_addCommittedItemsToScene` not called on shared Scene |
| E5 | Pro undo after Personal PDP accept | Accept PDP item, then Cmd+Z in Pro | PDP item removed from scene, pdp state restored | Undo doesn't know about PDP side of the commit |
| E6 | Single save captures both Pro and Personal state | Pro edits scene, Personal accepts PDP, Cmd+S | Server blob has both scene edit and committed PDP item | applyChange only captures one side |
| E7 | Auto-save during PDP extraction | Extraction in progress (async LLM call), auto-save fires | Save captures pre-extraction state; extraction result applied after | Race: half-written PDP in DiagramData at save time |
| E8 | Auto-save during cluster detection | Cluster detection running (async LLM), auto-save fires | Save captures pre-detection clusters; new clusters applied after | Race: cluster state inconsistent at save time |
| E9 | Close diagram during extraction | Start extraction, close diagram before it completes | No crash, no partial PDP written | Extraction callback fires after Scene is gone |

### Category 2: Multi-user concurrent (two embedded instances, same diagram, 409 mechanism)

User A and User B each run Pro+embedded Personal. Both have the same diagram open. Saves go through the server. 409 conflict mechanism resolves concurrent writes.

**Architectural risk**: Today's applyChange is partitioned (Pro sets scene fields, Personal sets personal fields). When embedded, one save must write ALL fields — but on 409 retry, it must not overwrite the other user's changes. The partitioned applyChange pattern must survive embedding, either by:
- (a) Composing two partitioned callbacks in sequence (scene merge then personal merge)
- (b) Tracking which fields actually changed and only writing those
- (c) Server-side partial updates instead of full blob replacement

This is an architectural decision that must be made before embedding ships. These tests validate whichever approach is chosen.

| # | Scenario | Steps | Pass criteria | What could break |
|---|----------|-------|---------------|------------------|
| M1 | Both edit scene | A adds person, saves. B moves person, saves (409 retry). | Both edits on server | B's retry replaces A's people array |
| M2 | A edits scene, B uses Personal | A adds person, saves. B extracts PDP, saves (409). | A's person + B's PDP on server | B's applyChange overwrites A's scene if unified |
| M3 | Both use Personal drawer | A extracts PDP, saves. B sends chat, saves (409). | Both PDP extractions and chat data present | B's retry replaces A's PDP |
| M4 | A accepts PDP, B edits scene | A commits PDP item (people moves from pdp to scene), saves. B adds event, saves (409). | Both committed person and B's event present | B's retry resets people to pre-commit state |
| M5 | Rapid alternating saves | A saves, B saves, A saves, B saves (multiple 409 cycles) | Final state has both users' latest from each partition | Data regresses to earlier state after many retries |
| M6 | One user offline, reconnects | A saves while B is offline. B reconnects, saves (409 with large delta). | B's retry merges onto A's state cleanly | Large version gap causes unexpected merge behavior |

#### Multi-user Test Results

**Legend**: "Agentic" = automated harness ran the scenario with no data loss detected. Only human verification counts as DONE.

| # | Result | Verification | Date | Notes |
|---|--------|-------------|------|-------|
| M1 | PASS (agentic) | Agentic only | 2026-04-15 | Needs human verification. |
| M2 | PASS (agentic) | Agentic only | 2026-04-15 | Needs human verification. |
| M3 | BLOCKED | — | 2026-04-15 | Requires embedded Personal-in-Pro architecture (not yet shipped). Cannot test shared-process multi-user with two separate apps. |
| M4 | BLOCKED | — | 2026-04-15 | Requires embedded Personal-in-Pro architecture. PDP commit moving items between pdp and scene arrays needs single-process shared Scene. |
| M5 | PASS (agentic) | Agentic only | 2026-04-15 | Needs human verification. |
| M6 | PASS (agentic) | Agentic only | 2026-04-15 | Needs human verification. |

### Category 3: Boundary and edge cases

| # | Scenario | Steps | Pass criteria | What could break |
|---|----------|-------|---------------|------------------|
| B1 | PDP commit atomicity | Accept PDP item (moves from pdp to people). Crash before save. Reopen. | Either fully committed or fully in PDP — never half-and-half | Partial commit: item in people AND pdp, or in neither |
| B2 | Chat history survives diagram save | Send chat, save diagram, close, reopen | Chat messages present | Statements in Discussion table not loaded on reopen (KNOWN BUG — filed in MVP dashboard) |
| B3 | Cluster cache key invalidation | Extract PDP (clusters generated), Pro edits scene (adds events), save | clusterCacheKey invalidated so clusters re-detect on next view | Stale clusters displayed after scene changes |
| B4 | Empty diagram round-trip | Both apps open empty diagram, save from each | No phantom data introduced, no crashes | Default values written as explicit data |

#### Boundary Test Results

**Legend**: "Agentic" = automated harness ran the scenario with no data loss detected. Only human verification counts as DONE.

| # | Result | Verification | Date | Notes |
|---|--------|-------------|------|-------|
| B1 | BLOCKED | — | 2026-04-15 | Requires embedded architecture to test crash-during-commit atomicity. Two separate apps can't share in-memory PDP commit state. |
| B2 | KNOWN BUG | — | — | Chat history lost on diagram reopen. Already filed in MVP dashboard. Statements are in Discussion DB table, not DiagramData — not a data integrity issue for this test plan. |
| B3 | BLOCKED | — | 2026-04-15 | Requires embedded architecture. clusterCacheKey invalidation on scene edit needs single-process shared Scene to observe stale cluster behavior. |
| B4 | PASS (agentic) | Agentic only | 2026-04-15 | Needs human verification. |

All embedded tests (Categories 1-3) are blocked until the embedded architecture ships. The current manual test script (tests 1-8) covers the two-separate-app architecture.

---

## Related Issues Found During Testing

### Free Diagram Corruption (Diagram 1924)

7 people (IDs 219, 220, 221, 222, 223, 224, 226) were dropped from `people[]` but their events (13), pair_bonds (6), and items (1) were preserved. All 7 were created in a single PDP commit batch on 2026-04-10.

**Most likely cause**: the pre-fix `applyChange` — the exact bug T0-4 fixes.

**Secondary bug**: `Scene.prune()` removes pair_bonds with orphaned person refs but does NOT check events for orphaned person/spouse/child refs. Events with orphaned person IDs survive indefinitely, causing crashes on next open.

Backed up to `/tmp/corrupt-diagram-1924-backup.fd`. The 7 missing people can be reconstructed from their event data.

### Free Diagram Auto-Arrange (False Alarm)

Two "Free Diagram" records exist: Diagram 723 (68 people, manually arranged by Patrick in 2024) and Diagram 1924 (21 people at position (0,0), Personal app). No auto-arrange capability exists. T2-1 remains open.
