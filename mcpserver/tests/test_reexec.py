"""
FD-336 oracle H2: a registration file can name only one path, so the MCP entry
point moves itself to the checkout the ticket resolves to before it serves.

These drive the real server over the real stdio protocol — what an MCP client
would get, not what an import would say.

    uv run pytest mcpserver/tests/test_reexec.py
"""

import functools
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcpserver.checkouts import Repo, Source

pytestmark = pytest.mark.sandbox

TICKET = "FD-336"
UNKNOWN_TICKET = "FD-000"

ROOT = Path("/Users/patrick/theapp")
FD_ORIGIN = ROOT / "familydiagram"
FD_WORKTREE = FD_ORIGIN / ".claude" / "worktrees" / TICKET
BTCOPILOT_WORKTREE = ROOT / "btcopilot" / ".claude" / "worktrees" / TICKET

WORKTREE_ENTRY = FD_WORKTREE / "mcpserver" / "mcp_server.py"
ORIGIN_ENTRY = FD_ORIGIN / "mcpserver" / "mcp_server.py"

TICKET_ENV = "FD_TICKET"
REEXEC_ENV = "FD_MCPSERVER_REEXEC"
CHECKOUTS_TOOL = "get_checkouts"
HANDSHAKE_TIMEOUT = 120
PROTOCOL_VERSION = "2024-11-05"


def _client_env(ticket, moved: bool) -> dict:
    """What an MCP client starts the server with: the ticket, and nothing that
    could put a checkout on the path behind the entry point's back."""
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env["PYTHONUNBUFFERED"] = "1"
    kept = [
        entry
        for entry in env.get("PYTHONPATH", "").split(os.pathsep)
        if entry and Path(entry) not in (FD_WORKTREE, BTCOPILOT_WORKTREE)
    ]
    if kept:
        env["PYTHONPATH"] = os.pathsep.join(kept)
    else:
        env.pop("PYTHONPATH", None)
    if ticket:
        env[TICKET_ENV] = ticket
    else:
        env.pop(TICKET_ENV, None)
    if moved:
        env[REEXEC_ENV] = "1"
    else:
        env.pop(REEXEC_ENV, None)
    return env


@functools.lru_cache(maxsize=None)
def _serve(entry: Path, ticket, moved: bool = False):
    """Speak stdio JSON-RPC to the entry point. Returns (tool names, checkouts).

    stderr goes to a file rather than a pipe: the server logs there while the
    handshake is in flight, and an undrained pipe would block it. A watchdog
    kills a server that never answers, so a hang fails instead of hanging.
    """
    with tempfile.TemporaryFile(mode="w+") as errors:
        process = subprocess.Popen(
            [sys.executable, "-u", str(entry)],
            env=_client_env(ticket, moved),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errors,
            text=True,
            bufsize=1,
        )
        watchdog = threading.Timer(HANDSHAKE_TIMEOUT, process.kill)
        watchdog.start()

        def send(payload):
            process.stdin.write(json.dumps(payload) + "\n")
            process.stdin.flush()

        def reply(request_id):
            while True:
                line = process.stdout.readline()
                if not line:
                    errors.seek(0)
                    raise AssertionError(
                        f"{entry} stopped answering (killed after "
                        f"{HANDSHAKE_TIMEOUT}s, or exited):\n"
                        + "\n".join(errors.read().splitlines()[-25:])
                    )
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if message.get("id") == request_id:
                    return message

        try:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {"name": "fd336-tests", "version": "0"},
                    },
                }
            )
            assert "result" in reply(1), "server refused the MCP handshake"

            send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            tools = tuple(sorted(t["name"] for t in reply(2)["result"]["tools"]))

            checkouts = None
            if CHECKOUTS_TOOL in tools:
                send(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {"name": CHECKOUTS_TOOL, "arguments": {}},
                    }
                )
                checkouts = json.loads(reply(3)["result"]["content"][0]["text"])
            return tools, checkouts
        finally:
            watchdog.cancel()
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def test_entry_point_serves_the_ticket_harness():
    """H2: with the ticket named, an MCP client gets the ticket's own tools and the
    server says which checkout each repo came from."""
    tools, checkouts = _serve(WORKTREE_ENTRY, TICKET)
    assert (
        CHECKOUTS_TOOL in tools
    ), f"the ticket's harness was not served: {len(tools)} tools"

    assert checkouts["ticket"] == TICKET

    familydiagram = checkouts[Repo.FamilyDiagram.value]
    assert (familydiagram["source"], Path(familydiagram["path"])) == (
        Source.Worktree.value,
        FD_WORKTREE,
    )

    assert Path(checkouts[Repo.BTCopilot.value]["path"]) == BTCOPILOT_WORKTREE


