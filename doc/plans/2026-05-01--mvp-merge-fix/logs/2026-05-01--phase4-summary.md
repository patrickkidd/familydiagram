# Phase 4 — E2E Harness Run Summary

**Date:** 2026-05-01
**Operator:** Claude (autonomous)
**Status:** Partial — see Coverage section below.

## Coverage

| Layer | Validation method | Result |
|-------|------------------|--------|
| `apply_local_changes` algorithm | btcopilot unit tests (12 cases) | PASS — `test_apply_local_changes.py` |
| `Diagram.reserve_id_block` model + endpoint | btcopilot unit tests (10 cases) | PASS — `test_reserve_ids.py` |
| `Scene.setIdAllocator` / `nextId` delegation | familydiagram unit tests (5 cases) | PASS — `test_id_allocator.py` |
| Pro × Personal `applyChange` interactions (8 concurrent scenarios) | familydiagram integration tests | PASS — `test_serverfilemanagermodel.py` |
| Full HTTP-stack merge across two simulated clients | btcopilot integration tests (4 J-mirroring cases) | PASS — `test_mvp_merge_integration.py` |
| `_create_inferred_*` 409-replay idempotency | btcopilot unit tests (2 cases) | PASS — `test_inferred_idempotent.py` |
| Latent fix 3a (canonical blob in 200) | btcopilot unit + integration | PASS |
| **MCP-driven UI journeys (Pro app + Personal app concurrent)** | familydiagram-testing MCP harness | **DEFERRED** — see Limitations |

## Harness session log

```
[23:09]  launch_app(ephemeral_server=True, headless=False) → instance d7294bec, server_port 54675  ✓
[23:09]  launch_app(personal=True, server_url=..., headless=False) → instance fe761b02  ✓
[23:46]  open_server_diagram(d7294bec, 2) → success, Pro logged "Opening server diagram from file manager: 2, version: 1"  ✓
         (verified: ServerFileManagerModel binding code reached; allocator binding line entered.)
[23:46]  close_all_instances → 2 closed  ✓
[23:47]  Re-launched both instances headless (per user direction).
[23:47]  Both diagrams opened in respective apps without traceback.
[23:47]  get_app_output(959fd7cc) — output flooded by ~hundreds of QPainter::* warnings/sec
         from headless rendering. The merge-relevant log lines are present but not
         filterable through the current MCP tool surface.
```

## Limitations

The MCP harness is missing two pieces that the JOURNEYS as written depend on:

1. **`save_diagram` bridge command.** Referenced in `familydiagram/CLAUDE.md` (added 2026-04-30) as "Trigger save and block until complete, including all 409 retries. Returns `{success, conflicts}`." Tool not registered with `familydiagram-testing` MCP server. Without it, journeys cannot deterministically force a save and then verify the conflict count.

2. **Server stdout / log capture.** Pro stdout is dominated by Qt headless-rendering warnings (`QPainter::*` ~once per frame). The `reserve_ids` request and `Pushed diagram ...` log lines are present but not extractable from the noise without a `grep`-style tool. `get_app_output(last_n=200)` returns mostly painter spam.

## What this means

The MERGE LOGIC and ID ALLOCATION are validated end-to-end at the Python level by the integration test `test_mvp_merge_integration.py`. That test exercises the same code path the UI would exercise:
- HTTP `PUT /v1/diagrams/{id}` route handler
- `Diagram.update_with_version_check`
- `apply_local_changes` snapshot-diff
- `POST /v1/diagrams/{id}/reserve_ids` endpoint
- Canonical-blob response on 200

The UI-driven journey runs are deferred until the harness gains:
- The `save_diagram` bridge command (in-flight per CLAUDE.md note)
- A way to filter app stdout (or suppress Qt painter noise in headless)

The journeys themselves are recorded in `JOURNEYS.md` and ready to execute once the harness ships those tools. Patrick can then run them on real hardware per the methodology.

## Test totals

- btcopilot: **137 passed, 1 skipped** (full suite of schema, pro, personal tests)
- familydiagram: **27 passed** (id_allocator + serverfilemanagermodel tests touched by this PR)
- New tests added by this PR: **31** across 5 files

## Files

- `/Users/patrick/theapp/btcopilot/btcopilot/tests/schema/test_apply_local_changes.py` — 12 cases
- `/Users/patrick/theapp/btcopilot/btcopilot/tests/schema/test_inferred_idempotent.py` — 2 cases
- `/Users/patrick/theapp/btcopilot/btcopilot/tests/pro/test_reserve_ids.py` — 10 cases
- `/Users/patrick/theapp/btcopilot/btcopilot/tests/pro/test_mvp_merge_integration.py` — 4 cases (J-mirrored)
- `/Users/patrick/theapp/familydiagram/pkdiagram/tests/scene/test_id_allocator.py` — 5 cases
