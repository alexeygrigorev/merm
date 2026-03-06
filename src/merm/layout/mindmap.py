"""Radial tree layout for mindmap diagrams."""

import math
from dataclasses import dataclass

from merm.ir.mindmap import MindmapDiagram, MindmapNode
from merm.layout.config import MeasureFn

@dataclass(frozen=True)
class MindmapNodeLayout:
    """Position and size of a single mindmap node."""

    x: float  # center x
    y: float  # center y
    width: float
    height: float

@dataclass(frozen=True)
class MindmapLayoutResult:
    """Complete layout output for a mindmap."""

    nodes: dict[str, MindmapNodeLayout]
    width: float
    height: float

def _subtree_weight(node: MindmapNode) -> int:
    """Count total nodes in a subtree (including the node itself)."""
    if not node.children:
        return 1
    return 1 + sum(_subtree_weight(c) for c in node.children)

def _measure_node(node: MindmapNode, measure_fn: MeasureFn) -> tuple[float, float]:
    """Measure a node's dimensions based on its label and shape."""
    text_w, text_h = measure_fn(node.label, 14.0)
    padding_h = 20.0
    padding_v = 12.0
    w = text_w + padding_h * 2
    h = text_h + padding_v * 2
    # Minimum sizes
    w = max(w, 60.0)
    h = max(h, 36.0)
    return w, h

def layout_mindmap(
    diagram: MindmapDiagram,
    measure_fn: MeasureFn,
) -> MindmapLayoutResult:
    """Lay out a mindmap using a radial tree algorithm.

    The root is placed at the center. First-level children are distributed
    evenly around it. Deeper children extend outward along their parent's
    angular sector.
    """
    positions: dict[str, MindmapNodeLayout] = {}

    # Measure all nodes first
    sizes: dict[str, tuple[float, float]] = {}

    def _measure_all(node: MindmapNode) -> None:
        sizes[node.id] = _measure_node(node, measure_fn)
        for child in node.children:
            _measure_all(child)

    _measure_all(diagram.root)

    # Place root at origin (we'll shift everything later)
    root = diagram.root
    rw, rh = sizes[root.id]
    positions[root.id] = MindmapNodeLayout(x=0, y=0, width=rw, height=rh)

    # Radial layout parameters
    base_radius = 160.0  # distance from root to first-level children
    level_spacing = 140.0  # additional distance per level

    def _layout_children(
        parent: MindmapNode,
        parent_x: float,
        parent_y: float,
        angle_start: float,
        angle_span: float,
        level: int,
    ) -> None:
        """Recursively place children in an angular sector."""
        if not parent.children:
            return

        radius = base_radius + (level - 1) * level_spacing
        total_weight = sum(_subtree_weight(c) for c in parent.children)

        current_angle = angle_start
        for child in parent.children:
            weight = _subtree_weight(child)
            child_span = angle_span * (weight / total_weight)
            child_angle = current_angle + child_span / 2

            cx = parent_x + radius * math.cos(child_angle)
            cy = parent_y + radius * math.sin(child_angle)

            cw, ch = sizes[child.id]
            positions[child.id] = MindmapNodeLayout(x=cx, y=cy, width=cw, height=ch)

            # Recurse for grandchildren
            _layout_children(
                child,
                cx,
                cy,
                current_angle,
                child_span,
                level + 1,
            )

            current_angle += child_span

    # Distribute first-level children around full circle
    _layout_children(
        root,
        0,
        0,
        angle_start=-math.pi,
        angle_span=2 * math.pi,
        level=1,
    )

    # Compute bounding box and shift so all coordinates are positive
    if positions:
        min_x = min(nl.x - nl.width / 2 for nl in positions.values())
        min_y = min(nl.y - nl.height / 2 for nl in positions.values())
        max_x = max(nl.x + nl.width / 2 for nl in positions.values())
        max_y = max(nl.y + nl.height / 2 for nl in positions.values())

        padding = 40.0
        offset_x = -min_x + padding
        offset_y = -min_y + padding

        shifted: dict[str, MindmapNodeLayout] = {}
        for nid, nl in positions.items():
            shifted[nid] = MindmapNodeLayout(
                x=nl.x + offset_x,
                y=nl.y + offset_y,
                width=nl.width,
                height=nl.height,
            )

        total_width = (max_x - min_x) + 2 * padding
        total_height = (max_y - min_y) + 2 * padding

        return MindmapLayoutResult(
            nodes=shifted,
            width=total_width,
            height=total_height,
        )

    # Fallback for empty
    return MindmapLayoutResult(nodes=positions, width=200, height=200)

__all__ = ["MindmapLayoutResult", "MindmapNodeLayout", "layout_mindmap"]
