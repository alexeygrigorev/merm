"""Integration tests: full pipeline from mermaid text to SVG output."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pymermaid.layout import layout_diagram
from pymermaid.measure import TextMeasurer
from pymermaid.parser import parse_flowchart
from pymermaid.render import render_svg

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _render(source: str) -> str:
    """Parse mermaid text, lay out, and render to SVG string."""
    diagram = parse_flowchart(source)
    measurer = TextMeasurer()
    layout = layout_diagram(diagram, measure_fn=measurer.measure)
    return render_svg(diagram, layout)


def _assert_valid_svg(svg: str) -> None:
    """Assert the string looks like a valid SVG document."""
    assert "<svg" in svg
    assert "</svg>" in svg


def _assert_node_ids(svg: str, *node_ids: str) -> None:
    """Assert all given node IDs appear as data-node-id attributes."""
    for nid in node_ids:
        assert f'data-node-id="{nid}"' in svg, f"Missing node {nid!r}"


def _parse_viewbox(svg: str) -> tuple[float, float, float, float]:
    """Extract viewBox as (x, y, width, height)."""
    m = re.search(r'viewBox="([^"]+)"', svg)
    assert m, "No viewBox found"
    parts = m.group(1).split()
    return tuple(float(p) for p in parts)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Fixture file tests
# ---------------------------------------------------------------------------


class TestFixtureRendering:
    """Render each .mmd fixture file through the full pipeline."""

    def test_simple_flowchart(self) -> None:
        source = (FIXTURES_DIR / "simple_flowchart.mmd").read_text()
        svg = _render(source)
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B", "C")

    def test_multiple_shapes(self) -> None:
        source = (FIXTURES_DIR / "multiple_shapes.mmd").read_text()
        svg = _render(source)
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B", "C", "D", "E")

    def test_subgraphs(self) -> None:
        source = (FIXTURES_DIR / "subgraphs.mmd").read_text()
        svg = _render(source)
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B", "C", "D")
        # Subgraph titles should appear in SVG text
        assert "Frontend" in svg
        assert "Backend" in svg

    def test_styling(self) -> None:
        source = (FIXTURES_DIR / "styling.mmd").read_text()
        svg = _render(source)
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B", "C", "D", "E")


# ---------------------------------------------------------------------------
# Direction tests
# ---------------------------------------------------------------------------


class TestDirections:
    """Test all four graph directions."""

    @pytest.mark.parametrize("direction", ["TD", "LR", "BT", "RL"])
    def test_direction_renders(self, direction: str) -> None:
        svg = _render(f"graph {direction}\n    A --> B --> C")
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B", "C")

    def test_td_vs_lr_viewbox_differs(self) -> None:
        svg_td = _render("graph TD\n    A --> B --> C")
        svg_lr = _render("graph LR\n    A --> B --> C")
        _, _, w_td, h_td = _parse_viewbox(svg_td)
        _, _, w_lr, h_lr = _parse_viewbox(svg_lr)
        # TD should be taller than wide; LR should be wider than tall
        # At minimum the aspect ratios should differ
        ratio_td = w_td / h_td if h_td else 0
        ratio_lr = w_lr / h_lr if h_lr else 0
        assert ratio_td != pytest.approx(ratio_lr, abs=0.01), (
            f"TD ratio={ratio_td}, LR ratio={ratio_lr} should differ"
        )


# ---------------------------------------------------------------------------
# Node shape coverage
# ---------------------------------------------------------------------------


class TestNodeShapes:
    """All 14 node shapes render correctly."""

    ALL_SHAPES_DIAGRAM = """\
