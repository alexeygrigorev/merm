"""Tests for issue 83: edge labels must not overlap diamond node borders."""

import xml.etree.ElementTree as ET

from merm.ir import Edge, EdgeType
from merm.layout import EdgeLayout, Point
from merm.render.edges import (
    _point_along_polyline,
    _rects_overlap,
    resolve_label_positions,
)

_NS = "http://www.w3.org/2000/svg"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_edge_layout(
    source: str, target: str, points: list[tuple[float, float]],
) -> EdgeLayout:
    return EdgeLayout(
        source=source,
        target=target,
        points=[Point(x=x, y=y) for x, y in points],
    )


def _make_ir_edge(
    source: str, target: str, label: str,
    edge_type: EdgeType = EdgeType.arrow,
) -> Edge:
    return Edge(source=source, target=target, label=label, edge_type=edge_type)


# ---------------------------------------------------------------------------
# Unit: _point_along_polyline
# ---------------------------------------------------------------------------

class TestPointAlongPolyline:
    def test_empty(self) -> None:
        assert _point_along_polyline([], 0.5) == (0.0, 0.0)

    def test_single_point(self) -> None:
        pts = [Point(10, 20)]
        assert _point_along_polyline(pts, 0.5) == (10.0, 20.0)

    def test_two_points_midpoint(self) -> None:
        pts = [Point(0, 0), Point(100, 0)]
        x, y = _point_along_polyline(pts, 0.5)
        assert abs(x - 50.0) < 0.01
        assert abs(y - 0.0) < 0.01

    def test_two_points_start(self) -> None:
        pts = [Point(0, 0), Point(100, 0)]
        x, y = _point_along_polyline(pts, 0.0)
        assert abs(x - 0.0) < 0.01
        assert abs(y - 0.0) < 0.01

    def test_two_points_end(self) -> None:
        pts = [Point(0, 0), Point(100, 0)]
        x, y = _point_along_polyline(pts, 1.0)
        assert abs(x - 100.0) < 0.01
        assert abs(y - 0.0) < 0.01

    def test_two_points_65_percent(self) -> None:
        pts = [Point(0, 0), Point(0, 200)]
        x, y = _point_along_polyline(pts, 0.65)
        assert abs(x - 0.0) < 0.01
        assert abs(y - 130.0) < 0.01

    def test_three_segments(self) -> None:
        pts = [Point(0, 0), Point(100, 0), Point(100, 100), Point(200, 100)]
        # Total length = 100 + 100 + 100 = 300
        x, y = _point_along_polyline(pts, 0.5)
        # At 150/300, we are at (100, 50)
        assert abs(x - 100.0) < 0.01
        assert abs(y - 50.0) < 0.01


# ---------------------------------------------------------------------------
# Unit: resolve_label_positions with diamond_node_ids
# ---------------------------------------------------------------------------

class TestResolveLabelPositionsDiamond:
    def test_source_diamond_biases_toward_target(self) -> None:
        """When source is diamond, label shifts from 50% toward 65% of edge."""
        el = _make_edge_layout("D", "R", [(100, 0), (100, 200)])
        ir = _make_ir_edge("D", "R", "Yes")
        result = resolve_label_positions(
            [(el, ir)], diamond_node_ids={"D"},
        )
        cx, cy = result[("D", "R")]
        # Without diamond bias: midpoint would be (100, 100).
        # With bias at 0.65: should be (100, 130).
        assert abs(cx - 100.0) < 0.01
        assert abs(cy - 130.0) < 0.01

    def test_target_diamond_biases_toward_source(self) -> None:
        """When target is diamond, label shifts from 50% toward 35%."""
        el = _make_edge_layout("R", "D", [(100, 0), (100, 200)])
        ir = _make_ir_edge("R", "D", "No")
        result = resolve_label_positions(
            [(el, ir)], diamond_node_ids={"D"},
        )
        cx, cy = result[("R", "D")]
        # Bias at 0.35: should be (100, 70).
        assert abs(cx - 100.0) < 0.01
        assert abs(cy - 70.0) < 0.01

    def test_both_diamond_uses_midpoint(self) -> None:
        """When both source and target are diamond, use standard midpoint."""
        el = _make_edge_layout("D1", "D2", [(100, 0), (100, 200)])
        ir = _make_ir_edge("D1", "D2", "maybe")
        result = resolve_label_positions(
            [(el, ir)], diamond_node_ids={"D1", "D2"},
        )
        cx, cy = result[("D1", "D2")]
        assert abs(cx - 100.0) < 0.01
        assert abs(cy - 100.0) < 0.01

    def test_no_diamond_ids_uses_midpoint(self) -> None:
        """When diamond_node_ids is None, behave as before (midpoint)."""
        el = _make_edge_layout("A", "B", [(100, 0), (100, 200)])
        ir = _make_ir_edge("A", "B", "label")
        result = resolve_label_positions([(el, ir)])
        cx, cy = result[("A", "B")]
        assert abs(cx - 100.0) < 0.01
        assert abs(cy - 100.0) < 0.01

    def test_non_diamond_edge_unaffected(self) -> None:
        """Edges between non-diamond nodes are not biased."""
        el = _make_edge_layout("A", "B", [(100, 0), (100, 200)])
        ir = _make_ir_edge("A", "B", "label")
        result = resolve_label_positions(
            [(el, ir)], diamond_node_ids={"D"},
        )
        cx, cy = result[("A", "B")]
        assert abs(cx - 100.0) < 0.01
        assert abs(cy - 100.0) < 0.01


