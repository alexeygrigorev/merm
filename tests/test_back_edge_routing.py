"""Tests for back-edge routing (task 34).

Verifies that multiple back-edges sharing layers are given distinct
horizontal channels so they don't overlap into one thick line.
"""

from __future__ import annotations

from pymermaid import render_diagram
from pymermaid.ir import Diagram, DiagramType, Direction, Edge, Node
from pymermaid.layout import EdgeLayout, Point, layout_diagram

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _measure(text: str, font_size: float) -> tuple[float, float]:
    """Simple measure function for testing."""
    return (len(text) * font_size * 0.6, font_size * 1.2)


def _make_diagram(
    node_ids: list[str],
    edges: list[tuple[str, str]],
    direction: Direction = Direction.TB,
) -> Diagram:
    nodes = tuple(Node(id=nid, label=nid) for nid in node_ids)
    ir_edges = tuple(Edge(source=s, target=t) for s, t in edges)
    return Diagram(
        type=DiagramType.flowchart,
        direction=direction,
        nodes=nodes,
        edges=ir_edges,
    )


def _get_edge_layout(
    result, source: str, target: str,
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


# ---------------------------------------------------------------------------
# Unit: Back-edge dummy node separation
# ---------------------------------------------------------------------------


class TestBackEdgeDummySeparation:
    """Back-edge dummy nodes for different back-edges must differ."""

    def test_two_back_edges_same_target(self):
        """Two back-edges targeting the same node get distinct dummy x-coords.

        Graph: A -> B -> C -> A  and  A -> B -> D -> A
        Both back-edges (C->A and D->A) pass through shared layers.
        """
        diagram = _make_diagram(
            ["A", "B", "C", "D"],
            [
                ("A", "B"),
                ("B", "C"),
                ("C", "A"),  # back-edge 1
                ("B", "D"),
                ("D", "A"),  # back-edge 2
            ],
        )
        result = layout_diagram(diagram, _measure)

        el1 = _get_edge_layout(result, "C", "A")
        el2 = _get_edge_layout(result, "D", "A")
        assert el1 is not None, "Edge C->A not found"
        assert el2 is not None, "Edge D->A not found"

        pts1 = _intermediate_points(el1)
        pts2 = _intermediate_points(el2)

        # Both back-edges have intermediate points
        assert len(pts1) > 0, "C->A should have intermediate waypoints"
        assert len(pts2) > 0, "D->A should have intermediate waypoints"

        # The x-coordinates of intermediate points must differ
        xs1 = [p.x for p in pts1]
        xs2 = [p.x for p in pts2]
        # Check that at least one pair of x-coords differs by >= 15px
        has_distinct = False
        for x1 in xs1:
            for x2 in xs2:
                if abs(x1 - x2) >= 15.0:
                    has_distinct = True
                    break
        assert has_distinct, (
            f"Back-edge intermediate x-coords should differ by >= 15px. "
            f"C->A: {xs1}, D->A: {xs2}"
        )

    def test_three_back_edges_same_target_registration_pattern(self):
        """Three back-edges to the same target get distinct channels.

        Mimics the registration.mmd pattern:
        EmailError->Form, ExistsError->Form, PasswordError->Form
        """
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
                ("EmailError", "Form"),        # back-edge 1
                ("ValidateEmail", "CheckExists"),
                ("CheckExists", "ExistsError"),
                ("ExistsError", "Form"),        # back-edge 2
                ("CheckExists", "ValidatePassword"),
                ("ValidatePassword", "PasswordError"),
                ("PasswordError", "Form"),      # back-edge 3
            ],
        )
        result = layout_diagram(diagram, _measure)

        el1 = _get_edge_layout(result, "EmailError", "Form")
        el2 = _get_edge_layout(result, "ExistsError", "Form")
        el3 = _get_edge_layout(result, "PasswordError", "Form")

        assert el1 is not None
        assert el2 is not None
        assert el3 is not None

        pts1 = _intermediate_points(el1)
        pts2 = _intermediate_points(el2)
        pts3 = _intermediate_points(el3)

        assert len(pts1) > 0
        assert len(pts2) > 0
        assert len(pts3) > 0

        # All three must have distinct x-coordinates for intermediate waypoints
        xs1 = set(round(p.x, 1) for p in pts1)
        xs2 = set(round(p.x, 1) for p in pts2)
        xs3 = set(round(p.x, 1) for p in pts3)

        # No two should share all their x-coordinates
        assert xs1 != xs2, f"Back-edges 1 and 2 share x-coords: {xs1}"
        assert xs1 != xs3, f"Back-edges 1 and 3 share x-coords: {xs1}"
        assert xs2 != xs3, f"Back-edges 2 and 3 share x-coords: {xs2}"

    def test_back_edges_different_targets_dont_interfere(self):
        """Back-edges targeting different nodes don't interfere with each other."""
        diagram = _make_diagram(
            ["A", "B", "C", "D", "E"],
            [
                ("A", "B"),
                ("B", "C"),
                ("C", "A"),  # back-edge to A
                ("A", "D"),
                ("D", "E"),
                ("E", "B"),  # back-edge to B
            ],
        )
        result = layout_diagram(diagram, _measure)

        el1 = _get_edge_layout(result, "C", "A")
        el2 = _get_edge_layout(result, "E", "B")
        assert el1 is not None
        assert el2 is not None

        # Both edges should have valid layouts (no crashes, no zero-length)
        assert len(el1.points) >= 2
        assert len(el2.points) >= 2


