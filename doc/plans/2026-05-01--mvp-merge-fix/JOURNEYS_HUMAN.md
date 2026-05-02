# MVP Merge Fix — Journeys for Patrick

This is the human-readable companion to [JOURNEYS.md](JOURNEYS.md) (which is for Claude/MCP). Methodology: [doc/TEST_JOURNEYS.md](../../TEST_JOURNEYS.md). Plan: [README.md](README.md).

For each journey: read the **Setup**, do the **Steps**, check the **Pass Criterion**, report `PASS` or `FAIL: <one-line reason>` in the Status column at the bottom. No judgment calls — observe vs. the stated criterion.

---

## One-time setup before any journey

1. Pro app and Personal app builds are current after the fix (not stale binaries).
   ```bash
   cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env make
   ```
2. Flask dev server is running on 8888 (or use the harness ephemeral server).
3. Open VSCode with debug targets "Pro" and "Personal" available.
4. Pick a unique short tag for this batch of runs (e.g., your initials + date — `pk0502`). You'll embed it in test artifact names so prior-run artifacts can't cause false positives.

For each journey below, REPLACE `$TAG` with your chosen tag (e.g., `pk0502`).

---

## J-1A — Pro held open, Personal edits a person, Pro saves a different person

**Tests:** Pro's stale snapshot does not clobber Personal's edits to a different item.

**Setup:**

Open the same diagram in both apps (a fresh server diagram with at least 3 people named A, B, C).

If you don't have one, create it:
1. Launch Pro. Click `New Diagram`. Add three Male people. Name them `A`, `B`, `C`. Save (Cmd+S).
2. Note the diagram name in the file manager.
3. The diagram is now on the server. Both apps will use this one.

**Steps:**

1. In Pro, double-click the diagram to open it. Don't close Pro after.
2. In Personal, open the same diagram from its file list. Don't close Personal after.
3. In Personal, tap person `A` to open the person properties drawer.
4. Change A's name to `A_PE_$TAG`. Personal auto-saves on edit — wait 2 seconds for the save to complete.
5. In Pro (which still has the stale view of A), tap person `B`.
6. Change B's name to `B_PR_$TAG` in the Pro properties drawer.
7. Press Cmd+S in Pro.
8. Close and re-open the diagram in BOTH apps (so they both refetch from server).

**Pass criterion:**

After step 8, BOTH apps display:
- Person A's name = `A_PE_$TAG` (Personal's edit survived Pro's save)
- Person B's name = `B_PR_$TAG` (Pro's edit applied)

**Fail signs:**

| Observation | What it means |
|-------------|---------------|
| A's name reverted to `A` | Pro's stale snapshot clobbered Personal's edit. **The bug is not fixed.** |
| B's name unchanged | Pro's edit didn't save at all. Different bug. |
| Either app shows a traceback in its VSCode Debug Console | Bug in merge or save path. Copy the traceback into the report. |

---

## J-1B — Personal held open, Pro edits, Personal auto-saves

**Mirror of J-1A** with roles swapped. Personal has the stale view; Pro saves first; Personal's auto-save must not clobber Pro's edit.

**Setup:** Same as J-1A (same diagram, A/B/C exist, both apps closed).

**Steps:**

1. In Personal, open the diagram. Don't close.
2. In Pro, open the same diagram. Don't close.
3. In Pro, click person `C`. Change C's name to `C_PR_$TAG`. Press Cmd+S.
4. In Personal (still has stale view of C), tap person `A`. Change A's name to `A_PE_$TAG`. Personal auto-saves — wait 2 seconds.
5. Close and re-open the diagram in BOTH apps.

**Pass criterion:** BOTH apps display:
- Person C's name = `C_PR_$TAG`
- Person A's name = `A_PE_$TAG`

**Fail signs:** Same shape as J-1A.

---

## J-2A — Personal deletes an event, Pro saves a different change

**Tests:** Deletes survive the other side's stale-snapshot save.

