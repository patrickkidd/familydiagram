# FMEA: DiagramData Concurrent Save Integrity

Date: 2026-04-12
Scope: Pro/Personal app concurrent saves, 409 conflict merge, field ownership

## Architecture

Both apps save via `Diagram.save()` → `applyChange(diagramData)` → PUT to server. On 409 (version mismatch), the server returns its latest blob and the client replays `applyChange` on it. Each app's `applyChange` explicitly sets only the fields it owns.

## What T0-4 Fixed

Pro app's `applyChange` was replacing the entire DiagramData. Now it explicitly sets ~35 Scene-owned fields, leaving Personal-owned fields (pdp, clusters, clusterCacheKey) untouched.

## Failure Modes — Field Ownership (T0-4 scope)

| # | Failure Mode | Trigger | Severity | Status | Test |
|---|---|---|---|---|---|
| F1 | PDP destroyed by Pro save | Pro's applyChange replaces entire DiagramData | Critical | **FIXED** (T0-4) | `test_save_preserves_server_pdp` |
| F2 | Clusters destroyed by Pro save | Same as F1 | Critical | **FIXED** (T0-4) | `test_save_preserves_server_clusters` |
| F3 | PDP destroyed on 409 retry | Pro replays applyChange on server's latest | Critical | **FIXED** (T0-4) | `test_save_merges_correctly_on_409_retry` |
| F4 | UI flags survive Personal save | Personal doesn't set UI flags | None | **SAFE** | `test_concurrent_ui_flags_survive_personal_apply` |
| F5 | Clusters survive Pro save | Pro doesn't set clusters | None | **SAFE** | `test_concurrent_clusters_survive_pro_apply` |
| F6 | PDP survives Pro save (full PDP) | Pro doesn't set pdp | None | **SAFE** | `test_concurrent_pdp_survives_pro_apply` |
| F7 | Empty PDP stays empty | No phantom data from merge | None | **SAFE** | `test_save_empty_pdp_stays_empty` |
| F8 | Scene data roundtrips correctly | Pro's explicit field list matches DiagramData | None | **SAFE** | `test_save_scene_roundtrip_fidelity` |
| F9 | hideSARFGraphics missing from Scene.diagramData() | Field in DiagramData but not in diagramData() kwargs | Medium | **FIXED** | scene.py updated |

## Failure Modes — Concurrent Scene Collection Writes (pre-existing, NOT fixed by T0-4)

Both apps write scene collections (people, events, pair_bonds, etc.) — Personal writes them because it commits PDP items into the scene and saves. This means scene collections are NOT a disjoint partition. On 409 retry, the retrying app's `applyChange` replaces these lists wholesale from its local state, destroying anything the other app added.

| # | Failure Mode | Trigger | Severity | Status | Test |
|---|---|---|---|---|---|
| C1 | Pro's person lost when Personal retries on 409 | Personal's applyChange replaces `people` from its scene | Critical | **KNOWN** — pre-existing | `test_concurrent_personal_saves_first_pro_replays` (documents limitation) |
| C2 | Personal's committed PDP person lost when Pro retries on 409 | Pro's applyChange replaces `people` from its scene, which doesn't have the committed person | Critical | **KNOWN** — pre-existing | `test_concurrent_pdp_commit_then_pro_saves_stale` (documents limitation) |
| C3 | Same as C1/C2 for events, pair_bonds, emotions, layers | Wholesale list replacement on 409 retry | Critical | **KNOWN** — pre-existing | Documented in test comments |
| C4 | lastItemId regression on 409 retry | App's stale lastItemId overwrites server's higher value | Critical | **KNOWN** — pre-existing | Not yet fixed; should use `max(server, local)` |
| C5 | Alternating saves cascade data loss | Each 409 retry overwrites scene collections from stale local state | Critical | **KNOWN** — pre-existing | `test_concurrent_alternating_saves_three_rounds` |

## Failure Modes — Error Handling

| # | Failure Mode | Trigger | Severity | Status |
|---|---|---|---|---|
| E1 | Pro save exhausts retries — shows dialog | 3x consecutive 409 | Medium | **HANDLED** — QMessageBox shown |
| E2 | Personal saveDiagram exhausts retries — silent failure | 3x consecutive 409 | High | **NOT HANDLED** — no user notification |
| E3 | Personal PDP accept exhausts retries — logs warning only | 3x consecutive 409 | Medium | **PARTIAL** — logged but not user-visible |

## Failure Modes — Boundary Cases

| # | Failure Mode | Trigger | Severity | Status |
|---|---|---|---|---|
| B1 | Chat history lost on diagram reopen | Statements in Discussion DB table not loaded | High | **KNOWN BUG** — filed in MVP dashboard |
| B2 | Prune gap: orphaned events not cleaned | Scene.prune() checks pair_bonds but not events for orphaned person refs | Medium | **KNOWN** — not yet filed |
| B3 | Diagram 1924 corruption (7 people lost) | Pre-fix applyChange during 409 retry | Critical | **ROOT CAUSE FIXED** by T0-4; data reparable |

## Mitigation Summary

**Fixed by T0-4:** F1-F3, F9, B3. Personal-owned fields (pdp, clusters, clusterCacheKey) are now safe from Pro app overwrites.

**Pre-existing, not addressed:** C1-C5 (scene collection wholesale replacement on concurrent writes). The architectural fix is to merge scene collections rather than replace them, or to use server-side partial updates. This is a future architectural decision documented in `familydiagram/doc/plans/diagram-data-integrity-tests.md`.

**Quick fix available:** C4 (lastItemId regression) — change to `max(diagramData.lastItemId, localData.get("lastItemId", 0))` in both apps' applyChange.

## Related Tests

22 automated tests in `familydiagram/pkdiagram/tests/models/test_serverfilemanagermodel.py`:
- 5 FR-2 merge tests (T0-4 fix validation)
- 7 concurrent save simulation tests (field ownership verification + known limitation documentation)
- 10 existing tests (index, sync, cache, save roundtrip)
