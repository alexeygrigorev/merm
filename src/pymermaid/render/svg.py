"""SVG rendering engine core.

Contains the render_svg function and all helper functions for generating
SVG output from a Diagram and LayoutResult, including node rendering,
edge rendering delegation, subgraph rendering, and style/defs generation.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from pymermaid.ir import Diagram, Edge, Node, Subgraph
from pymermaid.layout import EdgeLayout, LayoutResult, NodeLayout, SubgraphLayout
from pymermaid.render.edges import make_edge_defs, render_edge
from pymermaid.render.shapes import get_shape_renderer

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

# Shape selectors that share default fill/stroke.
_SHAPE_SELECTORS = ".node rect, .node polygon, .node circle, .node path, .node line"

# Default CSS embedded in <style>.
_DEFAULT_STYLE = (
    f"{_SHAPE_SELECTORS} {{ fill: {_NODE_FILL}; "
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


def _make_defs(svg: ET.Element) -> None:
    """Add a <defs> section with arrow/endpoint marker definitions."""
    defs = ET.SubElement(svg, "defs")
    make_edge_defs(defs)


def _make_style(svg: ET.Element, diagram: Diagram) -> None:
    """Add a <style> element with default theme CSS and classDef rules."""
    style = ET.SubElement(svg, "style")
    css = _DEFAULT_STYLE
    classdef_css = _build_classdef_css(diagram)
    if classdef_css:
        css += classdef_css + "\n"
    style.text = css


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
    ir_node: Node,
    nl: NodeLayout,
    inline_styles: dict[str, dict[str, str]],
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
    _render_text(g, ir_node.label, cx, cy)


def _render_edge_delegate(
    parent: ET.Element,
    el: EdgeLayout,
    ir_edge: Edge | None,
) -> None:
    """Delegate edge rendering to the edges module."""
    render_edge(parent, el, ir_edge)


def _render_subgraph_recursive(
    parent: ET.Element,
    subgraph: Subgraph,
    subgraph_layouts: dict[str, SubgraphLayout],
    node_layouts: dict[str, NodeLayout],
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
                    parent, child, subgraph_layouts, node_layouts,
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

    # Recurse into child subgraphs (rendered after parent for correct z-order:
    # outer bg first, then inner bg)
    for child in subgraph.subgraphs:
        _render_subgraph_recursive(
            parent, child, subgraph_layouts, node_layouts,
        )


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
    _make_style(svg, diagram)

    # Build lookup from IR nodes by id.
    node_map: dict[str, Node] = {n.id: n for n in diagram.nodes}

    # Build inline style lookup from diagram.styles
    inline_styles = _build_style_lookup(diagram)

    # Build edge lookup for labels
    edge_lookup = _build_edge_lookup(diagram)

    # Render subgraphs first (background), recursively
    sg_layouts = layout.subgraphs or {}
    for sg in diagram.subgraphs:
        _render_subgraph_recursive(svg, sg, sg_layouts, layout.nodes)

    # Render edges
    for el in layout.edges:
        ir_edge = edge_lookup.get((el.source, el.target))
        _render_edge_delegate(svg, el, ir_edge)

    # Render nodes (on top of edges)
    for node_id, nl in layout.nodes.items():
        # Get the IR node; fall back to a plain rect node if not in diagram.
        ir_node = node_map.get(node_id, Node(id=node_id, label=node_id))
        _render_node(svg, ir_node, nl, inline_styles)

    # Pretty-print
    ET.indent(svg)

    # Serialize to string
    return ET.tostring(svg, encoding="unicode", xml_declaration=False)
