"""SVG renderer for sequence diagrams.

Generates standalone SVG from a SequenceDiagram IR and SequenceLayout.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from pymermaid.ir.sequence import MessageType, SequenceDiagram
from pymermaid.layout.sequence import (
    ActivationLayout,
    FragmentLayout,
    MessageLayout,
    NoteLayout,
    ParticipantLayout,
    SequenceLayout,
)
from pymermaid.theme import DEFAULT_THEME, Theme

_SVG_NS = "http://www.w3.org/2000/svg"
_PADDING = 20


def _rc(val: float) -> str:
    """Round a coordinate to at most 2 decimal places."""
    rounded = round(val, 2)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def _build_defs(svg: ET.Element, theme: Theme) -> None:
    """Add marker definitions for sequence diagram arrows."""
    defs = ET.SubElement(svg, "defs")
    stroke = theme.edge_stroke

    # Solid arrowhead (filled triangle).
    m = ET.SubElement(defs, "marker")
    m.set("id", "seq-arrow")
    m.set("markerWidth", "10")
    m.set("markerHeight", "7")
    m.set("refX", "10")
    m.set("refY", "3.5")
    m.set("orient", "auto")
    poly = ET.SubElement(m, "polygon")
    poly.set("points", "0 0, 10 3.5, 0 7")
    poly.set("fill", stroke)

    # Open arrowhead (unfilled, lines only).
    m2 = ET.SubElement(defs, "marker")
    m2.set("id", "seq-arrow-open")
    m2.set("markerWidth", "10")
    m2.set("markerHeight", "7")
    m2.set("refX", "10")
    m2.set("refY", "3.5")
    m2.set("orient", "auto")
    pl = ET.SubElement(m2, "polyline")
    pl.set("points", "0 0, 10 3.5, 0 7")
    pl.set("fill", "none")
    pl.set("stroke", stroke)
    pl.set("stroke-width", "1.5")

    # Cross marker.
    m3 = ET.SubElement(defs, "marker")
    m3.set("id", "seq-cross")
    m3.set("markerWidth", "10")
    m3.set("markerHeight", "10")
    m3.set("refX", "5")
    m3.set("refY", "5")
    m3.set("orient", "auto")
    l1 = ET.SubElement(m3, "line")
    l1.set("x1", "0")
    l1.set("y1", "0")
    l1.set("x2", "10")
    l1.set("y2", "10")
    l1.set("stroke", stroke)
    l1.set("stroke-width", "2")
    l2 = ET.SubElement(m3, "line")
    l2.set("x1", "10")
    l2.set("y1", "0")
    l2.set("x2", "0")
    l2.set("y2", "10")
    l2.set("stroke", stroke)
    l2.set("stroke-width", "2")

    # Async (open arrow, one-sided).
    m4 = ET.SubElement(defs, "marker")
    m4.set("id", "seq-async")
    m4.set("markerWidth", "10")
    m4.set("markerHeight", "7")
    m4.set("refX", "10")
    m4.set("refY", "3.5")
    m4.set("orient", "auto")
    pl2 = ET.SubElement(m4, "polyline")
    pl2.set("points", "0 0, 10 3.5, 0 7")
    pl2.set("fill", "none")
    pl2.set("stroke", stroke)
    pl2.set("stroke-width", "1.5")


def _build_css(theme: Theme) -> str:
    """Build CSS for sequence diagram styling."""
    return (
        f".seq-participant rect {{ fill: {theme.node_fill}; "
        f"stroke: {theme.node_stroke}; stroke-width: {theme.node_stroke_width}; }}\n"
        f".seq-participant text {{ fill: {theme.node_text_color}; "
        f"font-family: {theme.font_family}; font-size: 14px; }}\n"
        f".seq-lifeline {{ stroke: {theme.node_stroke}; "
        f"stroke-width: 1; stroke-dasharray: 5,5; }}\n"
        f".seq-message line, .seq-message path {{ "
        f"stroke: {theme.edge_stroke}; stroke-width: {theme.edge_stroke_width}; }}\n"
        f".seq-message text {{ fill: {theme.text_color}; "
        f"font-family: {theme.font_family}; font-size: 12px; }}\n"
        f".seq-activation {{ fill: {theme.node_fill}; "
        f"stroke: {theme.node_stroke}; stroke-width: 1; }}\n"
        f".seq-note rect {{ fill: #ffffcc; stroke: #aaaa33; stroke-width: 1; }}\n"
        f".seq-note text {{ fill: {theme.text_color}; "
        f"font-family: {theme.font_family}; font-size: 12px; }}\n"
        f".seq-fragment rect {{ fill: none; "
        f"stroke: {theme.node_stroke}; stroke-width: 1; stroke-dasharray: 3,3; }}\n"
        f".seq-fragment text {{ fill: {theme.text_color}; "
        f"font-family: {theme.font_family}; font-size: 11px; font-weight: bold; }}\n"
        f".seq-actor line, .seq-actor circle {{ "
        f"stroke: {theme.node_stroke}; stroke-width: {theme.node_stroke_width}; "
        f"fill: none; }}\n"
        f".seq-actor text {{ fill: {theme.node_text_color}; "
        f"font-family: {theme.font_family}; font-size: 14px; }}\n"
    )


def _render_participant_box(
    parent: ET.Element, pl: ParticipantLayout,
) -> None:
    """Render a participant as a labeled rectangle."""
    g = ET.SubElement(parent, "g")
    g.set("class", "seq-participant")
    g.set("data-participant-id", pl.id)

    rect = ET.SubElement(g, "rect")
    rect.set("x", _rc(pl.box_x))
    rect.set("y", _rc(pl.box_y))
    rect.set("width", _rc(pl.box_w))
    rect.set("height", _rc(pl.box_h))
    rect.set("rx", "5")

    text = ET.SubElement(g, "text")
    text.set("x", _rc(pl.cx))
    text.set("y", _rc(pl.box_y + pl.box_h / 2))
    text.set("text-anchor", "middle")
    text.set("dominant-baseline", "central")
    text.text = pl.label


def _render_actor(parent: ET.Element, pl: ParticipantLayout) -> None:
    """Render a participant as a stick figure actor."""
    g = ET.SubElement(parent, "g")
    g.set("class", "seq-actor")
    g.set("data-participant-id", pl.id)

    cx = pl.cx
    # Stick figure layout within the box area.
    head_r = 10
    head_cy = pl.box_y + head_r + 2
    body_top = head_cy + head_r
    body_bottom = body_top + 15
    arm_y = body_top + 5
    leg_bottom = pl.box_y + pl.box_h - 15

    # Head circle.
    circle = ET.SubElement(g, "circle")
    circle.set("cx", _rc(cx))
    circle.set("cy", _rc(head_cy))
    circle.set("r", _rc(head_r))

    # Body line.
    line = ET.SubElement(g, "line")
    line.set("x1", _rc(cx))
    line.set("y1", _rc(body_top))
    line.set("x2", _rc(cx))
    line.set("y2", _rc(body_bottom))

    # Arms.
    arm = ET.SubElement(g, "line")
    arm.set("x1", _rc(cx - 15))
    arm.set("y1", _rc(arm_y))
    arm.set("x2", _rc(cx + 15))
    arm.set("y2", _rc(arm_y))

    # Left leg.
    ll = ET.SubElement(g, "line")
    ll.set("x1", _rc(cx))
    ll.set("y1", _rc(body_bottom))
    ll.set("x2", _rc(cx - 12))
    ll.set("y2", _rc(leg_bottom))

    # Right leg.
    rl = ET.SubElement(g, "line")
    rl.set("x1", _rc(cx))
    rl.set("y1", _rc(body_bottom))
    rl.set("x2", _rc(cx + 12))
    rl.set("y2", _rc(leg_bottom))

    # Label below figure.
    text = ET.SubElement(g, "text")
    text.set("x", _rc(cx))
    text.set("y", _rc(pl.box_y + pl.box_h - 2))
    text.set("text-anchor", "middle")
    text.set("dominant-baseline", "auto")
    text.text = pl.label


def _render_lifeline(
    parent: ET.Element, pl: ParticipantLayout, bottom_y: float,
) -> None:
    """Render a dashed lifeline from participant box to bottom."""
    line = ET.SubElement(parent, "line")
    line.set("class", "seq-lifeline")
    line.set("x1", _rc(pl.cx))
    line.set("y1", _rc(pl.box_y + pl.box_h))
    line.set("x2", _rc(pl.cx))
    line.set("y2", _rc(bottom_y))


def _get_marker(msg_type_str: str) -> tuple[str, bool]:
    """Return (marker-end url, is_dashed) for a message type."""
    mt = MessageType(msg_type_str)
    match mt:
        case MessageType.SOLID_ARROW:
            return "url(#seq-arrow)", False
        case MessageType.DASHED_ARROW:
            return "url(#seq-arrow)", True
        case MessageType.SOLID_OPEN:
            return "url(#seq-arrow-open)", False
        case MessageType.DASHED_OPEN:
            return "url(#seq-arrow-open)", True
        case MessageType.SOLID_CROSS:
            return "url(#seq-cross)", False
        case MessageType.DASHED_CROSS:
            return "url(#seq-cross)", True
        case MessageType.ASYNC:
            return "url(#seq-async)", False


def _render_message(parent: ET.Element, ml: MessageLayout) -> None:
    """Render a message arrow."""
    g = ET.SubElement(parent, "g")
    g.set("class", "seq-message")

    marker, is_dashed = _get_marker(ml.msg_type)

    if ml.is_self:
        # Self-message: loop arrow.
        sx = ml.sender_x
        offset = 20
        mid_y = ml.y + 15
        path = ET.SubElement(g, "path")
        d = (
            f"M {_rc(sx)} {_rc(ml.y)} "
            f"L {_rc(sx + offset)} {_rc(ml.y)} "
            f"L {_rc(sx + offset)} {_rc(mid_y)} "
            f"L {_rc(sx)} {_rc(mid_y)}"
        )
        path.set("d", d)
        path.set("fill", "none")
        path.set("marker-end", marker)
        if is_dashed:
            path.set("stroke-dasharray", "5,5")
    else:
        line = ET.SubElement(g, "line")
        line.set("x1", _rc(ml.sender_x))
        line.set("y1", _rc(ml.y))
        line.set("x2", _rc(ml.receiver_x))
        line.set("y2", _rc(ml.y))
        line.set("marker-end", marker)
        if is_dashed:
            line.set("stroke-dasharray", "5,5")

    # Message text label.
    if ml.text:
        text = ET.SubElement(g, "text")
        mid_x = (ml.sender_x + ml.receiver_x) / 2
        if ml.is_self:
            mid_x = ml.sender_x + 25
        text.set("x", _rc(mid_x))
        text.set("y", _rc(ml.y - 5))
        text.set("text-anchor", "middle")
        text.text = ml.text


def _render_activation(parent: ET.Element, al: ActivationLayout) -> None:
    """Render an activation rectangle on a lifeline."""
    g = ET.SubElement(parent, "g")
    g.set("class", "seq-activation")

    rect = ET.SubElement(g, "rect")
    x = al.participant_cx - al.width / 2 + al.offset * 3
    rect.set("x", _rc(x))
    rect.set("y", _rc(al.y_start))
    rect.set("width", _rc(al.width))
    rect.set("height", _rc(max(al.y_end - al.y_start, 5)))
    rect.set("rx", "2")


def _render_note(parent: ET.Element, nl: NoteLayout) -> None:
    """Render a note box."""
    g = ET.SubElement(parent, "g")
    g.set("class", "seq-note")

    rect = ET.SubElement(g, "rect")
    rect.set("x", _rc(nl.x))
    rect.set("y", _rc(nl.y))
    rect.set("width", _rc(nl.width))
    rect.set("height", _rc(nl.height))
    rect.set("rx", "3")

    text = ET.SubElement(g, "text")
    text.set("x", _rc(nl.x + nl.width / 2))
    text.set("y", _rc(nl.y + nl.height / 2))
    text.set("text-anchor", "middle")
    text.set("dominant-baseline", "central")
    text.text = nl.text


def _render_fragment(parent: ET.Element, fl: FragmentLayout) -> None:
    """Render a fragment box (loop/alt/opt)."""
    g = ET.SubElement(parent, "g")
    g.set("class", "seq-fragment")

    rect = ET.SubElement(g, "rect")
    rect.set("x", _rc(fl.x))
    rect.set("y", _rc(fl.y))
    rect.set("width", _rc(fl.width))
    rect.set("height", _rc(fl.height))

    # Fragment type label in top-left corner.
    label_bg = ET.SubElement(g, "rect")
    label_text = fl.frag_type.upper()
    lw = len(label_text) * 8 + 10
    label_bg.set("x", _rc(fl.x))
    label_bg.set("y", _rc(fl.y))
    label_bg.set("width", _rc(lw))
    label_bg.set("height", "20")
    label_bg.set("fill", "#e8e8e8")
    label_bg.set("stroke", "none")

    type_text = ET.SubElement(g, "text")
    type_text.set("x", _rc(fl.x + 5))
    type_text.set("y", _rc(fl.y + 14))
    type_text.text = label_text

    # Condition/label text.
    if fl.label:
        cond_text = ET.SubElement(g, "text")
        cond_text.set("x", _rc(fl.x + lw + 5))
        cond_text.set("y", _rc(fl.y + 14))
        cond_text.text = f"[{fl.label}]"

    # Render section dividers (e.g. else lines in alt).
    for section in fl.sections:
        div_line = ET.SubElement(g, "line")
        div_line.set("x1", _rc(fl.x))
        div_line.set("y1", _rc(section.y))
        div_line.set("x2", _rc(fl.x + fl.width))
        div_line.set("y2", _rc(section.y))
        div_line.set("stroke-dasharray", "5,5")

        if section.label:
            sec_text = ET.SubElement(g, "text")
            sec_text.set("x", _rc(fl.x + 10))
            sec_text.set("y", _rc(section.y + 14))
            sec_text.text = f"[{section.label}]"


def render_sequence_svg(
    diagram: SequenceDiagram,
    layout: SequenceLayout,
    theme: Theme | None = None,
) -> str:
    """Render a sequence diagram to a standalone SVG string.

    Args:
        diagram: The SequenceDiagram IR (used for semantic info).
        layout: The computed SequenceLayout with positions.
        theme: Optional theme. Defaults to DEFAULT_THEME.

    Returns:
        SVG string.
    """
    if theme is None:
        theme = DEFAULT_THEME

    vb_x = -_PADDING
    vb_y = -_PADDING
    vb_w = layout.width + 2 * _PADDING
    vb_h = layout.height + 2 * _PADDING
    vb_w = max(vb_w, 1.0)
    vb_h = max(vb_h, 1.0)

    svg = ET.Element("svg")
    svg.set("xmlns", _SVG_NS)
    svg.set("viewBox", f"{vb_x} {vb_y} {_rc(vb_w)} {_rc(vb_h)}")
    svg.set("width", _rc(vb_w))
    svg.set("height", _rc(vb_h))
    svg.set("style", f"background-color: {theme.background_color}")

    _build_defs(svg, theme)

    style = ET.SubElement(svg, "style")
    style.text = _build_css(theme)

    # Render lifelines first (background).
    for pl in layout.participants:
        _render_lifeline(svg, pl, layout.lifeline_bottom)

    # Render fragments (background boxes).
    for fl in layout.fragments:
        _render_fragment(svg, fl)

    # Render activations.
    for al in layout.activations:
        _render_activation(svg, al)

    # Render messages.
    for ml in layout.messages:
        _render_message(svg, ml)

    # Render notes.
    for nl in layout.notes:
        _render_note(svg, nl)

    # Render participants (on top).
    for pl in layout.participants:
        if pl.is_actor:
            _render_actor(svg, pl)
        else:
            _render_participant_box(svg, pl)

    ET.indent(svg)
    return ET.tostring(svg, encoding="unicode", xml_declaration=False)
