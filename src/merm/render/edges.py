"""Edge rendering: markers, line styles, path generation, and labels."""

import math
import xml.etree.ElementTree as ET

from merm.ir import ArrowType, Edge, EdgeType
from merm.layout import EdgeLayout, Point

# Default edge stroke colour (used as fallback).
_DEFAULT_EDGE_STROKE = "#333333"

# How far to pull the path endpoint back from the node border per marker type.
# Must account for marker scaling: markerWidth / viewBox ratio.
# Arrow: viewBox 10x10, markerWidth=8, refX=0 => forward extent = 10*(8/10) = 8.0
# Circle: viewBox 10x10, markerWidth=8, refX=5 => forward extent = 5*(8/10) = 4.0
# Cross:  viewBox 11x11, markerWidth=8, refX=5.5 => forward extent = 5.5*(8/11) = 4.0
# No marker / none: shorten by 0
_MARKER_SHORTEN_BY_ARROW: dict[ArrowType, float] = {
    ArrowType.arrow: 8.0,
    ArrowType.circle: 4.0,
    ArrowType.cross: 4.0,
    ArrowType.none: 0.0,
}

# Backward-compatible alias: the arrow marker shortening value (8px).
_MARKER_SHORTEN = 8

def _marker_shorten(arrow: ArrowType) -> float:
    """Return the path shortening distance for a given arrow marker type."""
    return _MARKER_SHORTEN_BY_ARROW.get(arrow, 0.0)

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
    # refX=0 places the triangle BASE at the path endpoint.
    # Combined with _MARKER_SHORTEN=8, the path stops 8px before the
    # node boundary and the arrowhead fills the gap, so the TIP touches
    # the node while the stroke line stops cleanly at the arrowhead base.
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
    # refX=5 centers the circle at the endpoint (after shortening,
    # the circle straddles the gap between path end and node border).
    marker.set("refX", "5")
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
    # refX=5.5 centers the cross at the endpoint.
    marker.set("refX", "5.5")
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


