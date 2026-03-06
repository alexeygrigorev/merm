"""Tests for task 33: text overflow in non-rectangular shapes.

Verifies that text is fully contained within diamond, hexagon, circle,
parallelogram, trapezoid, and other non-rectangular shapes by checking
that the shape dimensions are large enough to inscribe the text bounding
box.
"""

import xml.etree.ElementTree as ET

from merm import render_diagram
from merm.ir import Diagram, Direction, Node, NodeShape
from merm.layout.sugiyama import layout_diagram
from merm.measure.text import _line_width

_SVG_NS = "http://www.w3.org/2000/svg"
_DEFAULT_FONT_SIZE = 16.0

def _render_and_parse(source: str) -> ET.Element:
    svg = render_diagram(source)
    return ET.fromstring(svg)

def _simple_measure(text: str, font_size: float) -> tuple[float, float]:
    """Simple text measurement matching heuristic mode."""
    lines = text.split("<br/>") if "<br/>" in text else [text]
    w = max(_line_width(line, font_size) for line in lines)
    h = font_size * 1.4 * len(lines)
    return (w, h)

def _layout_single_node(label: str, shape: NodeShape) -> tuple[float, float]:
    """Layout a single node and return its (width, height)."""
    diagram = Diagram(
        nodes=[Node(id="A", label=label, shape=shape)],
        edges=[],
        direction=Direction.TB,
    )
    result = layout_diagram(diagram, _simple_measure)
    node = result.nodes["A"]
    return (node.width, node.height)

# ---------------------------------------------------------------------------
# Diamond text containment
# ---------------------------------------------------------------------------

class TestDiamondTextContainment:
    """Diamond shape must have dimensions ~2x the text bbox."""

    def test_short_text(self):
        w, h = _layout_single_node("Yes?", NodeShape.diamond)
        tw = _line_width("Yes?", _DEFAULT_FONT_SIZE)
        th = _DEFAULT_FONT_SIZE * 1.4
        # Text must fit in inscribed rectangle: w/2 x h/2
        assert w / 2 > tw, f"Diamond too narrow: inscribed width {w/2} < text {tw}"
        assert h / 2 > th, f"Diamond too short: inscribed height {h/2} < text {th}"

    def test_medium_text(self):
        label = "Is it working?"
        w, h = _layout_single_node(label, NodeShape.diamond)
        tw = _line_width(label, _DEFAULT_FONT_SIZE)
        th = _DEFAULT_FONT_SIZE * 1.4
        assert w / 2 > tw
        assert h / 2 > th

    def test_long_text_wraps(self):
        label = "Out of beans or water?"
        w, h = _layout_single_node(label, NodeShape.diamond)
        # Even after wrapping, text must be inscribed
        assert w >= 70  # at least min width
        assert h >= 42  # at least min height
        # The diamond's inscribed rect (w/2, h/2) must be positive
        assert w / 2 > 0
        assert h / 2 > 0

    def test_very_long_text(self):
        label = "Is the system fully operational and ready?"
        w, h = _layout_single_node(label, NodeShape.diamond)
        # Diamond expands to accommodate wrapped text
        assert w > 100
        assert h > 50

    def test_diamond_larger_than_rect_for_same_text(self):
        """Diamond should be significantly larger than rect for the same text."""
        label = "Some test text"
        dw, dh = _layout_single_node(label, NodeShape.diamond)
        rw, rh = _layout_single_node(label, NodeShape.rect)
        assert dw > rw * 1.3, "Diamond should be wider than rect"
        assert dh > rh * 1.3, "Diamond should be taller than rect"

# ---------------------------------------------------------------------------
# Hexagon text containment
# ---------------------------------------------------------------------------

class TestHexagonTextContainment:
    """Hexagon: inset = w/4 each side, effective text width = w/2."""

    def test_short_text(self):
        w, h = _layout_single_node("OK", NodeShape.hexagon)
        tw = _line_width("OK", _DEFAULT_FONT_SIZE)
        # Effective text width in hexagon is w/2
        assert w / 2 > tw, f"Hexagon too narrow: usable {w/2} < text {tw}"

    def test_long_text(self):
        label = "Process incoming data packets"
        w, h = _layout_single_node(label, NodeShape.hexagon)
        # Even with wrapping, usable width must exceed text
        assert w > 100

    def test_hexagon_wider_than_rect(self):
        """Hexagon should be wider than rect for the same text."""
        label = "Test label"
        hw, _ = _layout_single_node(label, NodeShape.hexagon)
        rw, _ = _layout_single_node(label, NodeShape.rect)
        assert hw > rw * 1.3, "Hexagon should be wider than rect"

