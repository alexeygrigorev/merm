"""Tests for Task 42: Edge endpoint precision.

Verifies that edge source endpoints lie exactly on the source node boundary
(no gap) and that target endpoints are correctly positioned for both arrow
edges (arrowhead tip on boundary via marker refX) and open-link edges
(path endpoint on boundary, no marker).
"""

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from merm import render_diagram
from merm.layout.sugiyama import _boundary_point, _route_edge_on_boundary
from merm.layout.types import Point

FIXTURES = Path(__file__).parent / "fixtures"
NS = "{http://www.w3.org/2000/svg}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_on_rect_boundary(
    pt: Point,
    center: tuple[float, float],
    size: tuple[float, float],
    tolerance: float = 0.5,
) -> None:
    """Assert that *pt* lies on the boundary of the axis-aligned rect."""
    cx, cy = center
    hw, hh = size[0] / 2.0, size[1] / 2.0

    on_left_or_right = (
        abs(abs(pt.x - cx) - hw) < tolerance and abs(pt.y - cy) <= hh + tolerance
    )
    on_top_or_bottom = (
        abs(abs(pt.y - cy) - hh) < tolerance and abs(pt.x - cx) <= hw + tolerance
    )
    assert on_left_or_right or on_top_or_bottom, (
        f"Point ({pt.x:.2f}, {pt.y:.2f}) is not on rect boundary "
        f"center=({cx}, {cy}), size={size}"
    )

def _parse_svg_nodes(root: ET.Element) -> dict[str, dict]:
    """Extract node rects from rendered SVG."""
    nodes: dict[str, dict] = {}
    for g in root.iter(f"{NS}g"):
        if g.get("class") == "node":
            nid = g.get("data-id", "")
            rect = g.find(f"{NS}rect")
            if rect is not None:
                x = float(rect.get("x", "0"))
                y = float(rect.get("y", "0"))
                w = float(rect.get("width", "0"))
                h = float(rect.get("height", "0"))
                nodes[nid] = {"x": x, "y": y, "w": w, "h": h}
    return nodes

def _parse_svg_edges(root: ET.Element) -> list[dict]:
    """Extract edge info (source, target, path d-string) from rendered SVG."""
    edges: list[dict] = []
    for g in root.iter(f"{NS}g"):
        if g.get("class") == "edge":
            src = g.get("data-edge-source", "")
            tgt = g.get("data-edge-target", "")
            for path in g.iter(f"{NS}path"):
                d = path.get("d", "")
                marker_end = path.get("marker-end", "")
                if d:
                    edges.append({
                        "source": src,
                        "target": tgt,
                        "d": d,
                        "marker_end": marker_end,
                    })
    return edges

def _parse_path_start(d: str) -> tuple[float, float]:
    """Extract the first M coordinate from a path d-string."""
    m = re.match(r"M\s*([-\d.]+)[,\s]+([-\d.]+)", d)
    assert m, f"Could not parse M from path: {d[:60]}"
    return float(m.group(1)), float(m.group(2))

def _parse_path_end(d: str) -> tuple[float, float]:
    """Extract the last coordinate from a path d-string."""
    # Find all coordinate pairs at the end of L or C or bare segments
    coords = re.findall(r"([-\d.]+)[,\s]+([-\d.]+)", d)
    assert coords, f"Could not parse end from path: {d[:60]}"
    return float(coords[-1][0]), float(coords[-1][1])

def _point_on_rect(
    px: float, py: float,
    rect_x: float, rect_y: float, rect_w: float, rect_h: float,
    tolerance: float = 1.0,
) -> bool:
    """Check if a point lies on the boundary of an SVG rect (x,y,w,h)."""
    # Rect edges
    left = rect_x
    right = rect_x + rect_w
    top = rect_y
    bottom = rect_y + rect_h

    on_left_or_right = (
        (abs(px - left) < tolerance or abs(px - right) < tolerance)
        and top - tolerance <= py <= bottom + tolerance
    )
    on_top_or_bottom = (
        (abs(py - top) < tolerance or abs(py - bottom) < tolerance)
        and left - tolerance <= px <= right + tolerance
    )
    return on_left_or_right or on_top_or_bottom

# ---------------------------------------------------------------------------
# Unit: _boundary_point precision
# ---------------------------------------------------------------------------

