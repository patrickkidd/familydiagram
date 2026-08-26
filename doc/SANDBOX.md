# The sandbox

One harness for every ticket. It stands up a backend, a Pro app and a Personal app
together, all on the ticket's own code and one database, on a port nobody has to
know. It never touches the 8888 server or the dev database.

**Do not write a per-ticket sandbox script.** A ticket-named copy of any of this is
a defect — extend the harness instead. This is the only launch recipe in the repos.

---

## The one command

```
bin/sandbox up FD-336 --seed family --pro --personal
```

It prints the backend url, the database, which checkout each repo runs from, and an
env block to paste into a shell. Then:

```
bin/sandbox status          # url, ports, pids, checkouts, what is seeded
bin/sandbox reseed --seed hostile
bin/sandbox down            # backend, apps, redis, celery worker, throwaway database
```

`up` options:

| Option | Values | Default |
|---|---|---|
| `--seed` | profile name, a path to an exported json file, `prod`, or `none` | `none` |
| `--llm` | `stub`, `real` | `stub` |
| `--broker` | `memory`, `redis` | `memory` |
| `--user` | email the apps and the web UI log in as | the seed's own first user |
| `--pro` / `--personal` | launch that app against the backend | neither |

`--seed prod` means the production duplicate: it restores the production dump into a
throwaway database instead of seeding fixtures.

## Under it

`bin/sandbox` is a thin CLI over two things in this repo:

- `mcpserver/ephemeral_server.py` — one backend process, run directly when you want
  a backend and nothing else:
  ```
  uv run --directory ~/theapp python familydiagram/mcpserver/ephemeral_server.py \
      --ticket FD-336 --db sqlite --seed family --broker memory --llm stub
  ```
  It prints `READY:<port>` and `MANIFEST:<json>` on stdout once the server answers
  its own health check and the seed is applied. The manifest carries the url, the
  database, the broker, the resolved checkouts and everything the seed created.
  Flags: `--ticket`, `--port` (default: a free one), `--db`, `--seed`, `--broker`,
  `--llm`, `--prompts`, `--auto-auth-user`, `--hardware-uuid`.

  **`--hardware-uuid` is what makes the desktop apps open licensed.** The app
  treats a license as active only when one of its activations names a machine
  whose code is the app's own hardware uuid, so a seed without it produces rows
  that look licensed and behave unlicensed — the apps open to a "beta version
  without a license" prompt. Pass `pkdiagram.util.HARDWARE_UUID`; anything
  launching an app through `TestInstance` already does. The backend echoes the
  code it used and the launcher fails if it does not match.
- `mcpserver/mcp_server.py` — the same backend plus real apps, driven by an agent.

Nothing here ever kills a process by name or pattern. Each sandbox kills only the
children it started, so two units can run at once.

**Driving the launcher yourself: drain its pipes.** If you spawn it with piped
stdout or stderr and stop reading, it blocks mid-write once the pipe buffer fills —
the sandbox hangs with no error, and its own cleanup never runs. Read both streams
in threads, or send them straight to a file. The MCP harness already does this; it
is only a trap when you build the subprocess yourself.

---

## Agent-driven journeys (MCP)

```python
launch_app(ticket="FD-336", personal=False, seed="family", broker="redis")
# → {success, instance_id, server_port, manifest, bridge_connected, ...}

launch_app(ticket="FD-336", personal=True, ephemeral_server=False,
           server_url=<the first instance's manifest["url"]>)   # same database

seed_server_data(profile="hostile")            # or data={"users": [...]}
get_checkouts(ticket="FD-336")                 # which checkout each repo runs from
close_all_instances()
```

`TestInstance.start_backend(auto_auth_user, seed, db, broker, llm)` brings up a
backend with no app in front of it — for backend-only tests and for anything that
wants the manifest without paying for two Qt launches.

The manifest is the same object everywhere: `url`, `port`, `db`, `broker`, `llm`,
`prompts`, `dir`, `user` (the account the apps and the web UI log in as),
`checkouts`, and `seed` (the whole seed response, including its named-case
manifest).

- `ephemeral_server=True` is the default: every instance gets its own backend, its
  own database, its own prefs and app-data directories. Passing neither
  `ephemeral_server` nor `server_url` raises — the harness never targets a server it
  did not start, and there is no 8888 fallback.
- Two apps on one database is the `server_url` case above, and only that. An
  instance sharing someone else's backend cannot know which account that backend
  seeded, so pass `username=` — the other manifest's `user` is the account it
  seeded and licensed. Omitting it is an error, not a guess.
- A dead bridge, a main thread that never goes idle, or a backend that never answers
  health is a **failed launch**, not a warning.
- The 40-odd bridge tools (`click`, `find_element`, `get_app_state`, `save_diagram`,
  `open_server_diagram`, `inject_pdp_data`, …) are listed in `mcpserver/README.md`.

### Registration

