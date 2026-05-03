# MVP Merge Fix — Manual Test Journeys

Methodology: [doc/TEST_JOURNEYS.md](../../TEST_JOURNEYS.md). Plan: [README.md](README.md).

All journeys use the e2e harness (`familydiagram-testing` MCP). Each runs against an ephemeral btcopilot server with both apps connected. Patrick re-runs after Claude reports `READY FOR USER`.

Logs and screenshots are captured to [logs/](logs/) under `<timestamp>--<journey-id>/`.

---

## Phase 4 prerequisites (Claude implements before running journeys)

These don't exist today; harness work must precede the runs.

- **`seed_server_data(scenario="mvp_merge_baseline")`** — creates a user (`patrick+test@alaskafamilysystems.com`, role `ROLE_SUBSCRIBER`) and one diagram `Diagram 1` (id=1) with three persons A (id=1), B (id=2), C (id=3); person A has `cutoff=False`; one event `E1` (id=10) on person A. Server `lastItemId=10`. Implement in `familydiagram-testing/scenarios/mvp_merge_baseline.py` (or wherever harness scenarios live).
- **Local-file fixture** for J-5 — script that writes a `.fd` bundle to the sandbox dir before launching Pro. Path returned in launch_app metadata.
- **Server-stdout capture path** — harness writes ephemeral server stdout to a known sandbox file so journeys can `grep` it for `reserve_ids` requests. Document the path returned by `launch_app(ephemeral_server=True)`.

---

## Common pre-flight

> ```bash
> export RUN_TAG="$(date +%H%M%S%N | head -c 12)"
> echo "RUN_TAG=$RUN_TAG"
> ```

Every test artifact name embeds `$RUN_TAG`. Every DB verification filters by it.

Per-journey setup (Claude executes):
1. `launch_app(appType="pro", ephemeral_server=True, headless=False)` → `{instance_id: pro_id, server_port, server_log_path, sandbox_dir}`.
2. `launch_app(appType="personal", server_url=f"http://127.0.0.1:{server_port}")` → `{instance_id: personal_id}`.
3. `seed_server_data(instance_id=pro_id, scenario="mvp_merge_baseline")`.

`close_all_instances()` after each journey (also at journey failure to keep sandboxes clean).

**DB verification helper** (used by every journey):

```bash
# Saved as $JOURNEY_DIR/verify_db.sh, dumps person rows with name + id + selected fields.
curl -s -H "Cookie: session=test" "http://127.0.0.1:${SERVER_PORT}/v1/diagrams/1" \
  | uv run python -c "
import sys, pickle
import PyQt5.sip
data = pickle.load(sys.stdin.buffer)
for p in data.get('people', []):
    print(f\"id={p.get('id')} name={p.get('name')} cutoff={p.get('cutoff')}\")
for e in data.get('events', []):
    print(f\"event id={e.get('id')} person={e.get('person')}\")
print(f\"lastItemId={data.get('lastItemId')}\")
"
```

---

## J-1A — Pro left open while Personal edits a different person — Status: PENDING

**Tests goal G1:** Pro's stale snapshot does not clobber Personal's field edits to a different item when Pro saves.

**Pre-conditions:** Common pre-flight done. Server has persons A, B, C.

**Steps:**

1. `open_server_diagram(pro_id, id=1)`. **Observable:** `get_status(pro_id) == {appType:"pro", serverDiagramId:1, sceneLoaded:true}`.
2. `open_server_diagram(personal_id, id=1)`. **Observable:** `get_status(personal_id) == {appType:"personal", serverDiagramId:1, sceneLoaded:true}`.
3. `find_element(personal_id, kind="person", name="A")`. **Observable:** returns element id (non-null).
4. `click(personal_id, element_id_from_step_3)`. **Observable:** `personal_state(personal_id).pdpSheet.visible == true`.
5. `input(personal_id, field="personPropertiesName", value=f"A_PE_{RUN_TAG}")`. **Observable:** `prop(personal_id, "personPropertiesName") == f"A_PE_{RUN_TAG}"`.
6. `save_diagram(personal_id)`. **Observable:** returns `{success:true, conflicts:0}`.
7. `find_element(pro_id, kind="person", name="B")`. **Observable:** returns element id.
8. `click(pro_id, element_id_from_step_7)`. **Observable:** Pro's person-properties drawer opens.
9. `input(pro_id, field="personPropertiesName", value=f"B_PR_{RUN_TAG}")`. **Observable:** Pro's drawer shows new name.
10. `save_diagram(pro_id)`. **Observable:** returns `{success:true, conflicts:1}`. (Conflict count proves merge code fired.)
11. Run `verify_db.sh`. **Observable:** stdout contains both `id=1 name=A_PE_<RUN_TAG>` and `id=2 name=B_PR_<RUN_TAG>`.

