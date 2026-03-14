"""Edge rendering: markers, line styles, path generation, and labels."""

import math
import xml.etree.ElementTree as ET

from merm.ir import ArrowType, Edge, EdgeType
from merm.layout import EdgeLayout, Point

# Default edge stroke colour (used as fallback).
_DEFAULT_EDGE_STROKE = "#333333"

# How far to pull the path endpoint back from the node border so the stroke
# doesn't poke through the filled arrowhead.  Should equal markerWidth.
_MARKER_SHORTEN = 8.0

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
    marker.set("refX", "0")
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
    marker.set("markerWidth", "8")
    marker.set("markerHeight", "8")
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
    marker.set("markerWidth", "8")
    marker.set("markerHeight", "8")
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

def _shorten_end(points: list[Point], amount: float) -> list[Point]:
    """Pull the last point back along the final segment direction."""
    if len(points) < 2:
        return list(points)
    p_prev, p_last = points[-2], points[-1]
    dx = p_last.x - p_prev.x
    dy = p_last.y - p_prev.y
    length = math.hypot(dx, dy)
    if length < 1e-6 or amount >= length:
        return list(points)
    ratio = amount / length
    new_last = Point(p_last.x - dx * ratio, p_last.y - dy * ratio)
    return list(points[:-1]) + [new_last]

def _shorten_start(points: list[Point], amount: float) -> list[Point]:
    """Pull the first point forward along the first segment direction."""
    if len(points) < 2:
        return list(points)
    p_first, p_next = points[0], points[1]
    dx = p_next.x - p_first.x
    dy = p_next.y - p_first.y
    length = math.hypot(dx, dy)
    if length < 1e-6 or amount >= length:
        return list(points)
    ratio = amount / length
    new_first = Point(p_first.x + dx * ratio, p_first.y + dy * ratio)
    return [new_first] + list(points[1:])

# ---------------------------------------------------------------------------
# Edge style mapping
# ---------------------------------------------------------------------------

