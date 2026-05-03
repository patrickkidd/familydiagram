# Manual Test Journeys — Methodology

How fixes get verified in this codebase. Applies to all packages (familydiagram, btcopilot, fdserver).

---

## Roles

| Role | Does |
|------|------|
| Claude | Writes deterministic journeys per fix. Runs each journey via test harness when possible. Updates status as user reports. |
| Patrick | Runs the journey when Claude hands it off. Reports what was observed. Does NOT decide pass/fail by judgment — only reports against the journey's stated pass criterion. |

---

## Anatomy of a journey

Every journey has these parts. Skip none.

### Code

A short identifier (`J-NNN` or item-derived like `1A`, `1B`). One journey per code. Multiple code paths in the same fix get separate codes (split, don't conditionalize).

### Pre-conditions

Bulleted list of state required before running. Examples:
- "Flask dev server running on 8888"
- "Diagram 1976 (T04-04) seeded in dev DB"
- "Pro app build current after the fix"

Each pre-condition is verifiable with one command (curl, docker ps, file timestamp). Claude runs these checks first.

### Steps

Numbered, each step has exactly:
- **One action** — concrete: "Cmd+S", "type X in field Y", "click button Z"
- **One observable** — concrete: "title bar shows X", "list grows to N items", "no traceback in stdout"

No conditionals. No judgment ("looks right", "appears to work"). If the observable is "no error in stdout", the journey states the exact stdout sample to grep for.

### Pass criterion

One specific, observable condition. Either it holds or it doesn't.

✅ Good: "After step 7, the people list shows 3 entries: Alice, Bob, Charlie"  
❌ Bad: "Verify the merge worked correctly"

### Fail signs

What specific observable indicates the fix didn't work. Common: "Bob is missing from the people list", "Traceback appears in stdout", "App crashes on reopen".

### Status field

One of:
- `PENDING` — Claude has not implemented the fix yet
- `IN PROGRESS` — Claude is coding
- `READY FOR HARNESS` — Code shipped, Claude attempting to verify via test harness
- `READY FOR USER` — Harness verification done (or harness not applicable); waiting on Patrick
- `PASSED` — Patrick reported observing the pass criterion
- `FAILED: <one-line reason>` — Patrick reported the fail sign; sent back to Claude

Status lives next to the journey heading in the tracker. Claude updates it as state changes.

---

## How Patrick reports

Patrick replies with the code and what he observed:

> "1A: passed"  
> "1A: failed — saw J1-ProSide missing in Pro after reopen"  
> "1A: traceback at step 5 — `<paste>`"

Patrick does NOT need to decide whether a deviation was important. He reports observation; Claude interprets.

---

## Claude's harness obligation

Before handing a journey to Patrick, Claude attempts to run it through an automated harness:

| App / surface | Harness |
|---------------|---------|
| Family Diagram desktop (Pro / Personal) | `familydiagram-testing` MCP (`launch_app`, `click`, `open_server_diagram`, `get_app_state`, `screenshot`) |
| Family Diagram iOS | `familydiagram-testing` MCP (`launch_app_in_simulator`, `sim_*`) |
| Training app web UI | `chrome-devtools` MCP |
| Backend API only | `curl` against port 8888, or `pytest` |
| Pure data / library | `pytest` |
| Database state | `docker exec fd-postgres psql -c "..."` |

**If the harness can fully execute the journey,** Claude runs it, captures evidence (screenshots, stdout snippets, DB query output), and reports `READY FOR USER` with `harness PASS` annotation. Patrick still runs it on real hardware to catch hardware-only issues, but the harness pre-check filters obvious bugs.

**If the harness can execute part of the journey,** Claude runs what's possible and notes which steps need manual execution. The journey still gets handed off.

**If the harness cannot execute the journey at all** (e.g., requires actual network disconnection, requires inspecting a physical iOS device), Claude states this explicitly and hands the full journey to Patrick.

Never claim a fix is verified by harness alone. Real-hardware run by Patrick is the final word.

---

## Splitting vs conditionalizing

When a fix has multiple code paths, **always split into separate journeys, never conditionalize**.

❌ Bad: "Step 4: Personal saves first OR Pro saves first depending on timing..."  
✅ Good: Two journeys — `1A` (Pro saves first → Personal hits 409) and `1B` (Personal saves first → Pro hits 409). Each fully deterministic.

---

## Idempotency

A journey must be re-runnable without manual reset. Achieve this with a **single per-journey reset command** that wipes prior state and re-seeds the known fixture. Claude does the substitution / scripting work upfront — Patrick should only need to copy-paste, click, and type literal strings.

### The reset-script pattern (preferred)

Each workstream provides one or more fixture scripts that are **copy-paste-able as a single blockquote**. Patrick should not need to set environment variables, do string substitution, or chain multi-step setup.

Each journey starts with a single command:

> ```bash
> cd <repo> && uv run --env-file ../.env python doc/plans/<workstream>/fixtures/reset_<scenario>.py
> ```

The script:
- Connects to the real PostgreSQL via `docker exec fd-postgres psql ...`
- Finds or creates the test diagram (idempotent — run as many times as needed)
- Resets its blob to the known baseline (specific people, events, flags)
- Bumps version (so any in-flight client save will hit a 409 and refresh)
- Prints the diagram name to open in Pro/Personal

Test artifact names in journey steps are **literal hardcoded strings** scoped by journey code (e.g., `J1A_Personal_edit`, `J3_Pro_add`). Cross-run pollution is prevented by the reset, not by tag uniqueness.

❌ Avoid: `Add person named "A_PE_$TAG"` — forces Patrick to substitute every time he types  
✅ Use: `Add person named "J1A_Personal_edit"` after running `python fixtures/reset_baseline.py`

### Verification scripts

Pair each reset script with a `verify.py` that prints the diagram's current state in human-readable form (lists of people with id+name+key fields, list of events). The journey's "Verify" step is a single blockquote running this script. The pass criterion compares specific lines of the output against expected values stated in the journey.

❌ Avoid: pseudocode SQL pipelines that won't run as-pasted (e.g., `psql -tAc | python -c "..."` — `-tAc` produces `|`-delimited output that breaks the pipeline if the data contains `|`).  
✅ Use: a single `python fixtures/verify.py` that prints clean labeled output.

### Fixture script implementation rules

When Claude writes the fixture script:
1. **Construct the test diagram blob via the actual Scene/Person/Event API** so it round-trips through `Scene.read` cleanly. Hand-crafted dicts often miss fields the reader needs and cause silent loads of empty scenes.
2. **`util.WINDOW_BG`** must be set before instantiating Scene items — `QmlUtil` normally sets this; in a fixture script set it directly: `from PyQt5.QtGui import QColor; util.WINDOW_BG = QColor("white")`.
3. **`QApplication`** must exist before any Scene; use `QT_QPA_PLATFORM=offscreen` env var.
4. The script's stdout should end with a one-liner Patrick acts on, e.g., `In Pro and Personal, open the diagram named: <NAME>`.

### One-shot journeys

If a journey is intrinsically one-shot (e.g., "delete this row"), state that explicitly so Patrick doesn't re-run by accident.

---

## Robotic step rules

A "robotic" step has zero ambiguity. Concrete rules:

### Verify via DB query or shell command, not UI scanning

"The diagram looks right" is not verifiable. "Running this exact `psql` command outputs this exact line" is.

Each verification step is:
- A copy-paste-able shell command (or app stdout grep)
- An exact expected output or pattern
- A stated fail observable

### Setup checks: each is one command + expected output

❌ "Flask dev server up"  
✅ ```bash
curl -s http://127.0.0.1:8888/ > /dev/null && echo OK || echo "FAIL"
```
Expect: `OK`. If `FAIL`, abort and start Flask.

### UI actions: shorthand is acceptable, summary is not

Patrick built the apps. "Cmd+S to save", "double-click row labeled X in the file manager" — concrete. "Open the diagram" without saying how — summary, not allowed.

When Claude doesn't know an exact click path, Claude reads the relevant UI code (.ui files, .qml files, action handlers) BEFORE writing the step. If still unknown, the journey says explicitly: "TODO: confirm exact click path for X — Patrick fill in once". The fill-in becomes permanent for future re-uses.

### One action, one observable

Each numbered step has exactly one user action AND one observable. If a step describes two things, split it.

❌ "Click Save and verify the file manager updates"  
✅ "5. Press Cmd+S. **Observable:** save indicator briefly appears in title bar."  
   "6. Wait 1 second. **Observable:** file manager row's modified timestamp shows current time."

---

## Where journeys live

In the workstream tracker (e.g. `familydiagram/doc/plans/2026-04-17--data-integrity/README.md`). Not separate files. The tracker is the single page Patrick scans.

---

## Pre-flight setup rules

**Flask server is assumed running.** Never check whether Flask is up or whether Docker is running. Pre-flight is only for test data initialization.

**Test fixtures live in the workstream folder** (e.g. `familydiagram/doc/plans/2026-04-17--data-integrity/fixtures/`). The journey references them by relative path.

**Single setup command.** Pre-flight is exactly one blockquote command that initializes the diagram to a known state. No multi-step environment checks. Example:

> `uv run python familydiagram/doc/plans/2026-04-17--data-integrity/fixtures/seed_journey_1a.py`

The seed script is idempotent — re-running it resets to the known state without manual cleanup.

---

## Scope discipline

**One bug per journey session.** Claude writes the journey and fix for one bug at a time. Do not implement or write journeys for multiple bugs in a single session. This preserves the ability to bisect regressions — each bug's fix is a separate, verifiable commit.

**Steps test only the bug at hand.** Do not include observations about general app functionality that isn't directly relevant to the bug being tested. Every step must be necessary to reach or verify the specific failure mode.

---

## When the journey is wrong

If Patrick reports a fail and Claude determines the journey was ambiguous or wrong (rather than the fix), Claude rewrites the journey AND the fix as needed. Patrick should never have to debug an ambiguous test.