**Setup:** Pro and Personal both open the same diagram. Diagram must contain at least one event (e.g., a Birth event on person A). If none, create one in Pro: tap person A → Add Event → Birth → save.

**Steps:**

1. Both apps already have the diagram open from setup.
2. In Personal, find the Birth event on the timeline. Tap to open. Tap delete. Personal auto-saves — wait 2 seconds.
3. In Pro (stale view — still has the event), click person `B`. Change name to `B_PR_$TAG`. Press Cmd+S.
4. Close and re-open the diagram in BOTH apps.

**Pass criterion:** After step 4, BOTH apps show:
- The Birth event is GONE from the timeline.
- Person B's name = `B_PR_$TAG`.

**Fail signs:**

| Observation | What it means |
|-------------|---------------|
| Birth event reappears | Pro's stale snapshot resurrected the deleted event. **Bug not fixed.** |
| Person B's name unchanged | Pro's edit didn't save. |

---

## J-2B — Pro deletes a person, Personal auto-saves later

**Mirror of J-2A.** Pro deletes; Personal's stale-view auto-save must not resurrect.

**Setup:** Pro and Personal both open the diagram with persons A, B, C.

**Steps:**

1. Both apps open from setup.
2. In Pro, click person `C`. Press Delete (or use the toolbar delete). Press Cmd+S.
3. In Personal (stale view — still shows C), do anything that triggers an auto-save. The simplest: tap any event and delete it. Wait 2 seconds.
4. Close and re-open the diagram in BOTH apps.

**Pass criterion:** Person C is GONE in both apps after step 4.

**Fail signs:** If C reappears, Personal's stale snapshot resurrected the deleted person.

---

## J-3 — Both apps add new items concurrently, no id collision

**Tests:** Pro's server-side block allocation prevents `lastItemId` collisions when both apps allocate new items at the same time.

**Setup:** Pro and Personal both open the same diagram. Note Pro's last person id (if you can see it; otherwise just note that the diagram has N people).

**Steps:**

1. Both apps open from setup.
2. In Pro, add a new male person. Name them `Pro_$TAG`. Press Cmd+S.
3. In Personal, do a PDP commit that creates a new person. Easiest: send a chat message that mentions a new person, then accept the resulting PDP item with name `Pe_$TAG`. Personal auto-saves.
4. Close and re-open the diagram in BOTH apps.

**Pass criterion:** After step 4, BOTH apps show two new people: `Pro_$TAG` and `Pe_$TAG`. Their ids must be different (verify by clicking each and looking at the id field if visible, or by inspecting the DB).

**Optional DB verification:**
```bash
docker exec fd-postgres psql -U familydiagram -d familydiagram -tAc \
  "SELECT id, encode(data,'base64') FROM diagrams WHERE name LIKE '%MVP%' ORDER BY updated_at DESC LIMIT 1;" \
  | uv run python -c "
import sys, base64, pickle
import PyQt5.sip
diagram_id, blob_b64 = sys.stdin.read().split('|')
data = pickle.loads(base64.b64decode(blob_b64.strip()))
people = {p['id']: p['name'] for p in data['people']}
tag = '$TAG'
matched = {id: name for id, name in people.items() if tag in (name or '')}
print('Matched:', matched)
print('Distinct ids:', len(matched) == len(set(matched.keys())))
"
```

**Fail signs:**

| Observation | What it means |
|-------------|---------------|
| Only one of `Pro_$TAG` / `Pe_$TAG` appears | Merge dropped one. |
| Both appear but with the SAME id | Block allocation broken — collision occurred. |
| Pro raises a traceback during person-add | Allocator binding broken. |

---

## J-4 — Block allocator refills a second time mid-session

**Tests:** Pro's `ServerBlockAllocator` correctly requests a second block when the first is exhausted.

**Setup:**

Set the block size very small for this run so you don't have to add 100 people:
```bash
export FAMILYDIAGRAM_BLOCK_SIZE=3
```
Then launch Pro from this shell. Pro and Personal both open the same diagram.

