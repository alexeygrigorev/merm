"""Tests for issue 63: sequence diagram marker sizing.

Verifies that arrow markers use userSpaceOnUse so they don't scale
with stroke width, keeping arrowheads proportional.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from merm.layout.sequence import layout_sequence
from merm.parser.sequence import parse_sequence
from merm.render.sequence import render_sequence_svg

_SVG_NS = "http://www.w3.org/2000/svg"
_FIXTURES = Path(__file__).parent / "fixtures" / "corpus" / "sequence"


def _render_fixture(name: str) -> ET.Element:
    """Parse, layout, and render a sequence fixture, returning the SVG root."""
    text = (_FIXTURES / name).read_text()
    diagram = parse_sequence(text)
    layout = layout_sequence(diagram)
    svg_str = render_sequence_svg(diagram, layout)
    return ET.fromstring(svg_str)


def _get_markers(root: ET.Element) -> list[ET.Element]:
    """Extract all <marker> elements from an SVG."""
    return root.findall(f".//{{{_SVG_NS}}}marker")


class TestMarkerUnits:
    """All sequence markers must use markerUnits=userSpaceOnUse."""

    def test_basic_markers_use_user_space_on_use(self):
        root = _render_fixture("basic.mmd")
        markers = _get_markers(root)
        assert len(markers) > 0, "Expected at least one marker definition"
        for m in markers:
            assert m.get("markerUnits") == "userSpaceOnUse", (
                f"Marker '{m.get('id')}' should have markerUnits='userSpaceOnUse'"
            )

    def test_all_four_marker_ids_present(self):
        """Verify all marker types are defined."""
        root = _render_fixture("basic.mmd")
        markers = _get_markers(root)
        ids = {m.get("id") for m in markers}
        assert "seq-arrow" in ids
        assert "seq-arrow-open" in ids
        assert "seq-cross" in ids
        assert "seq-async" in ids


class TestMarkerDimensions:
    """Marker dimensions should be reasonable (not oversized)."""

    def test_marker_width_at_most_12(self):
        root = _render_fixture("basic.mmd")
        markers = _get_markers(root)
        for m in markers:
            w = float(m.get("markerWidth", "0"))
            assert w <= 12, (
                f"Marker '{m.get('id')}' markerWidth={w} exceeds 12px"
            )

    def test_marker_height_at_most_12(self):
        root = _render_fixture("basic.mmd")
        markers = _get_markers(root)
        for m in markers:
            h = float(m.get("markerHeight", "0"))
            assert h <= 12, (
                f"Marker '{m.get('id')}' markerHeight={h} exceeds 12px"
            )


class TestMarkerConsistencyAcrossTypes:
    """Solid and dashed arrows should use the same marker definitions."""

    def test_solid_and_dashed_use_same_marker(self):
        """basic.mmd has both ->> (solid) and -->> (dashed) arrows.
        Both should reference the same seq-arrow marker."""
        root = _render_fixture("basic.mmd")
        messages = root.findall(f".//{{{_SVG_NS}}}g[@class='seq-message']")
        marker_ends = set()
        for msg in messages:
            line = msg.find(f"{{{_SVG_NS}}}line")
            if line is not None:
                marker_ends.add(line.get("marker-end"))
            path = msg.find(f"{{{_SVG_NS}}}path")
            if path is not None:
                marker_ends.add(path.get("marker-end"))
        # Both solid and dashed arrows use seq-arrow
        assert "url(#seq-arrow)" in marker_ends


class TestRegressionOtherDiagrams:
    """Markers should still render correctly for other sequence diagrams."""

    def test_flink_diagrams_have_markers(self):
        """Flink diagrams should still have properly sized markers."""
        for name in ["flink_late_upsert.mmd", "flink_late_event.mmd"]:
            if not (_FIXTURES / name).exists():
                continue
            root = _render_fixture(name)
            markers = _get_markers(root)
            assert len(markers) > 0
            for m in markers:
                assert m.get("markerUnits") == "userSpaceOnUse"
                w = float(m.get("markerWidth", "0"))
                h = float(m.get("markerHeight", "0"))
                assert w <= 12
                assert h <= 12
