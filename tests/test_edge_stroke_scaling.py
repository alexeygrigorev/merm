"""Tests for edge stroke-width scaling and marker sizing (task 25)."""

import xml.etree.ElementTree as ET

import pytest

from pymermaid.ir import EdgeType
from pymermaid.render.edges import _STYLE_MAP, make_edge_defs

# ---------------------------------------------------------------------------
# Unit: _STYLE_MAP stroke-width values
# ---------------------------------------------------------------------------

class TestStyleMapStrokeWidths:
    """Verify _STYLE_MAP maps edge types to the correct stroke-width."""

    def test_arrow_stroke_width_is_2(self) -> None:
        assert _STYLE_MAP[EdgeType.arrow]["stroke-width"] == "2"

    def test_open_stroke_width_is_2(self) -> None:
        assert _STYLE_MAP[EdgeType.open]["stroke-width"] == "2"

    def test_dotted_stroke_width_is_2(self) -> None:
        assert _STYLE_MAP[EdgeType.dotted]["stroke-width"] == "2"

    def test_dotted_dasharray(self) -> None:
        assert _STYLE_MAP[EdgeType.dotted]["stroke-dasharray"] == "5,5"

    def test_dotted_arrow_stroke_width_is_2(self) -> None:
        assert _STYLE_MAP[EdgeType.dotted_arrow]["stroke-width"] == "2"

    def test_dotted_arrow_dasharray(self) -> None:
        assert _STYLE_MAP[EdgeType.dotted_arrow]["stroke-dasharray"] == "5,5"

    def test_thick_stroke_width_is_3_5(self) -> None:
        assert _STYLE_MAP[EdgeType.thick]["stroke-width"] == "3.5"

    def test_thick_arrow_stroke_width_is_3_5(self) -> None:
        assert _STYLE_MAP[EdgeType.thick_arrow]["stroke-width"] == "3.5"

    def test_invisible_stroke_width_is_0(self) -> None:
        assert _STYLE_MAP[EdgeType.invisible]["stroke-width"] == "0"

# ---------------------------------------------------------------------------
# Unit: Marker dimensions in SVG defs
# ---------------------------------------------------------------------------

class TestMarkerDimensions:
    """Verify marker elements have the correct markerWidth/markerHeight."""

    @pytest.fixture()
    def defs_element(self) -> ET.Element:
        defs = ET.Element("defs")
        make_edge_defs(defs)
        return defs

    def _find_marker(self, defs: ET.Element, marker_id: str) -> ET.Element:
        for marker in defs.iter("marker"):
            if marker.get("id") == marker_id:
                return marker
        pytest.fail(f"Marker '{marker_id}' not found in defs")

    # Arrow marker -- should remain at 8 (unchanged)
    def test_arrow_marker_width(self, defs_element: ET.Element) -> None:
        marker = self._find_marker(defs_element, "arrow")
        assert marker.get("markerWidth") == "8"
        assert marker.get("markerHeight") == "8"

    def test_arrow_marker_refx(self, defs_element: ET.Element) -> None:
        marker = self._find_marker(defs_element, "arrow")
        assert marker.get("refX") == "10"

    # Circle marker -- reduced from 11 to 8
    def test_circle_marker_width(self, defs_element: ET.Element) -> None:
        marker = self._find_marker(defs_element, "circle-end")
        assert marker.get("markerWidth") == "8"
        assert marker.get("markerHeight") == "8"

    # Cross marker -- reduced from 11 to 8
    def test_cross_marker_width(self, defs_element: ET.Element) -> None:
        marker = self._find_marker(defs_element, "cross-end")
        assert marker.get("markerWidth") == "8"
        assert marker.get("markerHeight") == "8"

    # Arrow-reverse marker -- should remain at 8 (unchanged)
    def test_arrow_reverse_marker_width(self, defs_element: ET.Element) -> None:
        marker = self._find_marker(defs_element, "arrow-reverse")
        assert marker.get("markerWidth") == "8"
        assert marker.get("markerHeight") == "8"
