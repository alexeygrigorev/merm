"""ER diagram SVG renderer.

Renders ERDiagram IR into SVG, including:
- Entity boxes with header (name) and attribute rows
- Divider line between header and attributes
- Key badges (PK, FK, UK) rendered distinctly
- Relationship lines with cardinality markers at endpoints
- Solid and dashed line styles
- Relationship labels centered on lines
"""

import xml.etree.ElementTree as ET

from pymermaid.ir.erdiag import (
    ERAttribute,
    ERAttributeKey,
    ERCardinality,
    ERDiagram,
    EREntity,
    ERLineStyle,
    ERRelationship,
)
from pymermaid.layout.types import EdgeLayout, LayoutResult, NodeLayout, Point
from pymermaid.render.edges import points_to_path_d
from pymermaid.theme import DEFAULT_THEME, Theme

# SVG namespace
_SVG_NS = "http://www.w3.org/2000/svg"

# Padding around viewBox
_PADDING = 20

# Entity box layout constants
_HEADER_HEIGHT = 30.0
_ATTR_LINE_HEIGHT = 20.0
_BOX_PADDING_H = 10.0
_CHAR_WIDTH = 8.0  # approximate character width at 14px
_FONT_SIZE = 14.0
_SMALL_FONT_SIZE = 12.0
_MIN_BOX_WIDTH = 100.0
_MIN_BOX_HEIGHT = 50.0

# ---------------------------------------------------------------------------
# Entity box size measurement
# ---------------------------------------------------------------------------

def measure_er_entity_box(entity: EREntity) -> tuple[float, float]:
    """Compute (width, height) for an entity box.

    The box has two sections:
    - Header: entity name
    - Attributes list (one row per attribute)
    """
    # Header height
    header_h = _HEADER_HEIGHT

    # Attributes height
    attrs_h = max(len(entity.attributes) * _ATTR_LINE_HEIGHT, _ATTR_LINE_HEIGHT)

    total_h = max(header_h + attrs_h, _MIN_BOX_HEIGHT)

    # Width: max of all text lines
    texts = [entity.id]
    for attr in entity.attributes:
        display = _attr_display(attr)
        texts.append(display)

    max_text_len = max((len(t) for t in texts), default=5)
    total_w = max(max_text_len * _CHAR_WIDTH + 2 * _BOX_PADDING_H, _MIN_BOX_WIDTH)

    return total_w, total_h

def _attr_display(attr: ERAttribute) -> str:
    """Build display string for an attribute."""
    base = f"{attr.type_str} {attr.name}"
    if attr.key != ERAttributeKey.NONE:
        base += f" {attr.key.value}"
    return base

# ---------------------------------------------------------------------------
# Marker definitions for cardinality notation
# ---------------------------------------------------------------------------

def _make_er_defs(
    defs: ET.Element,
    edge_stroke: str = "#333333",
) -> None:
    """Add marker definitions for ER cardinality notation."""
    # Exactly one: perpendicular line (bar)
    _marker_exactly_one(defs, "er-exactly-one", edge_stroke)
    # Zero or one: circle + bar
    _marker_zero_or_one(defs, "er-zero-or-one", edge_stroke)
    # One or more: crow's foot + bar
    _marker_one_or_more(defs, "er-one-or-more", edge_stroke)
    # Zero or more: crow's foot + circle
    _marker_zero_or_more(defs, "er-zero-or-more", edge_stroke)

def _marker_exactly_one(
    parent: ET.Element, marker_id: str, stroke: str,
) -> None:
    """Exactly one: single perpendicular bar."""
    marker = ET.SubElement(parent, "marker")
    marker.set("id", marker_id)
    marker.set("viewBox", "0 0 12 12")
    marker.set("markerWidth", "12")
    marker.set("markerHeight", "12")
    marker.set("refX", "9")
    marker.set("refY", "6")
    marker.set("orient", "auto")
    marker.set("markerUnits", "userSpaceOnUse")
    # Single vertical bar
    line = ET.SubElement(marker, "line")
    line.set("x1", "9")
    line.set("y1", "2")
    line.set("x2", "9")
    line.set("y2", "10")
    line.set("stroke", stroke)
    line.set("stroke-width", "1.5")

def _marker_zero_or_one(
    parent: ET.Element, marker_id: str, stroke: str,
) -> None:
    """Zero or one: circle + perpendicular bar."""
    marker = ET.SubElement(parent, "marker")
    marker.set("id", marker_id)
    marker.set("viewBox", "0 0 18 12")
    marker.set("markerWidth", "18")
    marker.set("markerHeight", "12")
    marker.set("refX", "15")
    marker.set("refY", "6")
    marker.set("orient", "auto")
    marker.set("markerUnits", "userSpaceOnUse")
    # Circle
    circle = ET.SubElement(marker, "circle")
    circle.set("cx", "6")
    circle.set("cy", "6")
    circle.set("r", "4")
    circle.set("fill", "white")
    circle.set("stroke", stroke)
    circle.set("stroke-width", "1.5")
    # Vertical bar
    line = ET.SubElement(marker, "line")
    line.set("x1", "15")
    line.set("y1", "2")
    line.set("x2", "15")
    line.set("y2", "10")
    line.set("stroke", stroke)
    line.set("stroke-width", "1.5")

