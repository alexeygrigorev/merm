"""Tests for text rendering fixes (empty nodes, text overlap, viewBox clipping).

Covers three related issues:
1. Multi-line/wrapped text positioned at wrong coordinates (empty nodes)
2. Text wrapping line overlap (lines too close together)
3. Text clipped outside viewBox for top-of-diagram nodes
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from pymermaid import render_diagram


def _parse_svg(svg_str: str) -> ET.Element:
    """Parse SVG string, stripping namespace for easier querying."""
    # Remove namespace for simpler xpath
    svg_str = svg_str.replace(' xmlns="http://www.w3.org/2000/svg"', "")
    return ET.fromstring(svg_str)


def _get_viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    """Extract viewBox as (x, y, width, height)."""
    vb = root.get("viewBox", "0 0 0 0")
    parts = vb.split()
    return tuple(float(p) for p in parts)


def _get_node_groups(root: ET.Element) -> list[ET.Element]:
    """Find all node <g> elements."""
    return [g for g in root.iter("g") if "node" in (g.get("class") or "")]


def _get_text_bounds(g: ET.Element) -> tuple[float, float] | None:
    """Get the approximate y-center of text content in a node group.

    Returns (min_y, max_y) of text elements/tspans, or None if no text found.
    """
    ys: list[float] = []
    for text_el in g.iter("text"):
        y_str = text_el.get("y")
        if y_str:
            ys.append(float(y_str))
        for tspan in text_el.iter("tspan"):
            ty = tspan.get("y")
            if ty:
                ys.append(float(ty))
    if not ys:
        return None
    return (min(ys), max(ys))


def _get_node_rect_bounds(
    g: ET.Element,
) -> tuple[float, float, float, float] | None:
    """Get (x, y, width, height) of the first rect/polygon/circle in a node group."""
    for rect in g.iter("rect"):
        x = float(rect.get("x", 0))
        y = float(rect.get("y", 0))
        w = float(rect.get("width", 0))
        h = float(rect.get("height", 0))
        return (x, y, w, h)
    return None


class TestMultilineTextPositioning:
    """Verify that multi-line text is positioned inside its node, not at (0,0)."""

    def test_registration_all_nodes_have_text_inside(self):
        """All 14 nodes in registration.mmd should have text inside their bounds."""
        source = """\
flowchart TD
    Start([User clicks Register]) --> Form[Display registration form]
    Form --> Submit[User submits form]
    Submit --> ValidateEmail{Email valid?}
    ValidateEmail -->|No| EmailError[Show email error]
    EmailError --> Form
    ValidateEmail -->|Yes| CheckExists{User exists?}
    CheckExists -->|Yes| ExistsError[Show already registered]
    ExistsError --> Form
    CheckExists -->|No| ValidatePassword{Password strong?}
    ValidatePassword -->|No| PasswordError[Show password requirements]
    PasswordError --> Form
    ValidatePassword -->|Yes| CreateUser[(Save to database)]
    CreateUser --> SendEmail[/Send verification email/]
    SendEmail --> Success([Show success message])
"""
        svg = render_diagram(source)
        root = _parse_svg(svg)
        nodes = _get_node_groups(root)

        # Should have 12 unique nodes (Form is referenced multiple times
        # but only defined once)
        assert len(nodes) == 12

        for g in nodes:
            node_id = g.get("data-node-id", "unknown")
            text_bounds = _get_text_bounds(g)
            assert text_bounds is not None, f"Node {node_id} has no text"

            shape_bounds = _get_node_rect_bounds(g)
            if shape_bounds is not None:
                sx, sy, sw, sh = shape_bounds
                text_min_y, text_max_y = text_bounds
                text_cy = (text_min_y + text_max_y) / 2.0

                # Text center should be within the shape bounds (with tolerance)
                assert sy - 10 <= text_cy <= sy + sh + 10, (
                    f"Node {node_id}: text center y={text_cy:.1f} "
                    f"outside shape bounds y=[{sy:.1f}, {sy + sh:.1f}]"
                )

    def test_multiline_text_uses_absolute_y(self):
        """Multi-line tspan elements should have absolute y attributes."""
        source = (
            "graph TD\n"
            '    A["First line<br/>Second line"]'
            ' --> B["One<br/>Two<br/>Three"]'
        )
        svg = render_diagram(source)
        root = _parse_svg(svg)
        nodes = _get_node_groups(root)

        for g in nodes:
            for text_el in g.iter("text"):
                tspans = list(text_el.iter("tspan"))
                if tspans:
                    # Each tspan should have an absolute y attribute
                    for tspan in tspans:
                        assert tspan.get("y") is not None, (
                            f"tspan in node {g.get('data-node-id')} "
                            "missing absolute y attribute"
                        )


class TestTextWrappingNoOverlap:
    """Verify that wrapped text lines don't overlap."""

    def test_long_text_lines_dont_overlap(self):
        """Long text that wraps should have distinct, non-overlapping y positions."""
        source = (
            'graph TD\n'
            '    A["This is a very long label that should be handled '
            'correctly by the renderer"] --> B["Another quite lengthy '
            'label with multiple words"]'
        )
        svg = render_diagram(source)
        root = _parse_svg(svg)
        nodes = _get_node_groups(root)

        for g in nodes:
            node_id = g.get("data-node-id", "unknown")
            for text_el in g.iter("text"):
                tspans = list(text_el.iter("tspan"))
                if len(tspans) > 1:
                    y_values = []
                    for ts in tspans:
                        y_str = ts.get("y")
                        if y_str:
                            y_values.append(float(y_str))

                    # Each subsequent line should be further down
                    for i in range(1, len(y_values)):
                        gap = y_values[i] - y_values[i - 1]
                        assert gap >= 10.0, (
                            f"Node {node_id}: line spacing {gap:.1f}px "
                            f"too small between lines {i - 1} and {i}"
                        )

    def test_both_wrapped_nodes_have_visible_text(self):
        """Both nodes in long_text.mmd should contain text elements."""
        source = (
            'graph TD\n'
            '    A["This is a very long label that should be handled '
            'correctly by the renderer"] --> B["Another quite lengthy '
            'label with multiple words"]'
        )
        svg = render_diagram(source)
        root = _parse_svg(svg)
        nodes = _get_node_groups(root)

        assert len(nodes) == 2
        for g in nodes:
            node_id = g.get("data-node-id", "unknown")
            text_bounds = _get_text_bounds(g)
            assert text_bounds is not None, (
                f"Node {node_id} has no visible text"
            )


