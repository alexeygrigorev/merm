"""Edge rendering: markers, line styles, path generation, and labels."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from pymermaid.ir import ArrowType, Edge, EdgeType
from pymermaid.layout import EdgeLayout, Point

# Default edge stroke colour (used as fallback).
_DEFAULT_EDGE_STROKE = "#333333"


# ---------------------------------------------------------------------------
# Marker definitions
# ---------------------------------------------------------------------------

def make_edge_defs(
    parent: ET.Element,
    edge_stroke: str = _DEFAULT_EDGE_STROKE,
) -> None:
    """Add all arrow/endpoint marker definitions to a <defs> element.

    Creates four ``<marker>`` elements: arrow, circle-end, cross-end,
    and arrow-reverse.
    """
    # 1. Triangle arrow (forward)
    _marker_arrow(parent, marker_id="arrow", orient="auto", fill=edge_stroke)

    # 2. Circle endpoint
    _marker_circle(parent, fill=edge_stroke)

    # 3. Cross endpoint
    _marker_cross(parent, stroke=edge_stroke)

    # 4. Reverse triangle arrow
    _marker_arrow(
        parent, marker_id="arrow-reverse",
        orient="auto-start-reverse", fill=edge_stroke,
    )


def _marker_arrow(
    parent: ET.Element, marker_id: str, orient: str, fill: str,
) -> None:
    marker = ET.SubElement(parent, "marker")
    marker.set("id", marker_id)
    marker.set("viewBox", "0 0 10 10")
    marker.set("markerWidth", "8")
    marker.set("markerHeight", "8")
    marker.set("refX", "10")
    marker.set("refY", "5")
    marker.set("orient", orient)
    marker.set("markerUnits", "userSpaceOnUse")
    path = ET.SubElement(marker, "path")
    path.set("d", "M 0 0 L 10 5 L 0 10 z")
    path.set("fill", fill)


def _marker_circle(parent: ET.Element, fill: str) -> None:
    marker = ET.SubElement(parent, "marker")
    marker.set("id", "circle-end")
    marker.set("viewBox", "0 0 10 10")
    marker.set("markerWidth", "11")
    marker.set("markerHeight", "11")
    marker.set("refX", "10")
    marker.set("refY", "5")
    marker.set("orient", "auto")
    marker.set("markerUnits", "userSpaceOnUse")
    circle = ET.SubElement(marker, "circle")
    circle.set("cx", "5")
    circle.set("cy", "5")
    circle.set("r", "5")
    circle.set("fill", fill)


def _marker_cross(parent: ET.Element, stroke: str) -> None:
    marker = ET.SubElement(parent, "marker")
    marker.set("id", "cross-end")
    marker.set("viewBox", "0 0 11 11")
    marker.set("markerWidth", "11")
    marker.set("markerHeight", "11")
    marker.set("refX", "10")
    marker.set("refY", "5.5")
    marker.set("orient", "auto")
    marker.set("markerUnits", "userSpaceOnUse")
    path = ET.SubElement(marker, "path")
    path.set("d", "M 1,1 l 9,9 M 10,1 l -9,9")
    path.set("stroke", stroke)
    path.set("stroke-width", "2")


# ---------------------------------------------------------------------------
# Path generation
# ---------------------------------------------------------------------------

def points_to_path_d(points: list[Point], smooth: bool = True) -> str:
    """Convert layout points to an SVG path d-string, optionally smoothed.

    - 0 points: returns ``""``
    - 1 point: ``"M x,y"``
    - 2 points: ``"M x1,y1 L x2,y2"``
    - 3+ points with *smooth=True*: cubic Bezier ``C`` commands via
      Catmull-Rom conversion.
    - 3+ points with *smooth=False*: straight ``M``/``L`` segments.
    """
    if not points:
        return ""
    if len(points) == 1:
        return f"M{points[0].x},{points[0].y}"
    if len(points) == 2 or not smooth:
        parts = [f"M{points[0].x},{points[0].y}"]
        for p in points[1:]:
            parts.append(f"L{p.x},{p.y}")
        return " ".join(parts)

    # 3+ points, smooth: Catmull-Rom to cubic Bezier
    return _catmull_rom_to_bezier(points)


def _catmull_rom_to_bezier(points: list[Point]) -> str:
    """Convert a sequence of points to a smooth cubic Bezier path.

    Uses Catmull-Rom spline conversion.  The first and last points are
    duplicated so the curve passes through all given points.
    """
    # Pad the endpoints
    pts = [points[0]] + list(points) + [points[-1]]
    parts = [f"M{points[0].x},{points[0].y}"]

    for i in range(1, len(pts) - 2):
        p0 = pts[i - 1]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[i + 2]

        # Catmull-Rom to cubic Bezier control points
        cp1x = p1.x + (p2.x - p0.x) / 6.0
        cp1y = p1.y + (p2.y - p0.y) / 6.0
        cp2x = p2.x - (p3.x - p1.x) / 6.0
        cp2y = p2.y - (p3.y - p1.y) / 6.0

        parts.append(f"C{cp1x},{cp1y} {cp2x},{cp2y} {p2.x},{p2.y}")

    return " ".join(parts)


def _self_loop_path_d(points: list[Point]) -> str:
    """Generate an SVG path for a self-loop edge.

    Expects 13 points from the layout encoding 4 cubic Bezier segments:
        p0  = start (left side of node bottom edge)
        p1, p2  = control points for segment 1
        p3  = left midpoint (widest horizontal spread)
        p4, p5  = control points for segment 2
        p6  = bottom apex
        p7, p8  = control points for segment 3
        p9  = right midpoint (widest horizontal spread)
        p10, p11 = control points for segment 4
        p12 = end (right side of node bottom edge)

    Both start and end are on the node bottom edge.  The loop descends
    below the node in a leaf/oval shape and the arrowhead re-enters
    from below, pointing upward into the node.
    """
    p = points[:13]
    return (
        f"M{p[0].x},{p[0].y} "
        f"C{p[1].x},{p[1].y} {p[2].x},{p[2].y} {p[3].x},{p[3].y} "
        f"C{p[4].x},{p[4].y} {p[5].x},{p[5].y} {p[6].x},{p[6].y} "
        f"C{p[7].x},{p[7].y} {p[8].x},{p[8].y} {p[9].x},{p[9].y} "
        f"C{p[10].x},{p[10].y} {p[11].x},{p[11].y} {p[12].x},{p[12].y}"
    )


# ---------------------------------------------------------------------------
# Edge style mapping
# ---------------------------------------------------------------------------

_STYLE_MAP: dict[EdgeType, dict[str, str]] = {
    EdgeType.arrow:       {"stroke-width": "1"},
    EdgeType.open:        {"stroke-width": "1"},
    EdgeType.dotted:      {"stroke-width": "1", "stroke-dasharray": "3"},
    EdgeType.dotted_arrow: {"stroke-width": "1", "stroke-dasharray": "3"},
    EdgeType.thick:       {"stroke-width": "3.5"},
    EdgeType.thick_arrow: {"stroke-width": "3.5"},
    EdgeType.invisible:   {"stroke-width": "0", "visibility": "hidden"},
}

# Edge types that receive a target arrow marker (when ArrowType is not none).
_ARROW_TYPES = {EdgeType.arrow, EdgeType.dotted_arrow, EdgeType.thick_arrow}


# ---------------------------------------------------------------------------
# Marker assignment
# ---------------------------------------------------------------------------

def _marker_end_url(arrow: ArrowType) -> str | None:
    match arrow:
        case ArrowType.arrow:
            return "url(#arrow)"
        case ArrowType.circle:
            return "url(#circle-end)"
        case ArrowType.cross:
            return "url(#cross-end)"
        case ArrowType.none:
            return None


def _marker_start_url(arrow: ArrowType) -> str | None:
    match arrow:
        case ArrowType.arrow:
            return "url(#arrow-reverse)"
        case _:
            return None


# ---------------------------------------------------------------------------
# Edge midpoint (for label positioning)
# ---------------------------------------------------------------------------

def _edge_midpoint(points: list[Point]) -> tuple[float, float]:
    """Return the midpoint of a polyline."""
    if len(points) == 0:
        return (0.0, 0.0)
    if len(points) == 1:
        return (points[0].x, points[0].y)
    mid_idx = len(points) // 2
    p1 = points[mid_idx - 1]
    p2 = points[mid_idx]
    return ((p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0)


# ---------------------------------------------------------------------------
# Render a single edge
# ---------------------------------------------------------------------------

def render_edge(
    parent: ET.Element,
    edge_layout: EdgeLayout,
    ir_edge: Edge | None,
    smooth: bool = True,
    edge_label_bg: str = "rgba(232,232,232,0.8)",
) -> None:
    """Render a single edge with correct style, markers, and optional label."""
    g = ET.SubElement(parent, "g")
    g.set("class", "edge")
    g.set("data-edge-source", edge_layout.source)
    g.set("data-edge-target", edge_layout.target)

    # Determine edge type and arrow types from IR (defaults for missing IR).
    if ir_edge is not None:
        edge_type = ir_edge.edge_type
        target_arrow = ir_edge.target_arrow
        source_arrow = ir_edge.source_arrow
    else:
        edge_type = EdgeType.arrow
        target_arrow = ArrowType.arrow
        source_arrow = ArrowType.none

    # Build the <path>.  Self-loops (source == target) use explicit cubic
    # Bezier curves so the loop stays compact.  Normal edges use Catmull-Rom.
    is_self_loop = edge_layout.source == edge_layout.target
    path = ET.SubElement(g, "path")
    if is_self_loop and len(edge_layout.points) >= 13:
        path.set("d", _self_loop_path_d(edge_layout.points))
    else:
        path.set("d", points_to_path_d(edge_layout.points, smooth=smooth))

    # Apply line style
    style_attrs = _STYLE_MAP.get(edge_type, {})
    for attr, val in style_attrs.items():
        path.set(attr, val)

    # Marker assignment
    # For "open", "dotted", "thick", and "invisible" edge types the target
    # arrow is suppressed regardless of the ArrowType.
    if edge_type in _ARROW_TYPES:
        url = _marker_end_url(target_arrow)
        if url:
            path.set("marker-end", url)
    else:
        # Still allow explicit non-arrow markers (circle, cross) on open/dotted/thick
        if target_arrow not in (ArrowType.arrow, ArrowType.none):
            url = _marker_end_url(target_arrow)
            if url:
                path.set("marker-end", url)

    if source_arrow != ArrowType.none:
        url = _marker_start_url(source_arrow)
        if url:
            path.set("marker-start", url)

    # Edge label
    label = ir_edge.label if ir_edge else None
    if label:
        mx, my = _edge_midpoint(edge_layout.points)
        _render_edge_label(g, label, mx, my, edge_label_bg)


def _render_edge_label(
    parent: ET.Element,
    label: str,
    cx: float,
    cy: float,
    bg_fill: str = "rgba(232,232,232,0.8)",
) -> None:
    """Render an edge label with a background rect and text."""
    parts = label.split("<br/>")

    # Approximate dimensions for background rect
    max_line_len = max(len(p) for p in parts)
    char_w = 7.0  # rough px per char at 12px font
    line_h = 16.0
    padding = 4.0
    rect_w = max_line_len * char_w + padding * 2
    rect_h = len(parts) * line_h + padding * 2

    # Background rect (rendered first so text is on top)
    rect = ET.SubElement(parent, "rect")
    rect.set("x", str(cx - rect_w / 2))
    rect.set("y", str(cy - rect_h / 2))
    rect.set("width", str(rect_w))
    rect.set("height", str(rect_h))
    rect.set("fill", bg_fill)
    rect.set("stroke", "none")

    # Text element
    text_el = ET.SubElement(parent, "text")
    text_el.set("text-anchor", "middle")
    text_el.set("dominant-baseline", "central")

    if len(parts) == 1:
        text_el.set("x", str(cx))
        text_el.set("y", str(cy))
        text_el.text = parts[0]
    else:
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


__all__ = [
    "make_edge_defs",
    "points_to_path_d",
    "render_edge",
]
