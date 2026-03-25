"""Tests for GH#1: subgraph edge duplicate node fix."""

import xml.etree.ElementTree as ET

from merm import render_diagram
from merm.parser.flowchart import parse_flowchart

REPRO_CASE = """\
flowchart LR
    subgraph Batch
        direction TB
        A1[PM groom #1] --> B1[SWE #1] --> C1[QA #1] --> D1[PM accept #1]
        A2[PM groom #2] --> B2[SWE #2] --> C2[QA #2] --> D2[PM accept #2]
    end
    Batch --> E[Pull next 2]
    E --> Batch
"""


class TestParserNoDuplicateNode:
    """Parser must not create a Node for IDs that are subgraph IDs."""

    def test_batch_not_in_nodes(self):
        diagram = parse_flowchart(REPRO_CASE)
        node_ids = [n.id for n in diagram.nodes]
        assert "Batch" not in node_ids

    def test_batch_is_in_subgraphs(self):
        diagram = parse_flowchart(REPRO_CASE)
        sg_ids = [sg.id for sg in diagram.subgraphs]
        assert "Batch" in sg_ids

    def test_edges_referencing_batch_exist(self):
        diagram = parse_flowchart(REPRO_CASE)
        sources = [e.source for e in diagram.edges]
        targets = [e.target for e in diagram.edges]
        assert "Batch" in sources, "Expected an edge with source='Batch'"
        assert "Batch" in targets, "Expected an edge with target='Batch'"

    def test_correct_node_count(self):
        """Should have 9 nodes: A1, B1, C1, D1, A2, B2, C2, D2, E."""
        diagram = parse_flowchart(REPRO_CASE)
        assert len(diagram.nodes) == 9
        expected_ids = {"A1", "B1", "C1", "D1", "A2", "B2", "C2", "D2", "E"}
        actual_ids = {n.id for n in diagram.nodes}
        assert actual_ids == expected_ids

    def test_subgraph_without_external_edges(self):
        """Subgraph with no external edges should still work normally."""
        text = (
            "flowchart TD\n"
            "  subgraph sg1[Title]\n"
            "    A --> B\n"
            "  end\n"
            "  C --> D\n"
        )
        diagram = parse_flowchart(text)
        node_ids = {n.id for n in diagram.nodes}
        assert "sg1" not in node_ids
        assert {"A", "B", "C", "D"} == node_ids
        assert len(diagram.subgraphs) == 1
        assert diagram.subgraphs[0].id == "sg1"

    def test_subgraph_id_with_shape_syntax_not_registered(self):
        """If a subgraph ID is used with shape syntax (e.g. Batch[Override]),
        it should still not create a node."""
        text = (
            "flowchart TD\n"
            "  subgraph Batch\n"
            "    A --> B\n"
            "  end\n"
            "  Batch[Override] --> E\n"
        )
        diagram = parse_flowchart(text)
        node_ids = [n.id for n in diagram.nodes]
        assert "Batch" not in node_ids