def _marker_one_or_more(
    parent: ET.Element, marker_id: str, stroke: str,
) -> None:
    """One or more: crow's foot + perpendicular bar."""
    marker = ET.SubElement(parent, "marker")
    marker.set("id", marker_id)
    marker.set("viewBox", "0 0 18 12")
    marker.set("markerWidth", "18")
    marker.set("markerHeight", "12")
    marker.set("refX", "15")
    marker.set("refY", "6")
    marker.set("orient", "auto")
    marker.set("markerUnits", "userSpaceOnUse")
    # Crow's foot (three lines spreading from right to left)
    path = ET.SubElement(marker, "path")
    path.set("d", "M15,6 L3,2 M15,6 L3,10 M15,6 L3,6")
    path.set("fill", "none")
    path.set("stroke", stroke)
    path.set("stroke-width", "1.5")
    # Vertical bar
    line = ET.SubElement(marker, "line")
    line.set("x1", "15")
    line.set("y1", "2")
    line.set("x2", "15")
    line.set("y2", "10")
    line.set("stroke", stroke)
    line.set("stroke-width", "1.5")

def _marker_zero_or_more(
    parent: ET.Element, marker_id: str, stroke: str,
) -> None:
    """Zero or more: crow's foot + circle."""
    marker = ET.SubElement(parent, "marker")
    marker.set("id", marker_id)
    marker.set("viewBox", "0 0 22 12")
    marker.set("markerWidth", "22")
    marker.set("markerHeight", "12")
    marker.set("refX", "19")
    marker.set("refY", "6")
    marker.set("orient", "auto")
    marker.set("markerUnits", "userSpaceOnUse")
    # Crow's foot
    path = ET.SubElement(marker, "path")
    path.set("d", "M19,6 L7,2 M19,6 L7,10 M19,6 L7,6")
    path.set("fill", "none")
    path.set("stroke", stroke)
    path.set("stroke-width", "1.5")
    # Circle
    circle = ET.SubElement(marker, "circle")
    circle.set("cx", "4")
    circle.set("cy", "6")
    circle.set("r", "3")
    circle.set("fill", "white")
    circle.set("stroke", stroke)
    circle.set("stroke-width", "1.5")

# ---------------------------------------------------------------------------
# Cardinality marker mapping
# ---------------------------------------------------------------------------

_CARD_MARKER_MAP: dict[ERCardinality, str] = {
    ERCardinality.EXACTLY_ONE: "url(#er-exactly-one)",
    ERCardinality.ZERO_OR_ONE: "url(#er-zero-or-one)",
    ERCardinality.ONE_OR_MORE: "url(#er-one-or-more)",
    ERCardinality.ZERO_OR_MORE: "url(#er-zero-or-more)",
}

# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _render_er_entity(
    parent: ET.Element,
    entity: EREntity,
    nl: NodeLayout,
    theme: Theme,
) -> None:
    """Render an entity box with header and attributes."""
    g = ET.SubElement(parent, "g")
    g.set("class", "er-entity")
    g.set("data-entity-id", entity.id)

    x, y, w, h = nl.x, nl.y, nl.width, nl.height

    # Outer box
    rect = ET.SubElement(g, "rect")
    rect.set("x", str(round(x, 2)))
    rect.set("y", str(round(y, 2)))
    rect.set("width", str(round(w, 2)))
    rect.set("height", str(round(h, 2)))
    rect.set("fill", theme.node_fill)
    rect.set("stroke", theme.node_stroke)
    rect.set("stroke-width", theme.node_stroke_width)

    # Entity name (header)
    name_el = ET.SubElement(g, "text")
    name_el.set("x", str(round(x + w / 2, 2)))
    name_el.set("y", str(round(y + 20, 2)))
    name_el.set("text-anchor", "middle")
    name_el.set("font-family", theme.font_family)
    name_el.set("font-size", f"{_FONT_SIZE}px")
    name_el.set("font-weight", "bold")
    name_el.set("fill", theme.node_text_color)
    name_el.text = entity.id

    # Divider line after header
    div_y = y + _HEADER_HEIGHT
    line_el = ET.SubElement(g, "line")
    line_el.set("x1", str(round(x, 2)))
    line_el.set("y1", str(round(div_y, 2)))
    line_el.set("x2", str(round(x + w, 2)))
    line_el.set("y2", str(round(div_y, 2)))
    line_el.set("stroke", theme.node_stroke)
    line_el.set("stroke-width", "1")

    # Attributes
    for i, attr in enumerate(entity.attributes):
        attr_y = div_y + (i + 0.5) * _ATTR_LINE_HEIGHT

        # Type and name
        attr_text = f"{attr.type_str} {attr.name}"
        attr_el = ET.SubElement(g, "text")
        attr_el.set("x", str(round(x + _BOX_PADDING_H, 2)))
        attr_el.set("y", str(round(attr_y, 2)))
        attr_el.set("dominant-baseline", "central")
        attr_el.set("font-family", theme.font_family)
        attr_el.set("font-size", f"{_SMALL_FONT_SIZE}px")
        attr_el.set("fill", theme.node_text_color)
        attr_el.text = attr_text

        # Key badge (PK/FK/UK) rendered in bold/italic to be visually distinct
        if attr.key != ERAttributeKey.NONE:
            key_el = ET.SubElement(g, "text")
            key_el.set("x", str(round(x + w - _BOX_PADDING_H, 2)))
            key_el.set("y", str(round(attr_y, 2)))
            key_el.set("text-anchor", "end")
            key_el.set("dominant-baseline", "central")
            key_el.set("font-family", theme.font_family)
            key_el.set("font-size", f"{_SMALL_FONT_SIZE}px")
            key_el.set("font-weight", "bold")
            key_el.set("font-style", "italic")
            key_el.set("fill", theme.node_text_color)
            key_el.text = attr.key.value