class TestViewBoxContainsAllText:
    """Verify that the SVG viewBox encompasses all text content."""

    def test_coffee_machine_text_not_clipped(self):
        """All text in coffee_machine.mmd should be within the viewBox."""
        source = """\
flowchart TD
   A(Coffee machine not working) --> B{Machine has power?}
   B -->|No| H(Plug in and turn on)
   B -->|Yes| C{Out of beans or water?}
   C -->|Yes| G(Refill beans and water)
   C -->|No| D{Filter warning?}
   D -->|Yes| I(Replace or clean filter)
   D -->|No| F(Send for repair)
"""
        svg = render_diagram(source)
        root = _parse_svg(svg)
        vb_x, vb_y, vb_w, vb_h = _get_viewbox(root)
        vb_bottom = vb_y + vb_h

        nodes = _get_node_groups(root)
        for g in nodes:
            node_id = g.get("data-node-id", "unknown")
            text_bounds = _get_text_bounds(g)
            if text_bounds is not None:
                text_min_y, text_max_y = text_bounds
                assert text_min_y >= vb_y - 5, (
                    f"Node {node_id}: text y={text_min_y:.1f} "
                    f"above viewBox top {vb_y:.1f}"
                )
                assert text_max_y <= vb_bottom + 5, (
                    f"Node {node_id}: text y={text_max_y:.1f} "
                    f"below viewBox bottom {vb_bottom:.1f}"
                )

    def test_multiline_text_vertically_spaced(self):
        """Multiline labels should have proper vertical spacing."""
        source = (
            "graph TD\n"
            '    A["First line<br/>Second line"]'
            ' --> B["One<br/>Two<br/>Three"]'
        )
        svg = render_diagram(source)
        root = _parse_svg(svg)
        nodes = _get_node_groups(root)

        # Node B has 3 lines - verify they're all spaced apart
        node_b = [g for g in nodes if g.get("data-node-id") == "B"]
        assert len(node_b) == 1

        for text_el in node_b[0].iter("text"):
            tspans = list(text_el.iter("tspan"))
            if len(tspans) >= 3:
                y_vals = [float(ts.get("y", "0")) for ts in tspans]
                # Lines should be monotonically increasing
                for i in range(1, len(y_vals)):
                    assert y_vals[i] > y_vals[i - 1], (
                        f"Line {i} y={y_vals[i]:.1f} not below "
                        f"line {i - 1} y={y_vals[i - 1]:.1f}"
                    )


class TestLineHeightConsistency:
    """Verify that text measurement and rendering use consistent line heights."""

    def test_node_height_accommodates_wrapped_text(self):
        """Nodes with wrapped text should be tall enough for all lines."""
        source = (
            'graph TD\n'
            '    A["This is a very long label that should be handled '
            'correctly by the renderer"]'
        )
        svg = render_diagram(source)
        root = _parse_svg(svg)
        nodes = _get_node_groups(root)

        assert len(nodes) == 1
        g = nodes[0]

        shape_bounds = _get_node_rect_bounds(g)
        assert shape_bounds is not None
        sx, sy, sw, sh = shape_bounds

        text_bounds = _get_text_bounds(g)
        assert text_bounds is not None
        text_min_y, text_max_y = text_bounds

        # All text lines should be within the shape bounds (with small tolerance
        # for the text baseline extending slightly beyond)
        assert text_min_y >= sy - 5, (
            f"Text top {text_min_y:.1f} above shape top {sy:.1f}"
        )
        assert text_max_y <= sy + sh + 5, (
            f"Text bottom {text_max_y:.1f} below shape bottom {sy + sh:.1f}"
        )
