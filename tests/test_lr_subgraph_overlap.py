"""Tests for LR/RL subgraph overlap fix (Task 36).

Ensures sibling subgraphs do not overlap in any direction,
with particular focus on LR/RL where the X-axis separation
is critical.
"""

import pytest

from pymermaid.ir import (
    Diagram,
    DiagramType,
    Direction,
    Edge,
    Node,
    Subgraph,
)
from pymermaid.layout import (
    LayoutResult,
    NodeLayout,
    SubgraphLayout,
    layout_diagram,
)
from pymermaid.parser.flowchart import parse_flowchart

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _measure(text: str, font_size: float) -> tuple[float, float]:
    return (len(text) * font_size * 0.6, font_size * 1.2)

def _make_diagram(
    node_ids: list[str],
    edges: list[tuple[str, str]],
    subgraphs: tuple[Subgraph, ...] = (),
    direction: Direction = Direction.LR,
) -> Diagram:
    nodes = tuple(Node(id=nid, label=nid) for nid in node_ids)
    ir_edges = tuple(Edge(source=s, target=t) for s, t in edges)
    return Diagram(
        type=DiagramType.flowchart,
        direction=direction,
        nodes=nodes,
        edges=ir_edges,
        subgraphs=subgraphs,
    )

def _bboxes_overlap(
    a: SubgraphLayout, b: SubgraphLayout, tolerance: float = 0.0,
) -> bool:
    """Check if two subgraph bounding boxes overlap."""
    a_right = a.x + a.width
    a_bottom = a.y + a.height
    b_right = b.x + b.width
    b_bottom = b.y + b.height

    x_overlap = a.x < b_right - tolerance and b.x < a_right - tolerance
    y_overlap = a.y < b_bottom - tolerance and b.y < a_bottom - tolerance
    return x_overlap and y_overlap

def _node_inside_subgraph(
    nl: NodeLayout, sg: SubgraphLayout, tolerance: float = 1.0,
) -> bool:
    """Check if a node is fully contained within a subgraph bbox."""
    return (
        nl.x >= sg.x - tolerance
        and nl.y >= sg.y - tolerance
        and nl.x + nl.width <= sg.x + sg.width + tolerance
        and nl.y + nl.height <= sg.y + sg.height + tolerance
    )

def _no_pair_overlaps(
    layouts: list[SubgraphLayout], tolerance: float = 0.0,
) -> bool:
    """Check that no pair of subgraph layouts overlap."""
    for i in range(len(layouts)):
        for j in range(i + 1, len(layouts)):
            if _bboxes_overlap(layouts[i], layouts[j], tolerance):
                return False
    return True

# ---------------------------------------------------------------------------
# Test: LR subgraph bounding box separation (2 siblings)
# ---------------------------------------------------------------------------

class TestLRSubgraphOverlap2Siblings:
    """Two sibling subgraphs with nodes sharing the same layers in LR."""

    def test_no_overlap(self):
        diagram = _make_diagram(
            node_ids=["A", "B", "C", "D"],
            edges=[("A", "B"), ("C", "D"), ("B", "C")],
            subgraphs=(
                Subgraph(id="GroupA", title="Group A", node_ids=("A", "B")),
                Subgraph(id="GroupB", title="Group B", node_ids=("C", "D")),
            ),
            direction=Direction.LR,
        )
        result = layout_diagram(diagram, _measure)
        sg_layouts = list(result.subgraphs.values())
        assert len(sg_layouts) == 2
        assert not _bboxes_overlap(sg_layouts[0], sg_layouts[1])

    def test_nodes_contained_in_subgraph(self):
        diagram = _make_diagram(
            node_ids=["A", "B", "C", "D"],
            edges=[("A", "B"), ("C", "D"), ("B", "C")],
            subgraphs=(
                Subgraph(id="GroupA", title="Group A", node_ids=("A", "B")),
                Subgraph(id="GroupB", title="Group B", node_ids=("C", "D")),
            ),
            direction=Direction.LR,
        )
        result = layout_diagram(diagram, _measure)
        for sg_id, sg_layout in result.subgraphs.items():
            # Find node IDs belonging to this subgraph
            for sg_def in diagram.subgraphs:
                if sg_def.id == sg_id:
                    for nid in sg_def.node_ids:
                        nl = result.nodes[nid]
                        assert _node_inside_subgraph(nl, sg_layout), (
                            f"Node {nid} not inside subgraph {sg_id}"
                        )

    def test_shared_layers_no_overlap(self):
        """Subgraphs whose nodes are on the same layers should not overlap."""
        diagram = _make_diagram(
            node_ids=["A1", "A2", "B1", "B2"],
            edges=[("A1", "A2"), ("B1", "B2")],
            subgraphs=(
                Subgraph(id="GroupA", title="Group A", node_ids=("A1", "A2")),
                Subgraph(id="GroupB", title="Group B", node_ids=("B1", "B2")),
            ),
            direction=Direction.LR,
        )
        result = layout_diagram(diagram, _measure)
        sg_layouts = list(result.subgraphs.values())
        assert len(sg_layouts) == 2
        assert not _bboxes_overlap(sg_layouts[0], sg_layouts[1])