class TestLayoutSubgraphEdges:
    """Layout engine must handle edges to/from subgraph IDs without crashing."""

    def test_no_crash(self):
        """Layout the reproduction case without KeyError."""
        svg = render_diagram(REPRO_CASE)
        assert svg is not None
        assert len(svg) > 0

    def test_edge_layouts_exist(self):
        """Both Batch->E and E->Batch edge paths should exist in the SVG."""
        svg = render_diagram(REPRO_CASE)
        root = ET.fromstring(svg)
        edges = root.findall(
            ".//{http://www.w3.org/2000/svg}g[@class='edge']",
        )
        # There should be at least 2 edges referencing Batch
        # (plus 6 internal edges: A1->B1->C1->D1 and A2->B2->C2->D2)
        assert len(edges) >= 2, f"Expected >= 2 edges, got {len(edges)}"

    def test_node_e_outside_subgraph_bbox(self):
        """Node E must be positioned OUTSIDE the Batch subgraph bounding box."""
        from merm.layout.sugiyama import layout_diagram
        from merm.measure.text import measure_text

        diagram = parse_flowchart(REPRO_CASE)
        layout = layout_diagram(diagram, measure_text)

        # Get node E position
        e_layout = layout.nodes["E"]
        e_left = e_layout.x
        e_right = e_layout.x + e_layout.width
        e_top = e_layout.y
        e_bottom = e_layout.y + e_layout.height

        # Get Batch subgraph bbox
        sg_layouts = layout.subgraphs or {}
        batch_sg = sg_layouts["Batch"]

        # E must not overlap the Batch subgraph box
        overlaps = (
            e_left < batch_sg.x + batch_sg.width
            and e_right > batch_sg.x
            and e_top < batch_sg.y + batch_sg.height
            and e_bottom > batch_sg.y
        )
        assert not overlaps, (
            f"Node E ({e_left:.1f},{e_top:.1f} - {e_right:.1f},{e_bottom:.1f}) "
            f"overlaps Batch subgraph ({batch_sg.x:.1f},{batch_sg.y:.1f} - "
            f"{batch_sg.x + batch_sg.width:.1f},{batch_sg.y + batch_sg.height:.1f})"
        )

    def test_lr_direction_respected(self):
        """In LR mode, node E should be to the right of the Batch subgraph."""
        from merm.layout.sugiyama import layout_diagram
        from merm.measure.text import measure_text

        diagram = parse_flowchart(REPRO_CASE)
        layout = layout_diagram(diagram, measure_text)

        e_layout = layout.nodes["E"]
        sg_layouts = layout.subgraphs or {}
        batch_sg = sg_layouts["Batch"]

        # E's left edge should be to the right of Batch's right edge
        assert e_layout.x >= batch_sg.x + batch_sg.width, (
            f"Node E x={e_layout.x:.1f} should be >= Batch right edge "
            f"{batch_sg.x + batch_sg.width:.1f}"
        )

    def test_edge_endpoints_near_subgraph_boundary(self):
        """Edge endpoints should be on or near the subgraph boundary rect."""
        from merm.layout.sugiyama import layout_diagram
        from merm.measure.text import measure_text

        diagram = parse_flowchart(REPRO_CASE)
        layout = layout_diagram(diagram, measure_text)

        sg_layouts = layout.subgraphs or {}
        batch_sg = sg_layouts["Batch"]

        # Find edges involving Batch
        batch_edges = [
            el for el in layout.edges
            if el.source == "Batch" or el.target == "Batch"
        ]
        assert len(batch_edges) >= 2, (
            f"Expected >= 2 Batch edges, got {len(batch_edges)}"
        )

        for el in batch_edges:
            # The endpoint touching the subgraph should be near its boundary
            if el.source == "Batch":
                pt = el.points[0]  # source point
            else:
                pt = el.points[-1]  # target point

            # Check that the point is near the subgraph boundary (within 20px)
            _TOLERANCE = 20.0
            near_boundary = (
                abs(pt.x - batch_sg.x) < _TOLERANCE
                or abs(pt.x - (batch_sg.x + batch_sg.width)) < _TOLERANCE
                or abs(pt.y - batch_sg.y) < _TOLERANCE
                or abs(pt.y - (batch_sg.y + batch_sg.height)) < _TOLERANCE
            )
            assert near_boundary, (
                f"Edge {el.source}->{el.target} endpoint ({pt.x:.1f},{pt.y:.1f}) "
                f"not near Batch boundary"
            )


class TestSVGRendering:
    """Integration: full render pipeline produces correct SVG."""

    def test_svg_is_valid_xml(self):
        svg = render_diagram(REPRO_CASE)
        root = ET.fromstring(svg)  # raises if invalid
        assert root.tag == "{http://www.w3.org/2000/svg}svg"

    def test_no_batch_node_in_svg(self):
        """No <g class="node" data-node-id="Batch"> should exist."""
        svg = render_diagram(REPRO_CASE)
        assert 'data-node-id="Batch"' not in svg

    def test_batch_subgraph_in_svg(self):
        """<g class="subgraph" data-subgraph-id="Batch"> should exist."""
        svg = render_diagram(REPRO_CASE)
        assert 'data-subgraph-id="Batch"' in svg

    def test_correct_node_count_in_svg(self):
        """Should have exactly 9 node <g> elements, not 10."""
        svg = render_diagram(REPRO_CASE)
        root = ET.fromstring(svg)
        # Find all <g class="node ..."> elements
        node_gs = [
            g for g in root.iter("{http://www.w3.org/2000/svg}g")
            if "node" in (g.get("class") or "").split()
        ]
        assert len(node_gs) == 9, (
            f"Expected 9 node <g> elements, got {len(node_gs)}: "
            f"{[g.get('data-node-id') for g in node_gs]}"
        )

    def test_edge_paths_present(self):
        """At least 8 edges total (6 internal + Batch->E + E->Batch)."""
        svg = render_diagram(REPRO_CASE)
        root = ET.fromstring(svg)
        edge_gs = [
            g for g in root.iter("{http://www.w3.org/2000/svg}g")
            if "edge" in (g.get("class") or "").split()
        ]
        assert len(edge_gs) >= 8, f"Expected >= 8 edges, got {len(edge_gs)}"


class TestRegression:
    """Regression tests: existing subgraph features must still work."""

    def test_simple_subgraph_edge(self):
        """The existing test_parse_edge_to_subgraph_id case still works."""
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

    def test_nested_subgraph_renders(self):
        """Nested subgraphs should still render correctly."""
        text = (
            "flowchart TD\n"
            "  subgraph outer\n"
            "    subgraph inner\n"
            "      A --> B\n"
            "    end\n"
            "    C --> D\n"
            "  end\n"
        )
        svg = render_diagram(text)
        assert 'data-subgraph-id="outer"' in svg
        assert 'data-subgraph-id="inner"' in svg
        assert 'data-node-id="A"' in svg
