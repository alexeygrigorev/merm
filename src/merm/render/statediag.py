"""State diagram SVG renderer.

Converts a StateDiagram + LayoutResult into SVG output, with specialized
rendering for state diagram node types (start/end circles, fork/join bars,
choice diamonds, composite states, notes).
"""

import re
import xml.etree.ElementTree as ET

from merm.ir import Edge
from merm.ir.statediag import (
    State,
    StateDiagram,
    StateNote,
    StateType,
)
from merm.layout.types import (
    EdgeLayout,
    LayoutResult,
    NodeLayout,
)
from merm.render.edges import (
    apply_bidi_offsets,
    make_edge_defs,
    render_edge,
    resolve_label_positions,
)
from merm.theme import DEFAULT_THEME, Theme

_PADDING = 20
_SVG_NS = "http://www.w3.org/2000/svg"

_COORD_RE = re.compile(r"\d+\.\d{3,}")

def _round_coord(val: float) -> str:
    """Format a float coordinate to at most 2 decimal places."""
    rounded = round(val, 2)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")

def _round_svg_coords(svg_str: str) -> str:
    """Round all float coordinate values in SVG string."""
    def _replacer(m: re.Match[str]) -> str:
        return f"{float(m.group()):.2f}".rstrip("0").rstrip(".")
    return _COORD_RE.sub(_replacer, svg_str)

def _build_style_css(theme: Theme) -> str:
    """Build CSS for state diagrams."""
    return (
        f".state rect, .state polygon, .state circle, .state line {{"
        f" fill: {theme.node_fill};"
        f" stroke: {theme.node_stroke};"
        f" stroke-width: {theme.node_stroke_width}; }}\n"
        f".state text {{"
        f" fill: {theme.node_text_color};"
        f" font-family: {theme.font_family};"
        f" font-size: {theme.node_font_size}; }}\n"
        f".edge path {{ fill: none;"
        f" stroke: {theme.edge_stroke};"
        f" stroke-width: {theme.edge_stroke_width}; }}\n"
        f".edge text {{"
        f" fill: {theme.text_color};"
        f" font-family: {theme.font_family};"
        f" font-size: {theme.edge_label_font_size}; }}\n"
        f".composite rect {{"
        f" fill: {theme.subgraph_fill};"
        f" stroke: {theme.subgraph_stroke};"
        f" stroke-width: {theme.subgraph_stroke_width}; opacity: 0.5; }}\n"
        f".composite text {{"
        f" fill: {theme.text_color};"
        f" font-family: {theme.font_family};"
        f" font-size: {theme.subgraph_title_font_size}; font-weight: bold; }}\n"
        f".note rect {{"
        f" fill: #ffa;"
        f" stroke: #aa3;"
        f" stroke-width: 1; }}\n"
        f".note text {{"
        f" fill: {theme.text_color};"
        f" font-family: {theme.font_family};"
        f" font-size: 12px; }}\n"
    )

def _render_start_state(
    parent: ET.Element, nl: NodeLayout,
) -> None:
    """Render a start state as a filled black circle."""
    g = ET.SubElement(parent, "g")
    g.set("class", "state start")
    cx = nl.x + nl.width / 2
    cy = nl.y + nl.height / 2
    r = min(nl.width, nl.height) / 2
    circle = ET.SubElement(g, "circle")
    circle.set("cx", _round_coord(cx))
    circle.set("cy", _round_coord(cy))
    circle.set("r", _round_coord(r))
    circle.set("fill", "black")
    circle.set("stroke", "black")

def _render_end_state(
    parent: ET.Element, nl: NodeLayout,
) -> None:
    """Render an end state as a bull's eye (circle in circle)."""
    g = ET.SubElement(parent, "g")
    g.set("class", "state end")
    cx = nl.x + nl.width / 2
    cy = nl.y + nl.height / 2
    r_outer = min(nl.width, nl.height) / 2
    r_inner = r_outer * 0.6
    outer = ET.SubElement(g, "circle")
    outer.set("cx", _round_coord(cx))
    outer.set("cy", _round_coord(cy))
    outer.set("r", _round_coord(r_outer))
    outer.set("fill", "none")
    outer.set("stroke", "black")
    outer.set("stroke-width", "2")
    inner = ET.SubElement(g, "circle")
    inner.set("cx", _round_coord(cx))
    inner.set("cy", _round_coord(cy))
    inner.set("r", _round_coord(r_inner))
    inner.set("fill", "black")
    inner.set("stroke", "black")