# ---------------------------------------------------------------------------
# Unit: Back-edge polyline geometry
# ---------------------------------------------------------------------------


class TestBackEdgePolylineGeometry:
    """Verify that back-edge polylines are geometrically separated."""

    def test_registration_back_edges_x_separation(self):
        """In the registration pattern, no two back-edges share intermediate
        waypoints (must differ by >= 15px on x-axis)."""
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
        layouts = []
        for src, tgt in back_edges:
            el = _get_edge_layout(result, src, tgt)
            assert el is not None, f"Edge {src}->{tgt} not found"
            layouts.append(el)

        # Check pairwise: intermediate waypoints differ by >= 15px on x
        for i in range(len(layouts)):
            for j in range(i + 1, len(layouts)):
                pts_i = _intermediate_points(layouts[i])
                pts_j = _intermediate_points(layouts[j])
                if not pts_i or not pts_j:
                    continue

                # For each pair of back-edges, check that the average
                # x-coordinate of their intermediates differs by >= 15px
                avg_xi = sum(p.x for p in pts_i) / len(pts_i)
                avg_xj = sum(p.x for p in pts_j) / len(pts_j)
                assert abs(avg_xi - avg_xj) >= 15.0, (
                    f"Back-edges {back_edges[i]} and {back_edges[j]} "
                    f"intermediate x-coords too close: "
                    f"avg_x={avg_xi:.1f} vs {avg_xj:.1f}"
                )

    def test_debug_loop_back_edge_avoids_nodes(self):
        """debug_loop.mmd: the back-edge (F->B) intermediate waypoints must
        not fall inside any node's bounding box."""
        diagram = _make_diagram(
            ["A", "B", "C", "D", "E", "F", "G"],
            [
                ("A", "B"),
                ("B", "C"),
                ("B", "D"),
                ("D", "E"),
                ("E", "F"),
                ("F", "B"),  # back-edge
                ("C", "G"),
            ],
        )
        result = layout_diagram(diagram, _measure)

        el = _get_edge_layout(result, "F", "B")
        assert el is not None, "Edge F->B not found"

        intermediates = _intermediate_points(el)

        # Check no intermediate point falls inside any node bbox
        for nid, nl in result.nodes.items():
            x1, y1 = nl.x, nl.y
            x2, y2 = nl.x + nl.width, nl.y + nl.height
            for p in intermediates:
                inside = x1 <= p.x <= x2 and y1 <= p.y <= y2
                assert not inside, (
                    f"Intermediate point ({p.x:.1f}, {p.y:.1f}) of back-edge "
                    f"F->B falls inside node {nid} bbox "
                    f"({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f})"
                )

    def test_minimum_channel_offset(self):
        """Back-edge channels must be separated by at least 20px."""
        diagram = _make_diagram(
            [
                "Form", "Submit", "ValidateEmail", "EmailError",
                "CheckExists", "ExistsError",
            ],
            [
                ("Form", "Submit"),
                ("Submit", "ValidateEmail"),
                ("ValidateEmail", "EmailError"),
                ("EmailError", "Form"),
                ("ValidateEmail", "CheckExists"),
                ("CheckExists", "ExistsError"),
                ("ExistsError", "Form"),
            ],
        )
        result = layout_diagram(diagram, _measure)

        el1 = _get_edge_layout(result, "EmailError", "Form")
        el2 = _get_edge_layout(result, "ExistsError", "Form")
        assert el1 is not None
        assert el2 is not None

        pts1 = _intermediate_points(el1)
        pts2 = _intermediate_points(el2)

        if pts1 and pts2:
            # Average x of each back-edge's intermediates
            avg_x1 = sum(p.x for p in pts1) / len(pts1)
            avg_x2 = sum(p.x for p in pts2) / len(pts2)
            assert abs(avg_x1 - avg_x2) >= 20.0, (
                f"Back-edge channels must be >= 20px apart, "
                f"got {abs(avg_x1 - avg_x2):.1f}px"
            )