`familydiagram/.mcp.json` registers `familydiagram-testing`; the same block is
mirrored in `theapp/.mcp.json` so it resolves from the usual launch directory. Both
name the origin clone's `mcp_server.py`, because a registration file can hold only
one path — on startup the server resolves `FD_TICKET` and **re-executes itself from
that checkout's harness**, so the tools you get are the ticket's, not master's.
`FD_WORKTREE_FAMILYDIAGRAM` does the same for a checkout with no ticket.

Restart Claude Code after editing either file, then `/mcp` to confirm. The server
logs the checkouts it resolved as its first line.

---

## Data

### Seed profiles

`--seed`, `seed_server_data(profile=...)` and `POST /test/seed {"profile": ...}` all
take the same expression: a profile name, several composed with `+`, and integer
arguments after `:`.

| Profile | What it seeds |
|---|---|
| `minimal` | one licensed user whose only diagram is the empty free diagram |
| `family` | a coherent three-generation family, plus a first discussion and a returning discussion whose re-extraction cursor is already advanced |
| `hostile` | the non-happy paths, deliberately (see below) |
| `random:<seed>:<people>` | a deterministic structurally-valid family — same seed and size, byte-identical data |

`family+hostile` seeds both. `random:7:20` seeds twenty people from seed 7.

Every seed returns a **manifest**: a map from case name to the ids it created and one
line saying what the case is for. Use it instead of hard-coding ids.

**Who you are logged in as, and why it decides licensing.** Only the **first**
account seeded can hold this machine's hardware uuid — the backend's machine codes
are globally unique, so everyone seeded after it gets a per-user code and cannot
open the desktop apps at all. The sandbox therefore seeds the login account first:

| You pass | Signed in as | Seeded |
|---|---|---|
| `--user EMAIL` | that account | it first, then the profile |
| nothing, with a seed | the seed's own `primary_user` | the profile, whose first user it is |
| nothing, no seed | nobody — a backend with no account | nothing |

Either way the manifest's `user` is the account that is signed in and licensed, and
the launcher fails if the backend licensed someone else. Naming an account never
changes *what* is seeded — the profile is seeded in full, and an account that is not
in it is added rather than replacing it.

Naming an account that **the seed you asked for** defines as a hostile licence
case is refused before anything is seeded:

    primary_user 'hostile+expired@test' is the expired-license case; the account
    the apps log in as cannot be one the seed leaves unlicensed

An account cannot be both the licensed account the apps sign in as and the case that
proves an expired licence. Drive those cases from a normal login account —
`--user hostile@test` owns the hostile *data* and signs in fine, while
`hostile+expired@test` and `hostile+nolicense@test` stay unlicensed for you to test
against.

The refusal knows only what the seed defines, so it is the profile that makes those
names mean something: `--user hostile+expired@test --seed hostile` is refused, while
the same name with `--seed family` is just an account that profile never heard of,
and is created and licensed like any other. Adding a user to a live
sandbox does not make it usable by the apps; that is why `reseed` resets the
database first. Reseeding also destroys the previous account, so anything already
signed in as it is stale — take the sandbox down and back up rather than reseeding
under a live app.

The hostile profile exists because language models under-generate bad data. It
covers: empty, single-token, last-name-only, unicode and 200-character names;
duplicate names; a self-referential pair bond; an event pointing at a deleted person;
a child of two bonds; staged data referencing rows that are gone; an empty diagram
and a very large one; a stale row version; diagrams shared read-only and read-write;
another user's private diagram; an expired license, no license at all, and a user
with no free diagram; a discussion with no owner and one bound to someone else's
diagram; emoji and very long statements.

### Production data

`--db prod` restores `fdserver/prod.dump` into a throwaway `fd_sandbox_<ticket>`
database on the local fdserver Postgres, points the backend at it, and drops that
database on `down`. The shared `familydiagram` dev database is never touched and the
dump is never committed. Refresh the dump with `fdserver/bin/pull_prod_to_dev.sh`.

It needs Docker running; if it isn't, the sandbox says so and names the command
rather than failing obscurely. The Postgres container is started from
`fdserver/docker-compose.yml` if it is not already up, and its credentials are read
from the running container, never hard-coded here.

This is real user data on Patrick's machine. It is not anonymised — treat a
production sandbox as production.

### Seeding from a file

`--seed <file.json>` takes either shape and routes on the singular keys:

- a **seed spec** (`users`, `diagrams`, `discussions`, `access_rights`) is merged the
  same way an inline payload is → `/test/seed`;
- a **production export** (`user`, `diagram`, plus `discussions`, `speakers`,
  `statements`) is loaded **preserving every row id**, so a bug reported against real
  rows can be replayed exactly → `/test/import`.

Examples of both live in `btcopilot/btcopilot/testing/examples/`.

### Other test routes

`/test/health`, `/test/reset`, `/test/seed`, `/test/import`,
`/test/diagrams/<id>` (GET and PUT raw pickle), `/test/diagrams/seed_pickle`. They
live in `btcopilot/btcopilot/testing/`, so they version-lock with the models they
seed, and they are registered only under `TESTING` or `BTCOPILOT_TEST_ROUTES=1`,
never under a production config.