**Pass criterion:** Step 11 stdout contains BOTH `name=A_PE_<RUN_TAG>` AND `name=B_PR_<RUN_TAG>`.

**Fail signs:**
| Observed | Means |
|----------|-------|
| Person A name reverted to "A" | Pro's stale snapshot clobbered Personal's edit — bug not fixed |
| Person B name not present | Pro's edit didn't apply — different bug |
| Step 10 returns `conflicts:0` | 409 didn't fire — merge code path not exercised; rerun |
| Traceback in either app's stdout | Bug in merge or save path |

---

## J-1B — Personal open while Pro edits, then Personal auto-saves — Status: PENDING

**Tests goal G2 (mirror of J-1A).**

**Pre-conditions:** Common pre-flight done.

**Steps:**

1. `open_server_diagram(personal_id, id=1)`. **Observable:** sceneLoaded.
2. `open_server_diagram(pro_id, id=1)`. **Observable:** sceneLoaded.
3. `find_element(pro_id, kind="person", name="C")`. **Observable:** returns element id.
4. `click(pro_id, element_from_step_3)`. **Observable:** Pro's drawer opens.
5. `input(pro_id, field="personPropertiesName", value=f"C_PR_{RUN_TAG}")`. **Observable:** Pro's drawer shows new name.
6. `save_diagram(pro_id)`. **Observable:** returns `{success:true, conflicts:0}`.
7. `find_element(personal_id, kind="person", name="A")`. **Observable:** returns element id.
8. `click(personal_id, element_from_step_7)`. **Observable:** `personal_state(personal_id).pdpSheet.visible == true`.
9. `input(personal_id, field="personPropertiesName", value=f"A_PE_{RUN_TAG}")`. **Observable:** Personal's drawer shows new name.
10. `save_diagram(personal_id)` (forces save explicitly even though Personal auto-saves; the bridge call also confirms completion). **Observable:** returns `{success:true, conflicts:1}`.
11. Run `verify_db.sh`. **Observable:** contains both `name=C_PR_<RUN_TAG>` and `name=A_PE_<RUN_TAG>`.

**Pass criterion:** Both name strings present in step 11.

**Fail signs:** Same shape as J-1A.

---

## J-2A — Personal deletes an event, Pro saves later — Status: PENDING

**Tests goal G3:** Deletion survives the other side's save.

**Pre-conditions:** Common pre-flight done. Event E1 (id=10) exists on person A.

**Steps:**

1. `open_server_diagram(pro_id, id=1)`. **Observable:** sceneLoaded.
2. `open_server_diagram(personal_id, id=1)`. **Observable:** sceneLoaded.
3. `find_element(personal_id, kind="event", id=10)`. **Observable:** returns element id.
4. `click(personal_id, element_from_step_3)`. **Observable:** event-properties drawer or selection visible.
5. Trigger event delete via Personal's UI: `click(personal_id, name="deleteEventButton")` or equivalent. **Observable:** `get_app_state(personal_id).events` no longer contains id=10.
6. `save_diagram(personal_id)`. **Observable:** returns `{success:true, conflicts:0}`.
7. `find_element(pro_id, kind="person", name="B")`. **Observable:** returns element id.
8. `input(pro_id, field="personPropertiesName", value=f"B_PR_{RUN_TAG}")`. **Observable:** Pro's drawer shows new name.
9. `save_diagram(pro_id)`. **Observable:** returns `{success:true, conflicts:1}`.
10. Run `verify_db.sh`. **Observable:** stdout contains `name=B_PR_<RUN_TAG>` AND no line starting with `event id=10`.

**Pass criterion:** Both: B has new name AND no event id=10 in DB.

**Fail signs:**
| Observed | Means |
|----------|-------|
| Line `event id=10 ...` present | Pro's stale snapshot resurrected the deleted event — bug not fixed |
| `name=B_PR_<RUN_TAG>` missing | Pro's edit lost — different bug |

---

## J-2B — Pro deletes a person, Personal auto-saves later — Status: PENDING

**Tests goal G3 mirror.**

**Pre-conditions:** Common pre-flight done.

**Steps:**

