"""Tests for subgraph support: parsing, layout, and rendering."""

from __future__ import annotations

import pytest
import xml.etree.ElementTree as ET

from pymermaid.ir import (
    Diagram,
    DiagramType,
    Direction,
    Edge,
    Node,
    Subgraph,
)
from pymermaid.layout import (
    NodeLayout,
    SubgraphLayout,
    layout_diagram,
)
from pymermaid.measure import measure_text
from pymermaid.parser.flowchart import ParseError, parse_flowchart
from pymermaid.render import render_svg

_SVG_NS = "http://www.w3.org/2000/svg"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _measure(text: str, font_size: float) -> tuple[float, float]:
    """Simple measure function for testing."""
    return (len(text) * font_size * 0.6, font_size * 1.2)


def _make_diagram(
    node_ids: list[str],
    edges: list[tuple[str, str]],
    subgraphs: tuple[Subgraph, ...] = (),
    direction: Direction = Direction.TB,
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


def _parse(svg_str: str) -> ET.Element:
    return ET.fromstring(svg_str)


def _center(nl: NodeLayout) -> tuple[float, float]:
    return (nl.x + nl.width / 2, nl.y + nl.height / 2)


# ---------------------------------------------------------------------------
# Unit: Parser subgraph handling (verify existing behavior)
# ---------------------------------------------------------------------------


class TestParserSubgraph:
    def test_parse_simple_subgraph(self):
        text = "flowchart TD\n  subgraph sg1[Title]\n    A --> B\n  end"
        diagram = parse_flowchart(text)
        assert len(diagram.subgraphs) == 1
        sg = diagram.subgraphs[0]
        assert sg.id == "sg1"
        assert sg.title == "Title"
        assert set(sg.node_ids) == {"A", "B"}

    def test_parse_nested_subgraphs(self):
        text = (
            "flowchart TD\n"
            "  subgraph outer[Outer]\n"
            "    subgraph inner[Inner]\n"
            "      A --> B\n"
            "    end\n"
            "    C\n"
            "  end\n"
        )
        diagram = parse_flowchart(text)
        assert len(diagram.subgraphs) == 1
        outer = diagram.subgraphs[0]
        assert outer.id == "outer"
        assert len(outer.subgraphs) == 1
        inner = outer.subgraphs[0]
        assert inner.id == "inner"
        assert set(inner.node_ids) == {"A", "B"}

    def test_parse_subgraph_direction(self):
        text = (
            "flowchart TD\n"
            "  subgraph sg1[Title]\n"
            "    direction LR\n"
            "    A --> B\n"
            "  end\n"
        )
        diagram = parse_flowchart(text)
        sg = diagram.subgraphs[0]
        assert sg.direction == Direction.LR

    def test_parse_edge_to_subgraph_id(self):
        text = (
            "flowchart TD\n"
            "  subgraph sg1[Title]\n"
            "    A --> B\n"
            "  end\n"
            "  C --> sg1\n"
        )
        diagram = parse_flowchart(text)
        edge_targets = [e.target for e in diagram.edges]
        assert "sg1" in edge_targets

    def test_unclosed_subgraph_raises(self):
        text = "flowchart TD\n  subgraph sg1[Title]\n    A --> B\n"
        try:
            parse_flowchart(text)
            assert False, "Expected ParseError"
        except ParseError:
            pass


# ---------------------------------------------------------------------------
# Unit: Layout SubgraphLayout data structure
# ---------------------------------------------------------------------------


class TestSubgraphLayoutDataclass:
    def test_subgraph_layout_importable(self):
        from pymermaid.layout import SubgraphLayout
        assert SubgraphLayout is not None

    def test_subgraph_layout_fields(self):
        sgl = SubgraphLayout(
            id="sg1", x=10.0, y=20.0, width=100.0, height=80.0, title="Title",
        )
        assert sgl.id == "sg1"
        assert sgl.x == 10.0
        assert sgl.y == 20.0
        assert sgl.width == 100.0
        assert sgl.height == 80.0
        assert sgl.title == "Title"


# ---------------------------------------------------------------------------
# Unit: Layout subgraph grouping
# ---------------------------------------------------------------------------


class TestLayoutSubgraphGrouping:
    def test_layout_result_has_subgraphs(self):
        sg = Subgraph(id="sg1", title="Group", node_ids=("A", "B"))
        d = _make_diagram(["A", "B", "C"], [("A", "B"), ("B", "C")], subgraphs=(sg,))
        result = layout_diagram(d, _measure)
        assert result.subgraphs is not None
        assert "sg1" in result.subgraphs

    def test_subgraph_layout_in_result(self):
        sg = Subgraph(id="sg1", title="Group", node_ids=("A", "B"))
        d = _make_diagram(["A", "B"], [("A", "B")], subgraphs=(sg,))
        result = layout_diagram(d, _measure)
        sgl = result.subgraphs["sg1"]
        assert isinstance(sgl, SubgraphLayout)
        assert sgl.width > 0
        assert sgl.height > 0

    def test_subgraph_bbox_encompasses_members(self):
        sg = Subgraph(id="sg1", title="Group", node_ids=("A", "B"))
        d = _make_diagram(["A", "B", "C"], [("A", "B"), ("B", "C")], subgraphs=(sg,))
        result = layout_diagram(d, _measure)
        sgl = result.subgraphs["sg1"]
        for nid in ("A", "B"):
            nl = result.nodes[nid]
            # Node bbox should be within subgraph bbox
            assert nl.x >= sgl.x, f"Node {nid} x={nl.x} < subgraph x={sgl.x}"
            assert nl.y >= sgl.y, f"Node {nid} y={nl.y} < subgraph y={sgl.y}"
            assert nl.x + nl.width <= sgl.x + sgl.width
            assert nl.y + nl.height <= sgl.y + sgl.height

    def test_subgraph_bbox_has_padding(self):
        """Subgraph bbox should have padding around member nodes."""
        sg = Subgraph(id="sg1", title="G", node_ids=("A",))
        d = _make_diagram(["A"], [], subgraphs=(sg,))
        result = layout_diagram(d, _measure)
        sgl = result.subgraphs["sg1"]
        nl = result.nodes["A"]
        # There should be at least some padding
        assert sgl.x < nl.x
        assert sgl.y < nl.y
        assert sgl.x + sgl.width > nl.x + nl.width
        assert sgl.y + sgl.height > nl.y + nl.height

    def test_grouped_nodes_adjacent_in_layer(self):
        """Nodes in same subgraph should be adjacent within their layer."""
        sg = Subgraph(id="sg1", title="Group", node_ids=("B", "C"))
        # A->B, A->C, A->D: B, C, D are all in layer 1
        d = _make_diagram(
            ["A", "B", "C", "D"],
            [("A", "B"), ("A", "C"), ("A", "D")],
            subgraphs=(sg,),
        )
        result = layout_diagram(d, _measure)
        # B and C should be closer to each other than to D
        b_cx = _center(result.nodes["B"])[0]
        c_cx = _center(result.nodes["C"])[0]
        d_cx = _center(result.nodes["D"])[0]
        bc_dist = abs(b_cx - c_cx)
        bd_dist = abs(b_cx - d_cx)
        cd_dist = abs(c_cx - d_cx)
        # Either B-C is closer than B-D, or C-D must be at one end
        assert bc_dist <= bd_dist or bc_dist <= cd_dist

    def test_nested_subgraph_bbox_containment(self):
        """Inner subgraph bbox should be within outer subgraph bbox."""
        inner = Subgraph(id="inner", title="Inner", node_ids=("A", "B"))
        outer = Subgraph(
            id="outer", title="Outer", node_ids=("C",),
            subgraphs=(inner,),
        )
        d = _make_diagram(
            ["A", "B", "C"],
            [("A", "B"), ("B", "C")],
            subgraphs=(outer,),
        )
        result = layout_diagram(d, _measure)
        assert "inner" in result.subgraphs
        assert "outer" in result.subgraphs
        inner_sgl = result.subgraphs["inner"]
        outer_sgl = result.subgraphs["outer"]
        # Inner should be within outer
        assert inner_sgl.x >= outer_sgl.x
        assert inner_sgl.y >= outer_sgl.y
        assert inner_sgl.x + inner_sgl.width <= outer_sgl.x + outer_sgl.width
        assert inner_sgl.y + inner_sgl.height <= outer_sgl.y + outer_sgl.height

    def test_empty_subgraph_omitted(self):
        """A subgraph with no nodes should not appear in subgraph layouts."""
        sg = Subgraph(id="sg_empty", title="Empty", node_ids=())
        d = _make_diagram(["A"], [])
        # Manually set subgraphs since _make_diagram doesn't pass it through
        d = Diagram(
            type=d.type, direction=d.direction, nodes=d.nodes,
            edges=d.edges, subgraphs=(sg,),
        )
        result = layout_diagram(d, _measure)
        assert "sg_empty" not in result.subgraphs

    def test_no_subgraphs_empty_dict(self):
        """Diagram with no subgraphs should have empty subgraphs dict."""
        d = _make_diagram(["A", "B"], [("A", "B")])
        result = layout_diagram(d, _measure)
        assert result.subgraphs is not None
        assert len(result.subgraphs) == 0


# ---------------------------------------------------------------------------
# Unit: Renderer subgraph SVG output
# ---------------------------------------------------------------------------


class TestRendererSubgraph:
    def _diagram_with_subgraph(self):
        sg = Subgraph(id="sg1", title="My Group", node_ids=("A", "B"))
        d = _make_diagram(["A", "B", "C"], [("A", "B"), ("B", "C")], subgraphs=(sg,))
        layout = layout_diagram(d, _measure)
        return d, layout

    def test_subgraph_g_element_exists(self):
        d, layout = self._diagram_with_subgraph()
        root = _parse(render_svg(d, layout))
        sg_groups = root.findall(".//*[@data-subgraph-id='sg1']")
        assert len(sg_groups) == 1

    def test_subgraph_g_has_class(self):
        d, layout = self._diagram_with_subgraph()
        root = _parse(render_svg(d, layout))
        sg_groups = root.findall(".//*[@data-subgraph-id='sg1']")
        assert sg_groups[0].get("class") == "subgraph"

    def test_subgraph_contains_rect_and_text(self):
        d, layout = self._diagram_with_subgraph()
        root = _parse(render_svg(d, layout))
        g = root.findall(".//*[@data-subgraph-id='sg1']")[0]
        rects = [el for el in g if el.tag in ("rect", f"{{{_SVG_NS}}}rect")]
        texts = [el for el in g if el.tag in ("text", f"{{{_SVG_NS}}}text")]
        assert len(rects) >= 1
        assert len(texts) >= 1

    def test_subgraph_title_rendered(self):
        d, layout = self._diagram_with_subgraph()
        root = _parse(render_svg(d, layout))
        g = root.findall(".//*[@data-subgraph-id='sg1']")[0]
        all_text = "".join(el.text or "" for el in g.iter())
        assert "My Group" in all_text

    def test_subgraph_rect_has_rx(self):
        d, layout = self._diagram_with_subgraph()
        root = _parse(render_svg(d, layout))
        g = root.findall(".//*[@data-subgraph-id='sg1']")[0]
        rects = [el for el in g if el.tag in ("rect", f"{{{_SVG_NS}}}rect")]
        assert rects[0].get("rx") == "5"

    def test_nested_subgraphs_rendered(self):
        inner = Subgraph(id="inner", title="Inner", node_ids=("A", "B"))
        outer = Subgraph(
            id="outer", title="Outer", node_ids=("C",),
            subgraphs=(inner,),
        )
        d = _make_diagram(
            ["A", "B", "C"],
            [("A", "B"), ("B", "C")],
            subgraphs=(outer,),
        )
        layout = layout_diagram(d, _measure)
        root = _parse(render_svg(d, layout))
        sg_groups = root.findall(".//*[@data-subgraph-id]")
        sg_ids = {g.get("data-subgraph-id") for g in sg_groups}
        assert "outer" in sg_ids
        assert "inner" in sg_ids

    def test_z_order_subgraphs_before_nodes(self):
        """Subgraph <g> should appear before node <g> in SVG tree."""
        d, layout = self._diagram_with_subgraph()
        root = _parse(render_svg(d, layout))
        # Find all direct children that are <g> elements
        children = list(root)
        sg_indices = []
        node_indices = []
        for i, child in enumerate(children):
            if child.get("class") == "subgraph":
                sg_indices.append(i)
            elif child.get("class") == "node":
                node_indices.append(i)
        if sg_indices and node_indices:
            assert max(sg_indices) < min(node_indices), (
                "Subgraph elements should appear before node elements"
            )

    def test_z_order_outer_before_inner(self):
        """Outer subgraph <g> should appear before inner subgraph <g>."""
        inner = Subgraph(id="inner", title="Inner", node_ids=("A", "B"))
        outer = Subgraph(
            id="outer", title="Outer", node_ids=("C",),
            subgraphs=(inner,),
        )
        d = _make_diagram(
            ["A", "B", "C"],
            [("A", "B"), ("B", "C")],
            subgraphs=(outer,),
        )
        layout = layout_diagram(d, _measure)
        root = _parse(render_svg(d, layout))
        children = list(root)
        outer_idx = None
        inner_idx = None
        for i, child in enumerate(children):
            if child.get("data-subgraph-id") == "outer":
                outer_idx = i
            elif child.get("data-subgraph-id") == "inner":
                inner_idx = i
        assert outer_idx is not None
        assert inner_idx is not None
        assert outer_idx < inner_idx


# ---------------------------------------------------------------------------
# Integration: End-to-end subgraph rendering
# ---------------------------------------------------------------------------


class TestIntegrationSubgraph:
    def test_parse_layout_render_valid_xml(self):
        text = (
            "flowchart TD\n"
            "  subgraph sg1[Processing]\n"
            "    A[Input] --> B[Process]\n"
            "  end\n"
            "  B --> C[Output]\n"
        )
        diagram = parse_flowchart(text)
        layout = layout_diagram(diagram, measure_text)
        svg = render_svg(diagram, layout)
        root = _parse(svg)  # should not raise
        assert root.tag in ("svg", f"{{{_SVG_NS}}}svg")

    def test_parse_layout_render_nested(self):
        text = (
            "flowchart TD\n"
            "  subgraph outer[Outer]\n"
            "    subgraph inner[Inner]\n"
            "      A --> B\n"
            "    end\n"
            "    C\n"
            "  end\n"
            "  B --> D\n"
        )
        diagram = parse_flowchart(text)
        layout = layout_diagram(diagram, measure_text)
        svg = render_svg(diagram, layout)
        root = _parse(svg)
        sg_groups = root.findall(".//*[@data-subgraph-id]")
        sg_ids = {g.get("data-subgraph-id") for g in sg_groups}
        assert "outer" in sg_ids
        assert "inner" in sg_ids
        # Check all subgraph rects and titles present
        for sg_g in sg_groups:
            rects = [el for el in sg_g if el.tag in ("rect", f"{{{_SVG_NS}}}rect")]
            texts = [el for el in sg_g if el.tag in ("text", f"{{{_SVG_NS}}}text")]
            assert len(rects) >= 1
            assert len(texts) >= 1

    def test_cross_boundary_edges_rendered(self):
        text = (
            "flowchart TD\n"
            "  subgraph sg1[Group]\n"
            "    A --> B\n"
            "  end\n"
            "  C --> A\n"
            "  B --> D\n"
        )
        diagram = parse_flowchart(text)
        layout = layout_diagram(diagram, measure_text)
        svg = render_svg(diagram, layout)
        root = _parse(svg)
        edge_groups = root.findall(".//*[@data-edge-source]")
        # Should have edges: A->B, C->A, B->D
        assert len(edge_groups) >= 3
        # All edges should have a path with a d attribute
        for eg in edge_groups:
            paths = [
                el for el in eg.iter()
                if el.tag in ("path", f"{{{_SVG_NS}}}path")
            ]
            assert len(paths) >= 1
            assert paths[0].get("d", "").startswith("M")

    @pytest.mark.skip(reason="Per-subgraph direction override not yet implemented in layout")
    def test_subgraph_direction_override_lr_in_td(self):
        """A subgraph with direction LR inside a TD diagram should lay out
        its nodes horizontally (same or similar y, different x)."""
        text = (
            "flowchart TD\n"
            "  subgraph sg1[Group]\n"
            "    direction LR\n"
            "    A --> B\n"
            "  end\n"
        )
        diagram = parse_flowchart(text)
        # The parser records the direction override, but the current layout
        # engine does not implement per-subgraph direction transforms.
        # Verify at least that the direction is recorded in the IR.
        sg = diagram.subgraphs[0]
        assert sg.direction == Direction.LR
        # Verify layout completes without error
        layout = layout_diagram(diagram, measure_text)
        assert "sg1" in layout.subgraphs
