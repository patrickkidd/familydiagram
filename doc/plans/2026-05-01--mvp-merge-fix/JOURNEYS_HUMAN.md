# MVP Merge Fix — Journeys for Patrick

Copy-paste-able. Each journey starts with one reset command, uses literal names (no env vars), and ends with one verify command. Methodology: [doc/TEST_JOURNEYS.md](../../TEST_JOURNEYS.md). Plan: [README.md](README.md).

For each journey: run the **Setup** command, do the **Steps**, run the **Verify** command, compare to **Pass criterion**, report `PASS` or `FAIL: <one-line reason>` in the Status table at the bottom.

---

## One-time prerequisites

1. Pro app build is current after the fix:
   > ```bash
   > cd /Users/patrick/theapp/familydiagram && PATH="/Users/patrick/dev/lib/Qt/5.15.2/clang_64/bin:$PATH" uv run --env-file ../.env make
   > ```
2. Flask dev server running on 8888 + Docker fd-postgres up. (Verified per existing CLAUDE.md.)
3. VSCode debug targets "Pro" and "Personal" available.

## Between every journey

**Quit both Pro and Personal entirely (Cmd+Q in each, not just close the diagram).** Then run the journey's reset command, then re-launch both apps via VSCode.

Why: each app holds an in-memory `_lastSavedSnapshot` and a Scene instance from the previous journey. Closing only the diagram window doesn't reliably purge these. The next save would merge stale state back into the freshly-reset server diagram, polluting the test.

---

## J-1A — Pro held open, Personal commits a PDP item, Pro saves a different change

**Tests:** Pro's stale snapshot does not clobber the new person Personal committed.

**Note on Personal's UI:** Personal is chat-first — it doesn't expose a person list or properties drawer. Personal's user-driven server saves go through `acceptPDPItem` (commit a pending PDP item to canonical) or `deleteEvent` (delete an event). The fixture pre-injects a PDP item named `J_PDP_pending` so Personal has something to Accept without needing live AI extraction.

**Setup** — copy and paste:
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/reset_baseline.py
> ```
> Expected output ends with: `In Pro and Personal, open the diagram named: MVP_Merge_Fix`

**Steps:**

1. In Pro, double-click `MVP_Merge_Fix` in the file manager. Don't close Pro.
2. In Personal, open `MVP_Merge_Fix` from its file list. The PDP sheet should show one pending person named `J_PDP_pending`. Don't close Personal.
3. In Personal, tap Accept on the pending `J_PDP_pending` PDP item. Personal auto-saves; wait until the title bar's "*" indicator clears (typically <1s).
4. In Pro (still has the stale view — doesn't know `J_PDP_pending` was committed), click person `B`. Change B's name via the properties drawer to `J1A_Pro_edit`. Press Cmd+S.
5. Close and re-open `MVP_Merge_Fix` in BOTH apps.

**Verify** — copy and paste:
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/verify.py
> ```