graph TD
    R["Rectangle"]
    RO("Rounded")
    ST(["Stadium"])
    SUB[["Subroutine"]]
    CYL[("Cylinder")]
    CIR(("Circle"))
    ASYM)Asymmetric(
    DIA{"Diamond"}
    HEX{{"Hexagon"}}
    PAR[/"Parallelogram"/]
    PARA[\\"ParallelogramAlt"\\]
    TRAP[/"Trapezoid"\\]
    TRAPA[\\"TrapezoidAlt"/]
    DCIR((("DoubleCircle")))
"""

    def test_all_14_shapes_present(self) -> None:
        svg = _render(self.ALL_SHAPES_DIAGRAM)
        _assert_valid_svg(svg)
        expected = [
            "R", "RO", "ST", "SUB", "CYL", "CIR", "ASYM",
            "DIA", "HEX", "PAR", "PARA", "TRAP", "TRAPA", "DCIR",
        ]
        _assert_node_ids(svg, *expected)
        assert len(expected) == 14


# ---------------------------------------------------------------------------
# Edge type coverage
# ---------------------------------------------------------------------------


class TestEdgeTypes:
    """All edge types render without error."""

    EDGES_DIAGRAM = """\
graph TD
    A --> B
    B --- C
    C -.-> D
    D ==> E
    E ~~~ F
    F --o G
    G --x H
    H -->|label| I
    I -- text --> J
"""

    def test_all_edge_types(self) -> None:
        svg = _render(self.EDGES_DIAGRAM)
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B", "C", "D", "E", "F", "G", "H", "I", "J")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Various edge-case diagrams."""

    def test_single_node(self) -> None:
        svg = _render("graph TD\n    A[Alone]")
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A")

    def test_self_referencing_edge(self) -> None:
        svg = _render("graph TD\n    A --> A")
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A")

    def test_disconnected_components(self) -> None:
        svg = _render("graph TD\n    A --> B\n    C --> D")
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B", "C", "D")

    def test_long_labels(self) -> None:
        long_label = "X" * 120
        svg = _render(f'graph TD\n    A["{long_label}"] --> B')
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B")

    def test_unicode_labels(self) -> None:
        source = (
            'graph TD\n'
            '    A["Caf\u00e9 \u00fc\u00f6\u00e4"] --> B["\u4f60\u597d\u4e16\u754c"]'
        )
        svg = _render(source)
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B")

    def test_cycle(self) -> None:
        svg = _render("graph TD\n    A --> B --> C --> A")
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B", "C")

    def test_nested_subgraphs(self) -> None:
        source = """\
graph TD
    subgraph outer[Outer]
        subgraph middle[Middle]
            subgraph inner[Inner]
                A --> B
            end
        end
        C --> D
    end
"""
        svg = _render(source)
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B", "C", "D")
        assert "Outer" in svg
        assert "Middle" in svg
        assert "Inner" in svg


# ---------------------------------------------------------------------------
# Styling integration
# ---------------------------------------------------------------------------


class TestStyling:
    """Styling features render without error."""

    def test_classdef_and_class_application(self) -> None:
        source = """\
graph TD
    A[Start]:::highlight --> B[End]
    classDef highlight fill:#ff0,stroke:#000
"""
        svg = _render(source)
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B")
        # The classDef CSS rule should appear in the SVG style block
        assert "highlight" in svg

    def test_inline_style(self) -> None:
        source = """\
graph TD
    A --> B
    style A fill:#f9f,stroke:#333
"""
        svg = _render(source)
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B")


# ---------------------------------------------------------------------------
# Additional coverage
# ---------------------------------------------------------------------------


class TestAdditional:
    """Additional integration tests for broader coverage."""

    def test_edge_with_dotted_label(self) -> None:
        svg = _render("graph TD\n    A -. dotted label .-> B")
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B")

    def test_edge_with_thick_label(self) -> None:
        svg = _render("graph TD\n    A == thick label ==> B")
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B")

    def test_multiple_edges_between_same_nodes(self) -> None:
        source = "graph TD\n    A --> B\n    A --> B"
        svg = _render(source)
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B")

    def test_many_nodes_chain(self) -> None:
        """A chain of 10 nodes renders without error."""
        nodes = " --> ".join(chr(65 + i) for i in range(10))
        svg = _render(f"graph LR\n    {nodes}")
        _assert_valid_svg(svg)
        for i in range(10):
            _assert_node_ids(svg, chr(65 + i))

    def test_comments_are_ignored(self) -> None:
        source = """\
graph TD
    %% This is a comment
    A --> B
    %% Another comment
    B --> C
"""
        svg = _render(source)
        _assert_valid_svg(svg)
        _assert_node_ids(svg, "A", "B", "C")
        # Comments should not appear in output
        assert "This is a comment" not in svg
