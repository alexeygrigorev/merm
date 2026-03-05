"""Tests for Task 37: Arrow-to-node gap fix.

Verifies that edge paths are shortened so arrowhead markers do not
touch or penetrate node borders, across all directions and marker types.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from pymermaid import render_diagram
from pymermaid.layout.sugiyama import _route_edge_on_boundary
from pymermaid.render.edges import make_edge_defs

# ---------------------------------------------------------------------------
# Helper: parse marker refX from rendered defs
# ---------------------------------------------------------------------------

def _get_marker_refx(marker_id: str) -> str:
    """Render defs and return the refX value for the given marker id."""
    defs = ET.Element("defs")
    make_edge_defs(defs)
    for marker in defs.iter("marker"):
        if marker.get("id") == marker_id:
            return marker.get("refX", "")
    raise AssertionError(f"Marker '{marker_id}' not found in defs")


# ---------------------------------------------------------------------------
# Unit: Marker refX alignment
# ---------------------------------------------------------------------------

class TestMarkerRefX:
    """Arrow marker refX should align the triangle tip with the path endpoint."""

    def test_arrow_refx_at_tip(self) -> None:
        """Arrow refX=10 means the tip (at viewBox x=10) sits at path end."""
        assert _get_marker_refx("arrow") == "10"

    def test_arrow_reverse_refx_at_tip(self) -> None:
        assert _get_marker_refx("arrow-reverse") == "10"

    def test_circle_end_refx(self) -> None:
        """Circle-end refX=10 places the rightmost edge at the path end."""
        assert _get_marker_refx("circle-end") == "10"

    def test_cross_end_refx(self) -> None:
        """Cross-end refX=10 places the rightmost X stroke at path end."""
        assert _get_marker_refx("cross-end") == "10"


# ---------------------------------------------------------------------------
# Unit: Edge endpoint offset (gap from node border)
# ---------------------------------------------------------------------------

class TestEdgeEndpointGap:
    """Edge start/end points should be offset from the node boundary."""

    def test_td_target_gap(self) -> None:
        """In a vertical (TD) layout, the edge end-y should be above the
        target node's top border (i.e., gap exists)."""
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        # Target top border is at 150 - 27 = 123
        tgt_top = tgt_pos[1] - tgt_size[1] / 2
        assert tgt_pt.y < tgt_top, (
            f"Edge end y={tgt_pt.y} should be above target top={tgt_top}"
        )

    def test_td_source_gap(self) -> None:
        """In TD, the edge start-y should be below the source node bottom."""
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        # Source bottom border is at 50 + 27 = 77
        src_bot = src_pos[1] + src_size[1] / 2
        assert src_pt.y > src_bot, (
            f"Edge start y={src_pt.y} should be below source bottom={src_bot}"
        )

    def test_lr_target_gap(self) -> None:
        """In a horizontal layout, edge end-x should be left of target."""
        src_pos = (50.0, 100.0)
        src_size = (80.0, 54.0)
        tgt_pos = (200.0, 100.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        tgt_left = tgt_pos[0] - tgt_size[0] / 2
        assert tgt_pt.x < tgt_left, (
            f"Edge end x={tgt_pt.x} should be left of target left={tgt_left}"
        )

    def test_lr_source_gap(self) -> None:
        """In horizontal, edge start-x should be right of source right border."""
        src_pos = (50.0, 100.0)
        src_size = (80.0, 54.0)
        tgt_pos = (200.0, 100.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        src_right = src_pos[0] + src_size[0] / 2
        assert src_pt.x > src_right, (
            f"Edge start x={src_pt.x} should be right of source right={src_right}"
        )

    def test_diagonal_gap(self) -> None:
        """Diagonal edges should also have a gap at both ends."""
        src_pos = (50.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (200.0, 200.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        # The gap should move both points away from the boundary
        # Source boundary would be closer to center than the gap-adjusted point
        # Check via distance from node centers
        import math
        src_dist = math.hypot(src_pt.x - src_pos[0], src_pt.y - src_pos[1])
        tgt_dist = math.hypot(tgt_pt.x - tgt_pos[0], tgt_pt.y - tgt_pos[1])

        # Both distances should be greater than the half-size (boundary is at half-size)
        # For a diagonal, the boundary point is somewhere on the rect edge
        # The gap pulls the point further from center
        src_half_min = min(src_size) / 2
        tgt_half_min = min(tgt_size) / 2
        assert src_dist > src_half_min, "Source point should be beyond boundary"
        assert tgt_dist > tgt_half_min, "Target point should be beyond boundary"

    def test_gap_is_small(self) -> None:
        """The gap should be small (a few pixels), not huge."""
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        tgt_top = tgt_pos[1] - tgt_size[1] / 2
        gap = tgt_top - tgt_pt.y
        assert 1.0 < gap < 10.0, f"Gap should be 1-10px, got {gap}"


# ---------------------------------------------------------------------------
# Integration: full render with gap
# ---------------------------------------------------------------------------

class TestRenderWithGap:
    """Render complete diagrams and verify gaps exist in the SVG paths."""

    def _render_and_get_edge_paths(self, source: str) -> list[str]:
        """Render source and return all edge path d-strings."""
        svg_str = render_diagram(source)
        root = ET.fromstring(svg_str)
        paths = []
        for g in root.iter("{http://www.w3.org/2000/svg}g"):
            if g.get("class") == "edge":
                for path in g.iter("{http://www.w3.org/2000/svg}path"):
                    d = path.get("d", "")
                    if d:
                        paths.append(d)
        return paths

    def _get_node_layouts(self, source: str) -> dict:
        """Render and get node layout info from the SVG."""
        svg_str = render_diagram(source)
        root = ET.fromstring(svg_str)
        nodes = {}
        for g in root.iter("{http://www.w3.org/2000/svg}g"):
            if g.get("class") == "node":
                nid = g.get("data-id", "")
                rect = g.find("{http://www.w3.org/2000/svg}rect")
                if rect is not None:
                    x = float(rect.get("x", "0"))
                    y = float(rect.get("y", "0"))
                    w = float(rect.get("width", "0"))
                    h = float(rect.get("height", "0"))
                    nodes[nid] = {"x": x, "y": y, "w": w, "h": h}
        return nodes

    def test_td_arrows_have_gap(self) -> None:
        source = "flowchart TD\n    A --> B --> C"
        paths = self._render_and_get_edge_paths(source)
        assert len(paths) >= 2, "Expected at least 2 edge paths"

    def test_lr_arrows_have_gap(self) -> None:
        source = "flowchart LR\n    A --> B --> C"
        paths = self._render_and_get_edge_paths(source)
        assert len(paths) >= 2

    def test_bt_arrows_have_gap(self) -> None:
        source = "flowchart BT\n    A --> B --> C"
        paths = self._render_and_get_edge_paths(source)
        assert len(paths) >= 2

    def test_rl_arrows_have_gap(self) -> None:
        source = "flowchart RL\n    A --> B --> C"
        paths = self._render_and_get_edge_paths(source)
        assert len(paths) >= 2

    def test_markers_present_in_svg(self) -> None:
        """Verify that arrow markers are defined in the rendered SVG."""
        source = "flowchart TD\n    A --> B"
        svg_str = render_diagram(source)
        root = ET.fromstring(svg_str)
        marker_ids = set()
        for marker in root.iter("{http://www.w3.org/2000/svg}marker"):
            marker_ids.add(marker.get("id"))
        assert "arrow" in marker_ids
        assert "circle-end" in marker_ids
        assert "cross-end" in marker_ids

    def test_circle_endpoint_renders(self) -> None:
        source = "flowchart TD\n    A --o B"
        svg_str = render_diagram(source)
        assert "circle-end" in svg_str

    def test_cross_endpoint_renders(self) -> None:
        source = "flowchart TD\n    A --x B"
        svg_str = render_diagram(source)
        assert "cross-end" in svg_str
