"""Compact tree layout for mindmap diagrams."""

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
    """Lay out a mindmap using a balanced bi-directional tree.

    The root is placed at the center vertically. The first half of its
    children extend to the right and the second half extend to the left,
    creating the classic mindmap shape with the root in the middle and
    branches going left and right.

    This produces a compact layout with low whitespace by using a
    horizontal tree arrangement rather than a radial one.
    """
    # Measure all nodes first
    sizes: dict[str, tuple[float, float]] = {}

    def _measure_all(node: MindmapNode) -> None:
        sizes[node.id] = _measure_node(node, measure_fn)
        for child in node.children:
            _measure_all(child)

    _measure_all(diagram.root)

    root = diagram.root
    rw, rh = sizes[root.id]

    if not root.children:
        # Single-node mindmap
        padding = 4.0
        nodes = {
            root.id: MindmapNodeLayout(
                x=rw / 2 + padding,
                y=rh / 2 + padding,
                width=rw,
                height=rh,
            )
        }
        return MindmapLayoutResult(
            nodes=nodes,
            width=rw + 2 * padding,
            height=rh + 2 * padding,
        )

    # Layout parameters
    h_gap = 2.0    # horizontal gap between parent and children column
    v_gap = 6.0    # vertical gap between sibling nodes

    positions: dict[str, MindmapNodeLayout] = {}

    def _subtree_height(node: MindmapNode) -> float:
        """Compute the vertical extent of a subtree in horizontal layout."""
        _nw, nh = sizes[node.id]
        if not node.children:
            return nh
        children_h = sum(
            _subtree_height(c) for c in node.children
        ) + v_gap * (len(node.children) - 1)
        return max(nh, children_h)

    def _layout_right(
        node: MindmapNode,
        left_x: float,
        center_y: float,
    ) -> None:
        """Lay out a subtree extending to the right."""
        nw, nh = sizes[node.id]
        positions[node.id] = MindmapNodeLayout(
            x=left_x + nw / 2, y=center_y, width=nw, height=nh,
        )
        if not node.children:
            return
        children_x = left_x + nw + h_gap
        total_ch = sum(
            _subtree_height(c) for c in node.children
        ) + v_gap * (len(node.children) - 1)
        cur_y = center_y - total_ch / 2
        for child in node.children:
            ch = _subtree_height(child)
            _layout_right(child, children_x, cur_y + ch / 2)
            cur_y += ch + v_gap

    def _layout_left(
        node: MindmapNode,
        right_x: float,
        center_y: float,
    ) -> None:
        """Lay out a subtree extending to the left."""
        nw, nh = sizes[node.id]
        positions[node.id] = MindmapNodeLayout(
            x=right_x - nw / 2, y=center_y, width=nw, height=nh,
        )
        if not node.children:
            return
        children_right_x = right_x - nw - h_gap
        total_ch = sum(
            _subtree_height(c) for c in node.children
        ) + v_gap * (len(node.children) - 1)
        cur_y = center_y - total_ch / 2
        for child in node.children:
            ch = _subtree_height(child)
            _layout_left(child, children_right_x, cur_y + ch / 2)
            cur_y += ch + v_gap

    # Split children: first half goes right, second half goes left.
    # Balance by subtree weight.
    children = list(root.children)
    weights = [_subtree_weight(c) for c in children]

    # Greedy split: assign children alternately to balance weight
    right_children: list[MindmapNode] = []
    left_children: list[MindmapNode] = []
    right_w = 0
    left_w = 0
    for child, w in sorted(zip(children, weights), key=lambda x: -x[1]):
        if right_w <= left_w:
            right_children.append(child)
            right_w += w
        else:
            left_children.append(child)
            left_w += w

    # Preserve original ordering within each side
    right_set = {c.id for c in right_children}
    right_children = [c for c in children if c.id in right_set]
    left_children = [c for c in children if c.id not in right_set]

    # Compute heights for each side
    right_total_h = sum(
        _subtree_height(c) for c in right_children
    ) + max(0, v_gap * (len(right_children) - 1)) if right_children else 0

    left_total_h = sum(
        _subtree_height(c) for c in left_children
    ) + max(0, v_gap * (len(left_children) - 1)) if left_children else 0

    # Place root at (0, 0)
    positions[root.id] = MindmapNodeLayout(x=0, y=0, width=rw, height=rh)

    # Layout right subtrees
    if right_children:
        right_x = rw / 2 + h_gap
        cur_y = -right_total_h / 2
        for child in right_children:
            ch = _subtree_height(child)
            _layout_right(child, right_x, cur_y + ch / 2)
            cur_y += ch + v_gap

    # Layout left subtrees
    if left_children:
        left_x = -rw / 2 - h_gap
        cur_y = -left_total_h / 2
        for child in left_children:
            ch = _subtree_height(child)
            _layout_left(child, left_x, cur_y + ch / 2)
            cur_y += ch + v_gap

    # Compute bounding box and shift so all coordinates are positive
    min_x = min(nl.x - nl.width / 2 for nl in positions.values())
    min_y = min(nl.y - nl.height / 2 for nl in positions.values())
    max_x = max(nl.x + nl.width / 2 for nl in positions.values())
    max_y = max(nl.y + nl.height / 2 for nl in positions.values())

    padding = 4.0
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

__all__ = ["MindmapLayoutResult", "MindmapNodeLayout", "layout_mindmap"]