def _render_fork_join_state(
    parent: ET.Element, nl: NodeLayout,
) -> None:
    """Render a fork/join state as a horizontal black bar."""
    g = ET.SubElement(parent, "g")
    g.set("class", "state fork-join")
    rect = ET.SubElement(g, "rect")
    rect.set("x", _round_coord(nl.x))
    rect.set("y", _round_coord(nl.y))
    rect.set("width", _round_coord(nl.width))
    rect.set("height", _round_coord(nl.height))
    rect.set("rx", "3")
    rect.set("fill", "black")
    rect.set("stroke", "black")

def _render_choice_state(
    parent: ET.Element, nl: NodeLayout,
) -> None:
    """Render a choice state as a diamond."""
    g = ET.SubElement(parent, "g")
    g.set("class", "state choice")
    cx = nl.x + nl.width / 2
    cy = nl.y + nl.height / 2
    points = (
        f"{_round_coord(cx)},{_round_coord(nl.y)} "
        f"{_round_coord(nl.x + nl.width)},{_round_coord(cy)} "
        f"{_round_coord(cx)},{_round_coord(nl.y + nl.height)} "
        f"{_round_coord(nl.x)},{_round_coord(cy)}"
    )
    polygon = ET.SubElement(g, "polygon")
    polygon.set("points", points)

def _render_normal_state(
    parent: ET.Element, state: State, nl: NodeLayout, theme: Theme,
) -> None:
    """Render a normal state as a rounded rectangle with label."""
    g = ET.SubElement(parent, "g")
    g.set("class", "state")
    g.set("data-state-id", state.id)
    rect = ET.SubElement(g, "rect")
    rect.set("x", _round_coord(nl.x))
    rect.set("y", _round_coord(nl.y))
    rect.set("width", _round_coord(nl.width))
    rect.set("height", _round_coord(nl.height))
    rect.set("rx", "10")
    rect.set("ry", "10")

    # Label text
    cx = nl.x + nl.width / 2
    cy = nl.y + nl.height / 2
    text_el = ET.SubElement(g, "text")
    text_el.set("x", _round_coord(cx))
    text_el.set("y", _round_coord(cy))
    text_el.set("text-anchor", "middle")
    text_el.set("dominant-baseline", "central")
    text_el.set("font-family", theme.font_family)
    text_el.text = state.label

def _render_composite_state(
    parent: ET.Element,
    state: State,
    nl: NodeLayout,
    child_layouts: dict[str, NodeLayout],
    theme: Theme,
) -> None:
    """Render a composite state (state with children) as a container box."""
    g = ET.SubElement(parent, "g")
    g.set("class", "composite")
    g.set("data-state-id", state.id)
    rect = ET.SubElement(g, "rect")
    rect.set("x", _round_coord(nl.x))
    rect.set("y", _round_coord(nl.y))
    rect.set("width", _round_coord(nl.width))
    rect.set("height", _round_coord(nl.height))
    rect.set("rx", "10")
    rect.set("ry", "10")

    # Title label at top of composite state
    text_el = ET.SubElement(g, "text")
    text_el.set("x", _round_coord(nl.x + 10))
    text_el.set("y", _round_coord(nl.y + 18))
    text_el.set("font-family", theme.font_family)
    text_el.text = state.label


def _render_state_node(
    parent: ET.Element,
    state: State,
    nl: NodeLayout,
    child_layouts: dict[str, NodeLayout],
    theme: Theme,
) -> None:
    """Render a single state node based on its type."""
    match state.state_type:
        case StateType.START:
            _render_start_state(parent, nl)
        case StateType.END:
            _render_end_state(parent, nl)
        case StateType.FORK | StateType.JOIN:
            _render_fork_join_state(parent, nl)
        case StateType.CHOICE:
            _render_choice_state(parent, nl)
        case StateType.NORMAL:
            if state.children:
                _render_composite_state(
                    parent, state, nl, child_layouts, theme,
                )
            else:
                _render_normal_state(parent, state, nl, theme)

def _render_note(
    parent: ET.Element,
    note: StateNote,
    node_layouts: dict[str, NodeLayout],
    theme: Theme,
) -> None:
    """Render a note as a yellow box positioned beside a state."""
    nl = node_layouts.get(note.state_id)
    if nl is None:
        return

    note_w = max(len(note.text) * 8, 60)
    note_h = 30
    gap = 15

    if note.position == "left":
        nx = nl.x - note_w - gap
    else:
        nx = nl.x + nl.width + gap
    ny = nl.y + (nl.height - note_h) / 2

    g = ET.SubElement(parent, "g")
    g.set("class", "note")

    rect = ET.SubElement(g, "rect")
    rect.set("x", _round_coord(nx))
    rect.set("y", _round_coord(ny))
    rect.set("width", _round_coord(note_w))
    rect.set("height", _round_coord(note_h))
    rect.set("rx", "3")

    text_el = ET.SubElement(g, "text")
    text_el.set("x", _round_coord(nx + note_w / 2))
    text_el.set("y", _round_coord(ny + note_h / 2))
    text_el.set("text-anchor", "middle")
    text_el.set("dominant-baseline", "central")
    text_el.set("font-family", theme.font_family)
    text_el.text = note.text

