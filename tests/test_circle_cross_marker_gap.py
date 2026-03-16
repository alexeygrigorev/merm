"""Tests for issue 91: Circle and cross endpoint markers must touch target node.

Circle (--o) and cross (--x) markers use smaller refX values than arrow
markers. The path shortening must be per-marker-type so these markers
reach the node border without a visible gap.
"""

import math
import xml.etree.ElementTree as ET

from merm import render_diagram
from merm.ir import ArrowType
from merm.layout import Point
from merm.render.edges import (
    _MARKER_SHORTEN_BY_ARROW,
    _marker_shorten,
    _shorten_end,
)

_SVG_NS = "http://www.w3.org/2000/svg"


def _parse_path_endpoint(d: str) -> tuple[float, float]:
    """Extract the final point from a path d-string."""
    import re
    coords = re.findall(r"(-?\d+\.?\d*),(-?\d+\.?\d*)", d)
    if coords:
        return float(coords[-1][0]), float(coords[-1][1])
    raise ValueError(f"Cannot parse endpoint from path: {d}")


def _get_edge_paths(svg: str) -> list[dict]:
    """Extract edge path data with source/target info."""
    root = ET.fromstring(svg)
    edges = []
    for g in root.findall(f".//{{{_SVG_NS}}}g"):
        cls = g.get("class", "")
        if "edge" not in cls:
            continue
        source = g.get("data-edge-source", "")
        target = g.get("data-edge-target", "")
        path = g.find(f"{{{_SVG_NS}}}path")
        if path is not None and source and target:
            edges.append({
                "source": source,
                "target": target,
                "d": path.get("d", ""),
                "marker_end": path.get("marker-end", ""),
            })
    return edges


def _get_node_bounds(svg: str) -> dict[str, dict]:
    """Extract node bounding boxes from SVG."""
    root = ET.fromstring(svg)
    nodes = {}
    for g in root.findall(f".//{{{_SVG_NS}}}g"):
        node_id = g.get("data-node-id")
        if not node_id:
            continue
        rect = g.find(f"{{{_SVG_NS}}}rect")
        if rect is not None:
            nodes[node_id] = {
                "x": float(rect.get("x", "0")),
                "y": float(rect.get("y", "0")),
                "w": float(rect.get("width", "0")),
                "h": float(rect.get("height", "0")),
            }
    return nodes


def _dist_to_rect_boundary(px: float, py: float, rect: dict) -> float:
    """Distance from point to nearest rectangle boundary edge."""
    x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
    cx = max(x, min(px, x + w))
    cy = max(y, min(py, y + h))
    if x <= px <= x + w and y <= py <= y + h:
        return min(px - x, x + w - px, py - y, y + h - py)
    return math.hypot(px - cx, py - cy)


# ---------------------------------------------------------------------------
# Unit tests for per-marker shortening values
# ---------------------------------------------------------------------------


class TestMarkerShortenValues:
    """Per-marker shortening must match each marker's geometry."""

    def test_arrow_shorten_is_8(self):
        assert _marker_shorten(ArrowType.arrow) == 8.0

    def test_circle_shorten_is_5(self):
        assert _marker_shorten(ArrowType.circle) == 5.0

    def test_cross_shorten_is_5_5(self):
        assert _marker_shorten(ArrowType.cross) == 5.5

    def test_none_shorten_is_0(self):
        assert _marker_shorten(ArrowType.none) == 0.0

    def test_circle_shorten_less_than_arrow(self):
        """Circle marker shortening must be less than arrow (smaller refX)."""
        assert _marker_shorten(ArrowType.circle) < _marker_shorten(ArrowType.arrow)

    def test_cross_shorten_less_than_arrow(self):
        """Cross marker shortening must be less than arrow (smaller refX)."""
        assert _marker_shorten(ArrowType.cross) < _marker_shorten(ArrowType.arrow)

    def test_all_arrow_types_have_entries(self):
        """Every ArrowType must have a shortening value defined."""
        for at in ArrowType:
            assert at in _MARKER_SHORTEN_BY_ARROW, (
                f"ArrowType.{at.name} missing from _MARKER_SHORTEN_BY_ARROW"
            )


class TestShortenEndPerMarker:
    """_shorten_end with per-marker amounts produces correct offsets."""

    def test_shorten_end_by_5_circle(self):
        """Circle marker: path shortened by 5px, not 8px."""
        pts = [Point(100, 0), Point(100, 100)]
        shortened = _shorten_end(pts, 5.0)
        # Last point should be at y=95 (100 - 5)
        assert abs(shortened[-1].y - 95.0) < 0.01

    def test_shorten_end_by_5_5_cross(self):
        """Cross marker: path shortened by 5.5px."""
        pts = [Point(100, 0), Point(100, 100)]
        shortened = _shorten_end(pts, 5.5)
        assert abs(shortened[-1].y - 94.5) < 0.01

    def test_shorten_end_by_8_arrow(self):
        """Arrow marker: path shortened by 8px (unchanged behavior)."""
        pts = [Point(100, 0), Point(100, 100)]
        shortened = _shorten_end(pts, 8.0)
        assert abs(shortened[-1].y - 92.0) < 0.01