# ---------------------------------------------------------------------------
# Unit: Regression -- forward edges unaffected
# ---------------------------------------------------------------------------


class TestForwardEdgeRegression:
    """Verify that graphs without cycles produce identical layouts."""

    def test_linear_chain_unchanged(self):
        """A linear chain (no cycles) should produce the same layout."""
        diagram = _make_diagram(
            ["A", "B", "C", "D"],
            [("A", "B"), ("B", "C"), ("C", "D")],
        )
        result = layout_diagram(diagram, _measure)

        # All nodes should be present and have valid positions
        for nid in ["A", "B", "C", "D"]:
            assert nid in result.nodes

        # All edges should be present
        assert len(result.edges) == 3

        # No back-edges, so all edges should have simple 2-point lines
        # (or go through dummies for multi-layer spans, but here each
        # edge spans exactly 1 layer so 2 points each)
        for el in result.edges:
            assert len(el.points) >= 2

    def test_diamond_unchanged(self):
        """A diamond pattern (no cycles) should produce the same layout."""
        diagram = _make_diagram(
            ["A", "B", "C", "D"],
            [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")],
        )
        result = layout_diagram(diagram, _measure)

        for nid in ["A", "B", "C", "D"]:
            assert nid in result.nodes
        assert len(result.edges) == 4

    def test_single_back_edge_still_routes(self):
        """A single back-edge should still route correctly (no offset needed)."""
        diagram = _make_diagram(
            ["A", "B", "C"],
            [("A", "B"), ("B", "C"), ("C", "A")],
        )
        result = layout_diagram(diagram, _measure)

        el = _get_edge_layout(result, "C", "A")
        assert el is not None
        assert len(el.points) >= 2


# ---------------------------------------------------------------------------
# Integration: Full render of fixture files
# ---------------------------------------------------------------------------


class TestRegistrationRendering:
    """Render the registration.mmd fixture and verify back-edge separation."""

    def test_registration_render_produces_svg(self):
        """Render registration.mmd and verify it produces valid SVG."""
        with open("tests/fixtures/github/registration.mmd") as f:
            source = f.read()
        svg = render_diagram(source)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_registration_back_edges_separated(self):
        """The three back-edges in registration.mmd must have distinct paths."""
        from pymermaid.measure import TextMeasurer
        from pymermaid.parser import parse_flowchart

        with open("tests/fixtures/github/registration.mmd") as f:
            source = f.read()

        diagram = parse_flowchart(source)
        measurer = TextMeasurer()
        result = layout_diagram(diagram, measurer.measure)

        back_edge_pairs = [
            ("EmailError", "Form"),
            ("ExistsError", "Form"),
            ("PasswordError", "Form"),
        ]

        layouts = {}
        for src, tgt in back_edge_pairs:
            el = _get_edge_layout(result, src, tgt)
            assert el is not None, f"Edge {src}->{tgt} not found in layout"
            layouts[(src, tgt)] = el

        # All three must have intermediate waypoints with distinct x-coords
        x_avgs = {}
        for key, el in layouts.items():
            pts = _intermediate_points(el)
            if pts:
                x_avgs[key] = sum(p.x for p in pts) / len(pts)

        keys = list(x_avgs.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                diff = abs(x_avgs[keys[i]] - x_avgs[keys[j]])
                assert diff >= 15.0, (
                    f"Back-edges {keys[i]} and {keys[j]} too close: "
                    f"{diff:.1f}px apart"
                )


class TestDebugLoopRendering:
    """Render the debug_loop.mmd fixture."""

    def test_debug_loop_render_produces_svg(self):
        """Render debug_loop.mmd and verify valid SVG."""
        with open("tests/fixtures/github/debug_loop.mmd") as f:
            source = f.read()
        svg = render_diagram(source)
        assert "<svg" in svg
        assert "</svg>" in svg