def _point_along_polyline(points: list[Point], fraction: float) -> tuple[float, float]:
    """Return the point at *fraction* (0..1) of the total polyline length.

    Used to bias label positions away from diamond nodes whose diagonal
    borders extend further than rectangular borders.
    """
    if len(points) == 0:
        return (0.0, 0.0)
    if len(points) == 1:
        return (points[0].x, points[0].y)

    # Compute cumulative segment lengths.
    seg_lengths: list[float] = []
    for i in range(1, len(points)):
        seg_lengths.append(math.hypot(
            points[i].x - points[i - 1].x,
            points[i].y - points[i - 1].y,
        ))
    total = sum(seg_lengths)
    if total < 1e-6:
        return (points[0].x, points[0].y)

    target_dist = fraction * total
    cumulative = 0.0
    for i, seg_len in enumerate(seg_lengths):
        if cumulative + seg_len >= target_dist:
            # Interpolate within this segment.
            remaining = target_dist - cumulative
            t = remaining / seg_len if seg_len > 1e-6 else 0.0
            px = points[i].x + t * (points[i + 1].x - points[i].x)
            py = points[i].y + t * (points[i + 1].y - points[i].y)
            return (px, py)
        cumulative += seg_len

    # Fallback: return last point.
    return (points[-1].x, points[-1].y)

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
    diamond_node_ids: set[str] | None = None,
    node_bboxes: list[tuple[float, float, float, float]] | None = None,
) -> dict[tuple[str, str], tuple[float, float]]:
    """Compute adjusted label positions so no two label bounding boxes overlap.

    Also avoids overlapping with obstacle edge paths (e.g. back-edges)
    and node bounding boxes.

    Args:
        labeled_edges: List of ``(edge_layout, ir_edge)`` pairs for edges
            that have labels.
        obstacle_edges: Optional list of edge layouts whose paths should be
            avoided by labels (e.g. back-edges).
        diamond_node_ids: Optional set of node IDs that are diamond-shaped.
            When an edge's source or target is a diamond, the label is
            biased away from it to avoid overlapping the diagonal border.
        node_bboxes: Optional list of node bounding boxes ``(x, y, w, h)``
            that labels should avoid overlapping.

    Returns:
        A dict mapping ``(source, target)`` to the adjusted ``(cx, cy)``
        position for the label.
    """
    if not labeled_edges:
        return {}

    diamonds = diamond_node_ids or set()

    # Compute initial positions from edge midpoints, biasing away from
    # diamond-shaped source/target nodes whose diagonal borders extend
    # further than rectangular borders.  Also track which edges are
    # back-edges (going upward) for node obstacle avoidance.
    entries: list[tuple[tuple[str, str], str, float, float]] = []
    back_edge_keys: set[tuple[str, str]] = set()
    for el, ir_edge in labeled_edges:
        key = (el.source, el.target)
        src_diamond = el.source in diamonds
        tgt_diamond = el.target in diamonds
        if src_diamond and not tgt_diamond:
            cx, cy = _point_along_polyline(el.points, 0.65)
        elif tgt_diamond and not src_diamond:
            cx, cy = _point_along_polyline(el.points, 0.35)
        else:
            cx, cy = _edge_midpoint(el.points)
        entries.append((key, ir_edge.label, cx, cy))
        if len(el.points) >= 2 and el.points[-1].y < el.points[0].y:
            back_edge_keys.add(key)

    # Sort by y then x for deterministic processing.
    entries.sort(key=lambda e: (e[3], e[2]))

    # Build mutable position list.
    positions: list[list[float]] = [[e[2], e[3]] for e in entries]
    labels = [e[1] for e in entries]

    # Pre-compute obstacle bounding boxes from edge paths.
    obstacle_bboxes: list[tuple[float, float, float, float]] = []
    if obstacle_edges:
        for oel in obstacle_edges:
            bbox = _edge_path_bbox(oel)
            if bbox[2] > 0 or bbox[3] > 0:
                obstacle_bboxes.append(bbox)

    # Include node bounding boxes as obstacles (with a small margin).
    # Only applied to back-edge labels which may cross over nodes.
    node_obstacle_bboxes: list[tuple[float, float, float, float]] = []
    if node_bboxes:
        node_margin = 4.0
        for nx, ny, nw, nh in node_bboxes:
            node_obstacle_bboxes.append((
                nx - node_margin,
                ny - node_margin,
                nw + 2 * node_margin,
                nh + 2 * node_margin,
            ))

    # Iterative nudging -- run up to 30 passes to resolve overlaps.
    gap = 10.0
    for _ in range(30):
        changed = False
        for i in range(len(entries)):
            bbox_i = _label_bbox(labels[i], positions[i][0], positions[i][1])

            # Check against obstacle edges (back-edge paths).
            for obs_bb in obstacle_bboxes:
                if _rects_overlap(bbox_i, obs_bb):
                    label_right = bbox_i[0] + bbox_i[2]
                    shift = label_right - obs_bb[0] + gap
                    positions[i][0] -= shift
                    changed = True
                    bbox_i = _label_bbox(
                        labels[i], positions[i][0], positions[i][1],
                    )

            # Check against node bounding boxes -- only for back-edge
            # labels to avoid destabilizing forward-edge labels that
            # naturally sit in the inter-rank gap between nodes.
            if node_obstacle_bboxes and entries[i][0] in back_edge_keys:
                for node_bb in node_obstacle_bboxes:
                    if _rects_overlap(bbox_i, node_bb):
                        lx, ly, lw, lh = bbox_i
                        nx, ny, nw, nh = node_bb

                        # Push in direction requiring least movement.
                        push_right = (nx + nw) - lx + gap
                        push_left = (lx + lw) - nx + gap
                        push_down = (ny + nh) - ly + gap
                        push_up = (ly + lh) - ny + gap

                        min_push = min(push_right, push_left,
                                       push_down, push_up)
                        if min_push == push_down:
                            positions[i][1] += push_down
                        elif min_push == push_up:
                            positions[i][1] -= push_up
                        elif min_push == push_right:
                            positions[i][0] += push_right
                        else:
                            positions[i][0] -= push_left

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

                    # Nudge along the axis with less overlap.
                    if y_overlap <= x_overlap:
                        positions[i][1] -= y_overlap / 2.0
                        positions[j][1] += y_overlap / 2.0
                    else:
                        positions[i][0] -= x_overlap / 2.0
                        positions[j][0] += x_overlap / 2.0
                    changed = True
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
    # Use per-marker-type shortening distances.
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
            pts = _shorten_end(pts, _marker_shorten(target_arrow))
        if has_start_marker:
            pts = _shorten_start(pts, _marker_shorten(source_arrow))
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