**Pass criterion:** Verify output shows BOTH:
- One person with `name='J_PDP_pending'` in the People list (Personal's PDP commit survived Pro's save; the PDP section should be empty)
- One person with `name='J1A_Pro_edit'` (Pro's edit to person B applied)

**Fail signs:**

| Observation | What it means |
|-------------|---------------|
| No `J_PDP_pending` person; PDP section still shows it pending | Pro's stale snapshot clobbered Personal's commit. **Bug not fixed.** |
| `J1A_Pro_edit` missing | Pro's edit didn't save. Different bug. |
| Either app shows a traceback in its VSCode Debug Console | Bug in merge or save path. Copy the traceback. |

---

## J-1B — Personal held open, Pro edits, Personal then commits PDP

**Mirror of J-1A:** Pro saves first; Personal then commits a PDP item with a stale view of Pro's edit. Personal's commit must NOT clobber Pro's edit.

**Setup** — copy and paste:
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/reset_baseline.py
> ```

**Steps:**

1. In Personal, open `MVP_Merge_Fix`. The PDP sheet shows `J_PDP_pending`. Don't close.
2. In Pro, open `MVP_Merge_Fix`. Don't close.
3. In Pro, click person `C`. Change C's name to `J1B_Pro_edit`. Press Cmd+S.
4. In Personal (still has stale view — doesn't know C was renamed), tap Accept on the `J_PDP_pending` PDP item. Wait until "*" clears.
5. Close and re-open `MVP_Merge_Fix` in BOTH apps.

**Verify:**
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/verify.py
> ```

**Pass criterion:** Verify shows BOTH:
- `name='J1B_Pro_edit'` (Pro's edit survived Personal's stale-view commit)
- `name='J_PDP_pending'` in People (Personal's PDP commit applied; PDP section empty)

**Fail signs:** Same shape as J-1A.

---

## J-2A — Personal deletes the event, Pro saves a different change

**Tests:** Deletes survive the other side's stale-snapshot save.

**Setup** — copy and paste:
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/reset_baseline.py
> ```

**Steps:**

1. In Pro, open `MVP_Merge_Fix`. Click person `A` to select. Add a Birth event for A (Person properties → Add Event → kind: Birth → Save). Press Cmd+S. Close `MVP_Merge_Fix` in Pro (do NOT close the Pro app).
2. In Pro, re-open `MVP_Merge_Fix`. Don't close. (Pro now has the Birth event in its view.)
3. In Personal, open `MVP_Merge_Fix`. Don't close. (Personal also has the Birth event.)
4. In Personal, find the Birth event on the timeline. Tap to open it. Tap delete. Wait until "*" clears.
5. In Pro (still has the event in its stale view), click person `B`. Change name to `J2A_Pro_edit`. Press Cmd+S.
6. Close and re-open `MVP_Merge_Fix` in BOTH apps.

**Verify:**
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/verify.py
> ```

**Pass criterion:** Verify shows:
- One person with `name='J2A_Pro_edit'`
- The "Events:" section is empty (no Birth event)

**Fail signs:**

| Observation | What it means |
|-------------|---------------|
| Birth event reappears under "Events:" | Pro's stale snapshot resurrected the deleted event. **Bug not fixed.** |
| `J2A_Pro_edit` missing | Pro's edit didn't save. |

---

## J-2B — Pro deletes a person, Personal auto-saves later

**Mirror of J-2A.**

**Setup** — copy and paste:
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/reset_baseline.py
> ```

**Steps:**

1. In Pro, open `MVP_Merge_Fix`. Add a Birth event for person `A` (Person properties → Add Event → kind: Birth → Save). Press Cmd+S. Close `MVP_Merge_Fix` in Pro (do NOT close the Pro app).
2. In Personal, open `MVP_Merge_Fix`. Don't close. (Personal now has the Birth event.)
3. In Pro, re-open `MVP_Merge_Fix`. Don't close.
4. In Pro, click person `C`. Press Delete. Press Cmd+S.
5. In Personal, tap the Birth event on the timeline. Tap delete. Wait until "*" clears. (Personal's internal Scene still holds person C from when the diagram was loaded; deleting the event triggers Personal's save with that stale Scene state, exercising the merge.)
6. Close and re-open `MVP_Merge_Fix` in BOTH apps.

**Verify:**
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/verify.py
> ```

**Pass criterion:** Verify shows:
- No person with `name='C'` (Pro's deletion survived Personal's auto-save)
- The "Events:" section is empty

**Fail signs:** If person `C` reappears, Personal's stale snapshot resurrected the deleted person.

---

## J-3 — Both apps add new persons concurrently, no id collision

**Tests:** Server-side block allocation prevents `lastItemId` collisions when Pro adds via toolbar AND Personal commits via PDP.

**Setup** — copy and paste:
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/reset_baseline.py
> ```

**Steps:**

1. In Pro, open `MVP_Merge_Fix`. Don't close.
2. In Personal, open `MVP_Merge_Fix`. PDP sheet shows `J_PDP_pending`. Don't close.
3. In Pro, click the male person toolbar button, then click on empty canvas to drop a new male person. Use the properties drawer to name them `J3_Pro_add`. Press Cmd+S.
4. In Personal, tap Accept on the `J_PDP_pending` PDP item. Wait until "*" clears.
5. Close and re-open `MVP_Merge_Fix` in BOTH apps.

**Verify:**
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/verify.py
> ```

**Pass criterion:** Verify shows:
- One person with `name='J3_Pro_add'`
- One person with `name='J_PDP_pending'`
- The two `id=` values for those persons are DIFFERENT

**Fail signs:**

| Observation | What it means |
|-------------|---------------|
| `J3_Pro_add` and `J_PDP_pending` share the same id | Block allocation broken — collision occurred. |
| One of the names missing | Merge dropped one. |
| Pro raises a traceback during person-add | Allocator binding broken. |

---

## J-4 — Block allocator refills a second time mid-session

**Tests:** Pro's `ServerBlockAllocator` correctly requests a second block when the first is exhausted.

**Setup** — copy and paste:
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/reset_baseline.py
> ```

Then, in your shell, set the block size to 3 BEFORE launching Pro:
> ```bash
> export FAMILYDIAGRAM_BLOCK_SIZE=3
> ```
> Then launch Pro from this shell (or set the var in your VSCode "Pro" launch config).

**Steps:**

1. In Pro, open `MVP_Merge_Fix`.
2. Add 4 male people via the toolbar. Name them `J4_one`, `J4_two`, `J4_three`, `J4_four`. Press Cmd+S after each.
3. Close and re-open `MVP_Merge_Fix` in Pro.

**Verify:**
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/verify.py
> ```

**Pass criterion:** Verify shows all 4 people: `J4_one`, `J4_two`, `J4_three`, `J4_four` with 4 DISTINCT id values.

**Fail signs:**

| Observation | What it means |
|-------------|---------------|
| Pro raises a traceback on the 4th add | Allocator refill broken. |
| Any name from J4_* missing after re-open | Refill returned a duplicate id; merge dropped it. |
| Two J4_* names with the same id | Refill returned an overlapping range. |

After this journey, **unset the env var** so other journeys use the default block size:
> ```bash
> unset FAMILYDIAGRAM_BLOCK_SIZE
> ```

---

## J-5 — Pro opens a local `.fd` file (no server, no allocator binding)

**Tests:** Local file open is unchanged. No allocator binding, no server traffic for ids.

**Setup:** No reset needed (no server diagram involved). You need any existing `.fd` file. If you don't have one handy, create one in Pro: File → New, add a male person named `J5_setup`, File → Save As → save to `~/Documents/J5_local.fd`.

**Steps:**

1. Quit Pro entirely.
2. Launch Pro fresh. Don't log in to a server account.
3. Open the local `.fd` file via File → Open.
4. Add a new male person. Name them `J5_local_add`. Press Cmd+S.
5. Quit and re-launch Pro. Open the same local file.

**Pass criterion:** `J5_local_add` is present after re-open. No traceback in Debug Console. No HTTP requests to `/v1/diagrams/.../reserve_ids` in Debug Console (because no server is involved).

**Fail signs:**

| Observation | What it means |
|-------------|---------------|
| `J5_local_add` missing after re-open | Local file save broken (regression unrelated to this PR). |
| Pro tries to make a `reserve_ids` HTTP request | Allocator was bound to a local-file Scene (it shouldn't be). |

---

## J-6 — Same event edited on both sides (item-level last-write-wins, **documented MVP behavior**)

**Tests:** When Pro and Personal both edit the SAME item (different fields), item-level last-write-wins applies — the second-saver's whole item dict overwrites the first. **One side's edits are lost.** Accepted MVP behavior; field-level merge is v3.

**Note on Personal's editable surface:** Personal can't edit canonical persons via UI — only events (`editEvent`/`deleteEvent`) and PDP items. So J-6 uses a Birth event as the shared item: Pro adds it; Personal edits the date; Pro (stale view) edits the description; one side's edit wins.

**Setup** — copy and paste:
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/reset_baseline.py
> ```

**Steps:**

1. In Pro, open `MVP_Merge_Fix`. Click person `A`. Add a Birth event for A (Person properties → Add Event → kind: Birth → date `1990-01-01` → description blank → Save). Press Cmd+S. Close `MVP_Merge_Fix` in Pro.
2. In Pro, re-open `MVP_Merge_Fix`. Don't close.
3. In Personal, open `MVP_Merge_Fix`. The Birth event appears in Personal's timeline. Don't close.
4. In Personal, tap the Birth event. Edit the date to `1991-06-15`. Save the event form. Wait until "*" clears.
5. In Pro (still sees the event with date 1990-01-01 and blank description), tap the same Birth event. Edit the description to `J6_Pro_edit`. Save the event form. Press Cmd+S.
6. Close and re-open `MVP_Merge_Fix` in BOTH apps.

**Verify:**
> ```bash
> cd /Users/patrick/theapp/familydiagram && uv run --env-file ../.env python doc/plans/2026-05-01--mvp-merge-fix/fixtures/verify.py
> ```

**Pass criterion (documented behavior):** Verify's "Events:" section shows ONE Birth event. Open the diagram in Pro and inspect:
- Description = `J6_Pro_edit` (Pro's edit)
- Date = `1990-01-01` (Pro's stale value; Personal's date edit was LOST)

This is item-level LWW: Pro saved last with the stale event dict, replacing Personal's date change.

**Fail signs:**

| Observation | What it means |
|-------------|---------------|
| Date is `1991-06-15` AND description is `J6_Pro_edit` | Field-level merge happened (unexpected — investigate as good surprise). |
| Description not `J6_Pro_edit` | Pro's edit didn't save. Different bug. |

**Note:** This documents the MVP cost of accepting item-level LWW. Field-level merge is v3.

---

## Status

Replace `PENDING` with `PASS` or `FAIL: <one-line reason>` after running each.

| Journey | Status |
|---------|--------|
| J-1A | PASS (2026-05-02) |
| J-1B | PASS (2026-05-02) |
| J-2A | PASS (2026-05-02) |
| J-2B | PASS (2026-05-02) |
| J-3  | PASS (2026-05-02) — Pro id=7, Personal id=106, no collision |
| J-4  | PASS (2026-05-02) — refill happened ~3x; final lastItemId=14 well past initial block end of 8 |
| J-5  | PASS (2026-05-02) |
| J-6  | DEFERRED — Personal UI doesn't expose `editEvent` yet (slot exists but no QML surface). Covered by unit test `test_same_item_both_sides_edited_local_wins`. Re-enable as a manual journey once Personal exposes event editing. |

---

## Reporting

Reply with the journey code(s) and result(s). Examples:

> "J-1A: PASS. J-1B: PASS. J-3: FAIL — both new people had the same id."
>
> "J-2A: traceback at step 3 — `<paste>`"

If a journey was ambiguous to follow, also report that — Claude rewrites the journey, not just the fix.
