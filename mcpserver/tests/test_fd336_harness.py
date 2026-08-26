"""
FD-336 sandbox harness. Each test names the oracle item it enforces:
doc/workstreams/oracles/FD-336/2026-08-26--1-fd-336-harness.oracle.md

These drive the real launcher and real child processes — nothing here is faked.

    uv run pytest mcpserver/tests/test_fd336_harness.py
"""

import hashlib
import json
import os
import pickle
import signal
import subprocess
import sys
import time
import wsgiref.handlers
from datetime import datetime
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import btcopilot
from btcopilot.testing.credentials import BLANKED
from btcopilot.testing.fixtures import HUGE_PEOPLE, Case
from btcopilot.testing.llmstub import coach_reply
from mcpserver.checkouts import Checkouts, Repo, Source
from mcpserver.mcp_server import (
    LoginState,
    TestInstance,
    close_all_instances,
    get_checkouts,
    launch_app,
    seed_server_data,
)
from mcpserver.sandbox import Db, Llm, MANIFEST_PREFIX, READY_PREFIX

pytestmark = pytest.mark.sandbox

TICKET = "FD-336"
UNKNOWN_TICKET = "FD-000"
PATRICK_PORT = 8888

ROOT = Path("/Users/patrick/theapp")
FD_WORKTREE = ROOT / "familydiagram" / ".claude" / "worktrees" / TICKET
BTCOPILOT_WORKTREE = ROOT / "btcopilot" / ".claude" / "worktrees" / TICKET
LAUNCHER = FD_WORKTREE / "mcpserver" / "ephemeral_server.py"

BACKEND_TIMEOUT = 90
APP_TIMEOUT = 60
HTTP_TIMEOUT = 20
HUGE_READ_TIMEOUT = 30
REAP_TIMEOUT = 20

HOSTILE_PROFILE = "hostile"
FULL_PROFILE = "family+hostile"
HOSTILE_OWNER = "hostile@test"
SHARED_USER = "harness@example.com"
SEED_PASSWORD = "test"
STUB_PREFIX = coach_reply("").strip()

# Every degenerate shape oracle H3 requires the mocked seed to exemplify.
REQUIRED_CASES = [
    Case.EmptyName,
    Case.SingleTokenName,
    Case.LastNameOnly,
    Case.UnicodeName,
    Case.LongName,
    Case.DuplicateNames,
    Case.SelfReferentialBond,
    Case.DanglingEventPerson,
    Case.StagedDanglingPdp,
    Case.EmptyDiagram,
    Case.HugeDiagram,
    Case.StaleVersion,
    Case.SharedReadOnly,
    Case.SharedReadWrite,
    Case.NoAccess,
    Case.ExpiredLicense,
    Case.NoLicense,
    Case.NoFreeDiagram,
    Case.OrphanDiscussion,
]


# ---------------------------------------------------------------------------
# Backend under test
# ---------------------------------------------------------------------------


def _env_without_worktrees() -> dict:
    """The launcher's environment with both FD-336 worktrees removed from the
    import path, so worktree code inside the server can only come from --ticket."""
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env["PYTHONUNBUFFERED"] = "1"
    kept = [
        entry
        for entry in env.get("PYTHONPATH", "").split(os.pathsep)
        if entry and Path(entry) not in (FD_WORKTREE, BTCOPILOT_WORKTREE)
    ]
    env["PYTHONPATH"] = os.pathsep.join(kept)
    return env


def _env_without_credentials() -> dict:
    """Blanked rather than unset: Flask's app.run() calls flask.cli.load_dotenv(),
    which walks up from the working directory and fills every name the sandbox has
    not already set from ~/theapp/.env — so an absent provider key would be replaced
    by Patrick's production one. A name already present, even empty, is left alone."""
    env = _env_without_worktrees()
    env.update({name: "" for name in BLANKED})
    return env


