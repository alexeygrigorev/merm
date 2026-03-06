"""Tests for self-loop shape, stroke width, and arrowhead placement (Task 38)."""

import xml.etree.ElementTree as ET

from merm import render_diagram
from merm.layout import layout_diagram
from merm.measure import measure_text
from merm.parser.flowchart import parse_flowchart

_SVG_NS = "http://www.w3.org/2000/svg"

def _parse_svg(svg_str: str) -> ET.Element:
    return ET.fromstring(svg_str)

def _find_edge_groups(root: ET.Element) -> list[ET.Element]:
    """Find all <g class='edge'> elements."""
    groups = []
    for g in root.iter(f"{{{_SVG_NS}}}g"):
        if g.get("class") == "edge":
            groups.append(g)
    # Also check without namespace (in case SVG doesn't use namespace prefix)
    if not groups:
        for g in root.iter("g"):
            if g.get("class") == "edge":
                groups.append(g)
    return groups

def _find_self_loop_group(root: ET.Element) -> ET.Element | None:
    """Find the edge group where source == target."""
    for g in _find_edge_groups(root):
        if g.get("data-edge-source") == g.get("data-edge-target"):
            return g
    return None

def _find_self_loop_path(root: ET.Element) -> ET.Element | None:
    """Find the <path> element for the self-loop edge."""
    g = _find_self_loop_group(root)
    if g is None:
        return None
    for path in g.iter(f"{{{_SVG_NS}}}path"):
        return path
    for path in g.iter("path"):
        return path
    return None

# ---------------------------------------------------------------------------
# Unit: Loop geometry (layout points)
# ---------------------------------------------------------------------------

class TestSelfLoopGeometry:
    """Test that the self-loop layout points satisfy acceptance criteria."""

    def _get_layout(self, source: str):
        diagram = parse_flowchart(source)
        return layout_diagram(diagram, measure_text), diagram

    def test_self_loop_source_target_match(self):
        layout, _ = self._get_layout("graph TD\n    A --> A")
        self_loops = [e for e in layout.edges if e.source == e.target]
        assert len(self_loops) == 1
        assert self_loops[0].source == "A"
        assert self_loops[0].target == "A"

    def test_start_point_at_bottom_edge(self):
        """p0.y should equal node center y + node height / 2 (bottom edge)."""
        layout, _ = self._get_layout("graph TD\n    A --> A")
        nl = layout.nodes["A"]
        cy = nl.y + nl.height / 2
        bot = cy + nl.height / 2

        edge = [e for e in layout.edges if e.source == e.target][0]
        p0 = edge.points[0]
        assert abs(p0.y - bot) < 0.01, f"p0.y={p0.y} should be bot={bot}"

    def test_end_point_at_bottom_edge(self):
        """p12.y should equal node center y + node height / 2 (bottom edge),
        NOT the top edge.  The arrowhead must re-enter from below."""
        layout, _ = self._get_layout("graph TD\n    A --> A")
        nl = layout.nodes["A"]
        cy = nl.y + nl.height / 2
        bot = cy + nl.height / 2
        top = cy - nl.height / 2

        edge = [e for e in layout.edges if e.source == e.target][0]
        p12 = edge.points[12]
        assert abs(p12.y - bot) < 0.01, (
            f"p12.y={p12.y} should be bot={bot}, not top={top}"
        )

    def test_horizontal_spread_ge_80pct_node_width(self):
        """The max x spread of loop points should be >= 80% of node width."""
        layout, _ = self._get_layout("graph TD\n    A --> A")
        nl = layout.nodes["A"]

        edge = [e for e in layout.edges if e.source == e.target][0]
        xs = [p.x for p in edge.points]
        spread = max(xs) - min(xs)
        threshold = 0.8 * nl.width
        assert spread >= threshold, (
            f"spread={spread:.2f} should be >= 0.8 * {nl.width:.2f} = {threshold:.2f}"
        )

    def test_bottom_apex_in_range(self):
        """The bottom apex (p6) y should be between bot + 1.5*h and bot + 2.5*h."""
        layout, _ = self._get_layout("graph TD\n    A --> A")
        nl = layout.nodes["A"]
        cy = nl.y + nl.height / 2
        bot = cy + nl.height / 2
        h = nl.height

        edge = [e for e in layout.edges if e.source == e.target][0]
        p6 = edge.points[6]
        low = bot + 1.5 * h
        high = bot + 2.5 * h
        assert low <= p6.y <= high, (
            f"apex y={p6.y:.2f} should be in [{low:.2f}, {high:.2f}]"
        )

    def test_no_point_above_node_top(self):
        """No self-loop control point should have y < node top."""
        layout, _ = self._get_layout("graph TD\n    A --> A")
        nl = layout.nodes["A"]
        top = nl.y  # NodeLayout.y is top-left corner

        edge = [e for e in layout.edges if e.source == e.target][0]
        min_y = min(p.y for p in edge.points)
        assert min_y >= top, (
            f"min_y={min_y:.2f} should be >= node top={top:.2f}"
        )

    def test_13_points(self):
        """Self-loop should have exactly 13 points."""
        layout, _ = self._get_layout("graph TD\n    A --> A")
        edge = [e for e in layout.edges if e.source == e.target][0]
        assert len(edge.points) == 13