def render_state_svg(
    diagram: StateDiagram,
    layout: LayoutResult,
    theme: Theme | None = None,
) -> str:
    """Render a StateDiagram and its LayoutResult to SVG.

    Args:
        diagram: The state diagram IR.
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
    svg.set(
        "viewBox",
        f"{vb_x} {vb_y} {_round_coord(vb_w)} {_round_coord(vb_h)}",
    )
    svg.set("width", _round_coord(vb_w))
    svg.set("height", _round_coord(vb_h))
    svg.set("style", f"background-color: {theme.background_color}")

    # Defs (arrow markers)
    defs = ET.SubElement(svg, "defs")
    make_edge_defs(defs, edge_stroke=theme.edge_stroke)

    # Style
    style = ET.SubElement(svg, "style")
    style.text = _build_style_css(theme)

    # Build state map
    state_map: dict[str, State] = {}
    for s in diagram.states:
        state_map[s.id] = s
        for child in s.children:
            state_map[child.id] = child

    # Build set of composite child IDs to avoid double-rendering
    composite_child_ids: set[str] = set()
    for state in diagram.states:
        if state.children:
            for child in state.children:
                composite_child_ids.add(child.id)

    # Render composite state backgrounds first (subgraphs)
    sg_layouts = layout.subgraphs or {}
    for state in diagram.states:
        if state.children:
            sgl = sg_layouts.get(state.id)
            if sgl:
                nl = NodeLayout(
                    x=sgl.x, y=sgl.y,
                    width=sgl.width, height=sgl.height,
                )
                # Render just the composite box (not children here)
                g = ET.SubElement(svg, "g")
                g.set("class", "composite")
                g.set("data-state-id", state.id)
                rect = ET.SubElement(g, "rect")
                rect.set("x", _round_coord(nl.x))
                rect.set("y", _round_coord(nl.y))
                rect.set("width", _round_coord(nl.width))
                rect.set("height", _round_coord(nl.height))
                rect.set("rx", "10")
                rect.set("ry", "10")
                text_el = ET.SubElement(g, "text")
                text_el.set("x", _round_coord(nl.x + 10))
                text_el.set("y", _round_coord(nl.y + 16))
                text_el.set("font-family", theme.font_family)
                text_el.text = state.label

    # Build transition label map for edge rendering
    label_map: dict[tuple[str, str], str] = {}
    for t in diagram.transitions:
        if t.label:
            label_map[(t.source, t.target)] = t.label

    # Apply perpendicular offsets to bidirectional edges.
    offset_edges = apply_bidi_offsets(layout.edges)

    # Resolve label positions to avoid overlapping labels.
    labeled_state_edges: list[tuple[EdgeLayout, Edge]] = []
    for el in offset_edges:
        label = label_map.get((el.source, el.target))
        if label:
            labeled_state_edges.append((
                el,
                Edge(source=el.source, target=el.target, label=label),
            ))
    state_label_positions = resolve_label_positions(labeled_state_edges)

    # Render edges with labels inline
    for el in offset_edges:
        label = label_map.get((el.source, el.target))
        # Create a minimal Edge IR to carry the label
        ir_edge = Edge(
            source=el.source,
            target=el.target,
            label=label,
        ) if label else None
        lpos = state_label_positions.get((el.source, el.target))
        render_edge(
            svg, el, ir_edge, edge_label_bg=theme.edge_label_bg,
            label_pos=lpos,
        )

    # Render state nodes
    for node_id, nl in layout.nodes.items():
        state = state_map.get(node_id)
        if state is None:
            # Auto-created state (e.g. start/end pseudo-states)
            state = State(id=node_id, label=node_id)
        if state.children:
            # Composite rendered as subgraph background above
            continue
        _render_state_node(svg, state, nl, layout.nodes, theme)

    # Render notes
    for note in diagram.notes:
        _render_note(svg, note, layout.nodes, theme)

    ET.indent(svg)
    result = ET.tostring(svg, encoding="unicode", xml_declaration=False)
    return _round_svg_coords(result)

__all__ = ["render_state_svg"]
