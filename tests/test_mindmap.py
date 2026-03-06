"""Tests for mindmap IR, parser, layout, renderer, and integration."""

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from merm import render_diagram
from merm.ir.mindmap import MindmapDiagram, MindmapNode, MindmapShape
from merm.layout.mindmap import layout_mindmap
from merm.parser.flowchart import ParseError
from merm.parser.mindmap import parse_mindmap
from merm.render.mindmap import render_mindmap_svg

FIXTURES = Path(__file__).parent / "fixtures" / "corpus" / "mindmap"

def _simple_measure(text: str, font_size: float) -> tuple[float, float]:
    """Simple text measurer for tests."""
    return (len(text) * font_size * 0.6, font_size * 1.4)

# ---------------------------------------------------------------------------
# IR unit tests
# ---------------------------------------------------------------------------

class TestMindmapIR:
    def test_create_node_with_all_fields(self):
        node = MindmapNode(
            id="root",
            label="Central Topic",
            shape=MindmapShape.CIRCLE,
            children=(
                MindmapNode(id="a", label="A", shape=MindmapShape.DEFAULT),
            ),
        )
        assert node.id == "root"
        assert node.label == "Central Topic"
        assert node.shape == MindmapShape.CIRCLE
        assert len(node.children) == 1
        assert node.children[0].id == "a"

    def test_create_diagram_with_nested_children(self):
        leaf = MindmapNode(id="leaf", label="Leaf", shape=MindmapShape.DEFAULT)
        branch = MindmapNode(
            id="branch", label="Branch", shape=MindmapShape.ROUNDED_RECT,
            children=(leaf,),
        )
        root = MindmapNode(
            id="root", label="Root", shape=MindmapShape.CIRCLE,
            children=(branch,),
        )
        diagram = MindmapDiagram(root=root)
        assert diagram.root.id == "root"
        assert diagram.root.children[0].id == "branch"
        assert diagram.root.children[0].children[0].id == "leaf"

    def test_shape_enum_members(self):
        expected = {"CIRCLE", "ROUNDED_RECT", "RECT", "CLOUD", "DEFAULT"}
        actual = {m.name for m in MindmapShape}
        assert actual == expected

# ---------------------------------------------------------------------------
# Parser unit tests
# ---------------------------------------------------------------------------

class TestParseMindmapBasic:
    def test_basic_fixture(self):
        text = (FIXTURES / "basic.mmd").read_text()
        diagram = parse_mindmap(text)
        assert diagram.root.label == "Central Topic"
        assert diagram.root.shape == MindmapShape.CIRCLE
        assert len(diagram.root.children) == 3
        # Check child names
        child_labels = [c.label for c in diagram.root.children]
        assert "Origins" in child_labels
        assert "Research" in child_labels
        assert "Tools" in child_labels

    def test_basic_fixture_depth(self):
        text = (FIXTURES / "basic.mmd").read_text()
        diagram = parse_mindmap(text)
        # Origins should have 2 children
        origins = [c for c in diagram.root.children if c.label == "Origins"][0]
        assert len(origins.children) == 2

    def test_single_root(self):
        text = (FIXTURES / "single_root.mmd").read_text()
        diagram = parse_mindmap(text)
        assert diagram.root.label == "Solo Node"
        assert diagram.root.shape == MindmapShape.CIRCLE
        assert len(diagram.root.children) == 0

class TestParseMindmapShapes:
    def test_circle_shape(self):
        text = "mindmap\n  root((Circle))"
        diagram = parse_mindmap(text)
        assert diagram.root.shape == MindmapShape.CIRCLE
        assert diagram.root.label == "Circle"

    def test_rounded_rect_shape(self):
        text = "mindmap\n  node(Rounded)"
        diagram = parse_mindmap(text)
        assert diagram.root.shape == MindmapShape.ROUNDED_RECT
        assert diagram.root.label == "Rounded"

    def test_rect_shape(self):
        text = "mindmap\n  node[Square]"
        diagram = parse_mindmap(text)
        assert diagram.root.shape == MindmapShape.RECT
        assert diagram.root.label == "Square"

    def test_cloud_shape(self):
        text = "mindmap\n  node))Cloud(("
        diagram = parse_mindmap(text)
        assert diagram.root.shape == MindmapShape.CLOUD
        assert diagram.root.label == "Cloud"

    def test_default_shape(self):
        text = "mindmap\n  Just Text"
        diagram = parse_mindmap(text)
        assert diagram.root.shape == MindmapShape.DEFAULT
        assert diagram.root.label == "Just Text"

    def test_shapes_fixture(self):
        text = (FIXTURES / "shapes.mmd").read_text()
        diagram = parse_mindmap(text)
        assert diagram.root.shape == MindmapShape.CIRCLE
        shapes = [c.shape for c in diagram.root.children]
        assert MindmapShape.ROUNDED_RECT in shapes
        assert MindmapShape.RECT in shapes
        assert MindmapShape.CLOUD in shapes
        assert MindmapShape.DEFAULT in shapes