# ---------------------------------------------------------------------------
# Unit: Stroke width in SVG
# ---------------------------------------------------------------------------

class TestSelfLoopStrokeWidth:
    """Test that self-loop stroke-width is correct."""

    def test_stroke_width_is_1(self):
        """The self-loop path should have stroke-width='2'."""
        svg = render_diagram("graph TD\n    A --> A")
        root = _parse_svg(svg)
        path = _find_self_loop_path(root)
        assert path is not None, "Self-loop path not found"
        assert path.get("stroke-width") == "2"

    def test_stroke_width_matches_normal_edge(self):
        """Self-loop and normal edge should have the same stroke-width."""
        svg = render_diagram("graph TD\n    A --> A\n    A --> B")
        root = _parse_svg(svg)

        edge_groups = _find_edge_groups(root)
        stroke_widths = set()
        for g in edge_groups:
            for path in g.iter(f"{{{_SVG_NS}}}path"):
                sw = path.get("stroke-width")
                if sw:
                    stroke_widths.add(sw)
                break
            else:
                for path in g.iter("path"):
                    sw = path.get("stroke-width")
                    if sw:
                        stroke_widths.add(sw)
                    break

        assert len(stroke_widths) == 1, (
            f"Expected uniform stroke-width, got: {stroke_widths}"
        )
        assert "2" in stroke_widths

# ---------------------------------------------------------------------------
# Unit: Arrowhead marker on self-loop
# ---------------------------------------------------------------------------

class TestSelfLoopArrowhead:
    """Test that the self-loop path has a marker-end (arrowhead)."""

    def test_marker_end_present(self):
        svg = render_diagram("graph TD\n    A --> A")
        root = _parse_svg(svg)
        path = _find_self_loop_path(root)
        assert path is not None
        marker = path.get("marker-end")
        assert marker is not None, "Self-loop path should have marker-end"
        assert "arrow" in marker

# ---------------------------------------------------------------------------
# Unit: Self-loop with label
# ---------------------------------------------------------------------------

