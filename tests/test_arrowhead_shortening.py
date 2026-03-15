"""Tests for arrowhead path shortening.

The edge path stroke should NOT extend all the way to the target node boundary.
Instead, the path should be shortened by the marker length so the arrowhead
triangle cleanly fills the gap between the path end and the node border.

Without shortening, the 2px stroke line extends through the arrowhead
triangle, creating a visible "stem" at the narrow tip.
"""

import math
import xml.etree.ElementTree as ET

from merm import render_diagram
from merm.render.edges import _MARKER_SHORTEN

_SVG_NS = "http://www.w3.org/2000/svg"


def _parse_path_endpoint(d: str) -> tuple[float, float]:
    """Extract the final point from a path d-string (L or C command)."""
    import re
    # Find all coordinate pairs (possibly prefixed by M, L, C commands)
    coords = re.findall(r"(-?\d+\.?\d*),(-?\d+\.?\d*)", d)
    if coords:
        return float(coords[-1][0]), float(coords[-1][1])
    raise ValueError(f"Cannot parse endpoint from path: {d}")


def _parse_path_startpoint(d: str) -> tuple[float, float]:
    """Extract the start point from a path d-string (M command)."""
    # "Mx,y ..."
    d = d.strip()
    assert d.startswith("M")
    rest = d[1:].split()[0]
    if "," in rest:
        x, y = rest.split(",")
        return float(x), float(y)
    return float(rest), 0.0


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
        cls = g.get("class", "")
        node_id = g.get("data-node-id") or g.get("data-state-id")
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
        polygon = g.find(f"{{{_SVG_NS}}}polygon")
        if polygon is not None:
            pts_str = polygon.get("points", "")
            coords = []
            for pair in pts_str.split():
                x, y = pair.split(",")
                coords.append((float(x), float(y)))
            if coords:
                xs = [c[0] for c in coords]
                ys = [c[1] for c in coords]
                nodes[node_id] = {
                    "x": min(xs),
                    "y": min(ys),
                    "w": max(xs) - min(xs),
                    "h": max(ys) - min(ys),
                }
    return nodes


def _dist_to_rect_boundary(px: float, py: float, rect: dict) -> float:
    """Distance from point to nearest rectangle boundary edge."""
    x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
    # Clamp point to rect boundary
    cx = max(x, min(px, x + w))
    cy = max(y, min(py, y + h))
    # If point is inside, distance to nearest edge
    if x <= px <= x + w and y <= py <= y + h:
        return min(px - x, x + w - px, py - y, y + h - py)
    return math.hypot(px - cx, py - cy)


class TestMarkerShortenConstant:
    """The _MARKER_SHORTEN constant must be > 0 to prevent stroke overlap."""

    def test_marker_shorten_is_positive(self):
        """Path shortening must be enabled (> 0) to prevent stroke through arrowhead."""
        assert _MARKER_SHORTEN > 0, (
            f"_MARKER_SHORTEN={_MARKER_SHORTEN} but must be > 0. "
            f"Without shortening, the path stroke extends through the arrowhead "
            f"triangle, creating a visible stem at the tip."
        )

    def test_marker_shorten_matches_marker_width(self):
        """Shortening should approximately match markerWidth (8) for clean arrowheads."""
        assert 6 <= _MARKER_SHORTEN <= 10, (
            f"_MARKER_SHORTEN={_MARKER_SHORTEN} should be ~8 (the markerWidth). "
            f"Too small = stem still visible, too large = gap before node."
        )


class TestPathEndpointShortened:
    """Edge path endpoints should stop short of the node boundary by marker length."""

    def test_flowchart_tb_arrow_shortened(self):
        """Vertical flowchart arrow should stop ~8px before target node."""
        svg = render_diagram("flowchart TB\n    A --> B")
        edges = _get_edge_paths(svg)
        nodes = _get_node_bounds(svg)
        assert len(edges) >= 1
        edge = edges[0]
        if edge["marker_end"]:
            ex, ey = _parse_path_endpoint(edge["d"])
            target = nodes.get(edge["target"])
            if target:
                dist = _dist_to_rect_boundary(ex, ey, target)
                assert dist >= 4, (
                    f"Path endpoint ({ex:.1f}, {ey:.1f}) is only {dist:.1f}px "
                    f"from target node boundary — should be ~8px (marker length). "
                    f"The path stroke will extend through the arrowhead."
                )

    def test_flowchart_lr_arrow_shortened(self):
        """Horizontal flowchart arrow should stop ~8px before target node."""
        svg = render_diagram("flowchart LR\n    A --> B")
        edges = _get_edge_paths(svg)
        nodes = _get_node_bounds(svg)
        assert len(edges) >= 1
        edge = edges[0]
        if edge["marker_end"]:
            ex, ey = _parse_path_endpoint(edge["d"])
            target = nodes.get(edge["target"])
            if target:
                dist = _dist_to_rect_boundary(ex, ey, target)
                assert dist >= 4, (
                    f"Path endpoint ({ex:.1f}, {ey:.1f}) is only {dist:.1f}px "
                    f"from target — should be ~8px."
                )

    def test_state_diagram_arrow_shortened(self):
        """State diagram arrows should stop short of target state boxes."""
        svg = render_diagram(
            "stateDiagram-v2\n    [*] --> Still\n    Still --> Moving\n"
            "    Moving --> Crash\n    Crash --> [*]"
        )
        edges = _get_edge_paths(svg)
        nodes = _get_node_bounds(svg)
        for edge in edges:
            if not edge["marker_end"]:
                continue
            target = nodes.get(edge["target"])
            if not target:
                continue  # Skip [*] pseudo-nodes
            ex, ey = _parse_path_endpoint(edge["d"])
            dist = _dist_to_rect_boundary(ex, ey, target)
            assert dist >= 4, (
                f"Edge {edge['source']}->{edge['target']}: path endpoint "
                f"is only {dist:.1f}px from target boundary."
            )

    def test_diagonal_arrow_shortened(self):
        """Diagonal arrows (LR with multiple targets) should also be shortened."""
        svg = render_diagram(
            "flowchart LR\n    A --> B\n    A --> C"
        )
        edges = _get_edge_paths(svg)
        nodes = _get_node_bounds(svg)
        for edge in edges:
            if not edge["marker_end"]:
                continue
            target = nodes.get(edge["target"])
            if not target:
                continue
            ex, ey = _parse_path_endpoint(edge["d"])
            dist = _dist_to_rect_boundary(ex, ey, target)
            assert dist >= 4, (
                f"Diagonal edge {edge['source']}->{edge['target']}: "
                f"path endpoint is only {dist:.1f}px from target."
            )