**Steps:**

1. Open the diagram in Pro.
2. Add 4 male people, naming them `J4_1_$TAG` through `J4_4_$TAG`. Press Cmd+S after each.
3. Close and re-open the diagram in Pro.

**Pass criterion:** All 4 people are present after re-open. None of their ids collide with each other.

**Fail signs:**

| Observation | What it means |
|-------------|---------------|
| Pro raises a traceback on person 4 | Allocator's refill logic broken. |
| Person 4 missing after re-open | Refill returned a duplicate id; merge dropped it. |
| Server log shows only one `POST /reserve_ids` request | Refill didn't fire — allocator counter not advancing. |

---

## J-5 — Local `.fd` file open (no server, no block allocation)

**Tests:** Local file open is unchanged. No allocator binding, no server traffic for ids.

**Setup:** A local `.fd` file on disk. Use any existing one or create a fresh diagram via File → New, then save it locally (NOT to the server).

**Steps:**

1. Quit Pro entirely.
2. Launch Pro fresh. Don't log in to a server account.
3. Open the local `.fd` file via File → Open.
4. Add a new male person. Name them `Local_$TAG`. Save (Cmd+S writes to the local file, not the server).
5. Quit and re-launch Pro. Open the same local file.

**Pass criterion:** `Local_$TAG` is present after re-open. No traceback. No HTTP request to any server during the session (verify in the Debug Console — should be silent).

**Fail signs:**

| Observation | What it means |
|-------------|---------------|
| Pro tries to make an HTTP request | Allocator was bound to a local-file Scene (it shouldn't be). |
| Person not present after re-open | Local file save broken (regression unrelated to this PR). |

---

## J-6 — Same item edited on both sides (item-level last-write-wins, **documented MVP behavior**)

**Tests:** When Pro and Personal both edit the SAME item but DIFFERENT fields, item-level last-write-wins applies. **One side's edits are lost.** This is accepted MVP behavior — field-level merge is deferred to v3. Run this journey to confirm the documented behavior.

**Setup:** Pro and Personal both open the same diagram. Person A exists with name `A` and cutoff `False`.

**Steps:**

1. In Personal, tap person A. Toggle the `cutoff` checkbox to True. Personal auto-saves — wait 2 seconds.
2. In Pro (stale view — still sees cutoff=False locally), click person A. Change name to `A_PR_$TAG`. Press Cmd+S.
3. Close and re-open the diagram in BOTH apps.

**Pass criterion (documented behavior):** After step 3, BOTH apps show:
- Person A's name = `A_PR_$TAG`
- Person A's cutoff = **`False`** (Personal's cutoff edit lost — Pro saved last with stale snapshot of A)

**Fail signs:**

| Observation | What it means |
|-------------|---------------|
| cutoff is `True` after step 3 | Field-level merge somehow happened (unexpected — investigate as a "good" surprise). |
| Person A's name unchanged | Pro's save didn't apply at all. Different bug. |

**Note:** This is the cost of accepting last-write-wins per item. Documented in plan README under "Out of scope". If you ever need field-level merge, schedule a follow-up.

---

## Status

Replace `PENDING` with `PASS` or `FAIL: <one-line reason>` after running each.

| Journey | Status |
|---------|--------|
| J-1A | PENDING |
| J-1B | PENDING |
| J-2A | PENDING |
| J-2B | PENDING |
| J-3  | PENDING |
| J-4  | PENDING |
| J-5  | PENDING |
| J-6  | PENDING (expected: see documented behavior in pass criterion) |

---

## Reporting

Reply with the journey code(s) and result(s). Examples:

> "J-1A: PASS. J-1B: PASS. J-3: FAIL — both new people had the same id."
>
> "J-2A: traceback at step 2 — `<paste>`"

If a journey was ambiguous to follow, also report that — Claude rewrites the journey, not just the fix.
