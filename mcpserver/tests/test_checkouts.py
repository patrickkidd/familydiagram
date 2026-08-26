"""Which checkout each repo runs from, and that the fallback is stated."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcpserver.checkouts import (
    Checkouts,
    Repo,
    Source,
    WORKTREES,
    ticket_from_path,
    workspace_root,
)

TICKET = "FD-999"


@pytest.fixture
def root(tmp_path, monkeypatch):
    for name in ("FD_TICKET", *(f"FD_WORKTREE_{r.value.upper()}" for r in Repo)):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / "pyproject.toml").write_text("[tool.uv.workspace]\nmembers = []\n")
    for repo in Repo:
        (tmp_path / repo.value).mkdir()
    return tmp_path


def worktree(root: Path, repo: Repo, ticket: str = TICKET) -> Path:
    path = root / repo.value / WORKTREES / ticket
    path.mkdir(parents=True)
    return path


def test_no_ticket_is_all_origin(root):
    checkouts = Checkouts.resolve(ticket=None, root=root)
    assert [checkouts[r].source for r in Repo] == [Source.Origin] * len(Repo)
    assert checkouts.familydiagram.path == root / Repo.FamilyDiagram.value


def test_worktree_wins_and_missing_ones_fall_back(root):
    expected = worktree(root, Repo.BTCopilot)
    checkouts = Checkouts.resolve(ticket=TICKET, root=root)
    assert checkouts.btcopilot.path == expected
    assert checkouts.btcopilot.source is Source.Worktree
    assert checkouts.fdserver.source is Source.Origin
    assert checkouts.fdserver.path == root / Repo.FDServer.value


def test_ticket_comes_from_the_environment(root, monkeypatch):
    expected = worktree(root, Repo.FamilyDiagram)
    monkeypatch.setenv("FD_TICKET", TICKET)
    checkouts = Checkouts.resolve(root=root)
    assert checkouts.ticket == TICKET
    assert checkouts.familydiagram.path == expected


def test_env_override_beats_the_ticket(root, monkeypatch, tmp_path):
    worktree(root, Repo.BTCopilot)
    override = tmp_path / "elsewhere"
    override.mkdir()
    monkeypatch.setenv("FD_WORKTREE_BTCOPILOT", str(override))
    checkouts = Checkouts.resolve(ticket=TICKET, root=root)
    assert checkouts.btcopilot.path == override
    assert checkouts.btcopilot.source is Source.Worktree


def test_env_override_pointing_nowhere_fails(root, monkeypatch, tmp_path):
    monkeypatch.setenv("FD_WORKTREE_BTCOPILOT", str(tmp_path / "gone"))
    with pytest.raises(RuntimeError, match="not a directory"):
        Checkouts.resolve(ticket=TICKET, root=root)


def test_missing_repo_fails(root):
    (root / Repo.FDServer.value).rmdir()
    with pytest.raises(RuntimeError, match="No fdserver checkout"):
        Checkouts.resolve(root=root)


def test_describe_names_every_repo_and_its_source(root):
    worktree(root, Repo.FamilyDiagram)
    lines = Checkouts.resolve(ticket=TICKET, root=root).describe().splitlines()
    sources = {line.split()[0]: line.split()[1] for line in lines[1:]}
    assert TICKET in lines[0]
    assert sources == {
        Repo.FamilyDiagram.value: Source.Worktree.value,
        Repo.BTCopilot.value: Source.Origin.value,
        Repo.FDServer.value: Source.Origin.value,
    }


def test_prompts_path_only_when_present(root):
    checkouts = Checkouts.resolve(root=root)
    assert checkouts.prompts_path is None
    prompts = root / Repo.FDServer.value / "prompts"
    prompts.mkdir()
    (prompts / "private_prompts.py").write_text("")
    assert Checkouts.resolve(root=root).prompts_path == prompts / "private_prompts.py"


def test_ticket_read_from_a_worktree_path():
    assert (
        ticket_from_path(Path("/a/b/.claude/worktrees/FD-336/mcpserver/x.py"))
        == "FD-336"
    )
    assert ticket_from_path(Path("/a/b/mcpserver/x.py")) is None


def test_workspace_root_is_the_uv_workspace(root):
    assert workspace_root(root / Repo.BTCopilot.value) == root
    with pytest.raises(RuntimeError, match="No uv workspace root"):
        workspace_root(Path("/"))


def test_this_checkout_resolves_itself():
    checkouts = Checkouts.resolve()
    assert checkouts.familydiagram.path == Path(__file__).parent.parent.parent
    assert checkouts.ticket == Path(__file__).parent.parent.parent.name