1. `open_server_diagram(personal_id, id=1)`. **Observable:** sceneLoaded.
2. `open_server_diagram(pro_id, id=1)`. **Observable:** sceneLoaded.
3. `find_element(pro_id, kind="person", id=3)`. **Observable:** returns element id (person C).
4. `click(pro_id, element_from_step_3)`. **Observable:** Pro's selection model includes person C.
5. Trigger Pro delete: `click(pro_id, name="actionDelete")`. **Observable:** `get_app_state(pro_id).people` no longer contains id=3.
6. `save_diagram(pro_id)`. **Observable:** returns `{success:true, conflicts:0}`.
7. (Now force a Personal save while Personal still has id=3 in its stale view.) `find_element(personal_id, kind="event", id=10)`. **Observable:** returns element id.
8. `click(personal_id, element_from_step_7)`. **Observable:** event drawer opens.
9. `click(personal_id, name="deleteEventButton")`. **Observable:** event id=10 removed from Personal's local state.
10. `save_diagram(personal_id)`. **Observable:** returns `{success:true, conflicts:1}`.
11. Run `verify_db.sh`. **Observable:** no line `id=3 name=C ...`.

**Pass criterion:** No person id=3 in DB after step 11.

**Fail signs:**
| Observed | Means |
|----------|-------|
| `id=3 name=C ...` present | Personal's stale snapshot resurrected the deleted person — bug not fixed |

---

## J-3 — Both add new items concurrently, no id collision — Status: PENDING

**Tests goal G4:** Block allocation prevents `lastItemId` collision.

**Pre-conditions:** Common pre-flight done. Server `lastItemId=10`.

**Steps:**

1. `open_server_diagram(pro_id, id=1)`. **Observable:** server log file contains `POST /v1/diagrams/1/reserve_ids` (grep `${SERVER_LOG_PATH}` for that exact substring; expect exactly one match).
2. `open_server_diagram(personal_id, id=1)`. **Observable:** server log contains no additional `reserve_ids` (Personal does not reserve).
3. `click(pro_id, name="addPersonAction")`. **Observable:** `get_app_state(pro_id).people` length increased by 1; the new person's `id` field is in the range [11, 110] (Pro's reserved block, since baseline `lastItemId` was 10).
4. `input(pro_id, field="personPropertiesName", value=f"NewPro_{RUN_TAG}")`. **Observable:** Pro's drawer shows new name.
5. `inject_pdp_data(personal_id, scenario="single_person", name=f"NewPe_{RUN_TAG}")`. **Observable:** `get_app_state(personal_id).pdp.people` length increased by 1.
6. `click(personal_id, name="acceptAllPDPItems")`. **Observable:** `get_app_state(personal_id).pdp.people` length is 0; `get_app_state(personal_id).people` length increased by 1.
7. `save_diagram(personal_id)`. **Observable:** returns `{success:true}`.
8. `save_diagram(pro_id)`. **Observable:** returns `{success:true, conflicts:1}`.
9. Run `verify_db.sh`. **Observable:** stdout contains BOTH `name=NewPro_<RUN_TAG>` AND `name=NewPe_<RUN_TAG>`. The two `id=` values printed for these names are NOT equal. The Pro one's id is in [11, 110]; the Personal one's id is > 110.

**Pass criterion:** Both names present in DB AND their ids do not collide AND ranges match expectations.

**Fail signs:**
| Observed | Means |
|----------|-------|
| Pro's id == Personal's id | Block allocation broken — collision occurred |
| One of the names missing | Merge dropped one — separate bug |
| Pro's id outside [11, 110] | Block allocator not bound; Scene fell back to local counter |
| Personal's id ≤ 110 | Server `lastItemId` not advanced by reservation |
| No `reserve_ids` line in server log after step 1 | Allocator not requesting block on diagram open |

---

## J-4 — Allocator block refill mid-session — Status: PENDING

**Tests:** Pro's allocator can request a second block when its first block is exhausted.

**Pre-conditions:** Common pre-flight done. (Effectively forces refill by setting `BLOCK_SIZE=3` for this run via env var read by the allocator; alternatively, add 100 persons in step 4. Document: configurable for test reproducibility.)

**Setup:** Set `FAMILYDIAGRAM_BLOCK_SIZE=3` before launching Pro for this journey.

**Steps:**