class TestBoundaryPoint:
    """_boundary_point must return exact ray-rectangle intersections."""

    def test_vertical_down(self) -> None:
        pt = _boundary_point(100, 100, 80, 54, 0, 1)
        assert pt.x == 100.0
        assert pt.y == 127.0  # 100 + 54/2

    def test_vertical_up(self) -> None:
        pt = _boundary_point(100, 100, 80, 54, 0, -1)
        assert pt.x == 100.0
        assert pt.y == 73.0  # 100 - 54/2

    def test_horizontal_right(self) -> None:
        pt = _boundary_point(100, 100, 80, 54, 1, 0)
        assert pt.x == 140.0  # 100 + 80/2
        assert pt.y == 100.0

    def test_horizontal_left(self) -> None:
        pt = _boundary_point(100, 100, 80, 54, -1, 0)
        assert pt.x == 60.0  # 100 - 80/2
        assert pt.y == 100.0

    def test_45_degree_hits_correct_edge(self) -> None:
        """45-degree diagonal on a non-square rect hits the shorter side."""
        # 80x54 rect at (100, 100). dx=dy=1 -> slope=1.
        # tx_time = 40/1 = 40, ty_time = 27/1 = 27
        # t = min(40, 27) = 27 -> hits top/bottom edge first
        pt = _boundary_point(100, 100, 80, 54, 1, 1)
        assert abs(pt.y - 127.0) < 0.01  # bottom edge
        assert abs(pt.x - 127.0) < 0.01  # 100 + 27

    def test_near_vertical(self) -> None:
        """Near-vertical edge (small dx) should hit top/bottom, not side."""
        pt = _boundary_point(100, 100, 80, 54, 0.01, 1)
        assert abs(pt.y - 127.0) < 0.5  # hits bottom edge

# ---------------------------------------------------------------------------
# Unit: _route_edge_on_boundary gap behavior
# ---------------------------------------------------------------------------

class TestRouteEdgeOnBoundary:
    """Source endpoint has zero gap; target gap is configurable."""

    def test_source_on_boundary_vertical(self) -> None:
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        src_pt, _ = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)
        _assert_on_rect_boundary(src_pt, src_pos, src_size)

    def test_target_on_boundary_vertical(self) -> None:
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        _, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)
        _assert_on_rect_boundary(tgt_pt, tgt_pos, tgt_size)

    def test_source_on_boundary_horizontal(self) -> None:
        src_pos = (50.0, 100.0)
        src_size = (80.0, 54.0)
        tgt_pos = (200.0, 100.0)
        tgt_size = (80.0, 54.0)

        src_pt, _ = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)
        _assert_on_rect_boundary(src_pt, src_pos, src_size)

    def test_target_on_boundary_horizontal(self) -> None:
        src_pos = (50.0, 100.0)
        src_size = (80.0, 54.0)
        tgt_pos = (200.0, 100.0)
        tgt_size = (80.0, 54.0)

        _, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)
        _assert_on_rect_boundary(tgt_pt, tgt_pos, tgt_size)

    def test_source_on_boundary_diagonal(self) -> None:
        src_pos = (50.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (200.0, 200.0)
        tgt_size = (80.0, 54.0)

        src_pt, _ = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)
        _assert_on_rect_boundary(src_pt, src_pos, src_size)

    def test_target_on_boundary_diagonal(self) -> None:
        src_pos = (50.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (200.0, 200.0)
        tgt_size = (80.0, 54.0)

        _, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)
        _assert_on_rect_boundary(tgt_pt, tgt_pos, tgt_size)

    def test_zero_gap_default(self) -> None:
        """Default gaps are zero -- both endpoints on boundary."""
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)

        src_bot = src_pos[1] + src_size[1] / 2
        tgt_top = tgt_pos[1] - tgt_size[1] / 2
        assert abs(src_pt.y - src_bot) < 0.01
        assert abs(tgt_pt.y - tgt_top) < 0.01

    def test_explicit_target_gap(self) -> None:
        """target_gap pulls the target point inward."""
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        _, tgt_pt = _route_edge_on_boundary(
            src_pos, src_size, tgt_pos, tgt_size, target_gap=5.0,
        )
        tgt_top = tgt_pos[1] - tgt_size[1] / 2
        assert tgt_pt.y < tgt_top - 2.0, (
            "target_gap should pull endpoint away from boundary"
        )

    def test_explicit_source_gap(self) -> None:
        """source_gap pulls the source point inward."""
        src_pos = (100.0, 50.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 150.0)
        tgt_size = (80.0, 54.0)

        src_pt, _ = _route_edge_on_boundary(
            src_pos, src_size, tgt_pos, tgt_size, source_gap=5.0,
        )
        src_bot = src_pos[1] + src_size[1] / 2
        assert src_pt.y > src_bot + 2.0, (
            "source_gap should pull endpoint away from boundary"
        )

    def test_same_position_nodes(self) -> None:
        """When nodes are at the same position, return sensible fallback."""
        pos = (100.0, 100.0)
        size = (80.0, 54.0)
        src_pt, tgt_pt = _route_edge_on_boundary(pos, size, pos, size)
        # Should not crash and should return finite points
        assert math.isfinite(src_pt.x) and math.isfinite(src_pt.y)
        assert math.isfinite(tgt_pt.x) and math.isfinite(tgt_pt.y)

    def test_very_short_edge_no_overshoot(self) -> None:
        """Very close nodes should not have endpoints that cross each other."""
        src_pos = (100.0, 100.0)
        src_size = (80.0, 54.0)
        tgt_pos = (100.0, 160.0)  # just 6px gap between boundaries
        tgt_size = (80.0, 54.0)

        src_pt, tgt_pt = _route_edge_on_boundary(src_pos, src_size, tgt_pos, tgt_size)
        # Source point should be above target point for TD layout
        assert src_pt.y <= tgt_pt.y, "Source should not overshoot past target"

