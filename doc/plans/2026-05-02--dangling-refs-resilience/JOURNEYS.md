# Journeys — Dangling-Refs Resilience

Each journey states the setup, action, expected observation, and pass criterion. Patrick runs on real iPhone hardware after rebuild and reports against the criterion.

---

## J-1924-A — Diagram 1924 opens on iPhone

**Setup:** Rebuilt Personal app installed on iPhone, signed in to prod, account that owns diagram 1924.

**Action:** Open the app, let it load the last-opened diagram (1924).

**Expected:**
- App reaches the main scene/PDP UI without showing an error or remaining on a loading spinner.
- Datadog log: `Dropping irrecoverable Event id=...` warnings for several event ids in the 158–200 range.
- Datadog log: `Event ... has dangling person refs; dropping ids ...` for shift events.

**Pass criterion:** App is interactive, scene is non-empty (~21 people, ~12 events).

**Observation:** _(Patrick to fill in)_

---

## J-1924-B — Clear-and-re-extract recovery flow

**Setup:** J-1924-A passed.

**Action:**
1. Tap "Clear all events and people" (or whatever the in-app clear control is).
2. Wait for save acknowledgment.
3. Trigger re-extract from chat history (200 statements in discussion 55, 12 in discussion 58).

**Expected:**
- Step 1 produces an actual server save (not a no-op). Datadog should show a successful PUT to `/personal/diagrams/1924`.
- Step 3 repopulates PDP from chat history.
- After re-extract, scene has fresh extracted people/events with no dangling refs.

**Pass criterion:** Diagram 1924 reaches a clean state and PDP is rebuilt from chat.

**Observation:** _(Patrick to fill in)_

---

## J-CLEAR-NULL — Clear works on a fully-corrupt blob

**Setup:** Pro app or test harness creates a synthetic diagram with intentionally-broken events that cause a partial-load (or simulate via reverting reader resilience temporarily). Personal app opens it.

This journey is covered by `test_clearDiagramData_works_when_scene_is_None` and is **AUTOMATED** — no hardware run needed. Listed here for traceability.

**Pass criterion:** unit test passes.

**Observation:** PASSED in CI.

---

## J-WRITER-WARN — Writer-side warning fires on corrupted outgoing data

**Setup:** Pro app, in-memory scene with a dangling ref injected (e.g., directly mutate `scene._events[0]._person` to a dummy Person not added to scene; this is hard to do legitimately, mostly a synthetic test).

This journey is also covered by `test_diagramData_warns_on_outgoing_dangling_refs` and is **AUTOMATED**.

**Pass criterion:** unit test passes.

**Observation:** PASSED in CI.

---

## Datadog setup (Patrick)

After rebuild lands in beta, configure two Datadog monitors:

1. `service:familydiagram message:"Dropping irrecoverable Event"` → low-priority alert; aggregate by `event.id` and `kind`. Tells us which events are being dropped on real users' diagrams. When this fires, the dropped chunk is in the log payload — recoverable on user request.
2. `service:familydiagram message:"Outgoing scene has dangling person refs"` → **high-priority alert**. This indicates an active writer bug producing fresh corruption — needs investigation.