### Background jobs

`--broker memory` (default) has no worker: anything queued silently never runs.
Rebuild diagram / deep re-extract needs `--broker redis`, which starts a private
redis on a free port and a celery worker (`--pool=solo`) against the same app
configuration, both as children of the backend.

### LLM, and what a sandbox can reach

`--llm stub` (default) replaces the model clients with a deterministic stand-in, so
no sandbox spends money or needs API keys. It also **blanks the model credentials in
the sandbox's environment**, which matters more than it sounds: Flask's dev server
loads `~/theapp/.env` when it starts, so without that a sandbox silently inherits
Patrick's real Anthropic, Gemini, OpenAI and other production keys and a journey
that forgot `--llm stub` would bill his account.

`--llm real` deliberately keeps them: it uses the real clients and the real fdserver
prompts, which is what makes extraction results representative rather than the
open-source stubs. It spends money on every run. The prompts themselves come from
the resolved fdserver checkout either way (`--prompts auto`).

The database is never at risk from that inheritance — the sandbox sets its own
database before the server starts, and Flask's loader never overwrites a name that
is already set.

`GET /test/health` reports `credentials_present`, read after that dotenv load:
whether the serving process still holds **any** credential a sandbox was supposed
to be stripped of — the model providers, but also transcription, Stripe, Atlassian
and GitHub. It is the check worth asserting, because `llm: "stub"` only says the
stand-in is installed. It means "this sandbox is not hermetic", which is broader
than "this run can spend money": a stubbed sandbox that inherited nothing but a
GitHub token reports `true`. The names belong to btcopilot
(`btcopilot.testing.credentials`), so what gets blanked and what health reports on
cannot drift apart.

Build and release credentials (`FD_BUILD_*`, `TWINE_*`) are deliberately not on that
list — nothing a sandbox starts reads them at runtime.

---

## Which code runs

`Checkouts.resolve(ticket)` decides, per repo, and every entry point prints the
result. For each of familydiagram, btcopilot and fdserver:

1. `FD_WORKTREE_<REPO>` if set (must exist),
2. else `<repo>/.claude/worktrees/<ticket>` if it exists,
3. else the origin clone — the fallback is always stated, never silent.

The ticket comes from the argument, else `FD_TICKET`, else the worktree the harness
itself is running from.

| Role | Runs from |
|---|---|
| MCP harness | the familydiagram checkout — the server re-executes itself there |
| Backend | the btcopilot checkout, first on its import path |
| Celery worker | the same, with the backend's configuration by environment |
| Prompts | the fdserver checkout's `prompts/private_prompts.py` |
| Pro / Personal app | the familydiagram checkout, with the btcopilot checkout for schema and signing |
| Database | per instance: a temp sqlite file, a given uri, or the production restore |
| Prefs / app data | a temp directory per instance |

**The native module is shared.** `_pkdiagram` comes from the workspace venv, not from
a worktree. Running `make` in a worktree overwrites that one shared binary for every
checkout, Patrick's included. There is no per-worktree native build — if a ticket
changes C++, that is a known collision to coordinate, not something the harness
isolates.

---

## Failures and timeouts

Every wait has a deadline and every deadline is a failure.

| Wait | Limit |
|---|---|
| backend answers `/test/health` | 30s |
| backend reports ready to its caller | 120s, 900s with `--db prod` |
| redis accepts a ping | 15s |
| celery worker reports ready | 60s |
| bridge accepts a connection | 10s |
| app main thread goes idle | 30s (`timeout=`) |
| bridge command | 60s, 130s for save / open |

Troubleshooting:

- **`No backend: pass ephemeral_server=True…`** — deliberate. Nothing defaults to a
  server the harness did not start.
- **`No sandbox backend at <url>`** — a `server_url` you passed is not answering. An
  app is never launched at a backend that failed its health check.
- **Backend exited early** — the launcher's traceback is in the message. A missing
  `btcopilot.testing` means the btcopilot checkout predates the test package.
- **`Docker is not running`** — only `--db prod` needs it.
- **App fails to start with an import error** — stale bytecode in the worktree:
  `find . -name "*.pyc" -delete`.
- **Nothing seeded** — `--seed` defaults to `none`.
- **Orphans** — `close_all_instances()`, or `bin/sandbox down`. The MCP server also
  cleans up on exit, on signals, and when its parent dies.

## Tests

`mcpserver/tests/` is not in `pytest.ini`'s `testpaths`, so it never runs in the
default suite. Name the path to run it:

```
uv run pytest mcpserver/tests/test_checkouts.py        # fast, no processes
uv run pytest mcpserver/tests/test_sandbox.py          # fast, no processes
uv run pytest mcpserver/tests/test_fd336_harness.py    # real backends and apps
uv run pytest mcpserver/tests/test_concurrent_save.py  # launches two real apps
```

Anything that launches a real app or backend is marked `sandbox`.
