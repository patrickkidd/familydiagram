# UI Spec: User Details (FD-321)

**Decision (2026-06-15):** single-screen presentation (variant A). One reusable form drives both
the first-launch wizard and the Settings profile editor. Reference demo:
`doc/ui-specs/prototypes/FINAL-user-details.qml`.

## Purpose

Let a Personal-app user set their own name and birth date so (a) their own node on the diagram is
named, and (b) extraction/rebuild context knows who the speaker is (kills the duplicate-proband
class). Editable later in Settings.

## Components

### `UserDetailsForm.qml` (new, reusable — `Personal/`)
The shared body. A `Flickable` + `Column` of grouped cards, matching `VoiceSettingsPage` styling
(rounded `radius: 12` cards, `util.QML_ITEM_BG`, 1px `util.QML_ITEM_BORDER_COLOR` border, uppercase
`QML_INACTIVE_TEXT_COLOR` section labels).

- **YOUR NAME** card: two stacked fields — First name, Last name — separated by a hairline.
  Use `PK.TextField`. First name required.
- **DATE OF BIRTH** card: REUSE the `EventForm.qml` date idiom — a `PK.DatePickerButtons`
  (`datePicker:` bound to a `PK.DatePicker`, `hideTime: true` since birth has no time) paired with
  the `PK.DatePicker`. This gives a clickable/focusable editable date field; do NOT drop in a bare
  `PK.DatePicker` (Patrick 2026-06-15: the bare picker was unfocusable/clunky and couldn't be clicked
  into). Optional; the picker can only yield a real calendar date, so there is no invalid-date state.
- **FOCUS / TAB ORDER (mandatory, Patrick 2026-06-15):** the form must honor tab-focus order —
  First name → Last name → birth date field — via `KeyNavigation.tab`/`backtab` (chain the name
  `PK.TextField`s to `dateButtons.firstTabItem`, mirroring EventForm). First name field takes initial
  focus on open. Clicking any field must focus it.
- **Validation (C3):** red border + red helper text when First name is blank-after-touch. The date
  control cannot produce an invalid date, so C3 reduces to first-name-required. `valid = firstName.trim() != ""`.
- Exposes: `firstName`, `lastName`, `birthDate` (or M/D/Y), `valid`.

### Wizard surface (`wizardMode: true`)
- Title "Welcome" + subtitle explaining why.
- Bottom bar: **Get Started** (enabled only when `valid`) + **Skip for now** text button.
- Mounted from `PersonalContainer` on first launch when the profile-prompt flag is unset AND the
  current diagram's primary node has no name.

### Settings surface (`wizardMode: false`)
- Reuses the existing settings sub-page chrome (56px header, back chevron, centered title "Profile")
  exactly like `VoiceSettingsPage`/`ModelSettingsPage`.
- Bottom bar: **Save** (enabled when `valid`). No Skip.
- Pre-populated from the primary node's current name + birth event.
- Wire into `AccountDrawer` "ACCOUNT"/"Profile" entry (currently inert) and the Settings list.

## States
- **Empty / fresh:** wizard shown, all blank, Get Started disabled.
- **Invalid:** red validation on the offending field, primary button disabled.
- **Valid:** primary button enabled.
- **Skipped:** flag set, wizard never reappears (C2); app fully usable.
- **Pre-existing diagram (C6):** Settings opens with whatever the primary node already has (often
  blank); editable; lands on primary node or deterministic fallback when none is marked primary.

## Persistence (app → diagram → server)
- Name → primary `Person.name` / `Person.lastName`.
- Birth date → a **Birth event** on the primary node (NOT a scalar field) — Patrick, 2026-06-15.
- Skip flag → `AppConfig` pref (e.g. `personalProfilePrompted`), local, survives relaunch.
- Saved via the normal diagram save path; server diagram version advances; reload reflects it (C4/C5).
- **Two-location field-sync (C7):** if any new `DiagramData`/`Person` field is added, update BOTH
  `Scene.diagramData()` and `serverfilemanagermodel.applyChange()`/`setData()`. Birth-as-event avoids
  a new scalar field, minimizing this surface.

## Out of scope for this spec (handled in build, not UI)
Extraction/rebuild context plumbing (C8–C11) and the chat-label rename (C13) are backend; this spec
covers only the capture/edit UI.
