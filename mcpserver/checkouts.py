"""Which checkout of each repo a sandbox runs from.

A ticket's worktree wins when it exists; otherwise the origin clone is used and
the fallback is stated. Resolution order per repo:

    1. FD_WORKTREE_<REPO> env override (absolute path, must exist)
    2. <root>/<repo>/.claude/worktrees/<ticket>
    3. <root>/<repo>            (the origin clone)

The ticket comes from the argument, else FD_TICKET, else the worktree segment
of this module's own path.
"""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

WORKTREES = Path(".claude") / "worktrees"
PROMPTS = Path("prompts") / "private_prompts.py"
TICKET_ENV = "FD_TICKET"


class Repo(str, Enum):
    FamilyDiagram = "familydiagram"
    BTCopilot = "btcopilot"
    FDServer = "fdserver"


class Source(str, Enum):
    Worktree = "worktree"
    Origin = "origin"


@dataclass(frozen=True)
class Checkout:
    repo: Repo
    path: Path
    source: Source

    def __str__(self) -> str:
        return f"{self.repo.value:<14} {self.source.value:<9} {self.path}"


@dataclass(frozen=True)
class Checkouts:
    root: Path
    ticket: Optional[str]
    familydiagram: Checkout
    btcopilot: Checkout
    fdserver: Checkout

    @classmethod
    def resolve(
        cls, ticket: Optional[str] = None, root: Optional[Path] = None
    ) -> "Checkouts":
        here = Path(__file__).resolve()
        ticket = ticket or os.environ.get(TICKET_ENV) or ticket_from_path(here)
        root = Path(root).resolve() if root else workspace_root(here)
        return cls(
            root=root,
            ticket=ticket,
            **{r.name.lower(): _resolve_repo(r, ticket, root) for r in Repo},
        )

    def __getitem__(self, repo: Repo) -> Checkout:
        return getattr(self, repo.name.lower())

    @property
    def prompts_path(self) -> Optional[Path]:
        path = self.fdserver.path / PROMPTS
        return path if path.exists() else None

    def describe(self) -> str:
        header = f"{self.ticket or 'no ticket'} checkouts (root {self.root}):"
        return "\n".join([header] + [f"  {self[r]}" for r in Repo])

    def asdict(self) -> dict:
        return {
            "root": str(self.root),
            "ticket": self.ticket,
            **{
                r.value: {
                    "path": str(self[r].path),
                    "source": self[r].source.value,
                }
                for r in Repo
            },
        }


def _resolve_repo(repo: Repo, ticket: Optional[str], root: Path) -> Checkout:
    override = os.environ.get(f"FD_WORKTREE_{repo.value.upper()}")
    if override:
        path = Path(override).resolve()
        if not path.is_dir():
            raise RuntimeError(
                f"FD_WORKTREE_{repo.value.upper()}={override} is not a directory"
            )
        return Checkout(repo, path, Source.Worktree)

    origin = root / repo.value
    if not origin.is_dir():
        raise RuntimeError(f"No {repo.value} checkout at {origin}")

    if ticket:
        worktree = origin / WORKTREES / ticket
        if worktree.is_dir():
            return Checkout(repo, worktree, Source.Worktree)

    return Checkout(repo, origin, Source.Origin)


def ticket_from_path(path: Path) -> Optional[str]:
    parts = path.parts
    marker = WORKTREES.parts
    for i in range(len(parts) - len(marker)):
        if parts[i : i + len(marker)] == marker:
            return parts[i + len(marker)]
    return None


def workspace_root(start: Path) -> Path:
    """The uv workspace root — the directory holding the three repos."""
    current = start.resolve()
    while current != current.parent:
        pyproject = current / "pyproject.toml"
        if pyproject.is_file() and "[tool.uv.workspace]" in pyproject.read_text():
            return current
        current = current.parent
    raise RuntimeError(f"No uv workspace root above {start}")
