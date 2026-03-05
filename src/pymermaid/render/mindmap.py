"""SVG renderer for mindmap diagrams."""

from xml.sax.saxutils import escape

from pymermaid.ir.mindmap import MindmapDiagram, MindmapNode, MindmapShape
from pymermaid.layout.mindmap import MindmapLayoutResult, MindmapNodeLayout
from pymermaid.theme import Theme

MINDMAP_COLORS = [
    "#4572A7",  # steel blue
    "#AA4643",  # brick red
    "#89A54E",  # olive green
    "#80699B",  # muted purple
    "#3D96AE",  # teal
    "#DB843D",  # warm orange
    "#92A8CD",  # light slate blue
    "#A47D7C",  # mauve
    "#B5CA92",  # sage green
    "#5C6BC0",  # indigo
]

def _lighten_color(hex_color: str, factor: float = 0.3) -> str:
    """Lighten a hex color by mixing with white."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"

def _get_subtree_color_index(root: MindmapNode) -> dict[str, int]:
    """Assign a color index to each node based on its top-level subtree."""
    color_map: dict[str, int] = {}
    color_map[root.id] = -1  # root gets special handling

    for i, child in enumerate(root.children):
        color_idx = i % len(MINDMAP_COLORS)
        _assign_color(child, color_idx, color_map)

    return color_map

def _assign_color(node: MindmapNode, color_idx: int, color_map: dict[str, int]) -> None:
    """Recursively assign a color index to a node and its descendants."""
    color_map[node.id] = color_idx
    for child in node.children:
        _assign_color(child, color_idx, color_map)

def _render_node_shape(
    node_id: str,
    label: str,
    shape: MindmapShape,
    layout: MindmapNodeLayout,
    fill: str,
    stroke: str,
) -> list[str]:
    """Render a single node shape and its text label."""
    parts: list[str] = []
    cx, cy = layout.x, layout.y
    w, h = layout.width, layout.height

    if shape == MindmapShape.CIRCLE:
        r = max(w, h) / 2
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2" '
            f'class="mindmap-node" data-node-id="{escape(node_id)}"/>'
        )
    elif shape == MindmapShape.ROUNDED_RECT:
        rx = 12
        parts.append(
            f'<rect x="{cx - w/2:.1f}" y="{cy - h/2:.1f}" '
            f'width="{w:.1f}" height="{h:.1f}" rx="{rx}" ry="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2" '
            f'class="mindmap-node" data-node-id="{escape(node_id)}"/>'
        )
    elif shape == MindmapShape.CLOUD:
        # Render cloud as an ellipse with wavy appearance
        rx = w / 2 + 8
        ry = h / 2 + 4
        parts.append(
            f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2" '
            f'stroke-dasharray="8,4" '
            f'class="mindmap-node" data-node-id="{escape(node_id)}"/>'
        )
    elif shape == MindmapShape.RECT:
        parts.append(
            f'<rect x="{cx - w/2:.1f}" y="{cy - h/2:.1f}" '
            f'width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2" '
            f'class="mindmap-node" data-node-id="{escape(node_id)}"/>'
        )
    else:
        # DEFAULT: simple rounded rectangle
        rx = 6
        parts.append(
            f'<rect x="{cx - w/2:.1f}" y="{cy - h/2:.1f}" '
            f'width="{w:.1f}" height="{h:.1f}" rx="{rx}" ry="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2" '
            f'class="mindmap-node" data-node-id="{escape(node_id)}"/>'
        )

    # Text label
    parts.append(
        f'<text x="{cx:.1f}" y="{cy + 5:.1f}" '
        f'class="mindmap-label" data-node-id="{escape(node_id)}">'
        f"{escape(label)}</text>"
    )

    return parts

def _render_branch(
    parent_layout: MindmapNodeLayout,
    child_layout: MindmapNodeLayout,
    color: str,
    child_id: str,
) -> str:
    """Render a curved branch connection between parent and child."""
    x1, y1 = parent_layout.x, parent_layout.y
    x2, y2 = child_layout.x, child_layout.y

    # Quadratic bezier with control point offset perpendicular to the line
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    # Add a slight curve by offsetting the midpoint
    dx = x2 - x1
    dy = y2 - y1
    # Perpendicular offset for curve
    offset = 0.15
    ctrl_x = mx - dy * offset
    ctrl_y = my + dx * offset

    return (
        f'<path d="M {x1:.1f} {y1:.1f} Q {ctrl_x:.1f} {ctrl_y:.1f} {x2:.1f} {y2:.1f}" '
        f'fill="none" stroke="{color}" stroke-width="2.5" '
        f'stroke-linecap="round" '
        f'class="mindmap-branch" data-node-id="{escape(child_id)}"/>'
    )

def render_mindmap_svg(
    diagram: MindmapDiagram,
    layout: MindmapLayoutResult,
    theme: Theme | None = None,
) -> str:
    """Render a MindmapDiagram to an SVG string."""
    parts: list[str] = []

    # SVG header
    w = max(layout.width, 200)
    h = max(layout.height, 200)
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {w:.0f} {h:.0f}" '
        f'width="{w:.0f}" height="{h:.0f}">'
    )

    # Style
    parts.append("<style>")
    parts.append(
        ".mindmap-node { cursor: pointer; }"
    )
    parts.append(
        ".mindmap-label { font-family: sans-serif;"
        " font-size: 14px; text-anchor: middle;"
        " dominant-baseline: middle; fill: #333; }"
    )
    parts.append(
        ".mindmap-branch { fill: none; }"
    )
    parts.append("</style>")

    # Get color assignments per node
    color_map = _get_subtree_color_index(diagram.root)

    # Render branches first (below nodes)
    def _render_branches(node: MindmapNode) -> None:
        parent_layout = layout.nodes.get(node.id)
        if parent_layout is None:
            return
        for child in node.children:
            child_layout = layout.nodes.get(child.id)
            if child_layout is None:
                continue
            cidx = color_map.get(child.id, 0)
            color = MINDMAP_COLORS[cidx % len(MINDMAP_COLORS)]
            parts.append(_render_branch(parent_layout, child_layout, color, child.id))
            _render_branches(child)

    _render_branches(diagram.root)

    # Render nodes
    def _render_nodes(node: MindmapNode) -> None:
        nl = layout.nodes.get(node.id)
        if nl is None:
            return
        cidx = color_map.get(node.id, 0)
        if cidx == -1:
            # Root node: distinct color
            fill = "#f0f0f0"
            stroke = "#333"
        else:
            base_color = MINDMAP_COLORS[cidx % len(MINDMAP_COLORS)]
            fill = _lighten_color(base_color, 0.5)
            stroke = base_color

        node_lines = _render_node_shape(
            node.id, node.label, node.shape, nl, fill, stroke,
        )
        parts.extend(node_lines)

        for child in node.children:
            _render_nodes(child)

    _render_nodes(diagram.root)

    parts.append("</svg>")
    return "\n".join(parts)

__all__ = ["render_mindmap_svg"]