# ---------------------------------------------------------------------------
# Integration: SVG edge endpoint validation
# ---------------------------------------------------------------------------

def _render_and_parse(source: str) -> tuple[dict, list[dict]]:
    """Render a diagram and return (nodes, edges)."""
    svg_str = render_diagram(source)
    root = ET.fromstring(svg_str)
    return _parse_svg_nodes(root), _parse_svg_edges(root)

class TestSVGEdgeEndpoints:
    """Parse SVG output and verify edge endpoints lie on node boundaries."""

    def test_arrow_source_on_boundary(self) -> None:
        """Arrow edges: source endpoint on source rect boundary."""
        source = (FIXTURES / "corpus/edges/arrow.mmd").read_text()
        nodes, edges = _render_and_parse(source)
        assert len(edges) >= 2

        for edge in edges:
            src_node = nodes.get(edge["source"])
            if src_node is None:
                continue
            px, py = _parse_path_start(edge["d"])
            assert _point_on_rect(
                px, py, src_node["x"], src_node["y"],
                src_node["w"], src_node["h"], tolerance=1.0,
            ), (
                f"Edge {edge['source']}->{edge['target']}: "
                f"start ({px:.1f},{py:.1f}) not on source rect"
            )

    def test_arrow_target_near_boundary(self) -> None:
        """Arrow edges: target endpoint near target rect boundary."""
        source = (FIXTURES / "corpus/edges/arrow.mmd").read_text()
        nodes, edges = _render_and_parse(source)

        for edge in edges:
            tgt_node = nodes.get(edge["target"])
            if tgt_node is None:
                continue
            px, py = _parse_path_end(edge["d"])
            # For arrow edges the marker refX aligns the tip; the path
            # endpoint should be on (or very near) the boundary.
            assert _point_on_rect(
                px, py, tgt_node["x"], tgt_node["y"],
                tgt_node["w"], tgt_node["h"], tolerance=1.0,
            ), (
                f"Edge {edge['source']}->{edge['target']}: "
                f"end ({px:.1f},{py:.1f}) not near target rect"
            )

    def test_open_link_both_on_boundary(self) -> None:
        """Open-link edges (---): both endpoints on rect boundaries."""
        source = (FIXTURES / "corpus/edges/open_link.mmd").read_text()
        nodes, edges = _render_and_parse(source)
        assert len(edges) >= 2

        for edge in edges:
            src_node = nodes.get(edge["source"])
            tgt_node = nodes.get(edge["target"])
            if src_node is None or tgt_node is None:
                continue

            sx, sy = _parse_path_start(edge["d"])
            assert _point_on_rect(
                sx, sy, src_node["x"], src_node["y"],
                src_node["w"], src_node["h"], tolerance=1.0,
            ), (
                f"Open-link {edge['source']}->{edge['target']}: "
                f"start ({sx:.1f},{sy:.1f}) not on source rect"
            )

            tx, ty = _parse_path_end(edge["d"])
            assert _point_on_rect(
                tx, ty, tgt_node["x"], tgt_node["y"],
                tgt_node["w"], tgt_node["h"], tolerance=1.0,
            ), (
                f"Open-link {edge['source']}->{edge['target']}: "
                f"end ({tx:.1f},{ty:.1f}) not on target rect"
            )

    def test_diamond_fan_out(self) -> None:
        """Diamond graph: fan-out source endpoints validated."""
        source = (FIXTURES / "corpus/basic/diamond.mmd").read_text()
        nodes, edges = _render_and_parse(source)

        for edge in edges:
            src_node = nodes.get(edge["source"])
            if src_node is None:
                continue
            px, py = _parse_path_start(edge["d"])
            assert _point_on_rect(
                px, py, src_node["x"], src_node["y"],
                src_node["w"], src_node["h"], tolerance=1.0,
            ), (
                f"Diamond {edge['source']}->{edge['target']}: "
                f"start ({px:.1f},{py:.1f}) not on source rect"
            )

    def test_cross_boundary_edges(self) -> None:
        """Cross-boundary subgraph edges: all endpoints on boundaries."""
        source = (FIXTURES / "corpus/subgraphs/cross_boundary_edges.mmd").read_text()
        nodes, edges = _render_and_parse(source)

        for edge in edges:
            src_node = nodes.get(edge["source"])
            tgt_node = nodes.get(edge["target"])
            if src_node is None or tgt_node is None:
                continue
            px, py = _parse_path_start(edge["d"])
            assert _point_on_rect(
                px, py, src_node["x"], src_node["y"],
                src_node["w"], src_node["h"], tolerance=1.5,
            ), (
                f"Cross-boundary {edge['source']}->{edge['target']}: "
                f"start ({px:.1f},{py:.1f}) not on source rect"
            )

    def test_lr_direction(self) -> None:
        """LR direction: horizontal edges have endpoints on boundaries."""
        source = (FIXTURES / "corpus/direction/lr.mmd").read_text()
        nodes, edges = _render_and_parse(source)

        for edge in edges:
            src_node = nodes.get(edge["source"])
            if src_node is None:
                continue
            px, py = _parse_path_start(edge["d"])
            assert _point_on_rect(
                px, py, src_node["x"], src_node["y"],
                src_node["w"], src_node["h"], tolerance=1.0,
            ), (
                f"LR {edge['source']}->{edge['target']}: "
                f"start ({px:.1f},{py:.1f}) not on source rect"
            )

    def test_rl_direction(self) -> None:
        """RL direction: horizontal edges have endpoints on boundaries."""
        source = (FIXTURES / "corpus/direction/rl.mmd").read_text()
        nodes, edges = _render_and_parse(source)

        for edge in edges:
            src_node = nodes.get(edge["source"])
            if src_node is None:
                continue
            px, py = _parse_path_start(edge["d"])
            assert _point_on_rect(
                px, py, src_node["x"], src_node["y"],
                src_node["w"], src_node["h"], tolerance=1.0,
            ), (
                f"RL {edge['source']}->{edge['target']}: "
                f"start ({px:.1f},{py:.1f}) not on source rect"
            )

    def test_bt_direction(self) -> None:
        """BT direction: vertical edges have endpoints on boundaries."""
        source = "flowchart BT\n    A --> B --> C"
        nodes, edges = _render_and_parse(source)

        for edge in edges:
            src_node = nodes.get(edge["source"])
            if src_node is None:
                continue
            px, py = _parse_path_start(edge["d"])
            assert _point_on_rect(
                px, py, src_node["x"], src_node["y"],
                src_node["w"], src_node["h"], tolerance=1.0,
            ), (
                f"BT {edge['source']}->{edge['target']}: "
                f"start ({px:.1f},{py:.1f}) not on source rect"
            )

