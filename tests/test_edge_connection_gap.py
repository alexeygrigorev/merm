"""Tests for Task 52: Edge-to-node connection gap.

Verifies that edge paths start/end on node boundaries (within tolerance)
and that the arrowhead marker is cleanly aligned.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from merm import render_diagram
from merm.layout.sugiyama import _route_edge_on_boundary
from merm.render.edges import make_edge_defs

FIXTURES = Path(__file__).parent / "fixtures"
NS = "{http://www.w3.org/2000/svg}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_node_bboxes(svg_str: str) -> dict[str, dict]:
    """Parse all g.node[data-node-id] elements, extract bounding box.

    Returns dict mapping node_id -> {"x": float, "y": float, "w": float, "h": float}.
    """
    root = ET.fromstring(svg_str)
    nodes: dict[str, dict] = {}
    for g in root.iter(f"{NS}g"):
        if g.get("class") == "node":
            nid = g.get("data-node-id", "")
            if not nid:
                continue
            rect = g.find(f"{NS}rect")
            if rect is not None:
                nodes[nid] = {
                    "x": float(rect.get("x", "0")),
                    "y": float(rect.get("y", "0")),
                    "w": float(rect.get("width", "0")),
                    "h": float(rect.get("height", "0")),
                }
    return nodes

def _parse_edge_endpoints(svg_str: str) -> list[dict]:
    """Parse all g.edge elements, extract source, target, and path endpoints.

    Returns list of dicts with keys: source, target, d, start_x, start_y,
    end_x, end_y.
    """
    root = ET.fromstring(svg_str)
    edges: list[dict] = []
    for g in root.iter(f"{NS}g"):
        if g.get("class") == "edge":
            src = g.get("data-edge-source", "")
            tgt = g.get("data-edge-target", "")
            for path in g.iter(f"{NS}path"):
                d = path.get("d", "")
                if not d:
                    continue
                m = re.match(r"M\s*([-\d.]+)[,\s]+([-\d.]+)", d)
                coords = re.findall(r"([-\d.]+)[,\s]+([-\d.]+)", d)
                if m and coords:
                    edges.append({
                        "source": src,
                        "target": tgt,
                        "d": d,
                        "start_x": float(m.group(1)),
                        "start_y": float(m.group(2)),
                        "end_x": float(coords[-1][0]),
                        "end_y": float(coords[-1][1]),
                        "marker_end": path.get("marker-end", ""),
                    })
    return edges

def _point_on_rect_boundary(
    px: float,
    py: float,
    rx: float,
    ry: float,
    rw: float,
    rh: float,
    tolerance: float = 1.0,
) -> bool:
    """True if point (px, py) is within tolerance pixels of the rect boundary.

    Rect is defined by top-left (rx, ry) and size (rw, rh).
    """
    left = rx
    right = rx + rw
    top = ry
    bottom = ry + rh

    on_left_or_right = (
        (abs(px - left) < tolerance or abs(px - right) < tolerance)
        and top - tolerance <= py <= bottom + tolerance
    )
    on_top_or_bottom = (
        (abs(py - top) < tolerance or abs(py - bottom) < tolerance)
        and left - tolerance <= px <= right + tolerance
    )
    return on_left_or_right or on_top_or_bottom

def _render_fixture(fixture_path: str) -> str:
    """Read a fixture file and render it to SVG."""
    source = (FIXTURES / fixture_path).read_text()
    return render_diagram(source)

# ---------------------------------------------------------------------------
# Unit: _route_edge_on_boundary produces boundary-touching points
# ---------------------------------------------------------------------------

class TestRouteEdgeOnBoundary:
    """_route_edge_on_boundary must produce endpoints on node boundaries."""

    def test_td_layout_source_on_bottom(self) -> None:
        """TD layout: source endpoint y == src_center_y + src_h/2 (within 0.5px)."""
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        src_pt, _ = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)
        expected_y = src_pos[1] + src_size[1] / 2
        assert abs(src_pt.y - expected_y) < 0.5, (
            f"Source endpoint y={src_pt.y:.2f}, expected {expected_y:.2f}"
        )

    def test_td_layout_target_on_top(self) -> None:
        """TD layout: target endpoint y == tgt_center_y - tgt_h/2 (within 0.5px)."""
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        _, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)
        expected_y = tgt_pos[1] - tgt_size[1] / 2
        assert abs(tgt_pt.y - expected_y) < 0.5, (
            f"Target endpoint y={tgt_pt.y:.2f}, expected {expected_y:.2f}"
        )

    def test_lr_layout_source_on_right(self) -> None:
        """LR layout: source endpoint x == src_center_x + src_w/2 (within 0.5px)."""
        src_pos = (50.0, 100.0)
        src_size = (80.0, 54.0)
        tgt_pos = (200.0, 100.0)
        tgt_size = (80.0, 54.0)

        src_pt, _ = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)
        expected_x = src_pos[0] + src_size[0] / 2
        assert abs(src_pt.x - expected_x) < 0.5, (
            f"Source endpoint x={src_pt.x:.2f}, expected {expected_x:.2f}"
        )

    def test_lr_layout_target_on_left(self) -> None:
        """LR layout: target endpoint x == tgt_center_x - tgt_w/2 (within 0.5px)."""
        src_pos = (50.0, 100.0)
        src_size = (80.0, 54.0)
        tgt_pos = (200.0, 100.0)
        tgt_size = (80.0, 54.0)

        _, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)
        expected_x = tgt_pos[0] - tgt_size[0] / 2
        assert abs(tgt_pt.x - expected_x) < 0.5, (
            f"Target endpoint x={tgt_pt.x:.2f}, expected {expected_x:.2f}"
        )

    def test_diagonal_both_on_boundary(self) -> None:
        """Diagonal: both endpoints on respective rect boundaries (within 0.5px)."""
        src_pos = (50.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (200.0, 200.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        # Source: center-based rect
        src_cx, src_cy = src_pos
        src_hw, src_hh = src_size[0] / 2, src_size[1] / 2
        src_on_left_right = abs(abs(src_pt.x - src_cx) - src_hw) < 0.5
        src_on_top_bottom = abs(abs(src_pt.y - src_cy) - src_hh) < 0.5
        assert src_on_left_right or src_on_top_bottom, (
            f"Source ({src_pt.x:.2f}, {src_pt.y:.2f}) not on boundary"
        )

        # Target: center-based rect
        tgt_cx, tgt_cy = tgt_pos
        tgt_hw, tgt_hh = tgt_size[0] / 2, tgt_size[1] / 2
        tgt_on_left_right = abs(abs(tgt_pt.x - tgt_cx) - tgt_hw) < 0.5
        tgt_on_top_bottom = abs(abs(tgt_pt.y - tgt_cy) - tgt_hh) < 0.5
        assert tgt_on_left_right or tgt_on_top_bottom, (
            f"Target ({tgt_pt.x:.2f}, {tgt_pt.y:.2f}) not on boundary"
        )

# ---------------------------------------------------------------------------
# Integration: two_nodes.mmd gap check
# ---------------------------------------------------------------------------

class TestTwoNodesGap:
    """Render basic/two_nodes.mmd and verify edge endpoints are on node boundaries."""

    def test_source_start_on_boundary(self) -> None:
        svg = _render_fixture("corpus/basic/two_nodes.mmd")
        nodes = _parse_node_bboxes(svg)
        edges = _parse_edge_endpoints(svg)
        assert len(edges) >= 1, "Expected at least 1 edge"

        for edge in edges:
            src = nodes.get(edge["source"])
            assert src is not None, f"Source node {edge['source']} not found"
            assert _point_on_rect_boundary(
                edge["start_x"], edge["start_y"],
                src["x"], src["y"], src["w"], src["h"],
                tolerance=9.0,
            ), (
                f"Edge {edge['source']}->{edge['target']}: "
                f"start ({edge['start_x']:.1f},{edge['start_y']:.1f}) "
                f"not on source boundary"
            )

    def test_target_end_on_boundary(self) -> None:
        svg = _render_fixture("corpus/basic/two_nodes.mmd")
        nodes = _parse_node_bboxes(svg)
        edges = _parse_edge_endpoints(svg)
        assert len(edges) >= 1

        for edge in edges:
            tgt = nodes.get(edge["target"])
            assert tgt is not None, f"Target node {edge['target']} not found"
            assert _point_on_rect_boundary(
                edge["end_x"], edge["end_y"],
                tgt["x"], tgt["y"], tgt["w"], tgt["h"],
                tolerance=9.0,
            ), (
                f"Edge {edge['source']}->{edge['target']}: "
                f"end ({edge['end_x']:.1f},{edge['end_y']:.1f}) "
                f"not on target boundary"
            )

# ---------------------------------------------------------------------------
# Integration: diamond.mmd diagonal edges
# ---------------------------------------------------------------------------

class TestDiamondEdges:
    """Render basic/diamond.mmd and verify all 4 diagonal edge endpoints."""

    def test_all_sources_on_boundary(self) -> None:
        svg = _render_fixture("corpus/basic/diamond.mmd")
        nodes = _parse_node_bboxes(svg)
        edges = _parse_edge_endpoints(svg)
        assert len(edges) >= 4, f"Expected 4 edges, got {len(edges)}"

        for edge in edges:
            src = nodes.get(edge["source"])
            if src is None:
                continue
            assert _point_on_rect_boundary(
                edge["start_x"], edge["start_y"],
                src["x"], src["y"], src["w"], src["h"],
                tolerance=9.0,
            ), (
                f"Diamond {edge['source']}->{edge['target']}: "
                f"start ({edge['start_x']:.1f},{edge['start_y']:.1f}) "
                f"not on source boundary"
            )

    def test_all_targets_on_boundary(self) -> None:
        svg = _render_fixture("corpus/basic/diamond.mmd")
        nodes = _parse_node_bboxes(svg)
        edges = _parse_edge_endpoints(svg)
        assert len(edges) >= 4

        for edge in edges:
            tgt = nodes.get(edge["target"])
            if tgt is None:
                continue
            assert _point_on_rect_boundary(
                edge["end_x"], edge["end_y"],
                tgt["x"], tgt["y"], tgt["w"], tgt["h"],
                tolerance=9.0,
            ), (
                f"Diamond {edge['source']}->{edge['target']}: "
                f"end ({edge['end_x']:.1f},{edge['end_y']:.1f}) "
                f"not on target boundary"
            )

# ---------------------------------------------------------------------------
# Integration: linear_chain.mmd straight edges
# ---------------------------------------------------------------------------

class TestLinearChainEdges:
    """Render basic/linear_chain.mmd and verify all edge endpoints."""

    def test_all_endpoints_on_boundary(self) -> None:
        svg = _render_fixture("corpus/basic/linear_chain.mmd")
        nodes = _parse_node_bboxes(svg)
        edges = _parse_edge_endpoints(svg)
        assert len(edges) >= 4, f"Expected at least 4 edges, got {len(edges)}"

        for edge in edges:
            src = nodes.get(edge["source"])
            tgt = nodes.get(edge["target"])
            if src is None or tgt is None:
                continue
            assert _point_on_rect_boundary(
                edge["start_x"], edge["start_y"],
                src["x"], src["y"], src["w"], src["h"],
                tolerance=9.0,
            ), (
                f"Chain {edge['source']}->{edge['target']}: "
                f"start not on source boundary"
            )
            assert _point_on_rect_boundary(
                edge["end_x"], edge["end_y"],
                tgt["x"], tgt["y"], tgt["w"], tgt["h"],
                tolerance=9.0,
            ), (
                f"Chain {edge['source']}->{edge['target']}: "
                f"end not on target boundary"
            )

# ---------------------------------------------------------------------------
# Integration: LR direction
# ---------------------------------------------------------------------------

class TestLRDirection:
    """Render direction/lr.mmd and verify all edge endpoints."""

    def test_all_endpoints_on_boundary(self) -> None:
        svg = _render_fixture("corpus/direction/lr.mmd")
        nodes = _parse_node_bboxes(svg)
        edges = _parse_edge_endpoints(svg)
        assert len(edges) >= 2, f"Expected at least 2 edges, got {len(edges)}"

        for edge in edges:
            src = nodes.get(edge["source"])
            tgt = nodes.get(edge["target"])
            if src is None or tgt is None:
                continue
            assert _point_on_rect_boundary(
                edge["start_x"], edge["start_y"],
                src["x"], src["y"], src["w"], src["h"],
                tolerance=9.0,
            ), (
                f"LR {edge['source']}->{edge['target']}: "
                f"start ({edge['start_x']:.1f},{edge['start_y']:.1f}) "
                f"not on source boundary"
            )
            assert _point_on_rect_boundary(
                edge["end_x"], edge["end_y"],
                tgt["x"], tgt["y"], tgt["w"], tgt["h"],
                tolerance=9.0,
            ), (
                f"LR {edge['source']}->{edge['target']}: "
                f"end ({edge['end_x']:.1f},{edge['end_y']:.1f}) "
                f"not on target boundary"
            )

# ---------------------------------------------------------------------------
# Integration: BT direction
# ---------------------------------------------------------------------------

class TestBTDirection:
    """Render direction/bt.mmd and verify all edge endpoints."""

    def test_all_endpoints_on_boundary(self) -> None:
        svg = _render_fixture("corpus/direction/bt.mmd")
        nodes = _parse_node_bboxes(svg)
        edges = _parse_edge_endpoints(svg)
        assert len(edges) >= 2, f"Expected at least 2 edges, got {len(edges)}"

        for edge in edges:
            src = nodes.get(edge["source"])
            tgt = nodes.get(edge["target"])
            if src is None or tgt is None:
                continue
            assert _point_on_rect_boundary(
                edge["start_x"], edge["start_y"],
                src["x"], src["y"], src["w"], src["h"],
                tolerance=9.0,
            ), (
                f"BT {edge['source']}->{edge['target']}: "
                f"start ({edge['start_x']:.1f},{edge['start_y']:.1f}) "
                f"not on source boundary"
            )
            assert _point_on_rect_boundary(
                edge["end_x"], edge["end_y"],
                tgt["x"], tgt["y"], tgt["w"], tgt["h"],
                tolerance=9.0,  # path shortened by marker size (8px)
            ), (
                f"BT {edge['source']}->{edge['target']}: "
                f"end ({edge['end_x']:.1f},{edge['end_y']:.1f}) "
                f"not on target boundary"
            )

# ---------------------------------------------------------------------------
# Integration: no overshoot into node interior
# ---------------------------------------------------------------------------

class TestNoOvershoot:
    """Edge endpoints must not overshoot into the node interior."""

    def test_td_no_overshoot(self) -> None:
        """TD: source start y >= source bottom - 1; target end y <= target top + 1."""
        svg = _render_fixture("corpus/basic/two_nodes.mmd")
        nodes = _parse_node_bboxes(svg)
        edges = _parse_edge_endpoints(svg)

        for edge in edges:
            src = nodes.get(edge["source"])
            tgt = nodes.get(edge["target"])
            if src is None or tgt is None:
                continue
            src_bottom = src["y"] + src["h"]
            tgt_top = tgt["y"]
            assert edge["start_y"] >= src_bottom - 1.0, (
                f"Overshoot: start y={edge['start_y']:.1f} above "
                f"source bottom={src_bottom:.1f}"
            )
            assert edge["end_y"] <= tgt_top + 1.0, (
                f"Overshoot: end y={edge['end_y']:.1f} below "
                f"target top={tgt_top:.1f}"
            )

# ---------------------------------------------------------------------------
# Unit: arrowhead marker alignment
# ---------------------------------------------------------------------------

class TestArrowheadMarkerAlignment:
    """Arrow markers should produce a clean arrowhead without a line stub."""

    def test_arrow_marker_refx(self) -> None:
        """Verify refX is set appropriately for clean arrowhead rendering.

        Either refX=0 (line ends at triangle base) or refX=10 (tip at path
        end, but marker covers the line).
        """
        defs = ET.Element("defs")
        make_edge_defs(defs)
        for marker in defs.iter("marker"):
            if marker.get("id") == "arrow":
                ref_x = marker.get("refX", "")
                # refX should be either "0" or "10"
                assert ref_x in ("0", "10"), (
                    f"Arrow marker refX={ref_x}, expected 0 or 10"
                )
                return
        raise AssertionError("Arrow marker not found in defs")

    def test_arrow_marker_path_is_triangle(self) -> None:
        """Arrow marker path should be a proper triangle."""
        defs = ET.Element("defs")
        make_edge_defs(defs)
        for marker in defs.iter("marker"):
            if marker.get("id") == "arrow":
                path = marker.find("path")
                assert path is not None, "Arrow marker has no path element"
                d = path.get("d", "")
                assert "z" in d.lower(), "Arrow path should be closed (z)"
                return
        raise AssertionError("Arrow marker not found")

    def test_line_does_not_extend_past_arrowhead(self) -> None:
        """Render two_nodes.mmd and verify path endpoint coordinate math.

        The line path should not visibly extend past the arrowhead base.
        With refX=10, the tip is at path end, arrowhead body extends backward.
        With refX=0, the base is at path end, arrowhead extends forward.
        Either way, no visible line stub should appear.
        """
        svg = _render_fixture("corpus/basic/two_nodes.mmd")
        nodes = _parse_node_bboxes(svg)
        edges = _parse_edge_endpoints(svg)

        # Parse marker refX
        root = ET.fromstring(svg)
        arrow_refx = None
        marker_width = None
        for marker in root.iter(f"{NS}marker"):
            if marker.get("id") == "arrow":
                arrow_refx = float(marker.get("refX", "10"))
                marker_width = float(marker.get("markerWidth", "8"))
                break

        assert arrow_refx is not None, "Arrow marker not found in SVG"

        for edge in edges:
            if "arrow" not in edge.get("marker_end", ""):
                continue
            tgt = nodes.get(edge["target"])
            if tgt is None:
                continue

            tgt_top = tgt["y"]
            tgt_bottom = tgt["y"] + tgt["h"]
            end_y = edge["end_y"]

            if arrow_refx >= 9.0:
                # refX=10: tip at path end, path end should be on boundary
                assert abs(end_y - tgt_top) < 1.5 or abs(end_y - tgt_bottom) < 1.5, (
                    f"With refX=10, path end y={end_y:.1f} should be on "
                    f"target boundary (top={tgt_top:.1f}, bottom={tgt_bottom:.1f})"
                )
            else:
                # refX=0: base at path end, path end shortened by marker_width
                assert marker_width is not None
                # Path end should be marker_width before the boundary
                dist_to_top = abs(end_y - tgt_top)
                dist_to_bottom = abs(end_y - tgt_bottom)
                assert (
                    dist_to_top < marker_width + 1.0
                    or dist_to_bottom < marker_width + 1.0
                ), (
                    f"With refX=0, path end y={end_y:.1f} should be within "
                    f"marker_width ({marker_width}) of target boundary "
                    f"(top={tgt_top:.1f}, bottom={tgt_bottom:.1f})"
                )

# ---------------------------------------------------------------------------
# Integration: back-edge (curve) connection
# ---------------------------------------------------------------------------

class TestBackEdgeConnection:
    """Render flowchart/registration.mmd and verify edge endpoints for curves."""

    def test_all_edges_near_boundary(self) -> None:
        svg = _render_fixture("corpus/flowchart/registration.mmd")
        nodes = _parse_node_bboxes(svg)
        edges = _parse_edge_endpoints(svg)
        assert len(edges) >= 5, f"Expected at least 5 edges, got {len(edges)}"

        for edge in edges:
            src = nodes.get(edge["source"])
            tgt = nodes.get(edge["target"])
            if src is None or tgt is None:
                continue
            # Relaxed tolerance for curves
            assert _point_on_rect_boundary(
                edge["start_x"], edge["start_y"],
                src["x"], src["y"], src["w"], src["h"],
                tolerance=2.0,
            ), (
                f"Registration {edge['source']}->{edge['target']}: "
                f"start ({edge['start_x']:.1f},{edge['start_y']:.1f}) "
                f"not near source boundary"
            )
            assert _point_on_rect_boundary(
                edge["end_x"], edge["end_y"],
                tgt["x"], tgt["y"], tgt["w"], tgt["h"],
                tolerance=9.0,  # path shortened by marker size (8px)
            ), (
                f"Registration {edge['source']}->{edge['target']}: "
                f"end ({edge['end_x']:.1f},{edge['end_y']:.1f}) "
                f"not near target boundary"
            )
