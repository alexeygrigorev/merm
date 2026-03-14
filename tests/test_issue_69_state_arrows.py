"""Tests for issue 69: state diagram arrow connection to resized circles.

Verifies that edge endpoints connect to the resized start/end circle
boundaries (within 2px tolerance) and that edge paths are smooth.
"""

import math

import pytest

from merm.ir.statediag import (
    StateType,
)
from merm.layout.statediag import (
    _START_END_SIZE,
    layout_state_diagram,
)
from merm.layout.types import Point
from merm.measure import TextMeasurer
from merm.parser.statediag import parse_state_diagram
from merm.render.statediag import render_state_svg

_REPRO = """\
stateDiagram-v2
    [*] --> Still
    Still --> [*]
    Still --> Moving
    Moving --> Still
    Moving --> Crash
    Crash --> [*]
"""


def _layout_repro():
    diagram = parse_state_diagram(_REPRO)
    measurer = TextMeasurer()
    layout = layout_state_diagram(diagram, measurer.measure)
    return diagram, layout


def _state_types_map(diagram):
    """Build node_id -> StateType mapping."""
    m = {}
    for s in diagram.states:
        m[s.id] = s.state_type
        for c in s.children:
            m[c.id] = c.state_type
    return m


def _distance(p: Point, cx: float, cy: float) -> float:
    return math.hypot(p.x - cx, p.y - cy)


class TestEdgeEndpointsConnectToResizedCircles:
    """Edge endpoints must be within 2px of start/end circle boundaries."""

    def test_start_node_edge_endpoints_near_boundary(self):
        diagram, layout = _layout_repro()
        stypes = _state_types_map(diagram)
        radius = _START_END_SIZE / 2

        start_ids = {nid for nid, st in stypes.items() if st == StateType.START}
        assert start_ids, "Should have at least one start node"

        for el in layout.edges:
            if el.source in start_ids:
                nl = layout.nodes[el.source]
                cx = nl.x + nl.width / 2
                cy = nl.y + nl.height / 2
                first_pt = el.points[0]
                dist_from_center = _distance(first_pt, cx, cy)
                gap = abs(dist_from_center - radius)
                assert gap < 2.0, (
                    f"Source endpoint of edge {el.source}->{el.target} "
                    f"is {gap:.1f}px from circle boundary (max 2px). "
                    f"Point=({first_pt.x:.1f}, {first_pt.y:.1f}), "
                    f"center=({cx:.1f}, {cy:.1f}), radius={radius}"
                )

    def test_end_node_edge_endpoints_near_boundary(self):
        diagram, layout = _layout_repro()
        stypes = _state_types_map(diagram)
        radius = _START_END_SIZE / 2

        end_ids = {nid for nid, st in stypes.items() if st == StateType.END}
        assert end_ids, "Should have at least one end node"

        for el in layout.edges:
            if el.target in end_ids:
                nl = layout.nodes[el.target]
                cx = nl.x + nl.width / 2
                cy = nl.y + nl.height / 2
                last_pt = el.points[-1]
                dist_from_center = _distance(last_pt, cx, cy)
                gap = abs(dist_from_center - radius)
                assert gap < 2.0, (
                    f"Target endpoint of edge {el.source}->{el.target} "
                    f"is {gap:.1f}px from circle boundary (max 2px). "
                    f"Point=({last_pt.x:.1f}, {last_pt.y:.1f}), "
                    f"center=({cx:.1f}, {cy:.1f}), radius={radius}"
                )


class TestEdgePathSmoothness:
    """Edge paths should be smooth with no sharp reversals."""

    def _angle_between_segments(self, p1: Point, p2: Point, p3: Point) -> float:
        """Compute the angle (in degrees) between segments p1->p2 and p2->p3."""
        dx1, dy1 = p2.x - p1.x, p2.y - p1.y
        dx2, dy2 = p3.x - p2.x, p3.y - p2.y
        len1 = math.hypot(dx1, dy1)
        len2 = math.hypot(dx2, dy2)
        if len1 < 1e-6 or len2 < 1e-6:
            return 0.0
        dot = dx1 * dx2 + dy1 * dy2
        cos_angle = max(-1.0, min(1.0, dot / (len1 * len2)))
        return math.degrees(math.acos(cos_angle))

    def test_no_sharp_reversals_in_still_moving_edge(self):
        """The Still->Moving edge should have no sharp reversals (>120 degrees)."""
        diagram, layout = _layout_repro()

        still_moving_edges = [
            el for el in layout.edges
            if el.source == "Still" and el.target == "Moving"
        ]
        assert still_moving_edges, "Should have a Still->Moving edge"

        for el in still_moving_edges:
            points = el.points
            for i in range(1, len(points) - 1):
                angle = self._angle_between_segments(
                    points[i - 1], points[i], points[i + 1],
                )
                assert angle < 120.0, (
                    f"Sharp reversal ({angle:.1f} degrees) in Still->Moving "
                    f"edge at point {i}: {points[i]}"
                )

    def test_forward_edges_have_consistent_y_direction(self):
        """In TB layout, forward edges should flow downward (start y <= end y).

        Back-edges (like Moving->Still) are expected to go upward and are
        excluded from this check.
        """
        diagram, layout = _layout_repro()

        # Identify back-edges: edges where source node center is below target
        back_edges = set()
        for el in layout.edges:
            src_nl = layout.nodes.get(el.source)
            tgt_nl = layout.nodes.get(el.target)
            if src_nl and tgt_nl:
                src_cy = src_nl.y + src_nl.height / 2
                tgt_cy = tgt_nl.y + tgt_nl.height / 2
                if src_cy > tgt_cy + 5.0:
                    back_edges.add((el.source, el.target))

        for el in layout.edges:
            if (el.source, el.target) in back_edges:
                continue
            first = el.points[0]
            last = el.points[-1]
            assert first.y <= last.y + 5.0, (
                f"Edge {el.source}->{el.target} goes upward: "
                f"start.y={first.y:.1f}, end.y={last.y:.1f}"
            )