1. `open_server_diagram(pro_id, id=1)`. **Observable:** server log contains exactly one `POST /v1/diagrams/1/reserve_ids` with `count=3`. Server returns `{start:11, end:13}`.
2. `click(pro_id, name="addPersonAction")` four times consecutively (each adds a person). **Observable:** after the 4th add, `get_app_state(pro_id).people` shows 7 persons total. Their ids include 11, 12, 13 (first block) AND a fourth id from a NEW block (e.g., 14 if Personal hasn't allocated, or higher if it has).
3. **Observable:** server log now contains exactly TWO `POST /v1/diagrams/1/reserve_ids` entries.
4. `save_diagram(pro_id)`. **Observable:** `{success:true}`.
5. Run `verify_db.sh`. **Observable:** all four added persons present, ids do not duplicate.

**Pass criterion:** Two block requests visible in server log AND four added persons all have distinct ids.

**Fail signs:**
| Observed | Means |
|----------|-------|
| Only one block request | Refill logic broken — fourth `nextId()` returned a duplicate or stale id |
| Person id duplicate | Refill returned an overlapping range |
| Traceback at 4th add | Refill error not handled cleanly |

---

## J-5 — Pro opens local `.fd` file (no server) — Status: PENDING

**Tests goal G6:** Local file open is unchanged. No allocator binding, no server traffic for ids.

**Pre-conditions:**
- Phase 4 prereq: harness has placed a baseline `.fd` file at `${SANDBOX_DIR}/baseline.fd` containing 1 person (id=1, lastItemId=1).

**Steps:**

1. `launch_app(appType="pro", headless=False)`. (No `ephemeral_server`, no `server_url`.) **Observable:** `get_status(pro_id) == {appType:"pro", serverDiagramId:null}`.
2. `open_file(pro_id, path="${SANDBOX_DIR}/baseline.fd")`. **Observable:** `get_status(pro_id).sceneLoaded == true`.
3. `click(pro_id, name="addPersonAction")`. **Observable:** `get_app_state(pro_id).people` shows 2 persons. The new person's `id == 2` (sequential per local counter).
4. **Observable:** No process listening on a port for this Pro instance attempted any HTTP request (since no server URL was configured). Confirmed by `pro_id` not having a `server_port` in its launch metadata.

**Pass criterion:** Person id is 2 AND no allocator-binding code path executed (verifiable by absence of a `server_url` configured on `pro_id`).

**Fail signs:**
| Observed | Means |
|----------|-------|
| Person id ≠ 2 | Allocator was bound to local-file Scene (shouldn't be) |
| Traceback on add | Allocator binding path runs unconditionally |

---

## J-6 — Same-item bidirectional edit (item-level LWW documented) — Status: PENDING

**Tests:** When Pro and Personal both edit DIFFERENT FIELDS on the SAME item, item-level last-write-wins applies — the second saver's full item dict overwrites the first saver's changes for that item. **This is documented MVP behavior, not a bug.** Field-level LWW is deferred to v3.

**Pre-conditions:** Common pre-flight done.

**Steps:**

1. `open_server_diagram(pro_id, id=1)`. **Observable:** sceneLoaded.
2. `open_server_diagram(personal_id, id=1)`. **Observable:** sceneLoaded.
3. Personal: edit person A's `cutoff` field to `True`. (Click on A, set the cutoff toggle.) **Observable:** `prop(personal_id, "personPropertiesCutoff") == true`.
4. `save_diagram(personal_id)`. **Observable:** `{success:true, conflicts:0}`.
5. Run `verify_db.sh`. **Observable:** `id=1 name=A cutoff=True` is present.
6. Pro: edit person A's `name` to `f"A_PR_{RUN_TAG}"`. **Observable:** Pro's drawer shows new name. (Pro's local snapshot of A still has `cutoff=False` because Pro hasn't refreshed.)
7. `save_diagram(pro_id)`. **Observable:** `{success:true, conflicts:1}`.
8. Run `verify_db.sh`. **Observable:** `id=1 name=A_PR_<RUN_TAG> cutoff=False` — Pro's name change applied AND Pro's stale `cutoff=False` overwrote Personal's `cutoff=True`.

**Pass criterion:** DB shows `name=A_PR_<RUN_TAG>` AND `cutoff=False`. (NOT `cutoff=True`.) This documents the item-level LWW behavior.

**Fail signs:**
| Observed | Means |
|----------|-------|
| `cutoff=True` in DB after step 8 | Field-level merge somehow happened (which would be unexpected with snapshot-diff design — investigate) |
| `name` not updated | Pro's save didn't apply at all |

**Note for Patrick:** This journey PASSES when the user-visible behavior matches the design's stated tradeoff. If a real customer hits this and complains, it's a v3 work item, not an MVP regression.

---

## J-7 — `_create_inferred_*` idempotency on 409 retry (latent fix 3b) — Status: PENDING

**Tests latent fix 3b:** PDP commit on 409 retry does not duplicate inferred items.

**Pre-conditions:** Common pre-flight done.

**Steps:**

1. `open_server_diagram(pro_id, id=1)`. **Observable:** sceneLoaded.
2. `open_server_diagram(personal_id, id=1)`. **Observable:** sceneLoaded.
3. `inject_pdp_data(personal_id, scenario="birth_event_with_unknown_parent", child_name=f"Child_{RUN_TAG}")`. **Observable:** `get_app_state(personal_id).pdp.events` length increased by 1.
4. (Force a 409 by saving from Pro first to bump server version.) `find_element(pro_id, kind="person", name="A")`; `input(pro_id, field="personPropertiesName", value=f"A_PR_{RUN_TAG}")`; `save_diagram(pro_id)`. **Observable:** `{success:true, conflicts:0}`.
5. `click(personal_id, name="acceptAllPDPItems")`. **Observable:** `get_app_state(personal_id)` shows PDP cleared and committed items present locally.
6. `save_diagram(personal_id)`. **Observable:** `{success:true, conflicts:1}` (the 409 forces commit_pdp_items to re-run on retry).
7. Run `verify_db.sh`. Count rows with `name=Child_<RUN_TAG>` (should be 1, not 2). Count `event id=...` rows where the event is the synthetic Birth (should be 1). Count any synthetic pair_bond items inferred for the child's parents (should be 1, not 2).

**Pass criterion:** Each inferred-or-committed entity appears exactly once. No duplicates.

**Fail signs:**
| Observed | Means |
|----------|-------|
| 2 rows with `Child_<RUN_TAG>` | `_create_inferred_birth_items` ran twice without idempotency check — fix 3b broken |
| 2 inferred pair_bond rows for the same parents | `_create_inferred_pair_bond_items` not idempotent |

---

## J-8 — Server canonical-blob preserved across save (latent fix 3a) — Status: PENDING

**Tests latent fix 3a:** Server-side post-processing on the saved blob is reflected in the client's snapshot, so subsequent edits don't revert it.

**Pre-conditions:** Common pre-flight done.

**Setup:** Configure server to inject a known post-processing on save (e.g., add a marker field `data["serverProcessed"] = True`). For this test, instrument the Pro endpoint to set `data["lastTouchedBy"] = "server"` on every save.

**Steps:**

1. `open_server_diagram(pro_id, id=1)`. **Observable:** sceneLoaded.
2. `find_element(pro_id, kind="person", name="A")`; `input(pro_id, field="personPropertiesName", value=f"A1_{RUN_TAG}")`; `save_diagram(pro_id)`. **Observable:** `{success:true}`. Server's stored blob now has `lastTouchedBy="server"` and `name="A1_<RUN_TAG>"`.
3. (Verify client's local cache reflects server's post-processed state.) `get_app_state(pro_id).extra.lastTouchedBy` (or via instrumentation observing `Diagram.data` after save). **Observable:** equals `"server"`.
4. `find_element(pro_id, kind="person", name="B")`; `input(pro_id, field="personPropertiesName", value=f"B1_{RUN_TAG}")`; `save_diagram(pro_id)`. **Observable:** `{success:true, conflicts:0}` (no other client present, so no 409).
5. Run `verify_db.sh` with extended dump showing the `lastTouchedBy` field. **Observable:** field is present on the stored blob (server set it again on this save).

**Pass criterion:** After step 5, server's blob has `lastTouchedBy="server"` AND person A name is `A1_<RUN_TAG>` AND person B name is `B1_<RUN_TAG>`. None of the server's post-processing was reverted by the client's stale snapshot.

**Fail signs:**
| Observed | Means |
|----------|-------|
| Step 3 shows `lastTouchedBy != "server"` | Client's `Diagram.data` post-200 wasn't refreshed from server's response — fix 3a broken |
| Step 5 shows `name=A` (reverted from A1) | Client's snapshot was the bytes-it-sent, server's post-processing reverted on next save |

---

## Status summary

| Code | Goal | Status |
|------|------|--------|
| J-1A | G1 — Pro saves preserves Personal's edits to a different item | PENDING |
| J-1B | G2 — Personal saves preserves Pro's edits to a different item | PENDING |
| J-2A | G3 — Personal deletes survive Pro's save | PENDING |
| J-2B | G3 — Pro deletes survive Personal's save | PENDING |
| J-3  | G4 — Concurrent adds get distinct ids (block allocation) | PENDING |
| J-4  | Block allocator refill mid-session | PENDING |
| J-5  | G6 — Local `.fd` open unchanged | PENDING |
| J-6  | Same-item bidir edit → item-level LWW (documented behavior) | PENDING |
| J-7  | Latent fix 3b — `_create_inferred_*` idempotent on 409 retry | PENDING |
| J-8  | Latent fix 3a — server canonical blob preserved | PENDING |

J-4 (Pro × Pro) from earlier draft removed: it's a duplicate of J-1A's mechanism with different launch counts. If real-world Pro × Pro becomes a concern, add as separate journey later.
