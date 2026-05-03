# Data Integrity

**Last updated:** 2026-04-17. **Status of each item is in the table below.**

---

## TL;DR

Two apps share one diagram blob via concurrent saves. Fixes group into three piles:

1. **Stop writers from corrupting data** (5 items)
2. **Stop readers from crashing on already-corrupt data** (2 items)
3. **Personal app UI gaps**, unrelated to scene blob (2 items)

Diagram 1924 is **not** in scope: chat history lives in the `Discussion` DB table (independent of diagram blob), and the diagram data itself is reproducible by re-extraction in Personal. After items 1, 4, 5 land, re-extract 1924; item 2's crash guard makes it safe to open in the meantime.

---

## Mental Model

```
       ┌────────┐  edits   ┌────────┐  applyChange  ┌──────────┐
       │  Pro   │─────────→│ Scene  │──────────────→│  Server  │
       └────────┘          └────────┘               │  blob    │
                                                    │ (pickle) │
       ┌────────┐  edits   ┌────────┐  applyChange  │          │
       │Personal│─────────→│PDP +   │──────────────→│          │
       │        │          │Scene   │               └──────────┘
       └────────┘          └────────┘                     │
                                ▲                         │
                                └──── read + prune ───────┘

WRITERS THAT CAN CORRUPT (priority 1):
  • applyChange wholesale-replace on 409 retry  [merge fix]   ← Pro AND Personal
  • setDiagramData writes only some fields      [field cov]   ← 3 copies
  • commit_pdp_items partial mutation           [atomicity]
  • _addCommittedItemsToScene silent fault      [race]        ← LIVE post-T0-4
  • Scene.prune doesn't cascade events          [cascade]

READERS THAT CRASH ON CORRUPT DATA (priority 2):
  • Scene.prune null deref on missing person    [crash guard]
  • Emotions and→or logic typo                  [logic fix]

ALREADY CORRUPT:
  • Diagram 1924: 7 missing people, 13 orphan events, 6 orphan pair_bonds, pruned[] empty
    → confirmed via DB query 2026-04-17, NOT pruner-related → producer-side root cause

UI GAPS (independent track):
  • Chat history disappears on tab switch
  • Chat history disappears on diagram reopen
  • Chat discussions hardcoded to free_diagram_id
  • Save failures fail silently
```

---

## Status

Patrick: edit `Status` column inline. `PASS` / `FAIL` / blank.

