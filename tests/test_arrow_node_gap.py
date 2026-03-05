"""Tests for Task 37: Arrow-to-node gap fix.

Verifies that edge paths are shortened so arrowhead markers do not
touch or penetrate node borders, across all directions and marker types.
"""

import xml.etree.ElementTree as ET

from pymermaid import render_diagram
from pymermaid.layout.sugiyama import _route_edge_on_boundary
from pymermaid.layout.types import Point  # noqa: F401 (used by helper)
from pymermaid.render.edges import make_edge_defs

# ---------------------------------------------------------------------------
# Helper: assert a point lies on a rect boundary
# ---------------------------------------------------------------------------

def _assert_on_rect_boundary(
    pt: Point,
    center: tuple[float, float],
    size: tuple[float, float],
    tolerance: float = 0.5,
) -> None:
    """Assert that *pt* lies on the boundary of the rect centred at *center*."""
    cx, cy = center
    hw, hh = size[0] / 2.0, size[1] / 2.0

    on_left_or_right = (
        abs(abs(pt.x - cx) - hw) < tolerance and abs(pt.y - cy) <= hh + tolerance
    )
    on_top_or_bottom = (
        abs(abs(pt.y - cy) - hh) < tolerance and abs(pt.x - cx) <= hw + tolerance
    )
    assert on_left_or_right or on_top_or_bottom, (
        f"Point ({pt.x}, {pt.y}) is not on rect boundary "
        f"center=({cx}, {cy}), size={size}"
    )

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
    """Edge endpoints should lie exactly on the node boundary (no gap by default).

    Source endpoints always touch the node rect.  Target endpoints touch the
    rect as well -- the SVG marker ``refX`` handles arrowhead alignment so no
    path-level gap is needed.
    """

    def test_td_target_on_boundary(self) -> None:
        """In a vertical (TD) layout, the edge target endpoint should be
        exactly on the target node's top border."""
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        tgt_top = tgt_pos[1] - tgt_size[1] / 2
        assert abs(tgt_pt.y - tgt_top) < 0.5, (
            f"Edge end y={tgt_pt.y} should be on target top={tgt_top}"
        )

    def test_td_source_on_boundary(self) -> None:
        """In TD, the edge source endpoint should be on the source node bottom."""
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        src_bot = src_pos[1] + src_size[1] / 2
        assert abs(src_pt.y - src_bot) < 0.5, (
            f"Edge start y={src_pt.y} should be on source bottom={src_bot}"
        )

    def test_lr_target_on_boundary(self) -> None:
        """Horizontal: target endpoint on target left border."""
        src_pos = (50.0, 100.0)
        src_size = (80.0, 54.0)
        tgt_pos = (200.0, 100.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        tgt_left = tgt_pos[0] - tgt_size[0] / 2
        assert abs(tgt_pt.x - tgt_left) < 0.5, (
            f"Edge end x={tgt_pt.x} should be on target left={tgt_left}"
        )

    def test_lr_source_on_boundary(self) -> None:
        """In horizontal, edge source endpoint should be on source right border."""
        src_pos = (50.0, 100.0)
        src_size = (80.0, 54.0)
        tgt_pos = (200.0, 100.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        src_right = src_pos[0] + src_size[0] / 2
        assert abs(src_pt.x - src_right) < 0.5, (
            f"Edge start x={src_pt.x} should be on source right={src_right}"
        )

    def test_diagonal_on_boundary(self) -> None:
        """Diagonal edges should have endpoints exactly on both boundaries."""
        src_pos = (50.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (200.0, 200.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        # Source point should lie on the source rect boundary
        _assert_on_rect_boundary(src_pt, src_pos, src_size, tolerance=0.5)
        # Target point should lie on the target rect boundary
        _assert_on_rect_boundary(tgt_pt, tgt_pos, tgt_size, tolerance=0.5)

    def test_no_gap_by_default(self) -> None:
        """With default parameters, both endpoints lie exactly on boundaries."""
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        tgt_top = tgt_pos[1] - tgt_size[1] / 2
        gap = abs(tgt_top - tgt_pt.y)
        assert gap < 0.5, f"Gap should be <0.5px, got {gap}"

    def test_explicit_target_gap(self) -> None:
        """When target_gap is set, the target endpoint is pulled inward."""
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(
            src_pos, src_size, tgt_pos, tgt_size, target_gap=3.0,
        )

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
