"""Tests for the layout engine."""

from __future__ import annotations

import time

from pymermaid.ir import Diagram, DiagramType, Direction, Edge, Node
from pymermaid.layout import (
    EdgeLayout,
    LayoutConfig,
    LayoutResult,
    NodeLayout,
    Point,
    _assign_coordinates,
    _crossing_minimization,
    _insert_dummy_nodes,
    _longest_path_layering,
    _remove_cycles,
    layout_diagram,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _measure(text: str, font_size: float) -> tuple[float, float]:
    """Simple measure function for testing."""
    return (len(text) * font_size * 0.6, font_size * 1.2)


def _large_measure(text: str, font_size: float) -> tuple[float, float]:
    """Returns large dimensions."""
    return (200.0, 60.0)


def _small_measure(text: str, font_size: float) -> tuple[float, float]:
    """Returns small dimensions."""
    return (10.0, 10.0)


def _make_diagram(
    node_ids: list[str],
    edges: list[tuple[str, str]],
    direction: Direction = Direction.TB,
) -> Diagram:
    """Build a simple diagram from node IDs and edge pairs."""
    nodes = tuple(Node(id=nid, label=nid) for nid in node_ids)
    ir_edges = tuple(Edge(source=s, target=t) for s, t in edges)
    return Diagram(
        type=DiagramType.flowchart,
        direction=direction,
        nodes=nodes,
        edges=ir_edges,
    )


def _bounding_box(nl: NodeLayout) -> tuple[float, float, float, float]:
    """Return (x1, y1, x2, y2) of a NodeLayout."""
    return (nl.x, nl.y, nl.x + nl.width, nl.y + nl.height)


def _boxes_overlap(a: NodeLayout, b: NodeLayout) -> bool:
    """Check if two node bounding boxes overlap."""
    ax1, ay1, ax2, ay2 = _bounding_box(a)
    bx1, by1, bx2, by2 = _bounding_box(b)
    if ax1 >= bx2 or bx1 >= ax2:
        return False
    if ay1 >= by2 or by1 >= ay2:
        return False
    return True


def _center(nl: NodeLayout) -> tuple[float, float]:
    """Return center of a NodeLayout."""
    return (nl.x + nl.width / 2, nl.y + nl.height / 2)


# ---------------------------------------------------------------------------
# Unit: Data structures
# ---------------------------------------------------------------------------

class TestDataStructures:
    def test_point(self):
        p = Point(1.0, 2.0)
        assert p.x == 1.0
        assert p.y == 2.0

    def test_node_layout(self):
        nl = NodeLayout(x=10.0, y=20.0, width=100.0, height=50.0)
        assert nl.x == 10.0
        assert nl.y == 20.0
        assert nl.width == 100.0
        assert nl.height == 50.0

    def test_edge_layout(self):
        pts = [Point(0.0, 0.0), Point(10.0, 20.0)]
        el = EdgeLayout(points=pts, source="A", target="B")
        assert len(el.points) == 2
        assert el.source == "A"
        assert el.target == "B"

    def test_layout_result(self):
        nl = NodeLayout(x=0.0, y=0.0, width=50.0, height=30.0)
        el = EdgeLayout(points=[Point(0, 0), Point(1, 1)], source="A", target="B")
        lr = LayoutResult(nodes={"A": nl}, edges=[el], width=100.0, height=80.0)
        assert "A" in lr.nodes
        assert len(lr.edges) == 1
        assert lr.width == 100.0
        assert lr.height == 80.0

    def test_layout_config_defaults(self):
        cfg = LayoutConfig()
        assert cfg.rank_sep == 50.0
        assert cfg.node_sep == 30.0
        assert cfg.direction == Direction.TB

    def test_layout_config_overrides(self):
        cfg = LayoutConfig(rank_sep=100, node_sep=50, direction=Direction.LR)
        assert cfg.rank_sep == 100
        assert cfg.node_sep == 50
        assert cfg.direction == Direction.LR


# ---------------------------------------------------------------------------
# Unit: Cycle removal
# ---------------------------------------------------------------------------

class TestCycleRemoval:
    def test_acyclic_unchanged(self):
        edges = [("A", "B", 0), ("B", "C", 1)]
        result, reversed_set = _remove_cycles(["A", "B", "C"], edges)
        assert len(reversed_set) == 0
        # Edges should be the same
        pairs = [(s, t) for s, t, _ in result]
        assert ("A", "B") in pairs
        assert ("B", "C") in pairs

    def test_cycle_broken(self):
        edges = [("A", "B", 0), ("B", "C", 1), ("C", "A", 2)]
        result, reversed_set = _remove_cycles(["A", "B", "C"], edges)
        assert len(reversed_set) >= 1

    def test_self_loop_handled(self):
        # Self-loops should be preprocessed out before cycle removal,
        # but cycle removal itself shouldn't crash on empty input
        edges: list[tuple[str, str, int]] = []
        result, reversed_set = _remove_cycles(["A"], edges)
        assert len(reversed_set) == 0


# ---------------------------------------------------------------------------
# Unit: Layer assignment
# ---------------------------------------------------------------------------

class TestLayerAssignment:
    def test_linear_chain(self):
        edges = [("A", "B", 0), ("B", "C", 1)]
        layers = _longest_path_layering(["A", "B", "C"], edges)
        assert layers["A"] < layers["B"] < layers["C"]

    def test_diamond(self):
        edges = [("A", "B", 0), ("A", "C", 1), ("B", "D", 2), ("C", "D", 3)]
        layers = _longest_path_layering(["A", "B", "C", "D"], edges)
        assert layers["A"] == 0
        assert layers["B"] == 1
        assert layers["C"] == 1
        assert layers["D"] == 2

    def test_dummy_nodes_inserted(self):
        # A->C with layers 0 and 2 should get a dummy
        edges = [("A", "B", 0), ("B", "C", 1), ("A", "C", 2)]
        layers = _longest_path_layering(["A", "B", "C"], edges)
        # Edge A->C spans layers 0->2
        assert layers["C"] - layers["A"] == 2
        new_layers, new_edges, dummy_info = _insert_dummy_nodes(
            layers, [("A", "C", 2)]
        )
        assert len(dummy_info) >= 1
        # There should be a dummy node at layer 1
        for dummy_id, _ in dummy_info.items():
            assert new_layers[dummy_id] == 1


# ---------------------------------------------------------------------------
# Unit: Crossing minimization
# ---------------------------------------------------------------------------

class TestCrossingMinimization:
    def test_no_crossings_preserved(self):
        # A -> C, B -> D  (no crossings)
        layers = {"A": 0, "B": 0, "C": 1, "D": 1}
        layer_lists = [["A", "B"], ["C", "D"]]
        edges = [("A", "C", 0), ("B", "D", 1)]
        result = _crossing_minimization(layer_lists, edges, layers)
        # Order should remain A, B in layer 0 and C, D in layer 1
        assert result[0] == ["A", "B"]
        assert result[1] == ["C", "D"]

    def test_crossings_reduced(self):
        # A -> D, B -> C creates a crossing if order is [A,B],[C,D]
        layers = {"A": 0, "B": 0, "C": 1, "D": 1}
        layer_lists = [["A", "B"], ["C", "D"]]
        edges = [("A", "D", 0), ("B", "C", 1)]
        result = _crossing_minimization(layer_lists, edges, layers)
        # After minimization, layer 1 should be reordered to [D, C]
        assert result[1] == ["D", "C"]


# ---------------------------------------------------------------------------
# Unit: Coordinate assignment
# ---------------------------------------------------------------------------

class TestCoordinateAssignment:
    def test_rank_separation(self):
        layer_lists = [["A"], ["B"]]
        sizes = {"A": (60.0, 30.0), "B": (60.0, 30.0)}
        positions = _assign_coordinates(
            layer_lists, sizes, rank_sep=50.0, node_sep=30.0,
        )
        # B should be below A by at least rank_sep
        ya = positions["A"][1]
        yb = positions["B"][1]
        assert yb - ya >= 50.0

    def test_node_separation(self):
        layer_lists = [["A", "B"]]
        sizes = {"A": (60.0, 30.0), "B": (60.0, 30.0)}
        positions = _assign_coordinates(
            layer_lists, sizes, rank_sep=50.0, node_sep=30.0,
        )
        xa = positions["A"][0]
        xb = positions["B"][0]
        # Distance between centers should be at least node_width + node_sep
        assert abs(xb - xa) >= 60.0 + 30.0

    def test_wider_nodes_push_apart(self):
        layer_lists = [["A", "B"]]
        small_sizes = {"A": (40.0, 30.0), "B": (40.0, 30.0)}
        big_sizes = {"A": (120.0, 30.0), "B": (120.0, 30.0)}
        pos_small = _assign_coordinates(layer_lists, small_sizes, 50, 30)
        pos_big = _assign_coordinates(layer_lists, big_sizes, 50, 30)
        gap_small = abs(pos_small["B"][0] - pos_small["A"][0])
        gap_big = abs(pos_big["B"][0] - pos_big["A"][0])
        assert gap_big > gap_small


# ---------------------------------------------------------------------------
# Unit: Edge routing
# ---------------------------------------------------------------------------

class TestEdgeRouting:
    def test_adjacent_layer_two_points(self):
        """Edge between adjacent layers has exactly 2 points."""
        d = _make_diagram(["A", "B"], [("A", "B")])
        result = layout_diagram(d, _measure)
        assert len(result.edges) == 1
        assert len(result.edges[0].points) == 2

    def test_multi_layer_polyline(self):
        """Edge spanning multiple layers has 3+ points."""
        d = _make_diagram(["A", "B", "C"], [("A", "B"), ("B", "C"), ("A", "C")])
        result = layout_diagram(d, _measure)
        # Find the A->C edge
        ac_edges = [e for e in result.edges if e.source == "A" and e.target == "C"]
        assert len(ac_edges) == 1
        assert len(ac_edges[0].points) >= 3

    def test_self_loop_valid(self):
        """Self-loop produces at least 2 points."""
        d = _make_diagram(["A"], [("A", "A")])
        result = layout_diagram(d, _measure)
        self_edges = [e for e in result.edges if e.source == "A" and e.target == "A"]
        assert len(self_edges) == 1
        assert len(self_edges[0].points) >= 2

    def test_edge_endpoints_on_boundary(self):
        """Edge endpoints should be on node boundaries, not centers."""
        d = _make_diagram(["A", "B"], [("A", "B")])
        result = layout_diagram(d, _measure)
        edge = result.edges[0]
        a_nl = result.nodes["A"]
        b_nl = result.nodes["B"]
        a_cx, a_cy = _center(a_nl)
        b_cx, b_cy = _center(b_nl)
        # Start point should not be at A's center
        start = edge.points[0]
        end = edge.points[-1]
        # At least one coordinate should differ from center
        assert (abs(start.x - a_cx) > 0.1 or abs(start.y - a_cy) > 0.1)
        assert (abs(end.x - b_cx) > 0.1 or abs(end.y - b_cy) > 0.1)


# ---------------------------------------------------------------------------
# Integration: layout_diagram end-to-end
# ---------------------------------------------------------------------------

class TestLayoutDiagramIntegration:
    def test_simple_ab_tb(self):
        """A --> B with TB: A above B."""
        d = _make_diagram(["A", "B"], [("A", "B")])
        result = layout_diagram(d, _measure)
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.width > 0
        assert result.height > 0
        a_cy = _center(result.nodes["A"])[1]
        b_cy = _center(result.nodes["B"])[1]
        assert a_cy < b_cy

    def test_simple_ab_lr(self):
        """A --> B with LR: A left of B."""
        d = _make_diagram(["A", "B"], [("A", "B")], direction=Direction.LR)
        result = layout_diagram(d, _measure)
        a_cx = _center(result.nodes["A"])[0]
        b_cx = _center(result.nodes["B"])[0]
        assert a_cx < b_cx

    def test_simple_ab_bt(self):
        """A --> B with BT: A below B."""
        d = _make_diagram(["A", "B"], [("A", "B")], direction=Direction.BT)
        result = layout_diagram(d, _measure)
        a_cy = _center(result.nodes["A"])[1]
        b_cy = _center(result.nodes["B"])[1]
        assert a_cy > b_cy

    def test_simple_ab_rl(self):
        """A --> B with RL: A right of B."""
        d = _make_diagram(["A", "B"], [("A", "B")], direction=Direction.RL)
        result = layout_diagram(d, _measure)
        a_cx = _center(result.nodes["A"])[0]
        b_cx = _center(result.nodes["B"])[0]
        assert a_cx > b_cx

    def test_chain_five_nodes(self):
        """Chain of 5 nodes: all positioned, no overlaps."""
        edges = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "E")]
        d = _make_diagram(["A", "B", "C", "D", "E"], edges)
        result = layout_diagram(d, _measure)
        assert len(result.nodes) == 5
        nodes_list = list(result.nodes.values())
        for i in range(len(nodes_list)):
            for j in range(i + 1, len(nodes_list)):
                assert not _boxes_overlap(nodes_list[i], nodes_list[j])

    def test_diamond_no_overlaps(self):
        """Diamond: 4 nodes, 4 edges, no overlaps."""
        edges = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
        d = _make_diagram(["A", "B", "C", "D"], edges)
        result = layout_diagram(d, _measure)
        assert len(result.nodes) == 4
        assert len(result.edges) == 4
        nodes_list = list(result.nodes.values())
        for i in range(len(nodes_list)):
            for j in range(i + 1, len(nodes_list)):
                assert not _boxes_overlap(nodes_list[i], nodes_list[j])

    def test_cyclic_graph(self):
        """Cyclic graph completes without error."""
        edges = [("A", "B"), ("B", "C"), ("C", "A")]
        d = _make_diagram(["A", "B", "C"], edges)
        result = layout_diagram(d, _measure)
        assert len(result.nodes) == 3
        assert "A" in result.nodes
        assert "B" in result.nodes
        assert "C" in result.nodes

    def test_disconnected_components(self):
        """Two separate pairs, all 4 nodes positioned."""
        edges = [("A", "B"), ("C", "D")]
        d = _make_diagram(["A", "B", "C", "D"], edges)
        result = layout_diagram(d, _measure)
        assert len(result.nodes) == 4

    def test_self_loop_no_error(self):
        """Self-loop does not raise."""
        d = _make_diagram(["A"], [("A", "A")])
        result = layout_diagram(d, _measure)
        assert len(result.nodes) == 1
        assert len(result.edges) == 1

    def test_empty_diagram(self):
        """Empty diagram returns empty result."""
        d = Diagram()
        result = layout_diagram(d, _measure)
        assert len(result.nodes) == 0
        assert len(result.edges) == 0

    def test_single_node_no_edges(self):
        """Single node with no edges."""
        d = _make_diagram(["A"], [])
        result = layout_diagram(d, _measure)
        assert len(result.nodes) == 1
        assert len(result.edges) == 0

    def test_performance_100_nodes(self):
        """100-node chain completes in under 1 second."""
        ids = [f"N{i}" for i in range(100)]
        edges = [(f"N{i}", f"N{i+1}") for i in range(99)]
        d = _make_diagram(ids, edges)
        start = time.monotonic()
        result = layout_diagram(d, _measure)
        elapsed = time.monotonic() - start
        assert elapsed < 1.0
        assert len(result.nodes) == 100