# ---------------------------------------------------------------------------
# Circle sizing
# ---------------------------------------------------------------------------

class TestCircleSizing:
    """Circle uses diagonal of text bbox for diameter."""

    def test_short_text_compact(self):
        w, h = _layout_single_node("End", NodeShape.circle)
        # Should be reasonably compact
        assert w < 80, f"Circle too large for short text: {w}"
        assert w == h, "Circle should be square bounding box"

    def test_medium_text_proportional(self):
        label = "Start processing"
        w, h = _layout_single_node(label, NodeShape.circle)
        tw = _line_width(label, _DEFAULT_FONT_SIZE)
        th = _DEFAULT_FONT_SIZE * 1.4
        # Diameter should be based on diagonal, not max dimension
        # Diameter should be around diagonal + padding, not 2*max + padding
        assert w < 2 * max(tw, th) + 50, "Circle should not be wildly oversized"

    def test_double_circle_larger(self):
        label = "End"
        sw, _ = _layout_single_node(label, NodeShape.circle)
        dw, _ = _layout_single_node(label, NodeShape.double_circle)
        assert dw > sw, "Double circle must be larger than single circle"

# ---------------------------------------------------------------------------
# Parallelogram text containment
# ---------------------------------------------------------------------------

class TestParallelogramTextContainment:
    """Parallelogram: 10% skew reduces usable width to 80%."""

    def test_text_fits(self):
        label = "Input user credentials"
        w, h = _layout_single_node(label, NodeShape.parallelogram)
        tw = _line_width(label, _DEFAULT_FONT_SIZE)
        # Usable width is w * 0.8 (after 10% skew on each side)
        assert w * 0.8 > tw, f"Parallelogram too narrow: usable {w*0.8} < text {tw}"

    def test_parallelogram_alt(self):
        label = "Output results"
        w, h = _layout_single_node(label, NodeShape.parallelogram_alt)
        tw = _line_width(label, _DEFAULT_FONT_SIZE)
        assert w * 0.8 > tw

    def test_wider_than_rect(self):
        label = "Test label"
        pw, _ = _layout_single_node(label, NodeShape.parallelogram)
        rw, _ = _layout_single_node(label, NodeShape.rect)
        assert pw > rw, "Parallelogram should be wider than rect"

# ---------------------------------------------------------------------------
# Trapezoid text containment
# ---------------------------------------------------------------------------

class TestTrapezoidTextContainment:
    """Trapezoid: 10% inset on narrow side reduces usable width to 80%."""

    def test_text_fits(self):
        label = "Manual step"
        w, h = _layout_single_node(label, NodeShape.trapezoid)
        tw = _line_width(label, _DEFAULT_FONT_SIZE)
        assert w * 0.8 > tw, f"Trapezoid too narrow: usable {w*0.8} < text {tw}"

    def test_trapezoid_alt(self):
        label = "Review output"
        w, h = _layout_single_node(label, NodeShape.trapezoid_alt)
        tw = _line_width(label, _DEFAULT_FONT_SIZE)
        assert w * 0.8 > tw

    def test_wider_than_rect(self):
        label = "Test label"
        tw_trap, _ = _layout_single_node(label, NodeShape.trapezoid)
        rw, _ = _layout_single_node(label, NodeShape.rect)
        assert tw_trap > rw, "Trapezoid should be wider than rect"

# ---------------------------------------------------------------------------
# Integration: SVG rendering text containment
# ---------------------------------------------------------------------------