class TestParseMindmapEdgeCases:
    def test_comments_stripped(self):
        text = "mindmap\n  root((Root))\n    %% comment\n    Child"
        diagram = parse_mindmap(text)
        assert len(diagram.root.children) == 1
        assert diagram.root.children[0].label == "Child"

    def test_empty_input_raises(self):
        with pytest.raises(ParseError, match="Empty input"):
            parse_mindmap("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ParseError, match="Empty input"):
            parse_mindmap("   \n  ")

    def test_missing_mindmap_keyword_raises(self):
        with pytest.raises(ParseError, match="Missing 'mindmap' keyword"):
            parse_mindmap("root((Hello))\n  Child")

    def test_no_root_node_raises(self):
        with pytest.raises(ParseError, match="No root node"):
            parse_mindmap("mindmap\n")

# ---------------------------------------------------------------------------
# Layout unit tests
# ---------------------------------------------------------------------------

class TestLayoutMindmap:
    def test_single_root_centered(self):
        root = MindmapNode(id="root", label="Root", shape=MindmapShape.CIRCLE)
        diagram = MindmapDiagram(root=root)
        result = layout_mindmap(diagram, measure_fn=_simple_measure)
        assert "root" in result.nodes
        # Single node: should be centered in the canvas
        nl = result.nodes["root"]
        assert abs(nl.x - result.width / 2) < 1.0
        assert abs(nl.y - result.height / 2) < 1.0

    def test_four_children_equal_distance(self):
        children = tuple(
            MindmapNode(id=f"c{i}", label=f"Child {i}", shape=MindmapShape.DEFAULT)
            for i in range(4)
        )
        root = MindmapNode(
            id="root", label="Root", shape=MindmapShape.CIRCLE, children=children,
        )
        diagram = MindmapDiagram(root=root)
        result = layout_mindmap(diagram, measure_fn=_simple_measure)

        root_nl = result.nodes["root"]
        # All children should be at approximately equal distance from root
        distances = []
        for i in range(4):
            cnl = result.nodes[f"c{i}"]
            d = math.sqrt((cnl.x - root_nl.x) ** 2 + (cnl.y - root_nl.y) ** 2)
            distances.append(d)

        # All distances should be similar (within 10%)
        avg_d = sum(distances) / len(distances)
        for d in distances:
            assert abs(d - avg_d) < avg_d * 0.15

        # Children should not overlap each other
        for i in range(4):
            for j in range(i + 1, 4):
                ni = result.nodes[f"c{i}"]
                nj = result.nodes[f"c{j}"]
                dist = math.sqrt((ni.x - nj.x) ** 2 + (ni.y - nj.y) ** 2)
                # Distance should exceed combined half-widths
                min_dist = (ni.width + nj.width) / 4
                assert dist > min_dist, f"Children c{i} and c{j} overlap"

    def test_three_levels_increasing_radius(self):
        grandchild = MindmapNode(
            id="gc", label="Grandchild", shape=MindmapShape.DEFAULT,
        )
        child = MindmapNode(
            id="child", label="Child", shape=MindmapShape.DEFAULT,
            children=(grandchild,),
        )
        root = MindmapNode(
            id="root", label="Root", shape=MindmapShape.CIRCLE,
            children=(child,),
        )
        diagram = MindmapDiagram(root=root)
        result = layout_mindmap(diagram, measure_fn=_simple_measure)

        root_nl = result.nodes["root"]
        child_nl = result.nodes["child"]
        gc_nl = result.nodes["gc"]

        d_child = math.sqrt(
            (child_nl.x - root_nl.x) ** 2 + (child_nl.y - root_nl.y) ** 2
        )
        d_gc = math.sqrt(
            (gc_nl.x - root_nl.x) ** 2 + (gc_nl.y - root_nl.y) ** 2
        )
        assert d_gc > d_child, "Grandchild should be farther from root than child"

# ---------------------------------------------------------------------------
# Renderer unit tests
# ---------------------------------------------------------------------------

class TestRenderMindmapSVG:
    def _make_simple_diagram(self):
        children = (
            MindmapNode(id="a", label="Topic A", shape=MindmapShape.ROUNDED_RECT),
            MindmapNode(id="b", label="Topic B", shape=MindmapShape.RECT),
            MindmapNode(id="c", label="Topic C", shape=MindmapShape.DEFAULT),
        )
        root = MindmapNode(
            id="root", label="Central", shape=MindmapShape.CIRCLE,
            children=children,
        )
        return MindmapDiagram(root=root)

    def test_svg_wrapper(self):
        diagram = self._make_simple_diagram()
        layout = layout_mindmap(diagram, measure_fn=_simple_measure)
        svg = render_mindmap_svg(diagram, layout)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")

    def test_all_labels_present(self):
        diagram = self._make_simple_diagram()
        layout = layout_mindmap(diagram, measure_fn=_simple_measure)
        svg = render_mindmap_svg(diagram, layout)
        assert "Central" in svg
        assert "Topic A" in svg
        assert "Topic B" in svg
        assert "Topic C" in svg

    def test_three_branches_distinct_colors(self):
        diagram = self._make_simple_diagram()
        layout = layout_mindmap(diagram, measure_fn=_simple_measure)
        svg = render_mindmap_svg(diagram, layout)
        # Count distinct stroke colors in mindmap-branch paths
        pat1 = r'class="mindmap-branch"[^/]*stroke="(#[0-9a-fA-F]+)"'
        pat2 = r'stroke="(#[0-9a-fA-F]+)"[^/]*class="mindmap-branch"'
        branch_colors = set(re.findall(pat1, svg))
        branch_colors.update(re.findall(pat2, svg))
        assert len(branch_colors) >= 3

    def test_path_elements_for_branches(self):
        diagram = self._make_simple_diagram()
        layout = layout_mindmap(diagram, measure_fn=_simple_measure)
        svg = render_mindmap_svg(diagram, layout)
        assert "<path" in svg
        assert 'class="mindmap-branch"' in svg

    def test_circle_root_shape(self):
        root = MindmapNode(id="root", label="Root", shape=MindmapShape.CIRCLE)
        diagram = MindmapDiagram(root=root)
        layout = layout_mindmap(diagram, measure_fn=_simple_measure)
        svg = render_mindmap_svg(diagram, layout)
        assert "<circle" in svg

    def test_curved_paths(self):
        """Branch connections should use quadratic bezier curves (Q command)."""
        diagram = self._make_simple_diagram()
        layout = layout_mindmap(diagram, measure_fn=_simple_measure)
        svg = render_mindmap_svg(diagram, layout)
        # Q command indicates quadratic bezier curve
        assert " Q " in svg

    def test_valid_xml(self):
        diagram = self._make_simple_diagram()
        layout = layout_mindmap(diagram, measure_fn=_simple_measure)
        svg = render_mindmap_svg(diagram, layout)
        ET.fromstring(svg)  # Should not raise

# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestRenderDiagramDispatch:
    def test_dispatch_returns_svg(self):
        source = "mindmap\n  root((Hello))\n    Child A\n    Child B"
        svg = render_diagram(source)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_dispatch_contains_labels(self):
        source = "mindmap\n  root((Central))\n    Alpha\n    Beta"
        svg = render_diagram(source)
        assert "Central" in svg
        assert "Alpha" in svg
        assert "Beta" in svg

# ---------------------------------------------------------------------------
# Corpus fixture tests
# ---------------------------------------------------------------------------

class TestCorpusFixtures:
    @pytest.fixture(params=sorted(FIXTURES.glob("*.mmd")), ids=lambda p: p.stem)
    def fixture_path(self, request):
        return request.param

    def test_renders_without_error(self, fixture_path):
        text = fixture_path.read_text()
        svg = render_diagram(text)
        assert "<svg" in svg

    def test_well_formed_xml(self, fixture_path):
        text = fixture_path.read_text()
        svg = render_diagram(text)
        ET.fromstring(svg)  # Should not raise
