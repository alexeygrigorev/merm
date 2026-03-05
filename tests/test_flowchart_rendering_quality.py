"""Tests for flowchart rendering quality improvements (task 51).

Covers:
1. Back-edge channel separation
2. Back-edge anchor point fan-out
3. Parent-child horizontal alignment
4. Edge labels avoid crossing back-edge paths
5. Edge crossing gaps (deferred)
6. Parallelogram/trapezoid width
7. Consistent vertical spacing
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest

from pymermaid import render_diagram
from pymermaid.ir import Diagram, DiagramType, Direction, Edge, Node, NodeShape
from pymermaid.layout import EdgeLayout, LayoutResult, Point, layout_diagram

NS = {"svg": "http://www.w3.org/2000/svg"}

# ---------------------------------------------------------------------------
# Helpers (reused from test_back_edge_routing.py patterns)
# ---------------------------------------------------------------------------


def _measure(text: str, font_size: float) -> tuple[float, float]:
    """Simple measure function for testing."""
    return (len(text) * font_size * 0.6, font_size * 1.2)


def _make_diagram(
    node_ids: list[str],
    edges: list[tuple[str, str]],
    direction: Direction = Direction.TB,
    shapes: dict[str, NodeShape] | None = None,
    labels: dict[tuple[str, str], str] | None = None,
) -> Diagram:
    nodes = tuple(
        Node(
            id=nid, label=nid,
            shape=shapes.get(nid, NodeShape.rect) if shapes else NodeShape.rect,
        )
        for nid in node_ids
    )
    ir_edges = tuple(
        Edge(source=s, target=t, label=labels.get((s, t), "") if labels else "")
        for s, t in edges
    )
    return Diagram(
        type=DiagramType.flowchart,
        direction=direction,
        nodes=nodes,
        edges=ir_edges,
    )


def _get_edge_layout(
    result: LayoutResult, source: str, target: str,
) -> EdgeLayout | None:
    """Find the EdgeLayout for a given source->target pair."""
    for el in result.edges:
        if el.source == source and el.target == target:
            return el
    return None


def _intermediate_points(el: EdgeLayout) -> list[Point]:
    """Return the waypoints between source and target endpoints."""
    if len(el.points) <= 2:
        return []
    return el.points[1:-1]


def _parse_path_x_coords(d_attr: str) -> list[float]:
    """Extract all x-coordinates from an SVG path d attribute."""
    # Match numbers that appear as x-coords in M, L, C commands
    # Pattern: number before comma (x,y pairs)
    coords = re.findall(r"(-?[\d.]+),(-?[\d.]+)", d_attr)
    return [float(x) for x, _ in coords]


def _parse_path_coords(d_attr: str) -> list[tuple[float, float]]:
    """Extract all (x,y) coordinate pairs from an SVG path d attribute."""
    coords = re.findall(r"(-?[\d.]+),(-?[\d.]+)", d_attr)
    return [(float(x), float(y)) for x, y in coords]


def _load_registration_mmd() -> str:
    with open("tests/fixtures/corpus/flowchart/registration.mmd") as f:
        return f.read()


def _render_registration_svg() -> str:
    return render_diagram(_load_registration_mmd())


def _parse_svg(svg: str) -> ET.Element:
    return ET.fromstring(svg)


def _find_edge_elements(
    root: ET.Element, source: str, target: str,
) -> list[ET.Element]:
    """Find edge <g> elements matching source/target."""
    results = []
    for g in root.iter("{http://www.w3.org/2000/svg}g"):
        if g.get("class") == "edge":
            src_match = g.get("data-edge-source") == source
            tgt_match = g.get("data-edge-target") == target
            if src_match and tgt_match:
                results.append(g)
    # Also try without namespace (some SVGs don't use ns prefix)
    if not results:
        for g in root.iter("g"):
            if g.get("class") == "edge":
                src_match = g.get("data-edge-source") == source
                tgt_match = g.get("data-edge-target") == target
                if src_match and tgt_match:
                    results.append(g)
    return results


def _find_node_element(root: ET.Element, node_id: str) -> ET.Element | None:
    """Find node <g> element by data-node-id."""
    for g in root.iter("{http://www.w3.org/2000/svg}g"):
        if g.get("class") == "node" and g.get("data-node-id") == node_id:
            return g
    for g in root.iter("g"):
        if g.get("class") == "node" and g.get("data-node-id") == node_id:
            return g
    return None


def _get_edge_path_d(edge_g: ET.Element) -> str:
    """Get the d attribute from the path element of an edge group."""
    for path in edge_g.iter("{http://www.w3.org/2000/svg}path"):
        d = path.get("d")
        if d:
            return d
    for path in edge_g.iter("path"):
        d = path.get("d")
        if d:
            return d
    return ""


# ---------------------------------------------------------------------------
# Issue 1: Back-edge channel separation
# ---------------------------------------------------------------------------


class TestBackEdgeChannelSeparation:
    """Back-edges to the same target must have distinct horizontal channels."""

    def test_registration_layout_intermediate_x_separation(self):
        """Layout level: 3 back-edges in registration pattern have intermediate
        waypoint avg x-coords differing by >= 20px pairwise."""
        diagram = _make_diagram(
            [
                "Form", "Submit", "ValidateEmail", "EmailError",
                "CheckExists", "ExistsError", "ValidatePassword",
                "PasswordError",
            ],
            [
                ("Form", "Submit"),
                ("Submit", "ValidateEmail"),
                ("ValidateEmail", "EmailError"),
                ("EmailError", "Form"),
                ("ValidateEmail", "CheckExists"),
                ("CheckExists", "ExistsError"),
                ("ExistsError", "Form"),
                ("CheckExists", "ValidatePassword"),
                ("ValidatePassword", "PasswordError"),
                ("PasswordError", "Form"),
            ],
        )
        result = layout_diagram(diagram, _measure)

        back_edges = [
            ("EmailError", "Form"),
            ("ExistsError", "Form"),
            ("PasswordError", "Form"),
        ]
        avg_xs = {}
        for src, tgt in back_edges:
            el = _get_edge_layout(result, src, tgt)
            assert el is not None, f"Edge {src}->{tgt} not found"
            pts = _intermediate_points(el)
            assert len(pts) > 0, f"Edge {src}->{tgt} has no intermediate points"
            avg_xs[(src, tgt)] = sum(p.x for p in pts) / len(pts)

        keys = list(avg_xs.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                diff = abs(avg_xs[keys[i]] - avg_xs[keys[j]])
                assert diff >= 20.0, (
                    f"Back-edges {keys[i]} and {keys[j]} intermediate x-coords "
                    f"too close: {diff:.1f}px apart (need >= 20)"
                )

    def test_registration_svg_path_x_separation(self):
        """SVG level: 3 back-edge paths in registration.mmd have max x-coords
        differing by >= 15px pairwise."""
        svg = _render_registration_svg()
        root = _parse_svg(svg)

        back_edge_pairs = [
            ("EmailError", "Form"),
            ("ExistsError", "Form"),
            ("PasswordError", "Form"),
        ]

        max_xs = {}
        for src, tgt in back_edge_pairs:
            edges = _find_edge_elements(root, src, tgt)
            assert len(edges) > 0, f"Edge {src}->{tgt} not found in SVG"
            d = _get_edge_path_d(edges[0])
            assert d, f"No path d attribute for edge {src}->{tgt}"
            x_coords = _parse_path_x_coords(d)
            assert len(x_coords) > 0, f"No x-coords in path for edge {src}->{tgt}"
            max_xs[(src, tgt)] = max(x_coords)

        keys = list(max_xs.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                diff = abs(max_xs[keys[i]] - max_xs[keys[j]])
                assert diff >= 15.0, (
                    f"Back-edge paths {keys[i]} and {keys[j]} max x-coords "
                    f"too close: {diff:.1f}px apart (need >= 15)"
                )


# ---------------------------------------------------------------------------
# Issue 2: Back-edge anchor point fan-out
# ---------------------------------------------------------------------------


class TestBackEdgeAnchorFanOut:
    """Back-edges targeting the same node must land at different x-coordinates."""

    def test_registration_three_back_edges_fan_out(self):
        """3 back-edges to Form must have final-point x-coords >= 8px apart pairwise."""
        diagram = _make_diagram(
            [
                "Form", "Submit", "ValidateEmail", "EmailError",
                "CheckExists", "ExistsError", "ValidatePassword",
                "PasswordError",
            ],
            [
                ("Form", "Submit"),
                ("Submit", "ValidateEmail"),
                ("ValidateEmail", "EmailError"),
                ("EmailError", "Form"),
                ("ValidateEmail", "CheckExists"),
                ("CheckExists", "ExistsError"),
                ("ExistsError", "Form"),
                ("CheckExists", "ValidatePassword"),
                ("ValidatePassword", "PasswordError"),
                ("PasswordError", "Form"),
            ],
        )
        result = layout_diagram(diagram, _measure)

        back_edges = [
            ("EmailError", "Form"),
            ("ExistsError", "Form"),
            ("PasswordError", "Form"),
        ]
        final_xs = {}
        for src, tgt in back_edges:
            el = _get_edge_layout(result, src, tgt)
            assert el is not None, f"Edge {src}->{tgt} not found"
            assert len(el.points) >= 2, f"Edge {src}->{tgt} has < 2 points"
            # The final point is where the edge arrives at the target
            final_xs[(src, tgt)] = el.points[-1].x

        keys = list(final_xs.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                diff = abs(final_xs[keys[i]] - final_xs[keys[j]])
                assert diff >= 8.0, (
                    f"Back-edges {keys[i]} and {keys[j]} final x-coords "
                    f"too close: {diff:.1f}px apart (need >= 8)"
                )

    def test_synthetic_four_back_edges_fan_out(self):
        """4 back-edges to the same target must have 4 distinct attachment
        x-coordinates, minimum 8px apart pairwise."""
        diagram = _make_diagram(
            [
                "Target", "A", "B", "C", "D",
                "ErrA", "ErrB", "ErrC", "ErrD",
            ],
            [
                ("Target", "A"),
                ("A", "B"),
                ("B", "C"),
                ("C", "D"),
                ("A", "ErrA"),
                ("ErrA", "Target"),
                ("B", "ErrB"),
                ("ErrB", "Target"),
                ("C", "ErrC"),
                ("ErrC", "Target"),
                ("D", "ErrD"),
                ("ErrD", "Target"),
            ],
        )
        result = layout_diagram(diagram, _measure)

        back_edges = [
            ("ErrA", "Target"),
            ("ErrB", "Target"),
            ("ErrC", "Target"),
            ("ErrD", "Target"),
        ]
        final_xs = []
        for src, tgt in back_edges:
            el = _get_edge_layout(result, src, tgt)
            assert el is not None, f"Edge {src}->{tgt} not found"
            assert len(el.points) >= 2
            final_xs.append(el.points[-1].x)

        # All 4 should be distinct (>= 8px apart pairwise)
        for i in range(len(final_xs)):
            for j in range(i + 1, len(final_xs)):
                diff = abs(final_xs[i] - final_xs[j])
                assert diff >= 8.0, (
                    f"Back-edges {back_edges[i]} and {back_edges[j]} final x-coords "
                    f"too close: {diff:.1f}px apart (need >= 8)"
                )


# ---------------------------------------------------------------------------
# Issue 3: Parent-child horizontal alignment
# ---------------------------------------------------------------------------


class TestParentChildAlignment:
    """Nodes in a direct parent-child chain should be center-aligned."""

    def test_linear_chain_same_center_x(self):
        """A -> B -> C -> D: all 4 nodes share center-x within 1px."""
        diagram = _make_diagram(
            ["A", "B", "C", "D"],
            [("A", "B"), ("B", "C"), ("C", "D")],
        )
        result = layout_diagram(diagram, _measure)

        centers = []
        for nid in ["A", "B", "C", "D"]:
            nl = result.nodes[nid]
            cx = nl.x + nl.width / 2.0
            centers.append(cx)

        for i in range(len(centers)):
            for j in range(i + 1, len(centers)):
                diff = abs(centers[i] - centers[j])
                assert diff < 1.0, (
                    f"Nodes {['A','B','C','D'][i]} and {['A','B','C','D'][j]} "
                    f"center-x differ by {diff:.1f}px (need < 1.0)"
                )

    def test_registration_start_form_submit_aligned(self):
        """Start, Form, Submit in registration.mmd share center-x within 5px."""
        # Extract center-x from layout for Start, Form, Submit
        from pymermaid.measure import TextMeasurer
        from pymermaid.parser import parse_flowchart

        source = _load_registration_mmd()
        diagram = parse_flowchart(source)
        measurer = TextMeasurer()
        result = layout_diagram(diagram, measurer.measure)

        centers = {}
        for nid in ["Start", "Form", "Submit"]:
            nl = result.nodes[nid]
            centers[nid] = nl.x + nl.width / 2.0

        keys = list(centers.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                diff = abs(centers[keys[i]] - centers[keys[j]])
                assert diff < 5.0, (
                    f"Nodes {keys[i]} and {keys[j]} center-x differ by "
                    f"{diff:.1f}px (need < 5.0)"
                )

    def test_diamond_pattern_no_crash(self):
        """Diamond pattern (A->B, A->C, B->D, C->D) does not crash
        and all nodes are present."""
        diagram = _make_diagram(
            ["A", "B", "C", "D"],
            [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")],
        )
        result = layout_diagram(diagram, _measure)
        for nid in ["A", "B", "C", "D"]:
            assert nid in result.nodes, f"Node {nid} missing from layout"


# ---------------------------------------------------------------------------
# Issue 4: Edge labels avoid crossing back-edge paths
# ---------------------------------------------------------------------------


class TestEdgeLabelsAvoidBackEdgePaths:
    """Edge labels must not overlap with back-edge paths."""

    def test_registration_labels_no_overlap_with_back_edges(self):
        """In registration.mmd, no label bbox overlaps any back-edge path bbox."""
        svg = _render_registration_svg()
        root = _parse_svg(svg)

        # Collect back-edge path bounding boxes
        back_edge_pairs = [
            ("EmailError", "Form"),
            ("ExistsError", "Form"),
            ("PasswordError", "Form"),
        ]
        back_edge_bboxes = []
        for src, tgt in back_edge_pairs:
            edges = _find_edge_elements(root, src, tgt)
            for edge_g in edges:
                d = _get_edge_path_d(edge_g)
                if not d:
                    continue
                coords = _parse_path_coords(d)
                if not coords:
                    continue
                xs = [c[0] for c in coords]
                ys = [c[1] for c in coords]
                back_edge_bboxes.append((
                    min(xs), min(ys),
                    max(xs) - min(xs), max(ys) - min(ys),
                ))

        # Collect label bounding boxes (from <rect> elements inside edge groups)
        label_bboxes = []
        for g in root.iter("{http://www.w3.org/2000/svg}g"):
            if g.get("class") != "edge":
                continue
            # Look for rect elements (label backgrounds)
            for rect in g.iter("{http://www.w3.org/2000/svg}rect"):
                x = float(rect.get("x", "0"))
                y = float(rect.get("y", "0"))
                w = float(rect.get("width", "0"))
                h = float(rect.get("height", "0"))
                if w > 0 and h > 0:
                    label_bboxes.append((x, y, w, h))
        # Also try without namespace
        if not label_bboxes:
            for g in root.iter("g"):
                if g.get("class") != "edge":
                    continue
                for rect in g.iter("rect"):
                    x = float(rect.get("x", "0"))
                    y = float(rect.get("y", "0"))
                    w = float(rect.get("width", "0"))
                    h = float(rect.get("height", "0"))
                    if w > 0 and h > 0:
                        label_bboxes.append((x, y, w, h))

        # AABB overlap check
        def rects_overlap(a, b):
            ax, ay, aw, ah = a
            bx, by, bw, bh = b
            return (
                ax < bx + bw
                and ax + aw > bx
                and ay < by + bh
                and ay + ah > by
            )

        for label_bb in label_bboxes:
            for be_bb in back_edge_bboxes:
                assert not rects_overlap(label_bb, be_bb), (
                    f"Label bbox {label_bb} overlaps back-edge path bbox {be_bb}"
                )


# ---------------------------------------------------------------------------
# Issue 5: Edge crossing gaps (deferred)
# ---------------------------------------------------------------------------


class TestEdgeCrossingGaps:
    """Edge crossing gaps -- visual polish feature."""

    @pytest.mark.skip(reason="crossing gaps deferred to a future task")
    def test_crossing_gap_in_forced_crossing_diagram(self):
        """Build a diagram that forces a crossing and verify gap in path.
        TODO: Implement crossing gap detection when this feature is added.
        """
        svg = render_diagram(
            "flowchart TD\n"
            "    A --> C\n"
            "    B --> D\n"
            "    A --> D\n"
            "    B --> C\n"
        )
        _parse_svg(svg)
        # If crossing gaps are implemented, verify M commands near crossings
        # with 4-8px gap width. For now, this test is skipped.
        assert "<svg" in svg


# ---------------------------------------------------------------------------
# Issue 6: Parallelogram/trapezoid width
# ---------------------------------------------------------------------------


class TestParallelogramTrapezoidWidth:
    """Parallelogram and trapezoid nodes should not be excessively wide."""

    def test_parallelogram_short_text_width(self):
        """Parallelogram with short text: width <= 2.5x text width + padding."""
        diagram = _make_diagram(
            ["Hi"],
            [],
            shapes={"Hi": NodeShape.parallelogram},
        )
        result = layout_diagram(diagram, _measure)
        nl = result.nodes["Hi"]
        text_width = len("Hi") * 16.0 * 0.6  # using _measure formula
        max_expected = 2.5 * text_width + 32.0  # 32 = _NODE_PADDING_H
        assert nl.width <= max_expected, (
            f"Parallelogram width {nl.width:.1f} exceeds 2.5 * text_width + padding = "
            f"{max_expected:.1f}"
        )

    def test_parallelogram_long_text_ratio(self):
        """Parallelogram with long text: bbox width / text width ratio <= 2.0."""
        text = "Send verification email"
        diagram = _make_diagram(
            [text],
            [],
            shapes={text: NodeShape.parallelogram},
        )
        result = layout_diagram(diagram, _measure)
        nl = result.nodes[text]
        text_width = len(text) * 7.0  # approximate char width
        ratio = nl.width / text_width
        assert ratio <= 2.0, (
            f"Parallelogram width/text ratio {ratio:.2f} exceeds 2.0 "
            f"(width={nl.width:.1f}, text_width={text_width:.1f})"
        )

    def test_trapezoid_short_text_width(self):
        """Trapezoid with short text: width <= 2.5x text width + padding."""
        diagram = _make_diagram(
            ["Hi"],
            [],
            shapes={"Hi": NodeShape.trapezoid},
        )
        result = layout_diagram(diagram, _measure)
        nl = result.nodes["Hi"]
        text_width = len("Hi") * 16.0 * 0.6
        max_expected = 2.5 * text_width + 32.0
        assert nl.width <= max_expected, (
            f"Trapezoid width {nl.width:.1f} exceeds 2.5 * text_width + padding = "
            f"{max_expected:.1f}"
        )

    def test_trapezoid_long_text_ratio(self):
        """Trapezoid with long text: bbox width / text width ratio <= 2.0."""
        text = "Display registration form"
        diagram = _make_diagram(
            [text],
            [],
            shapes={text: NodeShape.trapezoid},
        )
        result = layout_diagram(diagram, _measure)
        nl = result.nodes[text]
        text_width = len(text) * 7.0
        ratio = nl.width / text_width
        assert ratio <= 2.0, (
            f"Trapezoid width/text ratio {ratio:.2f} exceeds 2.0 "
            f"(width={nl.width:.1f}, text_width={text_width:.1f})"
        )


# ---------------------------------------------------------------------------
# Issue 7: Consistent vertical spacing
# ---------------------------------------------------------------------------


class TestConsistentVerticalSpacing:
    """Vertical gaps between consecutive nodes should be consistent."""

    def test_linear_chain_equal_gaps(self):
        """A -> B -> C -> D -> E: all vertical gaps equal within 1px."""
        diagram = _make_diagram(
            ["A", "B", "C", "D", "E"],
            [("A", "B"), ("B", "C"), ("C", "D"), ("D", "E")],
        )
        result = layout_diagram(diagram, _measure)

        centers_y = []
        for nid in ["A", "B", "C", "D", "E"]:
            nl = result.nodes[nid]
            cy = nl.y + nl.height / 2.0
            centers_y.append(cy)

        gaps = [centers_y[i + 1] - centers_y[i] for i in range(len(centers_y) - 1)]
        for i in range(len(gaps)):
            for j in range(i + 1, len(gaps)):
                diff = abs(gaps[i] - gaps[j])
                assert diff < 1.0, (
                    f"Vertical gaps differ: gap[{i}]={gaps[i]:.1f}, "
                    f"gap[{j}]={gaps[j]:.1f}, diff={diff:.1f}px (need < 1.0)"
                )

    def test_registration_consecutive_layer_gaps(self):
        """Start->Form->Submit vertical gaps consistent within 5px."""
        from pymermaid.measure import TextMeasurer
        from pymermaid.parser import parse_flowchart

        source = _load_registration_mmd()
        diagram = parse_flowchart(source)
        measurer = TextMeasurer()
        result = layout_diagram(diagram, measurer.measure)

        centers_y = {}
        for nid in ["Start", "Form", "Submit"]:
            nl = result.nodes[nid]
            centers_y[nid] = nl.y + nl.height / 2.0

        gap1 = centers_y["Form"] - centers_y["Start"]
        gap2 = centers_y["Submit"] - centers_y["Form"]

        diff = abs(gap1 - gap2)
        assert diff < 5.0, (
            f"Vertical gaps differ: Start->Form={gap1:.1f}, "
            f"Form->Submit={gap2:.1f}, diff={diff:.1f}px (need < 5.0)"
        )


# ---------------------------------------------------------------------------
# Integration: Full regression
# ---------------------------------------------------------------------------


class TestIntegrationRegression:
    """Full render of registration.mmd produces valid SVG."""

    def test_registration_renders_valid_svg(self):
        svg = _render_registration_svg()
        assert "<svg" in svg
        assert "</svg>" in svg
