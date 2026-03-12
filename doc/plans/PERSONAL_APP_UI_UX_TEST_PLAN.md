# Personal App UI/UX Test Plan

**Date:** 2026-03-12
**Test env:** iOS Simulator UDID `E67BD538-249B-46F3-9F05-440389F76650` (iPhone 14 Pro)
**Method:** Layer 3 — TCP bridge at `127.0.0.1:9876` compiled into iOS simulator build
**Test user:** Patrick Stinson / `patrick@alaskafamilysystems.com` (pre-logged-in)
**Screenshots:** `familydiagram/screenshots/sim_20260312_05*.png`

---

## 1. What Was Tested

| Area | Method |
|------|--------|
| Discuss tab — chat display, PDP badge, extract | Bridge click + sim screenshot |
| PDP sheet — open, card display, accept, reject, Accept All | Bridge click by objectName |
| Learn tab — cluster list, cluster focus, event expand | Bridge click + sim screenshot |
| Plan tab — content | sim screenshot |
| Hamburger drawer — open, contents | Bridge click by position |
| Discussion title dropdown | Bridge click by position |
| "The Story" dropdown (Learn tab) | Bridge click by position |
| Add Data Point form — open, layout | Bridge click by position + sim screenshot |
| Add Data Point form — cancel | **BLOCKED** (see testing limitations) |

---

## 2. Bugs (New — not in TODO.md)