# ---------------------------------------------------------------------------
# Integration tests: rendered SVG endpoint proximity
# ---------------------------------------------------------------------------


class TestCircleEndpointTouchesNode:
    """Circle endpoint (--o) must touch the target node, not leave a gap."""

    def test_circle_endpoint_near_node(self):
        """Path endpoint with circle marker should be ~5px from node (not ~8px)."""
        svg = render_diagram("graph TD\n    A --o B")
        edges = _get_edge_paths(svg)
        nodes = _get_node_bounds(svg)

        circle_edges = [e for e in edges if "circle" in e["marker_end"]]
        assert len(circle_edges) >= 1, "Expected at least one circle-end edge"

        for edge in circle_edges:
            target = nodes.get(edge["target"])
            if not target:
                continue
            ex, ey = _parse_path_endpoint(edge["d"])
            dist = _dist_to_rect_boundary(ex, ey, target)
            # With circle shorten=5, dist should be ~5, not ~8
            # Allow some tolerance but ensure it's closer than arrow (8)
            assert dist < 7, (
                f"Circle endpoint ({ex:.1f}, {ey:.1f}) is {dist:.1f}px from "
                f"target node — should be ~5px (circle marker refX=5). "
                f"A gap > 7px means the old constant shortening is still used."
            )


class TestCrossEndpointTouchesNode:
    """Cross endpoint (--x) must touch the target node, not leave a gap."""

    def test_cross_endpoint_near_node(self):
        """Path endpoint with cross marker should be ~5.5px from node."""
        svg = render_diagram("graph TD\n    A --x B")
        edges = _get_edge_paths(svg)
        nodes = _get_node_bounds(svg)

        cross_edges = [e for e in edges if "cross" in e["marker_end"]]
        assert len(cross_edges) >= 1, "Expected at least one cross-end edge"

        for edge in cross_edges:
            target = nodes.get(edge["target"])
            if not target:
                continue
            ex, ey = _parse_path_endpoint(edge["d"])
            dist = _dist_to_rect_boundary(ex, ey, target)
            assert dist < 7, (
                f"Cross endpoint ({ex:.1f}, {ey:.1f}) is {dist:.1f}px from "
                f"target node — should be ~5.5px (cross marker refX=5.5)."
            )


class TestArrowStillWorks:
    """Arrow markers must continue to work correctly after the change."""

    def test_arrow_endpoint_shortened_by_8(self):
        """Arrow endpoint should still be ~8px from target node."""
        svg = render_diagram("graph TD\n    A --> B")
        edges = _get_edge_paths(svg)
        nodes = _get_node_bounds(svg)

        arrow_edges = [e for e in edges if "arrow" in e["marker_end"]
                       and "circle" not in e["marker_end"]
                       and "cross" not in e["marker_end"]]
        assert len(arrow_edges) >= 1

        for edge in arrow_edges:
            target = nodes.get(edge["target"])
            if not target:
                continue
            ex, ey = _parse_path_endpoint(edge["d"])
            dist = _dist_to_rect_boundary(ex, ey, target)
            # Arrow shortening = 8, so distance should be around 8
            assert dist >= 4, (
                f"Arrow endpoint too close to node: {dist:.1f}px"
            )


class TestMultipleMarkerTypes:
    """Mixed marker types in the same diagram."""

    def test_mixed_arrow_and_circle(self):
        """Diagram with both arrow and circle markers should use correct shortening."""
        svg = render_diagram("graph TD\n    A --> B\n    B --o C")
        edges = _get_edge_paths(svg)
        nodes = _get_node_bounds(svg)

        for edge in edges:
            target = nodes.get(edge["target"])
            if not target:
                continue
            ex, ey = _parse_path_endpoint(edge["d"])
            dist = _dist_to_rect_boundary(ex, ey, target)
            if "circle" in edge["marker_end"]:
                assert dist < 7, (
                    f"Circle edge {edge['source']}->{edge['target']}: "
                    f"gap is {dist:.1f}px, should be ~5px"
                )
            elif "arrow" in edge["marker_end"]:
                assert dist >= 4, (
                    f"Arrow edge {edge['source']}->{edge['target']}: "
                    f"gap is only {dist:.1f}px, should be ~8px"
                )
