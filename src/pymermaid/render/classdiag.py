"""Class diagram SVG renderer.

Renders ClassDiagram IR into SVG, including:
- Three-section class boxes (name header, fields, methods)
- Divider lines between sections
- Visibility markers as text prefix
- Relationship-specific SVG markers (hollow triangle, diamonds, etc.)
- Cardinality labels near endpoints
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from pymermaid.ir.classdiag import (
    ClassDiagram,
    ClassMember,
    ClassNode,
    ClassRelation,
    RelationType,
    Visibility,
)
from pymermaid.layout.types import EdgeLayout, LayoutResult, NodeLayout, Point
from pymermaid.render.edges import points_to_path_d
from pymermaid.theme import DEFAULT_THEME, Theme

# SVG namespace
_SVG_NS = "http://www.w3.org/2000/svg"

# Padding around viewBox
_PADDING = 20

# Class box layout constants
_HEADER_HEIGHT = 30.0
_ANNOTATION_HEIGHT = 16.0
_MEMBER_LINE_HEIGHT = 20.0
_BOX_PADDING_H = 10.0
_CHAR_WIDTH = 8.0  # approximate character width at 14px
_FONT_SIZE = 14.0
_SMALL_FONT_SIZE = 12.0
_MIN_BOX_WIDTH = 100.0


# ---------------------------------------------------------------------------
# Visibility display
# ---------------------------------------------------------------------------

_VISIBILITY_SYMBOL = {
    Visibility.PUBLIC: "+",
    Visibility.PRIVATE: "-",
    Visibility.PROTECTED: "#",
    Visibility.PACKAGE: "~",
}


def _member_display(member: ClassMember) -> str:
    """Build display string for a class member."""
    vis = _VISIBILITY_SYMBOL.get(member.visibility, "+")
    if member.is_method:
        suffix = f" {member.type_str}" if member.type_str else ""
        return f"{vis}{member.name}(){suffix}"
    else:
        suffix = f": {member.type_str}" if member.type_str else ""
        return f"{vis}{member.name}{suffix}"


# ---------------------------------------------------------------------------
# Class box size measurement
# ---------------------------------------------------------------------------

def measure_class_box(node: ClassNode) -> tuple[float, float]:
    """Compute (width, height) for a class box.

    The box has three sections:
    - Header: class name + optional annotation
    - Fields section
    - Methods section
    """
    fields = [m for m in node.members if not m.is_method]
    methods = [m for m in node.members if m.is_method]

    # Header height
    header_h = _HEADER_HEIGHT
    if node.annotation:
        header_h += _ANNOTATION_HEIGHT

    # Sections height
    fields_h = max(len(fields) * _MEMBER_LINE_HEIGHT, _MEMBER_LINE_HEIGHT)
    methods_h = max(len(methods) * _MEMBER_LINE_HEIGHT, _MEMBER_LINE_HEIGHT)

    total_h = header_h + fields_h + methods_h

    # Width: max of all text lines
    texts = [node.label]
    if node.annotation:
        texts.append(node.annotation)
    texts.extend(_member_display(m) for m in node.members)

    max_text_len = max((len(t) for t in texts), default=5)
    total_w = max(max_text_len * _CHAR_WIDTH + 2 * _BOX_PADDING_H, _MIN_BOX_WIDTH)

    return total_w, total_h


# ---------------------------------------------------------------------------
# Marker definitions for class diagram relationships
# ---------------------------------------------------------------------------

def _make_class_defs(
    defs: ET.Element,
    edge_stroke: str = "#333333",
) -> None:
    """Add marker definitions for class diagram relationship types."""
    # Inheritance: hollow triangle (filled white)
    _marker_triangle_hollow(defs, "inherit-arrow", edge_stroke)

    # Composition: filled diamond
    _marker_diamond(defs, "composition-arrow", edge_stroke, fill=edge_stroke)

    # Aggregation: hollow diamond
    _marker_diamond(defs, "aggregation-arrow", edge_stroke, fill="white")

    # Association: open arrow (simple triangle, filled)
    _marker_open_arrow(defs, "association-arrow", edge_stroke)

    # Dependency: open arrow (same as association, used with dashed line)
    _marker_open_arrow(defs, "dependency-arrow", edge_stroke)

    # Realization: hollow triangle (same as inheritance, used with dashed line)
    _marker_triangle_hollow(defs, "realization-arrow", edge_stroke)


def _marker_triangle_hollow(
    parent: ET.Element, marker_id: str, stroke: str,
) -> None:
    """Hollow triangle arrowhead (inheritance/realization)."""
    marker = ET.SubElement(parent, "marker")
    marker.set("id", marker_id)
    marker.set("markerWidth", "12")
    marker.set("markerHeight", "12")
    marker.set("refX", "12")
    marker.set("refY", "6")
    marker.set("orient", "auto")
    marker.set("markerUnits", "strokeWidth")
    path = ET.SubElement(marker, "path")
    path.set("d", "M0,0 L12,6 L0,12 Z")
    path.set("fill", "white")
    path.set("stroke", stroke)
    path.set("stroke-width", "1")


def _marker_diamond(
    parent: ET.Element, marker_id: str, stroke: str, fill: str,
) -> None:
    """Diamond marker (composition = filled, aggregation = hollow)."""
    marker = ET.SubElement(parent, "marker")
    marker.set("id", marker_id)
    marker.set("markerWidth", "16")
    marker.set("markerHeight", "10")
    marker.set("refX", "16")
    marker.set("refY", "5")
    marker.set("orient", "auto")
    marker.set("markerUnits", "strokeWidth")
    path = ET.SubElement(marker, "path")
    path.set("d", "M0,5 L8,0 L16,5 L8,10 Z")
    path.set("fill", fill)
    path.set("stroke", stroke)
    path.set("stroke-width", "1")


def _marker_open_arrow(
    parent: ET.Element, marker_id: str, stroke: str,
) -> None:
    """Open arrow (association/dependency) -- simple V-shape."""
    marker = ET.SubElement(parent, "marker")
    marker.set("id", marker_id)
    marker.set("markerWidth", "10")
    marker.set("markerHeight", "7")
    marker.set("refX", "10")
    marker.set("refY", "3.5")
    marker.set("orient", "auto")
    marker.set("markerUnits", "strokeWidth")
    path = ET.SubElement(marker, "path")
    path.set("d", "M0,0 L10,3.5 L0,7")
    path.set("fill", "none")
    path.set("stroke", stroke)
    path.set("stroke-width", "1.5")


# ---------------------------------------------------------------------------
# Relationship marker mapping
# ---------------------------------------------------------------------------

_REL_MARKER_MAP: dict[RelationType, str] = {
    RelationType.INHERITANCE: "url(#inherit-arrow)",
    RelationType.COMPOSITION: "url(#composition-arrow)",
    RelationType.AGGREGATION: "url(#aggregation-arrow)",
    RelationType.ASSOCIATION: "url(#association-arrow)",
    RelationType.DEPENDENCY: "url(#dependency-arrow)",
    RelationType.REALIZATION: "url(#realization-arrow)",
}

_DASHED_RELS = {RelationType.DEPENDENCY, RelationType.REALIZATION}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _render_class_node(
    parent: ET.Element,
    node: ClassNode,
    nl: NodeLayout,
    theme: Theme,
) -> None:
    """Render a three-section class box."""
    g = ET.SubElement(parent, "g")
    g.set("class", "class-node")
    g.set("data-node-id", node.id)

    x, y, w, h = nl.x, nl.y, nl.width, nl.height

    fields = [m for m in node.members if not m.is_method]
    methods = [m for m in node.members if m.is_method]

    header_h = _HEADER_HEIGHT
    if node.annotation:
        header_h += _ANNOTATION_HEIGHT

    fields_h = max(len(fields) * _MEMBER_LINE_HEIGHT, _MEMBER_LINE_HEIGHT)

    # Outer box
    rect = ET.SubElement(g, "rect")
    rect.set("x", str(round(x, 2)))
    rect.set("y", str(round(y, 2)))
    rect.set("width", str(round(w, 2)))
    rect.set("height", str(round(h, 2)))
    rect.set("fill", theme.node_fill)
    rect.set("stroke", theme.node_stroke)
    rect.set("stroke-width", theme.node_stroke_width)

    # Header section
    # Annotation text (if any)
    text_y = y
    if node.annotation:
        ann_el = ET.SubElement(g, "text")
        ann_el.set("x", str(round(x + w / 2, 2)))
        ann_el.set("y", str(round(text_y + 14, 2)))
        ann_el.set("text-anchor", "middle")
        ann_el.set("font-family", theme.font_family)
        ann_el.set("font-size", f"{_SMALL_FONT_SIZE}px")
        ann_el.set("font-style", "italic")
        ann_el.set("fill", theme.node_text_color)
        ann_el.text = node.annotation
        text_y += _ANNOTATION_HEIGHT

    # Class name
    name_el = ET.SubElement(g, "text")
    name_el.set("x", str(round(x + w / 2, 2)))
    name_el.set("y", str(round(text_y + 20, 2)))
    name_el.set("text-anchor", "middle")
    name_el.set("font-family", theme.font_family)
    name_el.set("font-size", f"{_FONT_SIZE}px")
    name_el.set("font-weight", "bold")
    name_el.set("fill", theme.node_text_color)
    name_el.text = node.label

    # Divider line after header
    div1_y = y + header_h
    line1 = ET.SubElement(g, "line")
    line1.set("x1", str(round(x, 2)))
    line1.set("y1", str(round(div1_y, 2)))
    line1.set("x2", str(round(x + w, 2)))
    line1.set("y2", str(round(div1_y, 2)))
    line1.set("stroke", theme.node_stroke)
    line1.set("stroke-width", "1")

    # Fields section
    for i, f in enumerate(fields):
        f_el = ET.SubElement(g, "text")
        f_el.set("x", str(round(x + _BOX_PADDING_H, 2)))
        f_el.set("y", str(round(div1_y + (i + 1) * _MEMBER_LINE_HEIGHT - 4, 2)))
        f_el.set("font-family", theme.font_family)
        f_el.set("font-size", f"{_SMALL_FONT_SIZE}px")
        f_el.set("fill", theme.node_text_color)
        f_el.text = _member_display(f)

    # Divider line after fields
    div2_y = div1_y + fields_h
    line2 = ET.SubElement(g, "line")
    line2.set("x1", str(round(x, 2)))
    line2.set("y1", str(round(div2_y, 2)))
    line2.set("x2", str(round(x + w, 2)))
    line2.set("y2", str(round(div2_y, 2)))
    line2.set("stroke", theme.node_stroke)
    line2.set("stroke-width", "1")

    # Methods section
    for i, m in enumerate(methods):
        m_el = ET.SubElement(g, "text")
        m_el.set("x", str(round(x + _BOX_PADDING_H, 2)))
        m_el.set("y", str(round(div2_y + (i + 1) * _MEMBER_LINE_HEIGHT - 4, 2)))
        m_el.set("font-family", theme.font_family)
        m_el.set("font-size", f"{_SMALL_FONT_SIZE}px")
        m_el.set("fill", theme.node_text_color)
        m_el.text = _member_display(m)


def _render_class_edge(
    parent: ET.Element,
    relation: ClassRelation,
    edge_layout: EdgeLayout,
    theme: Theme,
) -> None:
    """Render a class diagram relationship edge."""
    g = ET.SubElement(parent, "g")
    g.set("class", "class-edge")
    g.set("data-edge-source", relation.source)
    g.set("data-edge-target", relation.target)

    # Path
    path = ET.SubElement(g, "path")
    path.set("d", points_to_path_d(edge_layout.points, smooth=False))
    path.set("fill", "none")
    path.set("stroke", theme.edge_stroke)
    path.set("stroke-width", theme.edge_stroke_width)

    # Dashed line for dependency/realization
    if relation.rel_type in _DASHED_RELS:
        path.set("stroke-dasharray", "5,5")

    # Marker
    marker_url = _REL_MARKER_MAP.get(relation.rel_type)
    if marker_url:
        path.set("marker-end", marker_url)

    # Cardinality labels
    if relation.source_cardinality:
        pts = edge_layout.points
        away = pts[1] if len(pts) > 1 else pts[0]
        _render_cardinality(
            g, relation.source_cardinality,
            pts[0], away, theme,
        )

    if relation.target_cardinality:
        pts = edge_layout.points
        away = pts[-2] if len(pts) > 1 else pts[-1]
        _render_cardinality(
            g, relation.target_cardinality,
            pts[-1], away, theme,
        )

    # Label
    if relation.label:
        mid = _midpoint(edge_layout.points)
        label_el = ET.SubElement(g, "text")
        label_el.set("x", str(round(mid.x, 2)))
        label_el.set("y", str(round(mid.y - 8, 2)))
        label_el.set("text-anchor", "middle")
        label_el.set("font-family", theme.font_family)
        label_el.set("font-size", f"{_SMALL_FONT_SIZE}px")
        label_el.set("fill", theme.text_color)
        label_el.text = relation.label


def _render_cardinality(
    parent: ET.Element,
    text: str,
    near_point: Point,
    away_point: Point,
    theme: Theme,
) -> None:
    """Render a cardinality label near an endpoint."""
    # Offset slightly from the endpoint, perpendicular-ish to the edge
    dx = away_point.x - near_point.x
    dy = away_point.y - near_point.y

    # Offset 15px along the edge from the endpoint, and 12px perpendicular
    length = max((dx ** 2 + dy ** 2) ** 0.5, 1.0)
    nx, ny = dx / length, dy / length

    # Position: 15px along edge + 12px perpendicular
    lx = near_point.x + nx * 15 - ny * 12
    ly = near_point.y + ny * 15 + nx * 12

    el = ET.SubElement(parent, "text")
    el.set("x", str(round(lx, 2)))
    el.set("y", str(round(ly, 2)))
    el.set("text-anchor", "middle")
    el.set("font-family", theme.font_family)
    el.set("font-size", f"{_SMALL_FONT_SIZE}px")
    el.set("fill", theme.text_color)
    el.text = text


def _midpoint(points: list[Point]) -> Point:
    """Get the midpoint of a polyline."""
    if len(points) < 2:
        return points[0] if points else Point(0, 0)
    mid = len(points) // 2
    p1 = points[mid - 1]
    p2 = points[mid]
    return Point((p1.x + p2.x) / 2, (p1.y + p2.y) / 2)


def _round_coord(val: float) -> str:
    """Format a float coordinate."""
    rounded = round(val, 2)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def _build_class_diagram_css(theme: Theme) -> str:
    """Build CSS for class diagram elements."""
    return (
        f".class-node rect {{ fill: {theme.node_fill}; "
        f"stroke: {theme.node_stroke}; "
        f"stroke-width: {theme.node_stroke_width}; }}\n"
        f".class-node text {{ fill: {theme.node_text_color}; "
        f"font-family: {theme.font_family}; }}\n"
        f".class-node line {{ stroke: {theme.node_stroke}; }}\n"
        f".class-edge path {{ fill: none; "
        f"stroke: {theme.edge_stroke}; "
        f"stroke-width: {theme.edge_stroke_width}; }}\n"
        f".class-edge text {{ fill: {theme.text_color}; "
        f"font-family: {theme.font_family}; }}\n"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_class_diagram(
    diagram: ClassDiagram,
    layout: LayoutResult,
    theme: Theme | None = None,
) -> str:
    """Render a ClassDiagram and LayoutResult to SVG.

    Args:
        diagram: The class diagram IR.
        layout: The positioned layout result.
        theme: Optional theme. Defaults to DEFAULT_THEME.

    Returns:
        SVG string.
    """
    if theme is None:
        theme = DEFAULT_THEME

    vb_x = -_PADDING
    vb_y = -_PADDING
    vb_w = max(layout.width + 2 * _PADDING, 1.0)
    vb_h = max(layout.height + 2 * _PADDING, 1.0)

    svg = ET.Element("svg")
    svg.set("xmlns", _SVG_NS)
    svg.set("viewBox", f"{vb_x} {vb_y} {_round_coord(vb_w)} {_round_coord(vb_h)}")
    svg.set("width", _round_coord(vb_w))
    svg.set("height", _round_coord(vb_h))
    svg.set("style", f"background-color: {theme.background_color}")

    # Defs
    defs = ET.SubElement(svg, "defs")
    _make_class_defs(defs, edge_stroke=theme.edge_stroke)

    # Style
    style = ET.SubElement(svg, "style")
    style.text = _build_class_diagram_css(theme)

    # Build lookup maps
    class_map = {c.id: c for c in diagram.classes}

    # Build edge layout lookup: (source, target) -> EdgeLayout
    edge_layout_map: dict[tuple[str, str], EdgeLayout] = {}
    for el in layout.edges:
        key = (el.source, el.target)
        if key not in edge_layout_map:
            edge_layout_map[key] = el

    # Render edges first (underneath)
    for rel in diagram.relations:
        el = edge_layout_map.get((rel.source, rel.target))
        if el is None:
            continue
        _render_class_edge(svg, rel, el, theme)

    # Render class nodes
    for class_id, nl in layout.nodes.items():
        class_node = class_map.get(class_id)
        if class_node is None:
            # Auto-created class with no members
            class_node = ClassNode(
                id=class_id, label=class_id,
                annotation=None, members=(),
            )
        _render_class_node(svg, class_node, nl, theme)

    ET.indent(svg)
    return ET.tostring(svg, encoding="unicode", xml_declaration=False)


__all__ = [
    "measure_class_box",
    "render_class_diagram",
]