def _render_er_relationship(
    parent: ET.Element,
    rel: ERRelationship,
    edge_layout: EdgeLayout,
    theme: Theme,
) -> None:
    """Render an ER relationship edge with cardinality markers."""
    g = ET.SubElement(parent, "g")
    g.set("class", "er-relationship")
    g.set("data-edge-source", rel.source)
    g.set("data-edge-target", rel.target)

    # Path
    path = ET.SubElement(g, "path")
    path.set("d", points_to_path_d(edge_layout.points, smooth=False))
    path.set("fill", "none")
    path.set("stroke", theme.edge_stroke)
    path.set("stroke-width", theme.edge_stroke_width)

    # Dashed line style
    if rel.line_style == ERLineStyle.DASHED:
        path.set("stroke-dasharray", "5,5")

    # Source cardinality marker (at the start of the path)
    source_marker = _CARD_MARKER_MAP.get(rel.source_cardinality)
    if source_marker:
        path.set("marker-start", source_marker)

    # Target cardinality marker (at the end of the path)
    target_marker = _CARD_MARKER_MAP.get(rel.target_cardinality)
    if target_marker:
        path.set("marker-end", target_marker)

    # Label
    if rel.label:
        mid = _midpoint(edge_layout.points)
        label_el = ET.SubElement(g, "text")
        label_el.set("x", str(round(mid.x, 2)))
        label_el.set("y", str(round(mid.y - 8, 2)))
        label_el.set("text-anchor", "middle")
        label_el.set("font-family", theme.font_family)
        label_el.set("font-size", f"{_SMALL_FONT_SIZE}px")
        label_el.set("fill", theme.text_color)
        label_el.text = rel.label

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

def _build_er_diagram_css(theme: Theme) -> str:
    """Build CSS for ER diagram elements."""
    return (
        f".er-entity rect {{ fill: {theme.node_fill}; "
        f"stroke: {theme.node_stroke}; "
        f"stroke-width: {theme.node_stroke_width}; }}\n"
        f".er-entity text {{ fill: {theme.node_text_color}; "
        f"font-family: {theme.font_family}; }}\n"
        f".er-entity line {{ stroke: {theme.node_stroke}; }}\n"
        f".er-relationship path {{ fill: none; "
        f"stroke: {theme.edge_stroke}; "
        f"stroke-width: {theme.edge_stroke_width}; }}\n"
        f".er-relationship text {{ fill: {theme.text_color}; "
        f"font-family: {theme.font_family}; }}\n"
    )

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_er_diagram(
    diagram: ERDiagram,
    layout: LayoutResult,
    theme: Theme | None = None,
) -> str:
    """Render an ERDiagram and LayoutResult to SVG.

    Args:
        diagram: The ER diagram IR.
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
    _make_er_defs(defs, edge_stroke=theme.edge_stroke)

    # Style
    style = ET.SubElement(svg, "style")
    style.text = _build_er_diagram_css(theme)

    # Build lookup maps
    entity_map = {e.id: e for e in diagram.entities}

    # Build edge layout lookup: (source, target) -> EdgeLayout
    edge_layout_map: dict[tuple[str, str], EdgeLayout] = {}
    for el in layout.edges:
        key = (el.source, el.target)
        if key not in edge_layout_map:
            edge_layout_map[key] = el

    # Render edges first (underneath)
    for rel in diagram.relationships:
        el = edge_layout_map.get((rel.source, rel.target))
        if el is None:
            # Try reversed key
            el = edge_layout_map.get((rel.target, rel.source))
            if el is not None:
                el = EdgeLayout(
                    points=list(reversed(el.points)),
                    source=el.target,
                    target=el.source,
                )
        if el is None:
            continue
        _render_er_relationship(svg, rel, el, theme)

    # Render entity nodes
    for entity_id, nl in layout.nodes.items():
        entity = entity_map.get(entity_id)
        if entity is None:
            entity = EREntity(id=entity_id, attributes=())
        _render_er_entity(svg, entity, nl, theme)

    ET.indent(svg)
    return ET.tostring(svg, encoding="unicode", xml_declaration=False)

__all__ = [
    "measure_er_entity_box",
    "render_er_diagram",
]
