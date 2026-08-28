"""
FD-336 oracle H1: one harness, one sandbox doc, one registration.

The failure this guards against is drift, not a crash — a second sandbox script,
a second set of launch instructions, a hardcoded port coming back — so it reads
files and starts nothing.

    uv run pytest mcpserver/tests/test_one_harness.py
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TICKET = REPO.name
ROOT = REPO.parents[3]
WORKSPACE = ROOT / ".claude" / "worktrees" / TICKET

SANDBOX_DOC = Path("doc") / "SANDBOX.md"
SANDBOX_COMMAND = "bin/sandbox"
SERVER = "familydiagram-testing"
ORIGIN_ENTRY = ROOT / "familydiagram" / "mcpserver" / "mcp_server.py"

# A launcher, stack file, or seed script named after a ticket is a unit that
# built its own harness instead of fixing the shared one.
PRIVATE_HARNESS = (
    "doc/workstreams/**/fd*_sandbox*",
    "**/*_stack.py",
    "**/fd*_seed.py",
    "**/fd*_app.py",
    "bin/mcp_launch.py",
)

# The sandbox picks a free port and prints it. Any of these in the instructions
# means someone is being told to run a server by hand on a fixed port again.
BY_HAND = ("8889", "flask run")


def _workspace_readme() -> str:
    assert WORKSPACE.is_dir(), f"no {TICKET} worktree of the workspace at {WORKSPACE}"
    return (WORKSPACE / "CLAUDE.md").read_text()


def test_the_sandbox_has_one_doc_and_the_repo_index_points_at_it():
    assert (REPO / SANDBOX_DOC).is_file(), f"{SANDBOX_DOC} is the one sandbox doc"

    index = (REPO / "CLAUDE.md").read_text()
    assert f"({SANDBOX_DOC.as_posix()})" in index, (
        f"{SANDBOX_DOC} is not linked from this repo's doc index, so nobody finds it"
    )


def test_the_workspace_sends_everyone_to_the_one_command_and_the_one_doc():
    readme = _workspace_readme()
    assert SANDBOX_COMMAND in readme, (
        f"the workspace instructions never name {SANDBOX_COMMAND}, "
        "so the sandbox has no single entry point"
    )

    assert f"familydiagram/{SANDBOX_DOC.as_posix()}" in readme, (
        "the workspace instructions do not point at the one sandbox doc"
    )


def test_the_workspace_no_longer_tells_anyone_to_start_a_server_by_hand():
    readme = _workspace_readme()
    found = [text for text in BY_HAND if text in readme]
    assert not found, (
        f"the workspace instructions still carry a by-hand launch recipe ({found}); "
        "the sandbox chooses its own port and prints it"
    )


def test_no_unit_wrote_its_own_sandbox():
    private = sorted(
        str(match.relative_to(REPO))
        for pattern in PRIVATE_HARNESS
        for match in REPO.glob(pattern)
    )
    assert not private, (
        f"ticket-private harness code in {REPO.name}: {private}. "
        f"Fix {SANDBOX_COMMAND} or the mcpserver modules it drives instead."
    )


def test_one_registration_serves_both_workspaces():
    registrations = {
        path: json.loads((path / ".mcp.json").read_text())["mcpServers"]
        for path in (REPO, WORKSPACE)
    }
    missing = [str(path) for path, servers in registrations.items() if SERVER not in servers]
    assert not missing, f"{SERVER} is not registered in {missing}"

    entries = [servers[SERVER] for servers in registrations.values()]
    assert len({(e["command"], tuple(e["args"])) for e in entries}) == 1, (
        f"the two workspaces start {SERVER} differently, so which harness a session "
        f"gets depends on where it was opened: {[e['args'] for e in entries]}"
    )

    # Naming the origin clone is why the entry point has to move itself (H2).
    assert str(ORIGIN_ENTRY) in entries[0]["args"], (
        f"{SERVER} does not start {ORIGIN_ENTRY}; a registration that names a "
        "worktree only works for one ticket"
    )

    assert all("FD_TICKET" in e.get("env", {}) for e in entries), (
        "the registration does not pass FD_TICKET, so the server has no ticket to "
        "resolve a checkout from"
    )