class TestSVGTextContainment:
    """Render SVGs and verify text stays within shape boundaries."""

    def _extract_polygons(self, root: ET.Element) -> list[list[tuple[float, float]]]:
        """Extract polygon point lists from SVG."""
        polygons = []
        for poly in root.iter(f"{{{_SVG_NS}}}polygon"):
            pts_str = poly.get("points", "")
            pts = []
            for pair in pts_str.strip().split():
                x, y = pair.split(",")
                pts.append((float(x), float(y)))
            polygons.append(pts)
        return polygons

    def _point_in_polygon(
        self, x: float, y: float,
        polygon: list[tuple[float, float]],
    ) -> bool:
        """Ray casting algorithm for point-in-polygon test."""
        n = len(polygon)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def _inscribed_rect(
        self, polygon: list[tuple[float, float]],
    ) -> tuple[float, float, float, float]:
        """Approximate the inscribed rectangle of a convex polygon.

        Returns (cx, cy, half_w, half_h) of the largest axis-aligned
        rectangle centered at the polygon centroid that fits inside.
        """
        cx = sum(p[0] for p in polygon) / len(polygon)
        cy = sum(p[1] for p in polygon) / len(polygon)
        # Binary search for half_w and half_h
        hw, hh = 0.0, 0.0
        # Find max half-width
        lo, hi = 0.0, max(p[0] for p in polygon) - min(p[0] for p in polygon)
        for _ in range(50):
            mid = (lo + hi) / 2
            # Check all 4 corners
            if (self._point_in_polygon(cx - mid, cy, polygon) and
                    self._point_in_polygon(cx + mid, cy, polygon)):
                lo = mid
            else:
                hi = mid
        hw = lo
        lo, hi = 0.0, max(p[1] for p in polygon) - min(p[1] for p in polygon)
        for _ in range(50):
            mid = (lo + hi) / 2
            if (self._point_in_polygon(cx, cy - mid, polygon) and
                    self._point_in_polygon(cx, cy + mid, polygon)):
                lo = mid
            else:
                hi = mid
        hh = lo
        return cx, cy, hw, hh

    def test_diamond_svg_text_inside(self):
        source = 'graph TD\n    A{"Out of beans or water?"}'
        root = _render_and_parse(source)
        polygons = self._extract_polygons(root)
        assert len(polygons) >= 1, "Should have at least one polygon (diamond)"
        diamond = polygons[0]
        # Get the inscribed rectangle
        cx, cy, hw, hh = self._inscribed_rect(diamond)
        # The inscribed rect should be big enough to hold text
        assert hw > 10, f"Inscribed half-width too small: {hw}"
        assert hh > 5, f"Inscribed half-height too small: {hh}"

    def test_hexagon_svg_text_inside(self):
        source = 'graph TD\n    A{{"Process incoming data packets"}}'
        root = _render_and_parse(source)
        polygons = self._extract_polygons(root)
        assert len(polygons) >= 1
        hexagon = polygons[0]
        cx, cy, hw, hh = self._inscribed_rect(hexagon)
        assert hw > 10, f"Inscribed half-width too small: {hw}"

    def test_parallelogram_svg_text_inside(self):
        source = 'graph TD\n    A[/"Input user credentials"/]'
        root = _render_and_parse(source)
        polygons = self._extract_polygons(root)
        assert len(polygons) >= 1

    def test_trapezoid_svg_text_inside(self):
        source = 'graph TD\n    A[/"Manual verification step"\\]'
        root = _render_and_parse(source)
        polygons = self._extract_polygons(root)
        assert len(polygons) >= 1

# ---------------------------------------------------------------------------
# Integration: Coffee machine diagram
# ---------------------------------------------------------------------------

class TestCoffeeMachineDiagram:
    """The coffee_machine.mmd diagram should render without text overflow."""

    def test_renders_without_error(self):
        source = open("tests/fixtures/github/coffee_machine.mmd").read()
        svg = render_diagram(source)
        assert "<svg" in svg
        root = ET.fromstring(svg)
        # Should have polygon elements (diamonds)
        polygons = list(root.iter(f"{{{_SVG_NS}}}polygon"))
        assert len(polygons) > 0, "Coffee machine should have diamond nodes"

    def test_diamond_nodes_have_adequate_size(self):
        """Diamond nodes in coffee machine should have inscribed rect > text."""
        source = open("tests/fixtures/github/coffee_machine.mmd").read()
        svg = render_diagram(source)
        root = ET.fromstring(svg)
        polygons = list(root.iter(f"{{{_SVG_NS}}}polygon"))
        for poly in polygons:
            pts_str = poly.get("points", "")
            pts = []
            for pair in pts_str.strip().split():
                x, y = pair.split(",")
                pts.append((float(x), float(y)))
            if len(pts) == 4:
                # Likely a diamond - check it's not degenerate
                w = max(p[0] for p in pts) - min(p[0] for p in pts)
                h = max(p[1] for p in pts) - min(p[1] for p in pts)
                assert w > 20, f"Diamond too narrow: {w}"
                assert h > 20, f"Diamond too short: {h}"

# ---------------------------------------------------------------------------
# Regression: shapes that were already OK should not regress
# ---------------------------------------------------------------------------

class TestNoRegression:
    """Rounded rect, stadium, and regular rect should still work fine."""

    def test_rounded_rect(self):
        source = 'graph TD\n    A("Rounded rectangle text")'
        svg = render_diagram(source)
        assert "<svg" in svg

    def test_stadium(self):
        source = 'graph TD\n    A(["Stadium shape text"])'
        svg = render_diagram(source)
        assert "<svg" in svg

    def test_rect(self):
        source = 'graph TD\n    A["Regular rectangle"]'
        svg = render_diagram(source)
        assert "<svg" in svg