| # | Item | Test | Status |
|---|------|------|:------:|
| 1 | **Concurrent merge** — `merge_scene_collection` in `schema.py` + use in both `applyChange` callbacks (Pro + Personal) | Open T04-04 in both apps; both add data; both save; reopen each → both sides preserved | PASS |
| 2 | **Reader crash guard** — null-check in `Scene.prune` event loop + emotions `and`→`or` | Open Diagram 1924 in Pro → no traceback (may show fewer items, that's fine) | |
| 3 | **Prune cascade** — when `Scene.prune` removes a pair_bond/person, also remove referencing events | pytest only (synthetic blob) | |
| 4 | **commit_pdp_items atomic** — snapshot scene/pdp lists at entry; rollback on any exception | pytest only (forced fault via monkeypatch) | |
| 5 | **commit→Scene race** — try/except around `_addCommittedItemsToScene` body; on fault, force `_refreshDiagram()` and surface a toast | pytest + (optional) `--inject-commit-fault` debug flag | |
| 6 | **Field coverage** — fix all 3 copies of partial-write `setDiagramData` to write all 43 fields | Open T04-03 (all UI flags toggled), Personal extracts → all flags survive in Pro | |
| 7 | **Chat history persists** — endpoint returns both user+AI statements; client appends to `_statements`; QML resets `initSelectedDiscussion` on diagram change | Send chat, switch tab and back → message persists. Send chat, close diagram (no app kill), reopen → message persists. | |
| 8 | **Discussion uses client diagram_id** — `_create_discussion` reads from request body | pytest only (multi-diagram not in MVP UI) | |
| 9 | **Save failure surface** — toast/banner with retry on save error | Disconnect network, save → banner appears with Retry; reconnect, click Retry → save succeeds | |

---

## Locked decisions

- **Scene-collection merge** on 409: union by ID, local wins on conflict
- **Chat send**: endpoint returns both user + AI statements (one round-trip)
- **Multi-diagram chat**: fix `_create_discussion` to honor client `diagram_id` now
- **Save failure UI**: toast/banner with retry, not modal
- **Event orphans**: fix producers; NO read-time prune (would mask producer bugs — confirmed by 1924 root-cause investigation)

## Open decisions

None. Q1 (1924 fixup) resolved by dropping the item — chat is in a separate DB table; diagram data is reproducible via re-extraction. Q2 (toast component) resolved: new shared `PersonalToast.qml`, used by items 5 and 9.

---

## Common Setup (run once before any manual test)

```bash
curl -s http://127.0.0.1:8888/ > /dev/null && echo OK || echo "ERROR: start Flask on 8888"
docker ps --filter name=fd-postgres --format "{{.Status}}" | grep -q "Up" && echo OK || echo "ERROR: docker compose up"
docker exec fd-postgres psql -U familydiagram -d familydiagram -c "SELECT count(*) FROM diagrams WHERE id BETWEEN 1973 AND 1979;"  # expect 7
cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env make
```

**Launch:**
- Pro: `uv run python -m pkdiagram`
- Personal: `uv run python -m pkdiagram --personal`

---

## Manual journeys (one per item that has one)

Each journey is a robotic checklist. Patrick: write `PASS` or `FAIL: <reason>` next to the journey heading after running.

### Journey-1A (Item 1: Pro saves first → Personal hits 409 → Personal merges) — Status:

**Tests:** Personal's `applyChange` correctly merges Pro's people additions into its own payload on 409 retry — both sides' data survive.

**Trigger:** Pro saves first (bumping server version). Personal then deletes an event, which auto-saves immediately and hits 409. On retry the merge must preserve Pro's new person while applying Personal's deletion.

#### Pre-flight

> ```bash
> uv run python /Users/patrick/theapp/familydiagram/doc/plans/2026-04-17--data-integrity/fixtures/seed_journey_1a.py
> ```
> Expect: `Seeded: 71 → 71 people, hideNames=False, DB version now <N>`.

#### Steps

1. Launch **Pro** via VSCode debug target "Pro".

2. Double-click `T04-04-kitchen-sink-both-apps` in Pro.

3. Launch **Personal** via VSCode debug target "Personal".

4. In Personal, open `T04-04-kitchen-sink-both-apps`.

5. In Pro, add one male person to the canvas and set their First Name to `J1A`.

6. In Pro, press Cmd+S.

7. In Personal, delete any event on the canvas (tap event → delete). Personal auto-saves immediately — no gesture needed.

8. Close and reopen T04-04 in Pro.

9. Close and reopen T04-04 in Personal.

10. Verify DB:
    ```bash
    uv run python - <<PYEOF
    import base64, pickle, subprocess
    import PyQt5.sip
    out = subprocess.check_output(['docker','exec','fd-postgres','psql','-U','familydiagram','-d','familydiagram','-tAc',"SELECT encode(data,'base64') FROM diagrams WHERE id=1976"]).decode().strip()
    data = pickle.loads(base64.b64decode(out))
    names = [str(p.get('name') or '') for p in data.get('people', [])]
    print('person_present:', any(n.startswith('J1A') for n in names))
    print('people_count:', len(names))
    PYEOF
    ```
    **Observable:** `person_present: True` and `people_count: 72`.

#### Pass criterion

1. Close and reopen T04-04 in **Pro** — `J1A` person is visible on the canvas.
2. Close and reopen T04-04 in **Personal** — `J1A` person is visible.
3. DB check confirms `person_present: True` and `people_count: 72`.
4. No `Traceback` in either app's VSCode Debug Console.

#### Fail signs

| Observed | Means |
|----------|-------|
| `person_present: False` | Merge overwrote Pro's people list — bug in `applyChange` merge logic |
| `people_count < 72` | People were lost during merge |
| Traceback in either Debug Console | Bug in merge or save path; copy and report |

---

### Journey-1B (Item 1: Personal saves first → Pro hits 409 → Pro merges) — Status:

Mirror of 1A with roles swapped: Personal saves first (bumping the version); Pro then adds a person and saves, hitting 409, and Pro's merge must preserve that person.

Personal cannot add people — it is scene-read-only except via PDP commit. The version bump comes from Personal deleting an event (same auto-save trigger as 1A).

#### Pre-flight

> ```bash
> uv run python /Users/patrick/theapp/familydiagram/doc/plans/2026-04-17--data-integrity/fixtures/seed_journey_1a.py
> ```
> Expect: `Seeded: 71 → 71 people, 19 events, …`

#### Steps

1. Launch **Pro** via VSCode debug target "Pro".

2. Double-click `T04-04-kitchen-sink-both-apps` in Pro.

3. Launch **Personal** via VSCode debug target "Personal".

4. In Personal, open `T04-04-kitchen-sink-both-apps`.

5. In Personal, delete any event. Personal auto-saves immediately.

6. In Pro, add one male person and set their First Name to `J1B`.

7. In Pro, press Cmd+S.

8. Close and reopen T04-04 in Pro.

9. Verify DB:
    ```bash
    uv run python - <<PYEOF
    import base64, pickle, subprocess
    import PyQt5.sip
    out = subprocess.check_output(['docker','exec','fd-postgres','psql','-U','familydiagram','-d','familydiagram','-tAc',"SELECT encode(data,'base64') FROM diagrams WHERE id=1976"]).decode().strip()
    data = pickle.loads(base64.b64decode(out))
    names = [str(p.get('name') or '') for p in data.get('people', [])]
    print('person_present:', any(n.startswith('J1B') for n in names))
    print('people_count:', len(names))
    PYEOF
    ```

#### Pass criterion

1. `J1B` person visible on Pro's canvas after reopen.
2. DB: `person_present: True`, `people_count: 72`.
3. No `Traceback` in either Debug Console.

#### Fail signs

| Observed | Means |
|----------|-------|
| `person_present: False` | Pro's merge overwrote its own addition — bug in Pro's `applyChange` |
| `people_count < 71` | Pro's merge dropped existing people |
| Traceback in either Debug Console | Bug in merge or save path; copy and report |

---

### Journey-2 (Item 2: reader crash guard) — Status:

**Tests:** `Scene.prune` null-deref fix + emotions `and`→`or` fix — corrupt diagram opens without traceback.

#### Pre-flight

> No seed needed. Diagram 1924 is a permanently corrupt fixture in the DB.

#### Steps

1. Launch **Pro** via VSCode debug target "Pro".

2. Open `Free Diagram` (id 1924) from the file manager.

3. Close and reopen `Free Diagram`.

#### Pass criterion

1. Diagram opens and renders (corruption visible as missing people/events is expected).
2. No `Traceback` in Pro's Debug Console at any point.

#### Fail signs

| Observed | Means |
|----------|-------|
| Traceback on open | Null-deref in `Scene.prune` — fix not applied |
| Traceback on reopen | Prune runs again on reload — same bug |

---

### Journey-6 (Item 6: field coverage) — Status:

**Tests:** All three partial-write `setDiagramData` copies fixed — UI flags survive a Personal PDP extraction save.

#### Pre-flight

> ```bash
> uv run python /Users/patrick/theapp/familydiagram/doc/plans/2026-04-17--data-integrity/fixtures/seed_journey_6.py
> ```
> Expect: `Seeded T04-03: hideNames=True, hideToolBars=True, hideVariablesOnDiagram=True, …`

#### Steps

1. Launch **Pro** via VSCode debug target "Pro".

2. Open `T04-03-all-ui-flags-toggled` in Pro.

3. Launch **Personal** via VSCode debug target "Personal".

4. In Personal, open `T04-03-all-ui-flags-toggled`.

5. In Personal, trigger PDP extraction (Build my Diagram / extract button).

6. Close and reopen T04-03 in Pro.

7. Verify DB:
    ```bash
    uv run python - <<PYEOF
    import base64, pickle, subprocess
    import PyQt5.sip
    out = subprocess.check_output(['docker','exec','fd-postgres','psql','-U','familydiagram','-d','familydiagram','-tAc',"SELECT encode(data,'base64') FROM diagrams WHERE id=1975"]).decode().strip()
    data = pickle.loads(base64.b64decode(out))
    print('hideNames:', data.get('hideNames'))
    print('hideToolBars:', data.get('hideToolBars'))
    print('hideVariablesOnDiagram:', data.get('hideVariablesOnDiagram'))
    PYEOF
    ```

#### Pass criterion

1. All three flags visually active in Pro after reopen (names hidden, toolbars hidden, variables hidden).
2. DB: all three print `True`.
3. No `Traceback` in either Debug Console.

#### Fail signs

| Observed | Means |
|----------|-------|
| Any flag `False` in DB | That copy of `setDiagramData` still partial-writes — check which of the 3 copies |

---

### Journey-7 (Item 7: chat history persists) — Status:

**Tests:** Chat statements survive tab switch and diagram close/reopen without app quit.

#### Pre-flight

> ```bash
> uv run python /Users/patrick/theapp/familydiagram/doc/plans/2026-04-17--data-integrity/fixtures/seed_journey_7.py
> ```
> Expect: `Seeded T04-04: discussions cleared (0 remaining)`

#### Steps

1. Launch **Personal** via VSCode debug target "Personal".

2. Open `T04-04-kitchen-sink-both-apps`.

3. Send chat message `J7A`.

4. Switch to the PDP tab, then back to the chat tab.

5. Send chat message `J7B`.

6. Close T04-04 (do NOT quit the app).

7. Reopen T04-04.

#### Pass criterion

1. After step 4: `J7A` still visible in chat.
2. After step 7: `J7B` still visible in chat.
3. No `Traceback` in Personal's Debug Console.

#### Fail signs

| Observed | Means |
|----------|-------|
| `J7A` gone after tab switch | Client not retaining statements in memory — `_statements` append bug |
| `J7B` gone after reopen | Endpoint not returning both statements, or client not loading them on open |

---

### Journey-9 (Item 9: save failure surface) — Status:

**Tests:** Save failure shows a toast/banner with Retry; retry succeeds after network restored.

#### Pre-flight

> No seed needed. Any open diagram works.

#### Steps

1. Launch **Personal** via VSCode debug target "Personal".

2. Open `T04-04-kitchen-sink-both-apps`.

3. Delete any event (triggers an immediate save attempt).

4. ```bash
   sudo ifconfig en0 down
   ```
   Then immediately delete another event to trigger a save while offline.

5. ```bash
   sudo ifconfig en0 up
   ```

6. Tap Retry on the toast/banner.

#### Pass criterion

1. After step 4: toast/banner appears with a save-failure message and Retry button.
2. After step 6: banner clears; save succeeds (no further error).
3. No `Traceback` in Personal's Debug Console.

#### Fail signs

| Observed | Means |
|----------|-------|
| No toast/banner | Save failure not surfaced — `Diagram.save()` failure path not wired to UI |
| Banner stays after Retry | Retry not triggering re-save, or save still failing |

---

## Appendix A — Why diagram 1924 is out of scope

Patrick's chat history (the only valuable data in 1924) lives in the `Discussion` DB table, independent of the diagram pickle blob. The diagram data itself is reproducible by re-extracting in Personal — Patrick does this routinely. So 1924 needs nothing special: item 2 (crash guard) makes it safe to open; after items 1, 4, 5 land, re-extraction won't recreate the same corruption.

## Appendix B — Why we don't add read-time event-orphan pruning

Investigation 2026-04-17 ruled this out:

1. `Scene.prune` runs on read only, never on write — corrupted data is written to disk and persists across saves until reopen
2. Diagram 1924's `pruned[]` is empty — pruner did NOT remove the missing 7 people; they were lost by a writer
3. LLM extraction validates orphan refs before commit (`pdp.py:271-308`)
4. Therefore the orphans came from a writer-side bug; adding read-time prune masks producer bugs and creates silent data loss going forward

The right fix targets producers (items 1, 3, 4, 5). 1924 itself is handled by re-extraction (see Appendix A).

## Appendix C — File locations and line numbers (Claude's reference)

**Item 1 (concurrent merge):**
- `btcopilot/btcopilot/schema.py` — add `SCENE_COLLECTION_FIELDS` and `merge_scene_collection` to `DiagramData`
- `familydiagram/pkdiagram/models/serverfilemanagermodel.py` lines 543–551 — Pro `applyChange`
- `familydiagram/pkdiagram/personal/personalappcontroller.py` lines 276–285 — Personal `applyChange`
- `familydiagram/pkdiagram/tests/models/test_serverfilemanagermodel.py` — flip the 7 concurrent simulation tests added 2026-04-16 to assert correct merged behavior

**Item 2 (reader crash guard):**
- `familydiagram/pkdiagram/scene/scene.py` lines 992–1004 — event prune loop (line 996 null-deref) + emotions logic (and→or)

**Item 3 (prune cascade):**
- Same file, around line 990 — after pair_bond/multipleBirth orphan removal, re-sweep events for newly-orphaned refs

**Item 4 (commit atomicity):**
- `btcopilot/btcopilot/schema.py` — `commit_pdp_items` (~line 493). Wrap body in try/except with deep-copy snapshot of `self.people`, `self.events`, `self.pair_bonds`, `self.pdp` taken at entry; restore on exception.

**Item 5 (commit→Scene race):**
- `familydiagram/pkdiagram/personal/personalappcontroller.py` lines ~1031-1037 — `_addCommittedItemsToScene`

**Item 6 (field coverage):**
- `familydiagram/pkdiagram/server_types.py` lines 305-311 — client `setDiagramData` (writes 7/43)
- `btcopilot/btcopilot/pro/models/diagram.py` lines 100-105 — server `set_diagram_data` (writes 5/43)
- Same file lines 152-163 — `update_with_version_check` `diagram_data=` branch (third copy of bug)

**Item 7 (chat persists):**
- `btcopilot/btcopilot/personal/routes/discussions.py` `_create_discussion` line 37 + `POST /statements` endpoint — return both statements
- `familydiagram/pkdiagram/personal/personalappcontroller.py:_sendStatement` lines 910-941 — append both to `_statements`
- `familydiagram/pkdiagram/resources/qml/Personal/DiscussView.qml` lines 45, 71-78 — reset `initSelectedDiscussion` on diagram change

**Item 8 (`diagram_id` honored):**
- `btcopilot/btcopilot/personal/routes/discussions.py:37`

**Item 9 (save failure surface):**
- `familydiagram/pkdiagram/server_types.py` `Diagram.save()` failure paths — TBD, needs audit
- New: `familydiagram/pkdiagram/resources/qml/Personal/PersonalToast.qml`

## Appendix D — V1 investigation: empirical findings on Diagram 1924

DB query 2026-04-17, `id=1924`, `data_bytes=28879`, `updated_at=2026-03-09 21:03:22`:

- **People present (21):** 1, 2, 201–218, 225
- **Missing (7):** 219, 220, 221, 222, 223, 224, 226
- **Events: 31 total, 13 orphan**
- **Pair_bonds: 10 total, 6 orphan**
- **`pruned[]`: empty** ← confirms pruner didn't remove the 7
- **Sample orphan event:** `id=200 kind=birth dt=1980-05-01 desc='User born' person=226` (the user's own person was destroyed; event survived)