class TestIntegrationRender:
    """Full render roundtrip tests."""

    def test_reproduction_diagram_renders_valid_svg(self):
        diagram = parse_state_diagram(_REPRO)
        measurer = TextMeasurer()
        layout = layout_state_diagram(diagram, measurer.measure)
        svg = render_state_svg(diagram, layout)

        assert "<svg" in svg
        assert "</svg>" in svg
        assert "Still" in svg
        assert "Moving" in svg
        assert "Crash" in svg

    def test_svg_has_edge_paths(self):
        diagram = parse_state_diagram(_REPRO)
        measurer = TextMeasurer()
        layout = layout_state_diagram(diagram, measurer.measure)
        svg = render_state_svg(diagram, layout)

        # Should have edge paths
        assert 'class="edge"' in svg

    def test_start_end_nodes_are_20px(self):
        """After layout, start/end nodes should be 20x20."""
        diagram = parse_state_diagram(_REPRO)
        measurer = TextMeasurer()
        layout = layout_state_diagram(diagram, measurer.measure)
        stypes = _state_types_map(diagram)

        for nid, st in stypes.items():
            if st in (StateType.START, StateType.END):
                nl = layout.nodes[nid]
                assert nl.width == pytest.approx(20.0), (
                    f"Node {nid} width should be 20, got {nl.width}"
                )
                assert nl.height == pytest.approx(20.0), (
                    f"Node {nid} height should be 20, got {nl.height}"
                )


class TestRegressionExistingFixtures:
    """Existing state diagram fixtures should continue to render."""

    def test_basic_fixture_renders(self):
        import pathlib
        fixture = pathlib.Path(
            "/home/alexey/git/pymermaid/tests/fixtures/corpus/state/basic.mmd"
        )
        if not fixture.exists():
            pytest.skip("basic.mmd fixture not found")
        text = fixture.read_text()
        diagram = parse_state_diagram(text)
        measurer = TextMeasurer()
        layout = layout_state_diagram(diagram, measurer.measure)
        svg = render_state_svg(diagram, layout)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_all_state_fixtures_render(self):
        import pathlib
        fixture_dir = pathlib.Path(
            "/home/alexey/git/pymermaid/tests/fixtures/corpus/state"
        )
        if not fixture_dir.exists():
            pytest.skip("state fixtures directory not found")

        fixtures = list(fixture_dir.glob("*.mmd"))
        if not fixtures:
            pytest.skip("No .mmd fixtures found")

        for fixture in fixtures:
            text = fixture.read_text()
            diagram = parse_state_diagram(text)
            measurer = TextMeasurer()
            layout = layout_state_diagram(diagram, measurer.measure)
            svg = render_state_svg(diagram, layout)
            assert "<svg" in svg, f"Failed to render {fixture.name}"


class TestHelperFunctions:
    """Test the helper functions for boundary point computation."""

    def test_circle_boundary_point_below(self):
        from merm.layout.statediag import _circle_boundary_point
        # Circle at (100, 100), radius 10, reference below
        p = _circle_boundary_point(100, 100, 10, 100, 200)
        assert p.x == pytest.approx(100.0)
        assert p.y == pytest.approx(110.0)

    def test_circle_boundary_point_right(self):
        from merm.layout.statediag import _circle_boundary_point
        p = _circle_boundary_point(100, 100, 10, 200, 100)
        assert p.x == pytest.approx(110.0)
        assert p.y == pytest.approx(100.0)

    def test_circle_boundary_point_diagonal(self):
        from merm.layout.statediag import _circle_boundary_point
        p = _circle_boundary_point(100, 100, 10, 200, 200)
        expected_offset = 10 / math.sqrt(2)
        assert p.x == pytest.approx(100 + expected_offset)
        assert p.y == pytest.approx(100 + expected_offset)

    def test_circle_boundary_point_coincident_defaults_to_bottom(self):
        from merm.layout.statediag import _circle_boundary_point
        p = _circle_boundary_point(100, 100, 10, 100, 100)
        assert p.x == pytest.approx(100.0)
        assert p.y == pytest.approx(110.0)

    def test_rect_boundary_point_below(self):
        from merm.layout.statediag import _rect_boundary_point
        nl = Point(90, 95)  # Not a NodeLayout, need actual NodeLayout
        from merm.layout.types import NodeLayout
        nl = NodeLayout(x=90, y=95, width=20, height=10)
        p = _rect_boundary_point(nl, 100, 200)
        assert p.x == pytest.approx(100.0)
        assert p.y == pytest.approx(105.0)

    def test_rect_boundary_point_right(self):
        from merm.layout.statediag import _rect_boundary_point
        from merm.layout.types import NodeLayout
        nl = NodeLayout(x=90, y=90, width=20, height=20)
        p = _rect_boundary_point(nl, 200, 100)
        assert p.x == pytest.approx(110.0)
        assert p.y == pytest.approx(100.0)