class TestSelfLoopLabel:
    """Test self-loop edge label rendering."""

    def test_label_text_present(self):
        svg = render_diagram("graph TD\n    A -->|loop text| A")
        root = _parse_svg(svg)
        g = _find_self_loop_group(root)
        assert g is not None

        # Find text element with "loop text"
        found = False
        for text_el in g.iter(f"{{{_SVG_NS}}}text"):
            if text_el.text and "loop text" in text_el.text:
                found = True
                break
        if not found:
            for text_el in g.iter("text"):
                if text_el.text and "loop text" in text_el.text:
                    found = True
                    break
        assert found, "Label 'loop text' not found in self-loop SVG"

    def test_label_below_node(self):
        """The label y-coordinate should be below the node bottom edge."""
        svg = render_diagram("graph TD\n    A -->|loop text| A")
        root = _parse_svg(svg)
        g = _find_self_loop_group(root)
        assert g is not None

        # Get node bottom edge from layout
        diagram = parse_flowchart("graph TD\n    A -->|loop text| A")
        layout = layout_diagram(diagram, measure_text)
        nl = layout.nodes["A"]
        node_bottom = nl.y + nl.height

        # Find text y position
        text_y = None
        for text_el in g.iter(f"{{{_SVG_NS}}}text"):
            y_str = text_el.get("y")
            if y_str:
                text_y = float(y_str)
                break
        if text_y is None:
            for text_el in g.iter("text"):
                y_str = text_el.get("y")
                if y_str:
                    text_y = float(y_str)
                    break

        assert text_y is not None, "Could not find label y coordinate"
        assert text_y > node_bottom, (
            f"Label y={text_y} should be below node bottom={node_bottom}"
        )

# ---------------------------------------------------------------------------
# Unit: LR direction
# ---------------------------------------------------------------------------

class TestSelfLoopLRDirection:
    """Test that LR direction produces a horizontally-extending loop."""

    def test_lr_loop_extends_horizontally(self):
        layout, _ = TestSelfLoopGeometry()._get_layout(
            "graph LR\n    A --> A"
        )
        edge = [e for e in layout.edges if e.source == e.target][0]
        xs = [p.x for p in edge.points]
        ys = [p.y for p in edge.points]
        x_spread = max(xs) - min(xs)
        y_spread = max(ys) - min(ys)
        assert x_spread > y_spread, (
            f"LR loop should extend more horizontally: "
            f"x_spread={x_spread:.2f}, y_spread={y_spread:.2f}"
        )

    def test_rl_loop_extends_horizontally(self):
        layout, _ = TestSelfLoopGeometry()._get_layout(
            "graph RL\n    A --> A"
        )
        edge = [e for e in layout.edges if e.source == e.target][0]
        xs = [p.x for p in edge.points]
        ys = [p.y for p in edge.points]
        x_spread = max(xs) - min(xs)
        y_spread = max(ys) - min(ys)
        assert x_spread > y_spread, (
            f"RL loop should extend more horizontally: "
            f"x_spread={x_spread:.2f}, y_spread={y_spread:.2f}"
        )

# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------

class TestSelfLoopRegression:
    """Ensure normal edges still work alongside self-loops."""

    def test_normal_edge_renders(self):
        """Normal edge (no self-loop) should still render correctly."""
        svg = render_diagram("graph TD\n    A --> B")
        root = _parse_svg(svg)
        edges = _find_edge_groups(root)
        assert len(edges) == 1
        g = edges[0]
        assert g.get("data-edge-source") == "A"
        assert g.get("data-edge-target") == "B"

    def test_mixed_self_loop_and_normal_edge(self):
        """Diagram with both self-loop and normal edge renders without errors."""
        svg = render_diagram("graph TD\n    A --> A\n    A --> B")
        root = _parse_svg(svg)
        edges = _find_edge_groups(root)
        assert len(edges) == 2

        sources = {g.get("data-edge-source") for g in edges}
        targets = {g.get("data-edge-target") for g in edges}
        assert "A" in sources
        assert "A" in targets
        assert "B" in targets

    def test_mixed_both_edges_have_stroke_width(self):
        """Both edges in a mixed diagram should have stroke-width set."""
        svg = render_diagram("graph TD\n    A --> A\n    A --> B")
        root = _parse_svg(svg)
        edges = _find_edge_groups(root)
        for g in edges:
            for path in g.iter(f"{{{_SVG_NS}}}path"):
                sw = path.get("stroke-width")
                assert sw is not None, "Edge path missing stroke-width"
                break