_STYLE_MAP: dict[EdgeType, dict[str, str]] = {
    EdgeType.arrow:       {"stroke-width": "2"},
    EdgeType.open:        {"stroke-width": "2"},
    EdgeType.dotted:      {"stroke-width": "2", "stroke-dasharray": "5,5"},
    EdgeType.dotted_arrow: {"stroke-width": "2", "stroke-dasharray": "5,5"},
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

def _label_bbox(
    label: str, cx: float, cy: float,
) -> tuple[float, float, float, float]:
    """Compute approximate bounding box (x, y, w, h) for an edge label.

    Uses the same constants as ``_render_edge_label``.
    """
    parts = label.split("<br/>")
    max_line_len = max(len(p) for p in parts)
    char_w = 7.0
    line_h = 16.0
    padding = 4.0
    w = max_line_len * char_w + padding * 2
    h = len(parts) * line_h + padding * 2
    return (cx - w / 2, cy - h / 2, w, h)

def _rects_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> bool:
    """Return True if two axis-aligned rectangles (x, y, w, h) overlap."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (
        ax < bx + bw
        and ax + aw > bx
        and ay < by + bh
        and ay + ah > by
    )

def _edge_path_bbox(el: EdgeLayout) -> tuple[float, float, float, float]:
    """Compute an axis-aligned bounding box (x, y, w, h) for an edge's path."""
    if not el.points:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [p.x for p in el.points]
    ys = [p.y for p in el.points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return (min_x, min_y, max_x - min_x, max_y - min_y)

def resolve_label_positions(
    labeled_edges: list[tuple[EdgeLayout, Edge]],
    obstacle_edges: list[EdgeLayout] | None = None,
) -> dict[tuple[str, str], tuple[float, float]]:
    """Compute adjusted label positions so no two label bounding boxes overlap.

    Also avoids overlapping with obstacle edge paths (e.g. back-edges).

    Args:
        labeled_edges: List of ``(edge_layout, ir_edge)`` pairs for edges
            that have labels.
        obstacle_edges: Optional list of edge layouts whose paths should be
            avoided by labels (e.g. back-edges).

    Returns:
        A dict mapping ``(source, target)`` to the adjusted ``(cx, cy)``
        position for the label.
    """
    if not labeled_edges:
        return {}

    # Compute initial positions from edge midpoints.
    entries: list[tuple[tuple[str, str], str, float, float]] = []
    for el, ir_edge in labeled_edges:
        key = (el.source, el.target)
        cx, cy = _edge_midpoint(el.points)
        entries.append((key, ir_edge.label, cx, cy))

    # Sort by y then x for deterministic processing.
    entries.sort(key=lambda e: (e[3], e[2]))

    # Build mutable position list.
    positions: list[list[float]] = [[e[2], e[3]] for e in entries]
    labels = [e[1] for e in entries]

    # Pre-compute obstacle bounding boxes.
    obstacle_bboxes: list[tuple[float, float, float, float]] = []
    if obstacle_edges:
        for oel in obstacle_edges:
            bbox = _edge_path_bbox(oel)
            if bbox[2] > 0 or bbox[3] > 0:
                obstacle_bboxes.append(bbox)

    # Iterative nudging -- run up to 20 passes to resolve overlaps.
    gap = 6.0
    for _ in range(20):
        changed = False
        for i in range(len(entries)):
            bbox_i = _label_bbox(labels[i], positions[i][0], positions[i][1])

            # Check against obstacle edges (back-edge paths).
            for obs_bb in obstacle_bboxes:
                if _rects_overlap(bbox_i, obs_bb):
                    # Push label left so it clears the obstacle.
                    label_right = bbox_i[0] + bbox_i[2]
                    shift = label_right - obs_bb[0] + gap
                    positions[i][0] -= shift
                    changed = True
                    bbox_i = _label_bbox(
                        labels[i], positions[i][0], positions[i][1],
                    )

            for j in range(i + 1, len(entries)):
                bbox_j = _label_bbox(
                    labels[j], positions[j][0], positions[j][1],
                )
                if _rects_overlap(bbox_i, bbox_j):
                    # Compute overlap amount on each axis.
                    iy_bottom = bbox_i[1] + bbox_i[3]
                    jy_top = bbox_j[1]
                    y_overlap = iy_bottom - jy_top + gap

                    ix_right = bbox_i[0] + bbox_i[2]
                    jx_left = bbox_j[0]
                    x_overlap = ix_right - jx_left + gap

                    # Nudge along the axis with less overlap (cheaper
                    # to separate).
                    if y_overlap <= x_overlap:
                        # Push j down, i up by half each.
                        positions[i][1] -= y_overlap / 2.0
                        positions[j][1] += y_overlap / 2.0
                    else:
                        # Push i left, j right by half each.
                        positions[i][0] -= x_overlap / 2.0
                        positions[j][0] += x_overlap / 2.0
                    changed = True
                    # Recompute bbox_i after nudge.
                    bbox_i = _label_bbox(
                        labels[i], positions[i][0], positions[i][1],
                    )
        if not changed:
            break

    result: dict[tuple[str, str], tuple[float, float]] = {}
    for idx, entry in enumerate(entries):
        result[entry[0]] = (positions[idx][0], positions[idx][1])
    return result

# ---------------------------------------------------------------------------
# Render a single edge
# ---------------------------------------------------------------------------

def render_edge(
    parent: ET.Element,
    edge_layout: EdgeLayout,
    ir_edge: Edge | None,
    smooth: bool = True,
    edge_label_bg: str = "rgba(232,232,232,0.8)",
    label_pos: tuple[float, float] | None = None,
    skip_label: bool = False,
) -> None:
    """Render a single edge with correct style, markers, and optional label.

    Args:
        label_pos: If provided, use this ``(cx, cy)`` for the label instead
            of computing the edge midpoint.
        skip_label: If True, skip rendering the label (for two-pass rendering
            where labels are rendered separately on top of nodes).
    """
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

    # Determine which endpoints have markers so we can shorten the path
    # to prevent the stroke from poking through the filled arrowhead.
    has_end_marker = (
        (edge_type in _ARROW_TYPES and _marker_end_url(target_arrow) is not None)
        or (target_arrow not in (ArrowType.arrow, ArrowType.none)
            and _marker_end_url(target_arrow) is not None)
    )
    has_start_marker = (
        source_arrow != ArrowType.none
        and _marker_start_url(source_arrow) is not None
    )

    # Build the <path>.  Self-loops (source == target) use explicit cubic
    # Bezier curves so the loop stays compact.  Normal edges use Catmull-Rom.
    is_self_loop = edge_layout.source == edge_layout.target
    path = ET.SubElement(g, "path")
    if is_self_loop and len(edge_layout.points) >= 13:
        path.set("d", _self_loop_path_d(edge_layout.points))
    else:
        pts = list(edge_layout.points)
        if has_end_marker:
            pts = _shorten_end(pts, _MARKER_SHORTEN)
        if has_start_marker:
            pts = _shorten_start(pts, _MARKER_SHORTEN)
        path.set("d", points_to_path_d(pts, smooth=smooth))

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
    if not skip_label:
        label = ir_edge.label if ir_edge else None
        if label:
            if label_pos is not None:
                mx, my = label_pos
            else:
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
        # Set base position on the <text> element so tspan dy offsets
        # are relative to the label center, not the SVG origin.
        text_el.set("x", str(cx))
        text_el.set("y", str(cy))

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

def render_edge_label_only(
    parent: ET.Element,
    edge_layout: EdgeLayout,
    ir_edge: Edge | None,
    edge_label_bg: str = "rgba(232,232,232,0.8)",
    label_pos: tuple[float, float] | None = None,
) -> None:
    """Render only the label for an edge (without the path/markers).

    Used in two-pass rendering where edge paths are drawn first,
    then nodes, then edge labels on top so labels are not obscured
    by node backgrounds.
    """
    label = ir_edge.label if ir_edge else None
    if not label:
        return

    g = ET.SubElement(parent, "g")
    g.set("class", "edge-label")
    g.set("data-edge-source", edge_layout.source)
    g.set("data-edge-target", edge_layout.target)

    if label_pos is not None:
        mx, my = label_pos
    else:
        mx, my = _edge_midpoint(edge_layout.points)
    _render_edge_label(g, label, mx, my, edge_label_bg)


__all__ = [
    "make_edge_defs",
    "points_to_path_d",
    "render_edge",
    "render_edge_label_only",
    "resolve_label_positions",
]
