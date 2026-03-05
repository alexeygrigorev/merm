"""SVG rendering engine."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from pymermaid.ir import Diagram, Edge, Subgraph
from pymermaid.layout import EdgeLayout, LayoutResult, NodeLayout, Point

# Default padding around the viewBox so nodes are not clipped at edges.
_PADDING = 20

# Default theme colours.
_NODE_FILL = "#f9f9f9"
_NODE_STROKE = "#333"
_NODE_STROKE_WIDTH = "1"
_TEXT_FILL = "#333"
_FONT_FAMILY = "sans-serif"
_FONT_SIZE = "14px"
_EDGE_STROKE = "#333"
_SUBGRAPH_FILL = "#e8e8e8"
_SUBGRAPH_STROKE = "#999"
_SUBGRAPH_PADDING = 20.0

# SVG namespace.
_SVG_NS = "http://www.w3.org/2000/svg"

# Default CSS embedded in <style>.
_DEFAULT_STYLE = (
    f".node rect {{ fill: {_NODE_FILL}; "
    f"stroke: {_NODE_STROKE}; "
    f"stroke-width: {_NODE_STROKE_WIDTH}; }}\n"
    f".node text {{ fill: {_TEXT_FILL}; "
    f"font-family: {_FONT_FAMILY}; "
    f"font-size: {_FONT_SIZE}; }}\n"
    f".edge path {{ fill: none; "
    f"stroke: {_EDGE_STROKE}; stroke-width: 1; }}\n"
    f".edge text {{ fill: {_TEXT_FILL}; "
    f"font-family: {_FONT_FAMILY}; font-size: 12px; }}\n"
    f".subgraph rect {{ fill: {_SUBGRAPH_FILL}; "
    f"stroke: {_SUBGRAPH_STROKE}; "
    f"stroke-width: 1; opacity: 0.5; }}\n"
    f".subgraph text {{ fill: {_TEXT_FILL}; "
    f"font-family: {_FONT_FAMILY}; "
    f"font-size: 12px; font-weight: bold; }}\n"
)


def _build_edge_lookup(diagram: Diagram) -> dict[tuple[str, str], Edge]:
    """Map (source, target) to the first matching IR Edge for label lookup."""
    lookup: dict[tuple[str, str], Edge] = {}
    for e in diagram.edges:
        key = (e.source, e.target)
        if key not in lookup:
            lookup[key] = e
    return lookup


def _make_defs(svg: ET.Element) -> None:
    """Add a <defs> section with a default arrowhead marker."""
    defs = ET.SubElement(svg, "defs")
    marker = ET.SubElement(defs, "marker")
    marker.set("id", "arrowhead")
    marker.set("markerWidth", "10")
    marker.set("markerHeight", "7")
    marker.set("refX", "10")
    marker.set("refY", "3.5")
    marker.set("orient", "auto")
    marker.set("markerUnits", "strokeWidth")
    arrow_path = ET.SubElement(marker, "path")
    arrow_path.set("d", "M0,0 L10,3.5 L0,7 Z")
    arrow_path.set("fill", _EDGE_STROKE)


def _make_style(svg: ET.Element) -> None:
    """Add a <style> element with default theme CSS."""
    style = ET.SubElement(svg, "style")
    style.text = _DEFAULT_STYLE


def _render_text(
    parent: ET.Element,
    label: str,
    cx: float,
    cy: float,
) -> None:
    """Render a <text> element, handling multi-line labels with <tspan>."""
    parts = label.split("<br/>")
    text_el = ET.SubElement(parent, "text")
    text_el.set("text-anchor", "middle")
    text_el.set("dominant-baseline", "central")

    if len(parts) == 1:
        text_el.set("x", str(cx))
        text_el.set("y", str(cy))
        text_el.text = parts[0]
    else:
        # Multi-line: position first tspan, subsequent ones offset by 1.2em
        line_height = 1.2  # em
        total_height = line_height * (len(parts) - 1)
        start_offset = -total_height / 2.0

        for i, part in enumerate(parts):
            tspan = ET.SubElement(text_el, "tspan")
            tspan.set("x", str(cx))
            if i == 0:
                tspan.set("dy", f"{start_offset}em")
            else:
                tspan.set("dy", f"{line_height}em")
            tspan.text = part


def _render_node(
    parent: ET.Element,
    node_id: str,
    label: str,
    nl: NodeLayout,
) -> None:
    """Render a single node as a <g> group with <rect> and <text>."""
    g = ET.SubElement(parent, "g")
    g.set("class", "node")
    g.set("data-node-id", node_id)

    rect = ET.SubElement(g, "rect")
    rect.set("x", str(nl.x))
    rect.set("y", str(nl.y))
    rect.set("width", str(nl.width))
    rect.set("height", str(nl.height))

    cx = nl.x + nl.width / 2.0
    cy = nl.y + nl.height / 2.0
    _render_text(g, label, cx, cy)


def _points_to_path_d(points: list[Point]) -> str:
    """Convert a list of Points to an SVG path d attribute (M ... L ...)."""
    if not points:
        return ""
    parts = [f"M{points[0].x},{points[0].y}"]
    for p in points[1:]:
        parts.append(f"L{p.x},{p.y}")
    return " ".join(parts)


def _edge_midpoint(points: list[Point]) -> tuple[float, float]:
    """Return the midpoint of a polyline."""
    if len(points) == 0:
        return (0.0, 0.0)
    if len(points) == 1:
        return (points[0].x, points[0].y)
    # Use the midpoint of the middle segment
    mid_idx = len(points) // 2
    p1 = points[mid_idx - 1]
    p2 = points[mid_idx]
    return ((p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0)


def _render_edge(
    parent: ET.Element,
    el: EdgeLayout,
    ir_edge: Edge | None,
) -> None:
    """Render an edge as a <path>, optionally with a label <text>."""
    g = ET.SubElement(parent, "g")
    g.set("class", "edge")
    g.set("data-edge-source", el.source)
    g.set("data-edge-target", el.target)

    path = ET.SubElement(g, "path")
    path.set("d", _points_to_path_d(el.points))
    path.set("marker-end", "url(#arrowhead)")

    # Edge label
    label = ir_edge.label if ir_edge else None
    if label:
        mx, my = _edge_midpoint(el.points)
        label_text = ET.SubElement(g, "text")
        label_text.set("x", str(mx))
        label_text.set("y", str(my))
        label_text.set("text-anchor", "middle")
        label_text.set("dominant-baseline", "central")
        label_text.text = label


def _compute_subgraph_bbox(
    subgraph: Subgraph,
    node_layouts: dict[str, NodeLayout],
) -> tuple[float, float, float, float] | None:
    """Compute bounding box (x, y, width, height) for a subgraph's member nodes."""
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    found = False
    for nid in subgraph.node_ids:
        nl = node_layouts.get(nid)
        if nl is None:
            continue
        found = True
        min_x = min(min_x, nl.x)
        min_y = min(min_y, nl.y)
        max_x = max(max_x, nl.x + nl.width)
        max_y = max(max_y, nl.y + nl.height)

    if not found:
        return None

    # Add padding
    pad = _SUBGRAPH_PADDING
    return (
        min_x - pad,
        min_y - pad - 16,  # extra top padding for title
        (max_x - min_x) + 2 * pad,
        (max_y - min_y) + 2 * pad + 16,
    )