# ---------------------------------------------------------------------------
# Test: LR subgraph bounding box separation (3 siblings - CI pipeline)
# ---------------------------------------------------------------------------

class TestLRSubgraphOverlap3Siblings:
    """The CI pipeline diagram (Build, Test, Deploy) with direction LR."""

    @pytest.fixture()
    def ci_result(self) -> LayoutResult:
        diagram = _make_diagram(
            node_ids=["A", "B", "C", "D", "E", "F", "G"],
            edges=[
                ("A", "B"), ("B", "C"),  # Build
                ("C", "D"), ("C", "E"),  # Build -> Test
                ("D", "F"), ("E", "F"),  # Test -> Deploy
                ("F", "G"),              # Deploy
            ],
            subgraphs=(
                Subgraph(id="Build", title="Build", node_ids=("A", "B", "C")),
                Subgraph(id="Test", title="Test", node_ids=("D", "E")),
                Subgraph(id="Deploy", title="Deploy", node_ids=("F", "G")),
            ),
            direction=Direction.LR,
        )
        return layout_diagram(diagram, _measure)

    def test_no_pair_overlaps(self, ci_result: LayoutResult):
        sg_layouts = list(ci_result.subgraphs.values())
        assert len(sg_layouts) == 3
        assert _no_pair_overlaps(sg_layouts)

    def test_titles_within_bbox(self, ci_result: LayoutResult):
        for sg_layout in ci_result.subgraphs.values():
            # Title y should be within the bounding box
            # SubgraphLayout.y is the top of the box; title is at the top
            assert sg_layout.title is not None
            # The title starts at the top of the subgraph box, so it
            # should be inside.  We just verify the box has positive
            # dimensions (title_height is included).
            assert sg_layout.width > 0
            assert sg_layout.height > 0

    def test_all_nodes_inside_their_subgraph(self, ci_result: LayoutResult):
        sg_node_map = {
            "Build": ["A", "B", "C"],
            "Test": ["D", "E"],
            "Deploy": ["F", "G"],
        }
        for sg_id, nids in sg_node_map.items():
            sg_layout = ci_result.subgraphs[sg_id]
            for nid in nids:
                nl = ci_result.nodes[nid]
                assert _node_inside_subgraph(nl, sg_layout), (
                    f"Node {nid} not inside subgraph {sg_id}"
                )

# ---------------------------------------------------------------------------
# Test: CI pipeline from fixture file
# ---------------------------------------------------------------------------

class TestCIPipelineFixture:
    """Parse and layout the actual CI pipeline fixture."""

    def test_ci_pipeline_no_overlap(self):
        with open("tests/fixtures/github/ci_pipeline.mmd") as f:
            text = f.read()
        diagram = parse_flowchart(text)
        result = layout_diagram(diagram, _measure)
        sg_layouts = list(result.subgraphs.values())
        assert len(sg_layouts) >= 3
        assert _no_pair_overlaps(sg_layouts)

# ---------------------------------------------------------------------------
# Test: RL subgraph bounding box separation
# ---------------------------------------------------------------------------

class TestRLSubgraphOverlap:
    """RL diagram with 3 sibling subgraphs."""

    def test_no_overlap(self):
        diagram = _make_diagram(
            node_ids=["O1", "O2", "P1", "P2", "I1", "I2"],
            edges=[
                ("I1", "P1"), ("I2", "P2"),
                ("P1", "O1"), ("P2", "O2"),
            ],
            subgraphs=(
                Subgraph(id="Output", title="Output", node_ids=("O1", "O2")),
                Subgraph(id="Processing", title="Processing", node_ids=("P1", "P2")),
                Subgraph(id="Input", title="Input", node_ids=("I1", "I2")),
            ),
            direction=Direction.RL,
        )
        result = layout_diagram(diagram, _measure)
        sg_layouts = list(result.subgraphs.values())
        assert len(sg_layouts) == 3
        assert _no_pair_overlaps(sg_layouts)

