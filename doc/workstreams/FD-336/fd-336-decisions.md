# FD-336 design decisions (coordinator, 2026-08-25)

Inputs: ticket ACs (ratified by Patrick in chat), `fd-336-code-map.md`, `fd-336-critics.json`, `fd-336-reconciled.json`.
Each decision is a default Patrick may override; all are reversible inside the FD-336 worktrees.

| # | Question | Decision | Why |
|---|---|---|---|
| D1 | Discussion binding | `POST /personal/discussions/` honors `diagram_id` when the caller owns that diagram; absent → free diagram (Personal unchanged). **btcopilot change** — the ticket's "no btcopilot changes needed" is wrong. | Grounded: the route ignores `diagram_id` and hardwires the free diagram, so every embedded discussion/extract/commit would land on the wrong row while looking green in the client. |
| D2 | Chat defaults on a Pro case | `ensure_chat_defaults` (inject User id 1 / Assistant id 2) runs only for the caller's free diagram. On other diagrams the coach's subject is the primary-flagged person if any, else none. Every server-side row write bumps `version` (`set_diagram_data` included). | Grounded: chat turns rewrite the row unversioned; on a clinician case that creates phantom people, id collisions, and lets a stale Pro save overwrite silently. |
| D3 | Which server diagrams enable the feature | Owner-only, read-write opens. Shared cases and read-only opens show the slot disabled with a one-line explanation. | Personal routes are owner-only (403 otherwise); widening auth is a separate ticket. |
| D4 | Embedded pipeline saves vs unsaved Pro edits | An accept persists through the single saver, which writes the whole Scene; afterwards the Pro document is clean (no `*`). | One writer, one truth; the coach then sees the current state. Surprising-but-consistent beats a split-brain row. |
| D5 | Undo after accept | Accept pushes ONE command on Pro's Scene undo stack; undo removes the committed items from the Scene, restores the pre-accept PDP on the Diagram, and persists via the saver (card returns, row consistent). Personal's private undo stack and `HandlePDPItem` retire. | "One turn = one undo step" (2026-08-25 brainstorm); the half-undo (blob rewritten, scene untouched) is the split-brain the critics flagged. |
| D6 | Save-before-chat shape | On Send or Extract with a dirty Pro stack: modal "Save changes before chatting?" Save / Cancel. Save completes the PUT before the POST; Cancel blocks the send. Clean stack → no prompt. | Coach context and extraction dedup both read the persisted row. |
| D7 | S1 byte-identical against what | Output-vs-output: the saver's PUT body and stored row equal what the pre-refactor `setData` produced for identical Scene + cached row, on three row shapes (no pdp/clusters; populated; legacy with unknown top-level keys). | A raw-row gate is unpassable (canonicalization already drops unknown keys). |
| D8 | Diagram identity across cache swaps | The saver owns the merge-baseline snapshot and re-resolves the Diagram by id from the file model on every save. The snapshot-loss-on-swap path is in S3's concurrent-save scope. | Grounded: the 30-min poll / re-sync replaces the cached object and loses the ad-hoc baseline → spurious deletes. |
| D9 | lastItemId after block reservation | Client-side clamp in the saver: `max(server stored, scene.lastItemId, allocator block end)`. No server-side guard this ticket. | Keeps btcopilot scope minimal; the client is the only /v1 writer. |
| D10 | Label field contract | Writer emits Scene keys at commit: `{id, name, lastName, gender, parents}`; `name = person.name or person.last_name` (lastName None in that fallback). No multi-token splitting. Existing rows: a version-gated compat migration renames `last_name→lastName` and fills an empty `name` from `lastName`, so 1924 heals on reopen. | Grounded: name-only already labels; the real defects are dropped last names (snake key never read) and blank symbols for last-name-only people. Writer fix + data migration, not a defensive reader. |
| D11 | Placement of accepted people | Cascade offset from the viewport centre (not (0,0), not auto-arrange). | Ticket headline is "vibe-coding visible immediately"; 1924 has 21 people stacked at the origin. Incremental placement proper is a later story. |
| D12 | Save failure | A failed server save leaves the document dirty (today it is marked clean and edits are lost on close). Fixed in S1 since the saver returns success/failure. | Data-loss path, one line. |
| D13 | Standalone Personal after decomposition | Keeps its own Session/AppConfig/reload-on-session-change; only the Pro embedding injects Pro's Session and skips them. | Personal is unchanged for phone users. |
| D14 | Cross-device liveness | Reopen-to-see is acceptable; the 30-min poll stays. | Out of scope. |
| D15 | LLM in the e2e harness | Use the real key from `.env` on the ephemeral server when present; otherwise the chat-dependent journeys move to the human track. | Decided at WP-H. |
| D16 | MCP bridge in Pro | Bridge commands must not route Pro-instance `save_diagram`/`open_server_diagram` through the embedded controller; disambiguate by app type. | Grounded: the bridge prefers a PersonalAppController when it finds one. |

## Build order (worker model: Opus; briefs/review: Fable)

| WP | Repo | Scope | Gate |
|---|---|---|---|
| A | btcopilot | D1, D2, D10 writer (`committed_person_chunk`), tests | btcopilot suite green; new route/commit tests |
| B | familydiagram | Copilot removal (engine, view, qml, action, enum, tab index mapping, tests) | suite green; drawer loads with zero QML warnings; Triangles tab intact |
| C | familydiagram | S1 `DiagramSaver` wrapper + D7 byte-identical test + D8 baseline ownership + D12 | byte-identical on 3 rows; existing save tests green; save failure keeps dirty |
| D | familydiagram | `PersonalAppController` decomposition, no behaviour change (discussion, pdp, loader, peripherals) + unbind-on-scene-switch | personal tests green; late-callback test |
| E | familydiagram | S2: pipeline on the saver, JSON path retired, D5 undo command | concurrent tests drive the REAL saver; accept→undo consistency |
| F | familydiagram | Embed in CaseProperties, D3 gate, hamburger hidden, D6 prompt, D16 bridge | pytest-qt lifecycle tests; QML warnings zero over 20 open/close cycles |
| G | familydiagram | S3 complete DiagramData, D9 clamp, D10 migration, D11 placement, round-trip test | pdp/clusters survive a Pro save; lastItemId ≥ block end; round-trip equal |
| H | both | MCP journeys + human script | journeys green; human script handed off |
