"""
FD-336 oracle H2, defect F-015: the app a sandbox launches runs the ticket's code.

The backend was already asked which btcopilot it loaded; the app never was. So a
launch could report worktree checkouts and put the origin clone's Pro on screen,
which is exactly what happened: bin/sandbox passed its own "pro"/"personal" label
into TestInstance.create's ticket slot, that ticket matched no worktree, and the
resolver fell back to the origin clones without a word.

Every assertion here comes from the launched process — the environment it was
actually given, or the running app's own sys.modules — never from the launcher's
report of what it intended.

    uv run pytest mcpserver/tests/test_app_checkout.py
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcpserver.checkouts import Repo, Source
from mcpserver.mcp_server import LoginState, TestInstance, get_app_modules
from mcpserver.sandbox import Llm

pytestmark = pytest.mark.sandbox

TICKET = "FD-336"
ROOT = Path("/Users/patrick/theapp")
WORKTREES = Path(".claude") / "worktrees"
STATE_DIR = Path.home() / ".claude" / "sandboxes"

APP_TIMEOUT = 60
SANDBOX_TIMEOUT = 900
SEED = "family+hostile"

# The app's own name for each repo it imports, against the repo the resolver names.
IMPORTED = {"pkdiagram": Repo.FamilyDiagram, "btcopilot": Repo.BTCopilot}


def _worktree(repo: Repo) -> Path:
    path = ROOT / repo.value / WORKTREES / TICKET
    if not path.is_dir():
        pytest.skip(f"no {TICKET} worktree of {repo.value}; nothing to tell apart")
    return path


def _sandbox_command() -> Path:
    """The bin/sandbox this ticket owns, by the same rule the resolver uses."""
    workspace = ROOT / WORKTREES / TICKET / "bin" / "sandbox"
    return workspace if workspace.is_file() else ROOT / "bin" / "sandbox"


def _descendants(pid: int) -> list:
    found = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True)
    children = [int(x) for x in found.stdout.split()]
    return children + [g for child in children for g in _descendants(child)]


def _command(pid: int, with_env: bool = False) -> str:
    argv = ["ps"] + (["-E"] if with_env else []) + ["-p", str(pid), "-o", "command="]
    return subprocess.run(argv, capture_output=True, text=True, timeout=10).stdout


def _app_pythonpath(pid: int) -> list:
    """The import path of whichever process in this tree is the app itself.

    The recorded pid is `uv run`, a wrapper; the interpreter that answers the
    imports is its child, so asking the wrapper proves nothing about the app.
    """
    for candidate in [pid] + _descendants(pid):
        argv = _command(candidate).split()
        if not argv or not Path(argv[0]).name.startswith("python"):
            continue
        if "pkdiagram" not in " ".join(argv):
            continue
        found = re.search(r"\bPYTHONPATH=(\S*)", _command(candidate, with_env=True))
        assert found, f"pid {candidate} runs the app with no PYTHONPATH at all"
        return [entry for entry in found.group(1).split(os.pathsep) if entry]
    raise AssertionError(f"no python running pkdiagram under pid {pid}")


def _assert_leads_with_the_worktrees(pythonpath: list, source: str) -> None:
    expected = [str(_worktree(Repo.FamilyDiagram)), str(_worktree(Repo.BTCopilot))]
    assert pythonpath[: len(expected)] == expected, (
        f"{source} would import from {pythonpath[:2]}, not the {TICKET} worktrees "
        f"{expected} — Pro shows master's code while the launcher reports the worktree"
    )


# ---------------------------------------------------------------------------
# The regression itself
# ---------------------------------------------------------------------------


def test_a_label_cannot_be_mistaken_for_a_ticket():
    """F-015 root cause: create("pro") read "pro" as the ticket, matched no
    worktree, and silently resolved the origin clones. Keyword-only makes the
    same call a TypeError at the call site instead of a wrong app on screen."""
    with pytest.raises(TypeError):
        TestInstance.create("pro")


def test_an_unknown_ticket_still_says_it_fell_back():
    """The fallback stays — a ticket with no worktree yet is legitimate — but it
    is reported, so a caller can never take origin for a worktree."""
    instance = TestInstance.create(ticket="FD-000")
    assert instance.checkouts.familydiagram.source is Source.Origin

    assert instance.checkouts.ticket == "FD-000"


# ---------------------------------------------------------------------------
# H2 — the running app, asked directly
# ---------------------------------------------------------------------------


def test_pro_imports_this_ticket_and_says_so_itself():
    """The launched app reports where each repo came from out of its own
    sys.modules — the only evidence that survives the launcher being wrong."""
    instance = TestInstance.create(ticket=TICKET)
    try:
        ok, message = instance.launch(
            headless=True,
            seed=SEED,
            llm=Llm.Stub.value,
            login_state=LoginState.LoggedIn,
            timeout=APP_TIMEOUT,
        )
        assert ok, message

        loaded = get_app_modules(instance.id)["checkouts"]
        assert {name: Path(loaded[name]) for name in IMPORTED} == {
            name: _worktree(repo) for name, repo in IMPORTED.items()
        }, f"the running app imported {loaded}"

        _assert_leads_with_the_worktrees(_app_pythonpath(instance.pid), "the app")
    finally:
        instance.close(force=True)


# ---------------------------------------------------------------------------
# H2 — the same, driven the way Patrick drives it
# ---------------------------------------------------------------------------


def test_bin_sandbox_launches_pro_from_this_ticket():
    """F-015 as measured: `bin/sandbox up --pro` reported worktree checkouts and
    launched the origin clone's Pro. Drive the real command and read the app's
    environment out of the process it recorded."""
    command = _sandbox_command()
    assert command.is_file(), f"no sandbox command at {command}"

    # A ticket may only be up once, and the one that is up may be someone else's
    # session. Yield to it rather than tearing down work this test does not own.
    if (STATE_DIR / f"{TICKET}.json").is_file():
        pytest.skip(f"a {TICKET} sandbox is already up; not taking it down")

    up = subprocess.run(
        [
            str(command), "up", TICKET,
            "--seed", SEED,
            "--llm", Llm.Stub.value,
            "--pro",
        ],
        capture_output=True,
        text=True,
        timeout=SANDBOX_TIMEOUT,
    )
    try:
        assert up.returncode == 0, f"{up.stdout}\n{up.stderr}"

        state = json.loads((STATE_DIR / f"{TICKET}.json").read_text())
        assert state["checkouts"][Repo.FamilyDiagram.value]["source"] == (
            Source.Worktree.value
        ), state["checkouts"]

        _assert_leads_with_the_worktrees(
            _app_pythonpath(state["apps"]["pro"]["pid"]), "bin/sandbox's Pro"
        )
    finally:
        subprocess.run(
            [str(command), "down", TICKET], capture_output=True, text=True, timeout=120
        )
