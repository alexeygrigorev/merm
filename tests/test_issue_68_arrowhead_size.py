"""Tests for issue 68: sequence diagram oversized arrowheads.

Verifies that arrowhead marker dimensions have been reduced from
10x7 to approximately 6x4, with correct refX/refY alignment and
valid polygon/polyline geometry.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from merm.layout.sequence import layout_sequence
from merm.parser.sequence import parse_sequence
from merm.render.sequence import render_sequence_svg

_SVG_NS = "http://www.w3.org/2000/svg"
_FIXTURES = Path(__file__).parent / "fixtures" / "corpus" / "sequence"


def _render_text(text: str) -> ET.Element:
    """Parse, layout, and render a sequence diagram string."""
    diagram = parse_sequence(text)
    layout = layout_sequence(diagram)
    svg_str = render_sequence_svg(diagram, layout)
    return ET.fromstring(svg_str)


def _render_fixture(name: str) -> ET.Element:
    text = (_FIXTURES / name).read_text()
    return _render_text(text)


def _get_marker(root: ET.Element, marker_id: str) -> ET.Element:
    """Find a specific marker by id."""
    for m in root.findall(f".//{{{_SVG_NS}}}marker"):
        if m.get("id") == marker_id:
            return m
    raise AssertionError(f"Marker '{marker_id}' not found")


class TestArrowMarkerDimensions:
    """Verify all markers have reduced dimensions (not oversized)."""

    def test_seq_arrow_dimensions(self):
        root = _render_fixture("basic.mmd")
        m = _get_marker(root, "seq-arrow")
        w = float(m.get("markerWidth"))
        h = float(m.get("markerHeight"))
        assert w <= 8, f"seq-arrow markerWidth={w} should be <= 8"
        assert h <= 6, f"seq-arrow markerHeight={h} should be <= 6"
        assert w < 10, "seq-arrow markerWidth must be less than old value 10"
        assert h < 7, "seq-arrow markerHeight must be less than old value 7"

    def test_seq_arrow_open_dimensions(self):
        root = _render_fixture("basic.mmd")
        m = _get_marker(root, "seq-arrow-open")
        w = float(m.get("markerWidth"))
        h = float(m.get("markerHeight"))
        assert w <= 8, f"seq-arrow-open markerWidth={w} should be <= 8"
        assert h <= 6, f"seq-arrow-open markerHeight={h} should be <= 6"

    def test_seq_async_dimensions(self):
        root = _render_fixture("basic.mmd")
        m = _get_marker(root, "seq-async")
        w = float(m.get("markerWidth"))
        h = float(m.get("markerHeight"))
        assert w <= 8, f"seq-async markerWidth={w} should be <= 8"
        assert h <= 6, f"seq-async markerHeight={h} should be <= 6"

    def test_seq_cross_dimensions(self):
        root = _render_fixture("basic.mmd")
        m = _get_marker(root, "seq-cross")
        w = float(m.get("markerWidth"))
        h = float(m.get("markerHeight"))
        assert w <= 8, f"seq-cross markerWidth={w} should be <= 8"
        assert h <= 8, f"seq-cross markerHeight={h} should be <= 8"
        assert w < 10, "seq-cross markerWidth must be less than old value 10"
        assert h < 10, "seq-cross markerHeight must be less than old value 10"


class TestMarkerGeometryConsistency:
    """Verify refX/refY match the polygon/polyline geometry."""

    def test_seq_arrow_refx_matches_tip(self):
        """refX should equal the x-coord of the arrowhead tip (rightmost point)."""
        root = _render_fixture("basic.mmd")
        m = _get_marker(root, "seq-arrow")
        ref_x = float(m.get("refX"))
        marker_w = float(m.get("markerWidth"))
        # The tip of the arrow should be at refX = markerWidth
        assert ref_x == marker_w, (
            f"seq-arrow refX={ref_x} should equal markerWidth={marker_w}"
        )

    def test_seq_arrow_refy_centered(self):
        """refY should be half the markerHeight (vertically centered)."""
        root = _render_fixture("basic.mmd")
        m = _get_marker(root, "seq-arrow")
        ref_y = float(m.get("refY"))
        marker_h = float(m.get("markerHeight"))
        assert ref_y == marker_h / 2, (
            f"seq-arrow refY={ref_y} should equal markerHeight/2={marker_h / 2}"
        )

    def test_seq_arrow_polygon_within_bounds(self):
        """Polygon points should fit within markerWidth x markerHeight."""
        root = _render_fixture("basic.mmd")
        m = _get_marker(root, "seq-arrow")
        marker_w = float(m.get("markerWidth"))
        marker_h = float(m.get("markerHeight"))
        poly = m.find(f"{{{_SVG_NS}}}polygon")
        assert poly is not None, "seq-arrow must contain a polygon"
        points_str = poly.get("points")
        for pair in points_str.split(","):
            coords = pair.strip().split()
            x, y = float(coords[0]), float(coords[1])
            assert 0 <= x <= marker_w, f"polygon x={x} out of bounds [0, {marker_w}]"
            assert 0 <= y <= marker_h, f"polygon y={y} out of bounds [0, {marker_h}]"

    def test_seq_cross_ref_centered(self):
        """Cross marker refX/refY should be centered."""
        root = _render_fixture("basic.mmd")
        m = _get_marker(root, "seq-cross")
        ref_x = float(m.get("refX"))
        ref_y = float(m.get("refY"))
        marker_w = float(m.get("markerWidth"))
        marker_h = float(m.get("markerHeight"))
        assert ref_x == marker_w / 2
        assert ref_y == marker_h / 2

    def test_all_markers_use_user_space_on_use(self):
        root = _render_fixture("basic.mmd")
        for marker_id in ["seq-arrow", "seq-arrow-open", "seq-cross", "seq-async"]:
            m = _get_marker(root, marker_id)
            assert m.get("markerUnits") == "userSpaceOnUse"


class TestIntegrationRendering:
    """Integration tests rendering full diagrams with reduced arrowheads."""

    def test_basic_diagram_renders(self):
        root = _render_fixture("basic.mmd")
        messages = root.findall(f".//{{{_SVG_NS}}}g[@class='seq-message']")
        assert len(messages) > 0

    def test_all_message_types(self):
        """Render a diagram with all message types, verify markers present."""
        text = (
            "sequenceDiagram\n"
            "    Alice->>Bob: Solid arrow\n"
            "    Bob-->>Alice: Dashed arrow\n"
            "    Alice-)Bob: Async arrow\n"
            "    Bob-xAlice: Cross\n"
        )
        root = _render_text(text)
        markers = root.findall(f".//{{{_SVG_NS}}}marker")
        ids = {m.get("id") for m in markers}
        assert "seq-arrow" in ids
        assert "seq-async" in ids
        assert "seq-cross" in ids

    def test_self_message_renders(self):
        """Self-message arrows should still work with smaller arrowheads."""
        text = (
            "sequenceDiagram\n"
            "    Alice->>John: Hello\n"
            "    loop HealthCheck\n"
            "        John->>John: Fight against hypochondria\n"
            "    end\n"
        )
        root = _render_text(text)
        messages = root.findall(f".//{{{_SVG_NS}}}g[@class='seq-message']")
        # Should have at least 2 messages (one normal, one self)
        assert len(messages) >= 2
        # Self-message uses a path element
        xpath = f".//{{{_SVG_NS}}}g[@class='seq-message']//{{{_SVG_NS}}}path"
        paths = root.findall(xpath)
        assert len(paths) >= 1, "Self-message should render as a path"

    def test_arrowheads_have_marker_end(self):
        """All message lines/paths should reference a marker-end."""
        text = (
            "sequenceDiagram\n"
            "    Alice->>Bob: Hello\n"
            "    Bob-->>Alice: Hi\n"
        )
        root = _render_text(text)
        messages = root.findall(f".//{{{_SVG_NS}}}g[@class='seq-message']")
        for msg in messages:
            line = msg.find(f"{{{_SVG_NS}}}line")
            path = msg.find(f"{{{_SVG_NS}}}path")
            elem = line if line is not None else path
            assert elem is not None, "Message should have a line or path"
            marker_end = elem.get("marker-end")
            assert marker_end is not None, "Message should have marker-end attribute"
            assert marker_end.startswith("url(#seq-"), (
                f"Unexpected marker-end: {marker_end}"
            )
