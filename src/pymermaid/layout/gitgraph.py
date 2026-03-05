"""Layout engine for gitGraph diagrams.

Positions commits on a horizontal timeline with branch lanes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from pymermaid.ir.gitgraph import GitGraph

# Type alias for text measurement function: (text, font_size) -> (width, height)
MeasureFn = Callable[[str, float], tuple[float, float]]

# Layout constants
_X_SPACING = 80.0  # horizontal spacing between commits
_Y_SPACING = 50.0  # vertical spacing between branch lanes
_LEFT_MARGIN = 120.0  # space for branch labels
_TOP_MARGIN = 40.0
_FONT_SIZE = 14.0


@dataclass
class CommitLayout:
    """Positioned commit node."""

    id: str
    x: float
    y: float


@dataclass
class BranchLineSegment:
    """A horizontal line segment on a branch lane."""

    branch: str
    x1: float
    y: float
    x2: float


@dataclass
class MergeLineSegment:
    """A line connecting two branch lanes at a merge point."""

    from_x: float
    from_y: float
    to_x: float
    to_y: float
    is_cherry_pick: bool = False


@dataclass
class GitGraphLayout:
    """Complete layout for a gitGraph diagram."""

    commits: list[CommitLayout] = field(default_factory=list)
    branch_lines: list[BranchLineSegment] = field(default_factory=list)
    merge_lines: list[MergeLineSegment] = field(default_factory=list)
    branch_label_positions: dict[str, tuple[float, float]] = field(
        default_factory=dict
    )
    branch_lane_y: dict[str, float] = field(default_factory=dict)
    width: float = 0.0
    height: float = 0.0


def layout_gitgraph(
    graph: GitGraph,
    measure_fn: MeasureFn | None = None,
) -> GitGraphLayout:
    """Compute positions for all elements in a gitGraph.

    Args:
        graph: The gitGraph IR.
        measure_fn: Optional text measurement function (unused currently
                     but kept for API consistency with other layout modules).

    Returns:
        A GitGraphLayout with positioned elements.
    """
    layout = GitGraphLayout()

    # Assign y-coordinate to each branch lane
    for i, branch_name in enumerate(graph.branch_order):
        y = _TOP_MARGIN + i * _Y_SPACING
        layout.branch_lane_y[branch_name] = y
        layout.branch_label_positions[branch_name] = (10.0, y)

    # Assign x-coordinate to each commit in chronological order
    commit_positions: dict[str, CommitLayout] = {}
    for idx, commit in enumerate(graph.commits):
        x = _LEFT_MARGIN + idx * _X_SPACING
        y = layout.branch_lane_y.get(commit.branch, _TOP_MARGIN)
        cl = CommitLayout(id=commit.id, x=x, y=y)
        layout.commits.append(cl)
        commit_positions[commit.id] = cl

    # Build branch line segments: connect consecutive commits on the same branch
    # Track commits per branch in order
    branch_commits: dict[str, list[CommitLayout]] = {}
    for commit in graph.commits:
        cl = commit_positions[commit.id]
        branch_commits.setdefault(commit.branch, []).append(cl)

    for branch_name, cls in branch_commits.items():
        if len(cls) < 2:
            continue
        for j in range(len(cls) - 1):
            layout.branch_lines.append(
                BranchLineSegment(
                    branch=branch_name,
                    x1=cls[j].x,
                    y=cls[j].y,
                    x2=cls[j + 1].x,
                )
            )

    # Build merge and cherry-pick lines
    for commit in graph.commits:
        if commit.is_merge and len(commit.parents) == 2:
            # Merge line from the second parent (the merged branch) to this commit
            parent2_id = commit.parents[1]
            if parent2_id in commit_positions:
                parent_cl = commit_positions[parent2_id]
                commit_cl = commit_positions[commit.id]
                layout.merge_lines.append(
                    MergeLineSegment(
                        from_x=parent_cl.x,
                        from_y=parent_cl.y,
                        to_x=commit_cl.x,
                        to_y=commit_cl.y,
                        is_cherry_pick=False,
                    )
                )

        if commit.cherry_picked_from:
            source_id = commit.cherry_picked_from
            if source_id in commit_positions:
                source_cl = commit_positions[source_id]
                commit_cl = commit_positions[commit.id]
                layout.merge_lines.append(
                    MergeLineSegment(
                        from_x=source_cl.x,
                        from_y=source_cl.y,
                        to_x=commit_cl.x,
                        to_y=commit_cl.y,
                        is_cherry_pick=True,
                    )
                )

    # Compute total dimensions
    if layout.commits:
        max_x = max(cl.x for cl in layout.commits) + _X_SPACING
    else:
        max_x = _LEFT_MARGIN + _X_SPACING

    if layout.branch_lane_y:
        max_y = max(layout.branch_lane_y.values()) + _Y_SPACING
    else:
        max_y = _TOP_MARGIN + _Y_SPACING

    layout.width = max_x
    layout.height = max_y

    return layout


__all__ = [
    "BranchLineSegment",
    "CommitLayout",
    "GitGraphLayout",
    "MergeLineSegment",
    "layout_gitgraph",
]