def _render_subgraph(
    parent: ET.Element,
    subgraph: Subgraph,
    node_layouts: dict[str, NodeLayout],
) -> None:
    """Render a subgraph bounding box and title."""
    bbox = _compute_subgraph_bbox(subgraph, node_layouts)
    if bbox is None:
        return

    sx, sy, sw, sh = bbox
    g = ET.SubElement(parent, "g")
    g.set("class", "subgraph")
    g.set("data-subgraph-id", subgraph.id)

    rect = ET.SubElement(g, "rect")
    rect.set("x", str(sx))
    rect.set("y", str(sy))
    rect.set("width", str(sw))
    rect.set("height", str(sh))
    rect.set("rx", "5")

    title = subgraph.title or subgraph.id
    text_el = ET.SubElement(g, "text")
    text_el.set("x", str(sx + 8))
    text_el.set("y", str(sy + 14))
    text_el.text = title


def render_svg(diagram: Diagram, layout: LayoutResult) -> str:
    """Render a Diagram and its LayoutResult to a standalone SVG string.

    Args:
        diagram: The IR diagram.
        layout: The positioned layout result.

    Returns:
        A string containing valid SVG XML.
    """
    # Compute viewBox with padding
    vb_x = -_PADDING
    vb_y = -_PADDING
    vb_w = layout.width + 2 * _PADDING
    vb_h = layout.height + 2 * _PADDING

    # Ensure minimum dimensions
    vb_w = max(vb_w, 1.0)
    vb_h = max(vb_h, 1.0)

    svg = ET.Element("svg")
    svg.set("xmlns", _SVG_NS)
    svg.set("viewBox", f"{vb_x} {vb_y} {vb_w} {vb_h}")
    svg.set("width", str(vb_w))
    svg.set("height", str(vb_h))

    # Defs and style
    _make_defs(svg)
    _make_style(svg)

    # Build label lookup from IR nodes
    node_labels: dict[str, str] = {n.id: n.label for n in diagram.nodes}

    # Build edge lookup for labels
    edge_lookup = _build_edge_lookup(diagram)

    # Render subgraphs first (background)
    for sg in diagram.subgraphs:
        _render_subgraph(svg, sg, layout.nodes)

    # Render edges
    for el in layout.edges:
        ir_edge = edge_lookup.get((el.source, el.target))
        _render_edge(svg, el, ir_edge)

    # Render nodes (on top of edges)
    for node_id, nl in layout.nodes.items():
        label = node_labels.get(node_id, node_id)
        _render_node(svg, node_id, label, nl)

    # Pretty-print
    ET.indent(svg)

    # Serialize to string
    return ET.tostring(svg, encoding="unicode", xml_declaration=False)


__all__ = ["render_svg"]