### B1 — PDP badge count does not decrement on individual accept/reject
**Severity:** Medium
**Observed:** After accepting card 1 (Birth/Elizabeth O'Malley) and rejecting card 2 (Anthony/Person), the red badge on Discuss tab header stayed at **44**. Only after `acceptAllButton` was clicked did the badge clear.
**Expected:** Badge should count down as each item is reviewed.
**File:** `pkdiagram/resources/qml/Personal/PDPSheet.qml`, `PersonalContainer.qml` (`pdpCount` binding)

### B2 — Cluster card date range shows truncated end date
**Severity:** Low
**Observed:** "Early Adulthood Anxiety and ..." cluster shows date range `Jan 1,'75 - Jan 1` — the end date year is missing.
**Expected:** `Jan 1,'75 - Jan 1,'26` (or however the end date is formatted)
**File:** `pkdiagram/resources/qml/Personal/LearnView.qml` — date formatting in cluster card

### B3 — planView has no objectName (bridge can't inspect it)
**Severity:** Low (code quality / testability)
**Observed:** `find_element("planView")` returns "Element not found". The `PlanView` instance in `PersonalContainer.qml` has `id: planView` but no `objectName`.
**File:** `pkdiagram/resources/qml/Personal/PersonalContainer.qml` line ~300

### B4 — PDP sheet stays open across tab switches
**Severity:** Low
**Observed:** After PDP sheet was open on Discuss tab, clicking learnTab showed the PDP sheet overlaying the Learn view (Drawer parented to `Overlay.overlay` persists across tab switches).
**Note:** May be intentional — user may want to continue reviewing while on another tab. But if so, the header affordance (which appears to stay on Discuss header) is misleading.

---

## 3. UX Friction (New — not in TODO.md)

### U1 — "Review" heading in PDP sheet is disproportionately large
**Priority:** High
**Observed:** The word "Review" renders at a huge display font (~40-48px) while "Refresh" and "Accept All" are cramped pill buttons beside it. The huge text wastes ~30% of the header's vertical space.
**Suggestion:** Use a normal section title font size (16-18px) consistent with other headers, or reflow the layout so "Review" is a label row above the action buttons.

### U2 — Person-type PDP card uses oversized name font
**Priority:** Medium
**Observed:** When a PDP card shows a "Person" type, the person's name renders in a very large bold font (~36px "Anthony"), inconsistent with other card types (Birth, Married) which use normal-sized labels.
**File:** `pkdiagram/resources/qml/Personal/PDPSheet.qml` — Person card delegate

### U3 — Cluster titles truncated even when cluster is focused/expanded
**Priority:** Medium
**Observed:** In collapsed and focused (expanded) states, all three cluster cards show `...` truncation: "Early Adulthood Anxiety and ...", "Maternal Relationship Conflic...", "Reproductive Stress and Rec...". The focused state has no additional space showing the full title.
**Suggestion:** Show full title in the expanded state and in the focused cluster nav header.

### U4 — Time field shown by default in Add Data Point form
**Priority:** Low
**Observed:** Date row shows both `--/--/----` (date) and `--:-- pm` (time) side-by-side. Historical biographical events almost never have precise times; the time field adds noise.
**Suggestion:** Hide time field by default; add a "Add time" affordance if needed.

### U5 — Person field in Add Data Point is free-text
**Priority:** Low
**Observed:** The "Person" field in the event form accepts free text with no autocomplete or picker from existing diagram persons. Users will mistype names and create duplicates.
**Suggestion:** Autocomplete against known persons in the diagram (or show a picker).

### U6 — "The Story" header dropdown contains only "Clear Data..."
**Priority:** Low
**Observed:** Tapping the "The Story ▼" header on the Learn tab shows a single destructive option. An almost-empty dropdown implies more is coming but currently gives users no navigation value.
**Suggestion:** Either remove the dropdown affordance until there are real options, or add useful items (e.g., "Toggle Clusters", "Show All Events").

### U7 — Voice input button permanently hidden
**Priority:** Low
**Observed:** `micButton` in DiscussView has `visible: false` with a TODO comment ("re-enable when voice input is polished"). No alternative affordance is given.
**Note:** Already tracked in source code. Flagged here for prioritization.

### U8 — PDP sheet has no visible dismiss gesture
**Priority:** Low
**Observed:** The eventFormDrawer has `interactive: false` disabling swipe-to-close. The PDP sheet Drawer likely inherits the same. Users must use "Accept All" to dismiss, which is a destructive action for those who only wanted to glance at pending items.
**Suggestion:** Allow swipe-down to dismiss without accepting (or add explicit close button).

---

## 4. What Passed

| Test | Result |
|------|--------|
| Tab navigation Discuss / Learn / Plan | ✅ |
| Discuss chat message display (user + AI) | ✅ |
| PDP badge appears after extraction (44 items) | ✅ |
| Extract button triggers extraction + overlay | ✅ |
| PDP sheet opens with correct first card (Birth / Elizabeth O'Malley / 1954-12-03) | ✅ |
| PDP card shows type badge, person, date, edit pencil | ✅ |
| PDP accept (+) advances to next card | ✅ |
| PDP reject (×) advances to next card | ✅ |
| PDP Accept All closes sheet and clears badge | ✅ |
| Hamburger drawer opens with account info + diagram list | ✅ |
| Discussion title dropdown shows discussion list + "New Discussion" | ✅ |
| "The Story ▼" dropdown opens (shows "Clear Data...") | ✅ |
| Learn tab cluster list (3 clusters with color-coded borders) | ✅ |
| Cluster tap expands to focused view with mini-graph + event list | ✅ |
| Event row tap expands with tags, person, description | ✅ |
| Mini-graph highlights selected event | ✅ |
| Plan tab shows stub text ("Guidance, action items go here.") | ✅ |
| Add Data Point form opens with What/Who/When/Where/How sections | ✅ |

---

## 5. Testing Limitations

### L1 — Buttons inside Overlay.overlay items not reachable by coordinate click
Bridge `click` on `PersonalContainer` at computed overlay coordinates does **not** route to items parented to `Overlay.overlay` (Drawers, Popups). Only items with an explicit `objectName` can be found and clicked via `find_element`. Workarounds:
- Use `objectName` on all interactive elements in overlays (preferred fix — adds `objectName` to `cancelButton`, reject/accept card buttons)
- As an alternative: `set_property` on the overlay item's `visible` property to close drawers programmatically

### L2 — `get_bounds` fails on QQuickPopup (Drawer) items
Drawers are `QObject` (not `QQuickItem`) so calling `window()` on them raises `AttributeError`. Confirmed for `pdpSheet` and would apply to all `Drawer` instances.

### L3 — Cluster navigation arrows not reachable by coordinate click
The ◀ ▶ arrows in the cluster focus nav bar are in the `learnView` coordinate space but repeated click attempts at estimated positions collapsed the cluster instead of navigating. Bridge lacks a reliable way to target these without an `objectName`.

---

## 6. Recommended Automation Test Cases

Prioritized by value and current bridge feasibility.

### High Priority (implement now — bridge can support)

| ID | Test | Bridge method |
|----|------|---------------|
| A1 | Extract triggers extractOverlay then opens PDP sheet with items | click `extractButton`, wait, check `pdpSheet.visible` |
| A2 | PDP accept advances card index | click `acceptAllButton`'s sibling acceptButton (add objectName), check card index |
| A3 | PDP Accept All clears badge and closes sheet | click `acceptAllButton`, check `pdpBadge.visible == false` |
| A4 | Tab navigation switches currentView | click `discussTab/learnTab/planTab`, check `get_app_state().currentView` |
| A5 | Learn cluster focus shows event list | click cluster card, verify `learnView.expandedEvent` != null |
| A6 | Discussion dropdown creates new discussion | click `discussionMenuOpen` trigger, verify discussion list length increases |

### Medium Priority (requires objectName additions)

| ID | Test | Blocker |
|----|------|---------|
| A7 | Add Data Point form opens and cancels cleanly | Add `objectName` to `cancelButton` in EventForm.qml |
| A8 | PDP reject removes current card | Add `objectName` to card reject button |
| A9 | PDP Refresh button triggers refresh overlay | `refreshButton` already has objectName — needs overlay check |
| A10 | Plan tab deepens over time (future feature) | Plan tab is stub; automate when content lands |

### Low Priority (visual/layout — manual verification preferred)

| ID | Test | Notes |
|----|------|-------|
| V1 | PDP badge count decrements on individual accept/reject | Fix B1 first |
| V2 | Cluster title shows untruncated in focused state | Fix U3 first |
| V3 | "Review" header proportions | Fix U1 first |

---

## 7. objectName Additions Needed for Full Bridge Coverage

These elements need `objectName` to be automatable:

| File | Element | Suggested objectName |
|------|---------|---------------------|
| `EventForm.qml` | `cancelButton` | `"cancelButton"` (already has `id`) |
| `PDPSheet.qml` | card reject button | `"pdpRejectButton"` |
| `PDPSheet.qml` | card accept button | `"pdpAcceptButton"` |
| `PersonalContainer.qml` | hamburger button Rectangle | `"hamburgerButton"` |
| `PersonalContainer.qml` | `planView` instance | `"planView"` |
| `LearnView.qml` | cluster nav prev/next arrows | `"prevClusterButton"`, `"nextClusterButton"` |
