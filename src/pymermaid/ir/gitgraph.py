"""Intermediate representation for gitGraph diagrams."""

from dataclasses import dataclass
from enum import Enum

class CommitType(Enum):
    """Visual type for a commit node."""

    NORMAL = "NORMAL"
    REVERSE = "REVERSE"
    HIGHLIGHT = "HIGHLIGHT"

@dataclass(frozen=True)
class GitCommit:
    """A single commit in the git graph."""

    id: str  # auto-generated or user-specified
    branch: str  # branch this commit belongs to
    commit_type: CommitType  # visual type
    tag: str  # empty string if no tag
    parents: tuple[str, ...]  # parent commit IDs (2 for merges)
    is_merge: bool
    cherry_picked_from: str  # empty string if not a cherry-pick

@dataclass(frozen=True)
class GitBranch:
    """A branch in the git graph."""

    name: str
    start_commit: str  # commit ID where the branch was created

@dataclass(frozen=True)
class GitGraph:
    """Top-level gitGraph representation."""

    commits: tuple[GitCommit, ...]  # in chronological order
    branches: tuple[GitBranch, ...]  # in creation order
    branch_order: tuple[str, ...]  # branch names in lane order (top to bottom)

__all__ = ["CommitType", "GitBranch", "GitCommit", "GitGraph"]