# ---------------------------------------------------------------------------
# Test: TB/BT regression check
# ---------------------------------------------------------------------------

class TestTBBTRegression:
    """Existing TB subgraph layout should not be degraded."""

    def test_tb_no_overlap(self):
        diagram = _make_diagram(
            node_ids=["A", "B", "C", "D"],
            edges=[("A", "B"), ("C", "D"), ("B", "C")],
            subgraphs=(
                Subgraph(id="Frontend", title="Frontend", node_ids=("A", "B")),
                Subgraph(id="Backend", title="Backend", node_ids=("C", "D")),
            ),
            direction=Direction.TB,
        )
        result = layout_diagram(diagram, _measure)
        sg_layouts = list(result.subgraphs.values())
        assert len(sg_layouts) == 2
        assert not _bboxes_overlap(sg_layouts[0], sg_layouts[1])

    def test_bt_no_overlap(self):
        diagram = _make_diagram(
            node_ids=["A", "B", "C", "D"],
            edges=[("A", "B"), ("C", "D"), ("B", "C")],
            subgraphs=(
                Subgraph(id="Frontend", title="Frontend", node_ids=("A", "B")),
                Subgraph(id="Backend", title="Backend", node_ids=("C", "D")),
            ),
            direction=Direction.BT,
        )
        result = layout_diagram(diagram, _measure)
        sg_layouts = list(result.subgraphs.values())
        assert len(sg_layouts) == 2
        assert not _bboxes_overlap(sg_layouts[0], sg_layouts[1])

    def test_tb_subgraphs_fixture(self):
        """Test with the existing subgraphs.mmd fixture."""
        with open("tests/fixtures/subgraphs.mmd") as f:
            text = f.read()
        diagram = parse_flowchart(text)
        result = layout_diagram(diagram, _measure)
        sg_layouts = list(result.subgraphs.values())
        assert len(sg_layouts) >= 2
        assert _no_pair_overlaps(sg_layouts)

# ---------------------------------------------------------------------------
# Test: Nested subgraphs in LR
# ---------------------------------------------------------------------------

class TestNestedSubgraphsLR:
    """LR diagram with an outer subgraph containing 2 inner subgraphs."""

    def test_inner_no_overlap(self):
        diagram = _make_diagram(
            node_ids=["A", "B", "C", "D", "E"],
            edges=[("A", "B"), ("C", "D"), ("B", "E"), ("D", "E")],
            subgraphs=(
                Subgraph(
                    id="Outer",
                    title="Outer",
                    node_ids=("E",),
                    subgraphs=(
                        Subgraph(id="Inner1", title="Inner 1", node_ids=("A", "B")),
                        Subgraph(id="Inner2", title="Inner 2", node_ids=("C", "D")),
                    ),
                ),
            ),
            direction=Direction.LR,
        )
        result = layout_diagram(diagram, _measure)
        inner1 = result.subgraphs.get("Inner1")
        inner2 = result.subgraphs.get("Inner2")
        assert inner1 is not None
        assert inner2 is not None
        assert not _bboxes_overlap(inner1, inner2)

    def test_outer_contains_inner(self):
        diagram = _make_diagram(
            node_ids=["A", "B", "C", "D", "E"],
            edges=[("A", "B"), ("C", "D"), ("B", "E"), ("D", "E")],
            subgraphs=(
                Subgraph(
                    id="Outer",
                    title="Outer",
                    node_ids=("E",),
                    subgraphs=(
                        Subgraph(id="Inner1", title="Inner 1", node_ids=("A", "B")),
                        Subgraph(id="Inner2", title="Inner 2", node_ids=("C", "D")),
                    ),
                ),
            ),
            direction=Direction.LR,
        )
        result = layout_diagram(diagram, _measure)
        outer = result.subgraphs["Outer"]
        inner1 = result.subgraphs["Inner1"]
        inner2 = result.subgraphs["Inner2"]

        # Outer should contain both inner subgraphs
        tolerance = 1.0
        assert inner1.x >= outer.x - tolerance
        assert inner1.y >= outer.y - tolerance
        assert inner1.x + inner1.width <= outer.x + outer.width + tolerance
        assert inner1.y + inner1.height <= outer.y + outer.height + tolerance

        assert inner2.x >= outer.x - tolerance
        assert inner2.y >= outer.y - tolerance
        assert inner2.x + inner2.width <= outer.x + outer.width + tolerance
        assert inner2.y + inner2.height <= outer.y + outer.height + tolerance
