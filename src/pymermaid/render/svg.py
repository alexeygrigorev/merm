"""SVG rendering engine core.

Contains the render_svg function and all helper functions for generating
SVG output from a Diagram and LayoutResult, including node rendering,
edge rendering delegation, subgraph rendering, and style/defs generation.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from pymermaid.ir import Diagram, Edge, Node, Subgraph
from pymermaid.layout import EdgeLayout, LayoutResult, NodeLayout, SubgraphLayout
from pymermaid.render.edges import make_edge_defs, render_edge
from pymermaid.render.shapes import get_shape_renderer
from pymermaid.theme import DEFAULT_THEME, Theme

# Default padding around the viewBox so nodes are not clipped at edges.
_PADDING = 20

# SVG namespace.
_SVG_NS = "http://www.w3.org/2000/svg"

# Shape selectors that share default fill/stroke.
_SHAPE_SELECTORS = ".node rect, .node polygon, .node circle, .node path, .node line"

_SUBGRAPH_PADDING = 20.0

# Regex to find float values with more than 2 decimal places in SVG output.
_COORD_RE = re.compile(r"\d+\.\d{3,}")


def _round_coord(val: float) -> str:
    """Format a float coordinate, rounding to at most 2 decimal places."""
    rounded = round(val, 2)
    # Avoid trailing zeros: 10.00 -> "10.0" (keep at least one decimal),
    # but 10.50 -> "10.5"
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def _round_svg_coords(svg_str: str) -> str:
    """Round all float coordinate values in an SVG string to 2 decimal places."""
    def _replacer(m: re.Match[str]) -> str:
        return f"{float(m.group()):.2f}".rstrip("0").rstrip(".")
    return _COORD_RE.sub(_replacer, svg_str)


def _build_style_css(theme: Theme) -> str:
    """Build CSS string from a Theme instance."""
    return (
        f"{_SHAPE_SELECTORS} {{ fill: {theme.node_fill}; "
        f"stroke: {theme.node_stroke}; "
        f"stroke-width: {theme.node_stroke_width}; }}\n"
        f".node text {{ fill: {theme.node_text_color}; "
        f"font-family: {theme.font_family}; "
        f"font-size: {theme.node_font_size}; }}\n"
        f".edge path {{ fill: none; "
        f"stroke: {theme.edge_stroke}; stroke-width: {theme.edge_stroke_width}; }}\n"
        f".edge text {{ fill: {theme.text_color}; "
        f"font-family: {theme.font_family}; "
        f"font-size: {theme.edge_label_font_size}; }}\n"
        f".subgraph rect {{ fill: {theme.subgraph_fill}; "
        f"stroke: {theme.subgraph_stroke}; "
        f"stroke-width: {theme.subgraph_stroke_width}; opacity: 0.5; }}\n"
        f".subgraph text {{ fill: {theme.text_color}; "
        f"font-family: {theme.font_family}; "
        f"font-size: {theme.subgraph_title_font_size}; font-weight: bold; }}\n"
    )


def _build_edge_lookup(diagram: Diagram) -> dict[tuple[str, str], Edge]:
    """Map (source, target) to the first matching IR Edge for label lookup."""
    lookup: dict[tuple[str, str], Edge] = {}
    for e in diagram.edges:
        key = (e.source, e.target)
        if key not in lookup:
            lookup[key] = e
    return lookup


def _build_style_lookup(diagram: Diagram) -> dict[str, dict[str, str]]:
    """Map node id to inline style properties from diagram.styles."""
    lookup: dict[str, dict[str, str]] = {}
    for sd in diagram.styles:
        lookup[sd.target_id] = sd.properties
    return lookup


def _build_classdef_css(diagram: Diagram) -> str:
    """Build CSS rules from diagram.classes (classDef definitions).

    Returns a CSS string with one rule per class name.  The special class
    name ``"default"`` is emitted as ``.node { ... }`` so that it applies
    to all nodes without an explicit class.
    """
    rules: list[str] = []
    for cls_name, props in diagram.classes.items():
        css_body = ";".join(f"{k}:{v}" for k, v in props.items())
        if cls_name == "default":
            rules.append(f".node {{ {css_body}; }}")
        else:
            rules.append(f".{cls_name} {{ {css_body}; }}")
    return "\n".join(rules)


def _make_defs(svg: ET.Element, theme: Theme) -> None:
    """Add a <defs> section with arrow/endpoint marker definitions."""
    defs = ET.SubElement(svg, "defs")
    make_edge_defs(defs, edge_stroke=theme.edge_stroke)


def _make_style(svg: ET.Element, diagram: Diagram, theme: Theme) -> None:
    """Add a <style> element with theme CSS and classDef rules."""
    style = ET.SubElement(svg, "style")
    css = _build_style_css(theme)
    classdef_css = _build_classdef_css(diagram)
    if classdef_css:
        css += classdef_css + "\n"
    style.text = css


def _render_text(
    parent: ET.Element,
    label: str,
    cx: float,
    cy: float,
    theme: Theme,
) -> None:
    """Render a <text> element, handling multi-line labels with <tspan>.

    When the label contains ``fa:fa-<name>`` icon tokens, the text element
    is replaced by a mixed group of ``<text>`` and ``<g>`` (icon path)
    elements positioned inline.
    """
    from pymermaid.icons import has_icons

    if has_icons(label):
        _render_text_with_icons(parent, label, cx, cy, theme)
        return

    parts = label.split("<br/>")
    text_el = ET.SubElement(parent, "text")
    text_el.set("text-anchor", "middle")
    text_el.set("dominant-baseline", "central")
    text_el.set("font-family", theme.font_family)

    if len(parts) == 1:
        text_el.set("x", _round_coord(cx))
        text_el.set("y", _round_coord(cy))
        text_el.text = parts[0]
    else:
        # Multi-line: position first tspan, subsequent ones offset by 1.2em
        line_height = 1.2  # em
        total_height = line_height * (len(parts) - 1)
        start_offset = -total_height / 2.0

        for i, part in enumerate(parts):
            tspan = ET.SubElement(text_el, "tspan")
            tspan.set("x", _round_coord(cx))
            if i == 0:
                tspan.set("dy", f"{start_offset}em")
            else:
                tspan.set("dy", f"{line_height}em")
            tspan.text = part


def _render_text_with_icons(
    parent: ET.Element,
    label: str,
    cx: float,
    cy: float,
    theme: Theme,
) -> None:
    """Render label text with inline Font Awesome icons.

    Parses the label into text and icon segments, measures their widths,
    and positions them centered around *cx*.
    """
    from pymermaid.icons import get_icon_path, parse_label

    # Parse font size from theme (strip "px" suffix)
    font_size_str = theme.node_font_size.replace("px", "")
    try:
        font_size = float(font_size_str)
    except ValueError:
        font_size = 16.0

    segments = parse_label(label)

    # Compute total width of all segments for centering
    total_width = 0.0
    segment_widths: list[float] = []
    for seg in segments:
        if seg.kind == "icon":
            icon_data = get_icon_path(seg.value)
            if icon_data is not None:
                w = font_size + 2.0  # icon width + gap
            else:
                # Unknown icon: render name as text
                w = len(seg.value) * font_size * 0.6
        else:
            w = len(seg.value) * font_size * 0.6
        segment_widths.append(w)
        total_width += w

    # Starting x position (left edge of the first segment)
    x_pos = cx - total_width / 2.0

    text_color = theme.node_text_color

    for seg, sw in zip(segments, segment_widths):
        if seg.kind == "icon":
            icon_data = get_icon_path(seg.value)
            if icon_data is not None:
                path_d, vb_w, vb_h = icon_data
                # Scale icon to font_size, maintaining aspect ratio
                scale = font_size / vb_h
                icon_h = font_size
                # Center icon vertically around cy
                icon_x = x_pos + 1.0  # 1px gap
                icon_y = cy - icon_h / 2.0
                g = ET.SubElement(parent, "g")
                g.set("class", "fa-icon")
                g.set(
                    "transform",
                    f"translate({_round_coord(icon_x)},{_round_coord(icon_y)})"
                    f" scale({_round_coord(scale)})",
                )
                path_el = ET.SubElement(g, "path")
                path_el.set("d", path_d)
                path_el.set("fill", text_color)
            else:
                # Unknown icon: render the name as text fallback
                text_el = ET.SubElement(parent, "text")
                text_el.set("x", _round_coord(x_pos + sw / 2.0))
                text_el.set("y", _round_coord(cy))
                text_el.set("text-anchor", "middle")
                text_el.set("dominant-baseline", "central")
                text_el.set("font-family", theme.font_family)
                text_el.text = seg.value
        else:
            text_val = seg.value
            if text_val:
                text_el = ET.SubElement(parent, "text")
                text_el.set("x", _round_coord(x_pos + sw / 2.0))
                text_el.set("y", _round_coord(cy))
                text_el.set("text-anchor", "middle")
                text_el.set("dominant-baseline", "central")
                text_el.set("font-family", theme.font_family)
                text_el.text = text_val

        x_pos += sw


def _render_node(
    parent: ET.Element,
    ir_node: Node,
    nl: NodeLayout,
    inline_styles: dict[str, dict[str, str]],
    theme: Theme,
) -> None:
    """Render a single node using the appropriate shape renderer."""
    g = ET.SubElement(parent, "g")

    # Build class attribute: always "node", plus any CSS classes from the IR node.
    class_parts = ["node"] + list(ir_node.css_classes)
    g.set("class", " ".join(class_parts))
    g.set("data-node-id", ir_node.id)

    # Get the shape renderer.
    renderer = get_shape_renderer(ir_node.shape)

    # Determine inline style for the shape elements (from diagram.styles).
    node_style = inline_styles.get(ir_node.id)

    # Render shape SVG element strings, then parse and attach to <g>.
    shape_elems_str = renderer.render(
        nl.x, nl.y, nl.width, nl.height, ir_node.label, node_style,
    )
    for elem_str in shape_elems_str:
        shape_el = ET.fromstring(elem_str)
        g.append(shape_el)

    cx = nl.x + nl.width / 2.0
    cy = nl.y + nl.height / 2.0
    _render_text(g, ir_node.label, cx, cy, theme)


def _render_edge_delegate(
    parent: ET.Element,
    el: EdgeLayout,
    ir_edge: Edge | None,
    theme: Theme,
) -> None:
    """Delegate edge rendering to the edges module."""
    render_edge(parent, el, ir_edge, edge_label_bg=theme.edge_label_bg)


def _render_subgraph_recursive(
    parent: ET.Element,
    subgraph: Subgraph,
    subgraph_layouts: dict[str, SubgraphLayout],
    node_layouts: dict[str, NodeLayout],
    theme: Theme,
) -> None:
    """Render a subgraph and its children recursively.

    Outer subgraph <g> is rendered first (correct z-order), then inner children.
    Uses SubgraphLayout from the layout result when available, falling back
    to a simple node-based bbox computation.
    """
    sgl = subgraph_layouts.get(subgraph.id) if subgraph_layouts else None

    # Fallback: compute bbox from node positions if no SubgraphLayout
    if sgl is None:
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
            # Still recurse into children
            for child in subgraph.subgraphs:
                _render_subgraph_recursive(
                    parent, child, subgraph_layouts, node_layouts, theme,
                )
            return
        pad = _SUBGRAPH_PADDING
        sx = min_x - pad
        sy = min_y - pad - 16
        sw = (max_x - min_x) + 2 * pad
        sh = (max_y - min_y) + 2 * pad + 16
    else:
        sx, sy, sw, sh = sgl.x, sgl.y, sgl.width, sgl.height

    g = ET.SubElement(parent, "g")
    g.set("class", "subgraph")
    g.set("data-subgraph-id", subgraph.id)

    rect = ET.SubElement(g, "rect")
    rect.set("x", _round_coord(sx))
    rect.set("y", _round_coord(sy))
    rect.set("width", _round_coord(sw))
    rect.set("height", _round_coord(sh))
    rect.set("rx", _round_coord(theme.node_border_radius))

    title = subgraph.title or subgraph.id
    text_el = ET.SubElement(g, "text")
    text_el.set("x", _round_coord(sx + 8))
    text_el.set("y", _round_coord(sy + 14))
    text_el.set("font-family", theme.font_family)
    text_el.text = title

    # Recurse into child subgraphs (rendered after parent for correct z-order:
    # outer bg first, then inner bg)
    for child in subgraph.subgraphs:
        _render_subgraph_recursive(
            parent, child, subgraph_layouts, node_layouts, theme,
        )


def render_svg(
    diagram: Diagram,
    layout: LayoutResult,
    theme: Theme | None = None,
) -> str:
    """Render a Diagram and its LayoutResult to a standalone SVG string.

    Args:
        diagram: The IR diagram.
        layout: The positioned layout result.
        theme: Optional theme for styling. Defaults to DEFAULT_THEME.

    Returns:
        A string containing valid SVG XML.
    """
    if theme is None:
        theme = DEFAULT_THEME

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
    svg.set("viewBox", f"{vb_x} {vb_y} {_round_coord(vb_w)} {_round_coord(vb_h)}")
    svg.set("width", _round_coord(vb_w))
    svg.set("height", _round_coord(vb_h))
    svg.set("style", f"background-color: {theme.background_color}")

    # Defs and style
    _make_defs(svg, theme)
    _make_style(svg, diagram, theme)

    # Build lookup from IR nodes by id.
    node_map: dict[str, Node] = {n.id: n for n in diagram.nodes}

    # Build inline style lookup from diagram.styles
    inline_styles = _build_style_lookup(diagram)

    # Build edge lookup for labels
    edge_lookup = _build_edge_lookup(diagram)

    # Render subgraphs first (background), recursively
    sg_layouts = layout.subgraphs or {}
    for sg in diagram.subgraphs:
        _render_subgraph_recursive(svg, sg, sg_layouts, layout.nodes, theme)

    # Render edges
    for el in layout.edges:
        ir_edge = edge_lookup.get((el.source, el.target))
        _render_edge_delegate(svg, el, ir_edge, theme)

    # Render nodes (on top of edges)
    for node_id, nl in layout.nodes.items():
        # Get the IR node; fall back to a plain rect node if not in diagram.
        ir_node = node_map.get(node_id, Node(id=node_id, label=node_id))
        _render_node(svg, ir_node, nl, inline_styles, theme)

    # Pretty-print
    ET.indent(svg)

    # Serialize to string
    result = ET.tostring(svg, encoding="unicode", xml_declaration=False)

    # Round any remaining float coordinates with >2 decimal places
    return _round_svg_coords(result)