# ---------------------------------------------------------------------------
# Integration: measure function interaction
# ---------------------------------------------------------------------------

class TestMeasureInteraction:
    def test_large_measure_reflects_sizes(self):
        """Large measure function produces large node dimensions."""
        d = _make_diagram(["A", "B"], [("A", "B")])
        result = layout_diagram(d, _large_measure)
        a_nl = result.nodes["A"]
        assert a_nl.width >= 200.0
        assert a_nl.height >= 60.0

    def test_small_measure_tighter_layout(self):
        """Small measure produces tighter layout than large."""
        d = _make_diagram(["A", "B"], [("A", "B")])
        result_small = layout_diagram(d, _small_measure)
        result_large = layout_diagram(d, _large_measure)
        assert (
            result_large.width > result_small.width
            or result_large.height > result_small.height
        )

    def test_node_dimensions_from_measure(self):
        """Node dimensions reflect what measure_fn returns."""
        d = _make_diagram(["A"], [])
        result = layout_diagram(d, _large_measure)
        a_nl = result.nodes["A"]
        # Width should be at least the measured width (200) + padding
        assert a_nl.width >= 200.0


# ---------------------------------------------------------------------------
# Integration: spacing configuration
# ---------------------------------------------------------------------------

class TestSpacingConfig:
    def test_rank_sep_affects_distance(self):
        """Larger rank_sep increases distance between layers."""
        d = _make_diagram(["A", "B"], [("A", "B")])
        cfg_small = LayoutConfig(rank_sep=30.0)
        cfg_large = LayoutConfig(rank_sep=100.0)
        r_small = layout_diagram(d, _measure, cfg_small)
        r_large = layout_diagram(d, _measure, cfg_large)
        a_s, b_s = r_small.nodes["A"], r_small.nodes["B"]
        a_l, b_l = r_large.nodes["A"], r_large.nodes["B"]
        dist_small = abs(_center(b_s)[1] - _center(a_s)[1])
        dist_large = abs(_center(b_l)[1] - _center(a_l)[1])
        assert dist_large > dist_small

    def test_node_sep_affects_distance(self):
        """Larger node_sep increases distance between same-layer nodes."""
        edges = [("A", "B"), ("A", "C")]
        d = _make_diagram(["A", "B", "C"], edges)
        cfg_small = LayoutConfig(node_sep=10.0)
        cfg_large = LayoutConfig(node_sep=80.0)
        r_small = layout_diagram(d, _measure, cfg_small)
        r_large = layout_diagram(d, _measure, cfg_large)
        # B and C should be in the same layer
        b_small = _center(r_small.nodes["B"])[0]
        c_small = _center(r_small.nodes["C"])[0]
        b_large = _center(r_large.nodes["B"])[0]
        c_large = _center(r_large.nodes["C"])[0]
        gap_small = abs(c_small - b_small)
        gap_large = abs(c_large - b_large)
        assert gap_large > gap_small

    def test_bt_reverses_tb(self):
        """BT reverses the rank-axis ordering compared to TB."""
        d_tb = _make_diagram(["A", "B"], [("A", "B")])
        d_bt = _make_diagram(["A", "B"], [("A", "B")], direction=Direction.BT)
        r_tb = layout_diagram(d_tb, _measure)
        r_bt = layout_diagram(d_bt, _measure)
        # In TB: A.y < B.y; In BT: A.y > B.y
        assert _center(r_tb.nodes["A"])[1] < _center(r_tb.nodes["B"])[1]
        assert _center(r_bt.nodes["A"])[1] > _center(r_bt.nodes["B"])[1]

    def test_rl_reverses_lr(self):
        """RL reverses the rank-axis ordering compared to LR."""
        d_lr = _make_diagram(["A", "B"], [("A", "B")], direction=Direction.LR)
        d_rl = _make_diagram(["A", "B"], [("A", "B")], direction=Direction.RL)
        r_lr = layout_diagram(d_lr, _measure)
        r_rl = layout_diagram(d_rl, _measure)
        # In LR: A.x < B.x; In RL: A.x > B.x
        assert _center(r_lr.nodes["A"])[0] < _center(r_lr.nodes["B"])[0]
        assert _center(r_rl.nodes["A"])[0] > _center(r_rl.nodes["B"])[0]


# ---------------------------------------------------------------------------
# Import test
# ---------------------------------------------------------------------------

class TestImports:
    def test_public_api_importable(self):
        """All public names are importable from pymermaid.layout."""
        from pymermaid.layout import (
            EdgeLayout,
            LayoutConfig,
            LayoutResult,
            NodeLayout,
            Point,
            layout_diagram,
        )
        assert layout_diagram is not None
        assert LayoutResult is not None
        assert LayoutConfig is not None
        assert NodeLayout is not None
        assert EdgeLayout is not None
        assert Point is not None