# ---------------------------------------------------------------------------
# Integration: coffee_machine.mmd labels don't overlap diamond borders
# ---------------------------------------------------------------------------

def _find_child(parent: ET.Element, tag: str) -> ET.Element | None:
    el = parent.find(f"{{{_NS}}}{tag}")
    if el is None:
        el = parent.find(tag)
    return el


class TestCoffeeMachineDiamondLabels:
    """Integration test using the coffee_machine.mmd fixture."""

    def test_labels_outside_diamond_borders(self) -> None:
        """All edge labels must be fully outside diamond node boundaries."""
        from merm import render_diagram

        with open("tests/fixtures/corpus/flowchart/coffee_machine.mmd") as f:
            source = f.read()
        svg = render_diagram(source)
        root = ET.fromstring(svg)

        # Collect diamond node bounding boxes from the SVG.
        # Diamond nodes are rendered as <polygon> inside <g class="node">.
        diamond_bboxes: list[tuple[float, float, float, float]] = []
        for g in root.iter(f"{{{_NS}}}g"):
            if g.get("class") != "node":
                continue
            polygon = _find_child(g, "polygon")
            if polygon is None:
                continue
            # Parse polygon points to get bounding box.
            pts_str = polygon.get("points", "")
            if not pts_str:
                continue
            coords = []
            for pair in pts_str.strip().split():
                parts = pair.split(",")
                if len(parts) == 2:
                    coords.append((float(parts[0]), float(parts[1])))
            if not coords:
                continue
            xs = [c[0] for c in coords]
            ys = [c[1] for c in coords]
            diamond_bboxes.append(
                (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            )

        assert len(diamond_bboxes) >= 3, (
            f"Expected at least 3 diamond nodes, found {len(diamond_bboxes)}"
        )

        # Collect label background rects.
        label_rects: list[tuple[str, tuple[float, float, float, float]]] = []
        for g in root.iter(f"{{{_NS}}}g"):
            if g.get("class") not in ("edge", "edge-label"):
                continue
            rect = _find_child(g, "rect")
            text = _find_child(g, "text")
            if rect is None or text is None:
                continue
            x = float(rect.get("x", "0"))
            y = float(rect.get("y", "0"))
            w = float(rect.get("width", "0"))
            h = float(rect.get("height", "0"))
            label_text = text.text or ""
            label_rects.append((label_text, (x, y, w, h)))

        expected_labels = {"Yes", "No"}
        found_labels = {lr[0] for lr in label_rects}
        for exp in expected_labels:
            assert exp in found_labels, f"Label {exp!r} not found in SVG"

        # Verify no label rect overlaps any diamond bounding box.
        for label_text, lrect in label_rects:
            for i, dbox in enumerate(diamond_bboxes):
                assert not _rects_overlap(lrect, dbox), (
                    f"Label {label_text!r} rect {lrect} overlaps diamond "
                    f"bbox {dbox}"
                )