# ---------------------------------------------------------------------------
# Bidirectional edge offset
# ---------------------------------------------------------------------------

_BIDI_OFFSET = 4.0  # px perpendicular offset for each direction


def find_bidirectional_pairs(
    edges: list[EdgeLayout],
) -> set[tuple[str, str]]:
    """Return set of (source, target) keys that have a reverse edge.

    For each pair where both (A, B) and (B, A) exist, both keys are
    included in the returned set.
    """
    edge_keys: set[tuple[str, str]] = set()
    for el in edges:
        edge_keys.add((el.source, el.target))

    bidi: set[tuple[str, str]] = set()
    for src, tgt in edge_keys:
        if (tgt, src) in edge_keys:
            bidi.add((src, tgt))
            bidi.add((tgt, src))
    return bidi


def offset_edge_points(
    points: list[Point],
    offset: float,
) -> list[Point]:
    """Offset all points perpendicular to the overall edge direction.

    The offset is applied perpendicular to the line from the first
    point to the last point.  Positive offset shifts to the right
    (when looking from start to end).
    """
    if len(points) < 2:
        return list(points)

    # Overall direction from first to last point.
    dx = points[-1].x - points[0].x
    dy = points[-1].y - points[0].y
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return list(points)

    # Unit perpendicular vector (rotated 90 degrees clockwise).
    perp_x = dy / length
    perp_y = -dx / length

    return [
        Point(p.x + perp_x * offset, p.y + perp_y * offset)
        for p in points
    ]


def apply_bidi_offsets(
    edges: list[EdgeLayout],
) -> list[EdgeLayout]:
    """Return a new list of EdgeLayouts with bidirectional edges offset.

    For each pair of edges connecting the same two nodes in opposite
    directions, offset their paths by +/- _BIDI_OFFSET perpendicular
    to the edge direction so they appear as parallel lines.

    Single-direction edges are returned unchanged.
    """
    bidi_keys = find_bidirectional_pairs(edges)
    if not bidi_keys:
        return edges

    result: list[EdgeLayout] = []
    for el in edges:
        key = (el.source, el.target)
        if key in bidi_keys:
            # For reversed edges, the perpendicular vector naturally
            # flips direction.  To get the two edges on opposite sides
            # we use the SAME sign offset for both: the edge whose
            # (source, target) is lexicographically smaller gets +offset,
            # the reversed edge also gets +offset, but because its
            # perpendicular points the other way, it ends up on the
            # opposite side.
            #
            # However, if both edges share the same perpendicular
            # direction (e.g. both going the same way due to layout),
            # we need to ensure they get opposite signs.  The key
            # insight is: for truly reversed edges (A->B vs B->A),
            # the perpendicular naturally flips, so same sign = opposite
            # sides.  We always use +offset for both.
            shifted = offset_edge_points(el.points, _BIDI_OFFSET)
            result.append(EdgeLayout(
                points=shifted,
                source=el.source,
                target=el.target,
            ))
        else:
            result.append(el)
    return result


__all__ = [
    "apply_bidi_offsets",
    "find_bidirectional_pairs",
    "make_edge_defs",
    "offset_edge_points",
    "points_to_path_d",
    "render_edge",
    "render_edge_label_only",
    "resolve_label_positions",
]