def _start_backend(*flags, env=None):
    """Run the launcher and read its protocol lines. --port is never passed: the
    contract is that it picks a free one and reports the choice.

    Returns (process, manifest).
    """
    process = subprocess.Popen(
        [sys.executable, "-u", str(LAUNCHER), *flags],
        env=env or _env_without_worktrees(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    port = None
    deadline = time.time() + BACKEND_TIMEOUT
    while time.time() < deadline:
        line = process.stdout.readline()
        if not line:
            stderr = process.stderr.read()
            process.wait(timeout=5)
            raise AssertionError(
                f"launcher exited before MANIFEST (rc={process.returncode}):\n{stderr[-2000:]}"
            )
        if line.startswith(READY_PREFIX):
            port = int(line[len(READY_PREFIX) :])
        elif line.startswith(MANIFEST_PREFIX):
            manifest = json.loads(line[len(MANIFEST_PREFIX) :])
            assert port == manifest["port"], "READY port disagrees with the manifest"
            return process, manifest
    _stop(process)
    raise AssertionError(f"launcher never reported ready within {BACKEND_TIMEOUT}s")


def _stop(process) -> None:
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _health(url: str) -> dict:
    response = requests.get(f"{url}/test/health", timeout=HTTP_TIMEOUT)
    assert response.status_code == 200, f"{url}/test/health: {response.status_code}"
    return response.json()


# ---------------------------------------------------------------------------
# Signed client
# ---------------------------------------------------------------------------


def _headers(method, resource, secret, username, body=b"", content_type="text/html"):
    content_md5 = hashlib.md5(body).hexdigest()
    date = wsgiref.handlers.format_date_time(time.mktime(datetime.now().timetuple()))
    signature = btcopilot.sign(secret, method, content_md5, content_type, date, resource)
    return {
        "FD-Authentication": btcopilot.httpAuthHeader(username, signature),
        "FD-Client-Version": "99.99.99",
        "Date": date,
        "Content-MD5": content_md5,
        "Content-Type": content_type,
    }


def _login(url: str, username: str, password: str = SEED_PASSWORD) -> dict:
    body = pickle.dumps({"username": username, "password": password})
    response = requests.post(
        f"{url}/v1/sessions",
        data=body,
        headers=_headers(
            "POST", "/v1/sessions", btcopilot.ANON_SECRET, btcopilot.ANON_USER, body=body
        ),
        timeout=HTTP_TIMEOUT,
    )
    assert response.status_code == 200, f"login {username}: {response.status_code} {response.text[:200]}"
    return pickle.loads(response.content)["session"]["user"]


def _request(user, method, url, resource, body=None, timeout=HTTP_TIMEOUT):
    payload = json.dumps(body).encode() if body is not None else b""
    return requests.request(
        method,
        f"{url}{resource}",
        data=payload or None,
        headers=_headers(
            method,
            resource,
            user["secret"].encode(),
            user["username"],
            body=payload,
            content_type="application/json" if body is not None else "text/html",
        ),
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Process bookkeeping
# ---------------------------------------------------------------------------


def _descendants(pid: int) -> list:
    found = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True)
    children = [int(x) for x in found.stdout.split()]
    return children + [g for child in children for g in _descendants(child)]


def _alive(pid: int) -> bool:
    state = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True
    )
    return bool(state.stdout.strip()) and not state.stdout.strip().startswith("Z")


def _free_port() -> int:
    import socket

    with socket.socket() as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


# ---------------------------------------------------------------------------
# H2 — dynamic port, never Patrick's server
# ---------------------------------------------------------------------------


def test_backends_get_distinct_free_ports():
    """H2: the backend listens on a dynamically allocated free, unique port; the
    number is irrelevant to the caller and is never 8888."""
    first = TestInstance.create(ticket=TICKET)
    second = TestInstance.create(ticket=TICKET)
    try:
        ok, message = first.start_backend()
        assert ok, message

        ok, message = second.start_backend()
        assert ok, message

        assert first.server_port != second.server_port

        assert PATRICK_PORT not in (first.server_port, second.server_port)

        assert _health(first.manifest["url"])["success"] is True

        assert _health(second.manifest["url"])["success"] is True
    finally:
        first.close(force=True)
        second.close(force=True)


# ---------------------------------------------------------------------------
# H2 — the ticket's code, and it says which
# ---------------------------------------------------------------------------


def test_resolve_prefers_the_ticket_worktree_and_says_so():
    """H2: each repo runs the ticket's worktree, falling back to the origin clone
    only when the ticket has no worktree for it, and saying so."""
    resolved = Checkouts.resolve(TICKET)
    assert (resolved.familydiagram.path, resolved.familydiagram.source) == (
        FD_WORKTREE,
        Source.Worktree,
    )

    assert (resolved.btcopilot.path, resolved.btcopilot.source) == (
        BTCOPILOT_WORKTREE,
        Source.Worktree,
    )

    unknown = Checkouts.resolve(UNKNOWN_TICKET)
    assert [unknown[repo].source for repo in Repo] == [Source.Origin] * len(Repo)

    assert [unknown[repo].path for repo in Repo] == [ROOT / repo.value for repo in Repo]

    description = resolved.describe()
    assert all(repo.value in description for repo in Repo)

    assert all(resolved[repo].source.value in description for repo in Repo)

    tool = get_checkouts(ticket=TICKET)
    assert tool[Repo.BTCopilot.value]["source"] == Source.Worktree.value


def test_backend_for_a_ticket_runs_that_ticket_btcopilot():
    """H2: the server really is the ticket's code. Started with both worktrees
    stripped from PYTHONPATH, so worktree btcopilot inside it can only have come
    from --ticket resolution rather than from this test's environment."""
    process = None
    try:
        process, manifest = _start_backend("--ticket", TICKET)
        checkouts = manifest["checkouts"]
        assert checkouts[Repo.BTCopilot.value] == {
            "path": str(BTCOPILOT_WORKTREE),
            "source": Source.Worktree.value,
        }

        loaded = _health(manifest["url"])["btcopilot"]
        assert Path(loaded) == BTCOPILOT_WORKTREE / Repo.BTCopilot.value
    finally:
        _stop(process)


def test_launch_without_a_backend_refuses_to_start():
    """H2/H4: with neither its own sandbox backend nor an explicit server_url the
    harness refuses, rather than silently targeting Patrick's 8888."""
    instance = TestInstance.create(ticket=TICKET)
    try:
        with pytest.raises(ValueError):
            instance.launch(ephemeral_server=False, headless=True, timeout=10)

        assert (instance.process, instance.server_process, instance.server_port) == (
            None,
            None,
            None,
        )
    finally:
        instance.close(force=True)


# ---------------------------------------------------------------------------
# H3 — the mocked seed is deliberately non-happy-path
# ---------------------------------------------------------------------------


def test_seed_manifest_names_every_hostile_case_and_serves_the_huge_diagram():
    """H3: the mocked seed exemplifies the named non-happy paths, and the very
    large diagram is readable within the harness timeout."""
    try:
        launched = launch_app(
            ticket=TICKET,
            seed="minimal",
            llm=Llm.Stub.value,
            headless=True,
            login_state=LoginState.LoggedIn.value,
        )
        assert launched["success"] is True, launched.get("message")

        url = f"http://127.0.0.1:{TestInstance.get().server_port}"
        advertised = _health(url)["profiles"]
        unknown = set(FULL_PROFILE.split("+")) - set(advertised)
        assert not unknown, f"profiles this test names are not seedable: {unknown}"

        refused = requests.post(
            f"{url}/test/seed", json={"profile": "no-such-profile"}, timeout=HTTP_TIMEOUT
        )
        assert refused.status_code == 400, (
            f"an unknown seed profile must be refused loudly, got {refused.status_code}"
        )

        seeded = seed_server_data(HOSTILE_PROFILE)
        manifest = seeded["manifest"]
        missing = [case.value for case in REQUIRED_CASES if case.value not in manifest]
        assert not missing, f"seed manifest omits hostile cases: {missing}"

        huge = manifest[Case.HugeDiagram.value]
        assert str(HUGE_PEOPLE) in huge["what"], f"huge case is not {HUGE_PEOPLE} people: {huge}"

        user = _login(url, HOSTILE_OWNER)
        started = time.time()
        response = _request(
            user, "GET", url, f"/v1/diagrams/{huge['diagram_id']}", timeout=HUGE_READ_TIMEOUT
        )
        assert response.status_code == 200, response.text[:300]

        assert len(pickle.loads(response.content)["data"]) > 0
        assert time.time() - started < HUGE_READ_TIMEOUT
    finally:
        close_all_instances()


# ---------------------------------------------------------------------------
# H3/H4 — the LLM stub answers locally; real without a key fails loudly
# ---------------------------------------------------------------------------


def test_llm_stub_answers_locally_and_holds_no_credential():
    """H3/H4: llm=stub serves a chat turn with no provider involved, and the
    sandbox holds none of the credentials that would let it reach one.

    Deliberately launched from an untouched environment — the blanking has to be
    the harness's own doing. Flask's app.run() loads the nearest .env before
    serving, so before the launcher blanked them a stubbed sandbox held Patrick's
    live keys and any bypass of the stub would have billed him.
    """
    process = None
    try:
        process, manifest = _start_backend(
            "--ticket", TICKET, "--seed", FULL_PROFILE, "--llm", Llm.Stub.value
        )
        url = manifest["url"]
        health = _health(url)
        assert health["llm"] == Llm.Stub.value, "the serving process did not install the stub"

        assert health["llm_keys"] is False, (
            f"a stubbed sandbox inherited a live credential from {len(BLANKED)} watched names"
        )

        user = _login(url, HOSTILE_OWNER)
        response = _request(
            user,
            "POST",
            url,
            "/personal/discussions/",
            body={"statement": "My brother stopped calling after the funeral."},
        )
        assert response.status_code == 200, response.text[:300]

        reply = response.json()["statement"]
        assert reply.startswith(STUB_PREFIX), f"not a stub reply: {reply[:200]}"
    finally:
        _stop(process)


def test_llm_real_without_a_key_fails_instead_of_faking_a_reply():
    """H4: a missing dependency is a failure, not a silent success."""
    process = None
    try:
        process, manifest = _start_backend(
            "--ticket",
            TICKET,
            "--seed",
            FULL_PROFILE,
            "--llm",
            Llm.Real.value,
            env=_env_without_credentials(),
        )
        url = manifest["url"]
        health = _health(url)
        assert health["llm"] == Llm.Real.value, "the serving process still has the stub installed"

        assert health["llm_keys"] is False, "a credential leaked in; this is not the no-key path"

        user = _login(url, HOSTILE_OWNER)
        response = _request(
            user,
            "POST",
            url,
            "/personal/discussions/",
            body={"statement": "My brother stopped calling after the funeral."},
        )
        assert response.status_code == 500, (
            f"llm=real with no credential answered {response.status_code}: {response.text[:200]}"
        )

        assert b"Internal Server Error" in response.content, response.content[:200]

        assert "statement" not in response.text, f"a reply was fabricated: {response.text[:200]}"
    finally:
        _stop(process)


# ---------------------------------------------------------------------------
# H4 — loud failure
# ---------------------------------------------------------------------------


def test_launch_against_a_dead_server_fails_loudly():
    """H4: a health check against nothing is a failure, never a silent success."""
    dead = f"http://127.0.0.1:{_free_port()}"
    instance = TestInstance.create(ticket=TICKET)
    started = time.time()
    try:
        try:
            ok, message = instance.launch(
                ephemeral_server=False, server_url=dead, headless=True, timeout=15
            )
        except (RuntimeError, ValueError) as error:
            ok, message = False, str(error)
        assert ok is False, f"launch reported success against a dead server: {message}"

        assert time.time() - started < APP_TIMEOUT, "failure took longer than the launch timeout"
    finally:
        instance.close(force=True)


# ---------------------------------------------------------------------------
# H4 — isolated per instance, cleans up after itself, kills nothing else
# ---------------------------------------------------------------------------


def test_two_instances_share_a_database_stay_isolated_and_reap_only_their_own():
    """H4: two apps on one backend and database, with separate prefs and app data,
    fully reaped on close, and nothing else on the machine touched."""
    bystander = subprocess.Popen(["sleep", "300"])
    try:
        pro = TestInstance.create(ticket=TICKET)
        ok, message = pro.launch(
            headless=True,
            personal=False,
            ephemeral_server=True,
            auto_auth_user=SHARED_USER,
            username=SHARED_USER,
            login_state=LoginState.LoggedIn,
            timeout=APP_TIMEOUT,
        )
        assert ok, f"Pro launch failed: {message}"

        url = pro.manifest["url"]
        personal = TestInstance.create(ticket=TICKET)
        ok, message = personal.launch(
            headless=True,
            personal=True,
            ephemeral_server=False,
            server_url=url,
            username=SHARED_USER,
            login_state=LoginState.LoggedIn,
            timeout=APP_TIMEOUT,
        )
        assert ok, f"Personal launch failed: {message}"

        assert pro._sandbox.sandbox_dir != personal._sandbox.sandbox_dir
        assert pro._sandbox.prefs_dir != personal._sandbox.prefs_dir
        assert pro._sandbox.app_data_dir != personal._sandbox.app_data_dir

        seeded = requests.post(
            f"{url}/test/seed",
            json={"users": [{"username": SHARED_USER}]},
            timeout=HTTP_TIMEOUT,
        ).json()
        diagram_id = seeded["users"][0]["free_diagram_id"]
        assert diagram_id, "seeded user has no free diagram"

        opened = pro.bridge.send_command(
            {"command": "open_server_diagram", "diagramId": diagram_id}
        )
        assert opened.get("success"), f"Pro could not open the shared diagram: {opened}"

        added = pro.bridge.send_command({"command": "add_person"})
        assert added.get("success"), f"add_person failed: {added}"

        saved = pro.bridge.send_command({"command": "save_diagram"})
        assert saved.get("success"), f"save_diagram failed: {saved}"

        opened = personal.bridge.send_command(
            {"command": "open_server_diagram", "diagramId": diagram_id}
        )
        assert opened.get("success"), f"Personal could not open Pro's diagram: {opened}"

        items = personal.bridge.send_command({"command": "get_scene_items", "type": "Person"})
        assert items.get("items"), f"Pro's saved person is invisible to Personal: {items}"

        owned = []
        for instance in (pro, personal):
            for child in (instance.process, instance.server_process):
                if child and child.poll() is None:
                    owned.append(child.pid)
                    owned.extend(_descendants(child.pid))
        assert owned, "no harness processes were running to reap"

        assert close_all_instances()["success"] is True

        deadline = time.time() + REAP_TIMEOUT
        while time.time() < deadline and any(_alive(pid) for pid in owned):
            time.sleep(0.5)
        leaked = [pid for pid in owned if _alive(pid)]
        assert not leaked, f"close_all_instances left {leaked} running"

        assert bystander.poll() is None, "close_all_instances killed an unrelated process"
    finally:
        if bystander.poll() is None:
            bystander.send_signal(signal.SIGKILL)
        bystander.wait(timeout=5)
        close_all_instances()


# ---------------------------------------------------------------------------
# H3 — duplicate-production path
# ---------------------------------------------------------------------------


def _postgres_ready() -> bool:
    return (
        subprocess.run(
            ["docker", "exec", "fd-postgres", "pg_isready"], capture_output=True
        ).returncode
        == 0
    )


def _databases_named(name: str) -> str:
    result = subprocess.run(
        ["docker", "exec", "fd-postgres", "psql", "-U", "familydiagram", "-d", "postgres",
         "-tAc", f"SELECT datname FROM pg_database WHERE datname = '{name}'"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"psql failed: {result.stderr[-300:]}"
    return result.stdout.strip()


def test_prod_data_lands_in_a_throwaway_database_that_is_dropped():
    """H3: duplicate-production restores into a throwaway sandbox database on this
    machine and never touches the dev or production one."""
    if not _postgres_ready():
        pytest.skip("Docker container fd-postgres is not running; --db prod cannot be exercised")
    if not (ROOT / "fdserver" / "prod.dump").is_file():
        pytest.skip("No fdserver/prod.dump on this machine; refresh it with bin/pull_prod_to_dev.sh")

    sandbox_db = f"fd_sandbox_{TICKET.lower().replace('-', '_')}"
    instance = TestInstance.create(ticket=TICKET)
    try:
        ok, message = instance.start_backend(db=Db.Prod.value)
        assert ok, message

        assert sandbox_db in instance.manifest["db"], (
            f"--db prod did not name {sandbox_db}: {instance.manifest['db']}"
        )

        assert _databases_named(sandbox_db) == sandbox_db

        assert _databases_named("familydiagram") == "familydiagram", (
            "the shared dev database must be left intact"
        )
    finally:
        instance.close(force=True)

    assert _databases_named(sandbox_db) == "", f"{sandbox_db} survived teardown"