def test_a_worktree_entry_point_knows_its_own_ticket():
    """H2: no ticket in the environment, so the entry point takes it from its own
    path — a worktree's harness never has to be told which ticket it is."""
    tools, checkouts = _serve(WORKTREE_ENTRY, None)
    assert CHECKOUTS_TOOL in tools

    assert checkouts["ticket"] == TICKET

    assert Path(checkouts[Repo.FamilyDiagram.value]["path"]) == FD_WORKTREE


def test_entry_point_moves_itself_to_the_resolved_checkout():
    """H2: the move itself. A ticket with no worktree resolves familydiagram to the
    origin clone, so the entry point re-executes there and an MCP client gets origin
    master's tools instead of this worktree's — proving the hop really happens
    rather than the server merely reporting a different path."""
    worktree_tools, _ = _serve(WORKTREE_ENTRY, TICKET)
    origin_tools, checkouts = _serve(WORKTREE_ENTRY, UNKNOWN_TICKET)
    assert checkouts is None, (
        "still serving this worktree's harness; the entry point did not move to the "
        f"origin clone for {UNKNOWN_TICKET}"
    )

    assert CHECKOUTS_TOOL in worktree_tools and CHECKOUTS_TOOL not in origin_tools

    assert origin_tools and set(origin_tools) < set(
        worktree_tools
    ), "origin master's tool set should be a strict subset of this ticket's"


def test_a_server_that_has_already_moved_stays_put():
    """H2: the flag the entry point sets on itself before re-executing is what ends
    the hop. Without it a checkout that resolves elsewhere would exec forever and an
    MCP client would wait on a server that never starts. With the flag set the same
    ticket that moved the server above leaves it here — still this worktree's tools,
    now reporting the origin clone, which is what a ticket with no worktree gets."""
    tools, checkouts = _serve(WORKTREE_ENTRY, UNKNOWN_TICKET, moved=True)
    assert CHECKOUTS_TOOL in tools, "the flag did not stop the hop"

    assert checkouts["ticket"] == UNKNOWN_TICKET

    familydiagram = checkouts[Repo.FamilyDiagram.value]
    assert (familydiagram["source"], Path(familydiagram["path"])) == (
        Source.Origin.value,
        FD_ORIGIN,
    )


@pytest.mark.xfail(
    reason="origin master has no re-exec, so the registered entry point serves "
    "origin master's harness whatever the ticket. FD-336 must merge before any "
    "MCP client can reach a ticket's harness. Passing here means it merged — "
    "delete this marker.",
    strict=True,
)
def test_the_registered_origin_entry_point_serves_the_ticket_harness():
    """H2, as .mcp.json actually starts it: the registration names the origin clone,
    so that path must move itself into the ticket's worktree. It cannot yet — the
    code that moves it only exists on this branch."""
    tools, _ = _serve(ORIGIN_ENTRY, TICKET)
    assert CHECKOUTS_TOOL in tools, (
        f"the registered entry point served {len(tools)} tools without {CHECKOUTS_TOOL}: "
        "an MCP client gets origin master's harness, whatever the ticket"
    )
