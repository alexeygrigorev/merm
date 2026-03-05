"""Unit tests for SVG parsing utilities in tests/comparison.py."""

from pathlib import Path

from tests.comparison import (
    SVGDiff,
    parse_svg_edges,
    parse_svg_labels,
    parse_svg_nodes,
    structural_compare,
)

REFERENCE_DIR = Path(__file__).parent / "reference"

class TestParseSVGNodes:
    """Tests for parse_svg_nodes."""

    def test_simple_flowchart_node_count(self):
        """Simple flowchart has 3 nodes: Start, Process, End."""
        svg_text = (REFERENCE_DIR / "simple_flowchart.svg").read_text()
        nodes = parse_svg_nodes(svg_text)
        assert len(nodes) == 3

    def test_simple_flowchart_node_labels(self):
        """Check that expected labels are found."""
        svg_text = (REFERENCE_DIR / "simple_flowchart.svg").read_text()
        nodes = parse_svg_nodes(svg_text)
        all_labels = []
        for node in nodes:
            all_labels.extend(node.labels)
        assert "Start" in all_labels
        assert "Process" in all_labels
        assert "End" in all_labels

    def test_multiple_shapes_node_count(self):
        """Multiple shapes fixture has 5 nodes."""
        svg_text = (REFERENCE_DIR / "multiple_shapes.svg").read_text()
        nodes = parse_svg_nodes(svg_text)
        assert len(nodes) == 5

    def test_subgraphs_node_count(self):
        """Subgraphs fixture has 4 nodes."""
        svg_text = (REFERENCE_DIR / "subgraphs.svg").read_text()
        nodes = parse_svg_nodes(svg_text)
        assert len(nodes) == 4

    def test_styling_node_count(self):
        """Styling fixture has 5 nodes."""
        svg_text = (REFERENCE_DIR / "styling.svg").read_text()
        nodes = parse_svg_nodes(svg_text)
        assert len(nodes) == 5

    def test_empty_svg_returns_empty(self):
        """Empty/minimal SVG returns no nodes."""
        nodes = parse_svg_nodes('<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        assert nodes == []

    def test_empty_string_returns_empty(self):
        """Empty string returns no nodes."""
        nodes = parse_svg_nodes("")
        assert nodes == []

class TestParseSVGEdges:
    """Tests for parse_svg_edges."""

    def test_simple_flowchart_edge_count(self):
        """Simple flowchart has 2 edges: A->B, B->C."""
        svg_text = (REFERENCE_DIR / "simple_flowchart.svg").read_text()
        edges = parse_svg_edges(svg_text)
        assert len(edges) == 2

    def test_multiple_shapes_edge_count(self):
        """Multiple shapes has 4 edges."""
        svg_text = (REFERENCE_DIR / "multiple_shapes.svg").read_text()
        edges = parse_svg_edges(svg_text)
        assert len(edges) == 4

    def test_empty_svg_returns_empty(self):
        """Empty SVG returns no edges."""
        edges = parse_svg_edges('<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        assert edges == []

    def test_empty_string_returns_empty(self):
        """Empty string returns no edges."""
        edges = parse_svg_edges("")
        assert edges == []

    def test_edges_have_ids(self):
        """Edges should have non-empty IDs."""
        svg_text = (REFERENCE_DIR / "simple_flowchart.svg").read_text()
        edges = parse_svg_edges(svg_text)
        for edge in edges:
            assert edge.edge_id, "Edge should have a non-empty ID"

class TestParseSVGLabels:
    """Tests for parse_svg_labels."""

    def test_simple_flowchart_labels(self):
        """Should find Start, Process, End labels."""
        svg_text = (REFERENCE_DIR / "simple_flowchart.svg").read_text()
        labels = parse_svg_labels(svg_text)
        assert "Start" in labels
        assert "Process" in labels
        assert "End" in labels

    def test_multiple_shapes_labels(self):
        """Should find shape labels."""
        svg_text = (REFERENCE_DIR / "multiple_shapes.svg").read_text()
        labels = parse_svg_labels(svg_text)
        assert "Rectangle" in labels
        assert "Rounded" in labels
        assert "Diamond" in labels

    def test_multiple_shapes_edge_labels(self):
        """Should find Yes/No edge labels."""
        svg_text = (REFERENCE_DIR / "multiple_shapes.svg").read_text()
        labels = parse_svg_labels(svg_text)
        assert "Yes" in labels
        assert "No" in labels

    def test_empty_svg_returns_empty(self):
        """Empty SVG returns no labels."""
        labels = parse_svg_labels('<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        assert labels == []

class TestStructuralCompare:
    """Tests for structural_compare."""

    def test_identical_svgs(self):
        """Comparing an SVG against itself should report identical."""
        svg_text = (REFERENCE_DIR / "simple_flowchart.svg").read_text()
        diff = structural_compare(svg_text, svg_text)
        assert diff.identical is True
        assert diff.node_count_expected == diff.node_count_actual
        assert diff.edge_count_expected == diff.edge_count_actual
        assert diff.missing_labels == []
        assert diff.extra_labels == []

    def test_missing_node_detected(self):
        """SVG with fewer nodes should show in the diff."""
        ref_svg = (REFERENCE_DIR / "simple_flowchart.svg").read_text()
        # Use a minimal SVG with no mermaid structure as "our" output
        our_svg = '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
        diff = structural_compare(our_svg, ref_svg)
        assert diff.identical is False
        assert diff.node_count_actual == 0
        assert diff.node_count_expected == 3
        assert len(diff.missing_labels) > 0

    def test_extra_content_detected(self):
        """SVG with extra content should report extra labels."""
        # Use simple as reference (3 nodes), styling as ours (5 nodes)
        ref_svg = (REFERENCE_DIR / "simple_flowchart.svg").read_text()
        our_svg = (REFERENCE_DIR / "styling.svg").read_text()
        diff = structural_compare(our_svg, ref_svg)
        assert diff.identical is False
        assert diff.node_count_actual > diff.node_count_expected

    def test_summary_string(self):
        """Summary should be human-readable."""
        diff = SVGDiff(
            node_count_expected=5,
            node_count_actual=3,
            edge_count_expected=4,
            edge_count_actual=4,
            missing_labels=["Start", "End"],
            extra_labels=[],
            identical=False,
        )
        summary = diff.summary()
        assert "Expected 5 nodes, found 3" in summary
        assert "missing labels:" in summary

    def test_identical_summary(self):
        """Identical diff should say 'Identical'."""
        diff = SVGDiff(
            node_count_expected=3,
            node_count_actual=3,
            edge_count_expected=2,
            edge_count_actual=2,
            identical=True,
        )
        assert diff.summary() == "Identical"