# ---------------------------------------------------------------------------
# Integration: marker alignment
# ---------------------------------------------------------------------------

class TestMarkerAlignment:
    """Arrow markers should use refX-based alignment with the target boundary."""

    def test_arrow_marker_refx_is_10(self) -> None:
        """Arrow marker refX=10: tip (at x=10 in viewBox) aligns at path end."""
        from merm.render.edges import make_edge_defs

        defs = ET.Element("defs")
        make_edge_defs(defs)
        for marker in defs.iter("marker"):
            if marker.get("id") == "arrow":
                assert marker.get("refX") == "10"
                return
        raise AssertionError("Arrow marker not found")

    def test_circle_end_marker_refx(self) -> None:
        from merm.render.edges import make_edge_defs

        defs = ET.Element("defs")
        make_edge_defs(defs)
        for marker in defs.iter("marker"):
            if marker.get("id") == "circle-end":
                assert marker.get("refX") == "10"
                return
        raise AssertionError("circle-end marker not found")

    def test_cross_end_marker_refx(self) -> None:
        from merm.render.edges import make_edge_defs

        defs = ET.Element("defs")
        make_edge_defs(defs)
        for marker in defs.iter("marker"):
            if marker.get("id") == "cross-end":
                assert marker.get("refX") == "10"
                return
        raise AssertionError("cross-end marker not found")

    def test_circle_endpoint_renders(self) -> None:
        source = "flowchart TD\n    A --o B"
        svg_str = render_diagram(source)
        assert "circle-end" in svg_str

    def test_cross_endpoint_renders(self) -> None:
        source = "flowchart TD\n    A --x B"
        svg_str = render_diagram(source)
        assert "cross-end" in svg_str
