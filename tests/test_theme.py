"""Tests for the Theme system and its integration with the renderer."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest

from pymermaid.ir import (
    Diagram,
    DiagramType,
    Direction,
    Edge,
    Node,
    Subgraph,
)
from pymermaid.layout import EdgeLayout, LayoutResult, NodeLayout, Point, layout_diagram
from pymermaid.measure import measure_text
from pymermaid.render import render_svg
from pymermaid.theme import DEFAULT_THEME, Theme

_SVG_NS = "http://www.w3.org/2000/svg"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_diagram(
    nodes: list[tuple[str, str]] | None = None,
    edges: list[tuple[str, str, str | None]] | None = None,
    subgraphs: tuple[Subgraph, ...] = (),
) -> Diagram:
    if nodes is None:
        nodes = [("A", "A"), ("B", "B")]
    if edges is None:
        edges = [("A", "B", None)]
    return Diagram(
        type=DiagramType.flowchart,
        direction=Direction.TB,
        nodes=tuple(Node(id=nid, label=label) for nid, label in nodes),
        edges=tuple(
            Edge(source=s, target=t, label=lbl) for s, t, lbl in edges
        ),
        subgraphs=subgraphs,
    )


def _simple_layout(
    nodes: dict[str, tuple[float, float, float, float]] | None = None,
    edges: list[tuple[str, str, list[tuple[float, float]]]] | None = None,
    width: float = 200.0,
    height: float = 100.0,
) -> LayoutResult:
    if nodes is None:
        nodes = {
            "A": (20.0, 10.0, 80.0, 40.0),
            "B": (20.0, 80.0, 80.0, 40.0),
        }
    if edges is None:
        edges = [("A", "B", [(60.0, 50.0), (60.0, 80.0)])]
    nl = {
        nid: NodeLayout(x=x, y=y, width=w, height=h)
        for nid, (x, y, w, h) in nodes.items()
    }
    el = [
        EdgeLayout(
            source=src,
            target=tgt,
            points=[Point(x=px, y=py) for px, py in pts],
        )
        for src, tgt, pts in edges
    ]
    return LayoutResult(nodes=nl, edges=el, width=width, height=height)


def _parse(svg_str: str) -> ET.Element:
    return ET.fromstring(svg_str)


# ---------------------------------------------------------------------------
# 1. Theme dataclass unit tests
# ---------------------------------------------------------------------------


class TestThemeDataclass:
    def test_default_theme_is_instance(self):
        assert isinstance(DEFAULT_THEME, Theme)

    def test_default_node_fill(self):
        assert DEFAULT_THEME.node_fill == "#ECECFF"

    def test_default_node_stroke(self):
        assert DEFAULT_THEME.node_stroke == "#9370DB"

    def test_default_edge_stroke(self):
        assert DEFAULT_THEME.edge_stroke == "#333333"

    def test_default_edge_stroke_width(self):
        assert DEFAULT_THEME.edge_stroke_width == "2"

    def test_default_font_family(self):
        assert "trebuchet ms" in DEFAULT_THEME.font_family

    def test_default_font_size(self):
        assert DEFAULT_THEME.node_font_size == "16px"

    def test_default_subgraph_fill(self):
        assert DEFAULT_THEME.subgraph_fill == "#ffffde"

    def test_default_subgraph_stroke(self):
        assert DEFAULT_THEME.subgraph_stroke == "#aaaa33"

    def test_default_background(self):
        assert DEFAULT_THEME.background_color == "white"

    def test_default_rank_sep(self):
        assert DEFAULT_THEME.rank_sep == 80.0

    def test_default_node_sep(self):
        assert DEFAULT_THEME.node_sep == 50.0

    def test_default_node_padding_h(self):
        assert DEFAULT_THEME.node_padding_h == 15.0

    def test_default_node_padding_v(self):
        assert DEFAULT_THEME.node_padding_v == 10.0

    def test_default_node_min_height(self):
        assert DEFAULT_THEME.node_min_height == 54.0

    def test_default_node_border_radius(self):
        assert DEFAULT_THEME.node_border_radius == 5.0

    def test_default_edge_label_bg(self):
        assert DEFAULT_THEME.edge_label_bg == "rgba(232,232,232,0.8)"


class TestThemeCustomization:
    def test_custom_theme_creation(self):
        theme = Theme(node_fill="#ff0000", node_stroke="#00ff00")
        assert theme.node_fill == "#ff0000"
        assert theme.node_stroke == "#00ff00"
        # Other fields should still have defaults
        assert theme.font_family == DEFAULT_THEME.font_family

    def test_replace_method(self):
        custom = DEFAULT_THEME.replace(node_fill="#red")
        assert custom.node_fill == "#red"
        assert custom.node_stroke == DEFAULT_THEME.node_stroke

    def test_theme_is_frozen(self):
        with pytest.raises(AttributeError):
            DEFAULT_THEME.node_fill = "#000"  # type: ignore[misc]


class TestThemeImports:
    def test_import_from_theme_module(self):
        from pymermaid.theme import DEFAULT_THEME, Theme
        assert isinstance(DEFAULT_THEME, Theme)

    def test_import_from_render_package(self):
        from pymermaid.render import DEFAULT_THEME, Theme
        assert isinstance(DEFAULT_THEME, Theme)


# ---------------------------------------------------------------------------
# 2. Theme integration with renderer
# ---------------------------------------------------------------------------


class TestThemeRendererIntegration:
    def test_default_theme_node_fill_in_svg(self):
        d = _simple_diagram()
        lr = _simple_layout()
        result = render_svg(d, lr)
        assert "#ECECFF" in result

    def test_default_theme_node_stroke_in_svg(self):
        d = _simple_diagram()
        lr = _simple_layout()
        result = render_svg(d, lr)
        assert "#9370DB" in result

    def test_default_theme_font_family_in_css(self):
        d = _simple_diagram()
        lr = _simple_layout()
        result = render_svg(d, lr)
        assert "trebuchet ms" in result

    def test_default_theme_edge_stroke_width_in_css(self):
        d = _simple_diagram()
        lr = _simple_layout()
        result = render_svg(d, lr)
        # The CSS for .edge path should have stroke-width: 2
        assert "stroke-width: 2" in result

    def test_default_theme_subgraph_fill_in_css(self):
        sg = Subgraph(id="sg1", title="Group", node_ids=("A", "B"))
        d = _simple_diagram(subgraphs=(sg,))
        lr = _simple_layout()
        result = render_svg(d, lr)
        assert "#ffffde" in result

    def test_default_theme_subgraph_stroke_in_css(self):
        sg = Subgraph(id="sg1", title="Group", node_ids=("A", "B"))
        d = _simple_diagram(subgraphs=(sg,))
        lr = _simple_layout()
        result = render_svg(d, lr)
        assert "#aaaa33" in result

    def test_custom_theme_node_fill(self):
        custom = Theme(node_fill="#ff0000")
        d = _simple_diagram()
        lr = _simple_layout()
        result = render_svg(d, lr, theme=custom)
        assert "#ff0000" in result
        assert "#ECECFF" not in result

    def test_custom_theme_subgraph_colors(self):
        custom = Theme(subgraph_fill="#123456", subgraph_stroke="#654321")
        sg = Subgraph(id="sg1", title="Custom", node_ids=("A", "B"))
        d = _simple_diagram(subgraphs=(sg,))
        lr = _simple_layout()
        result = render_svg(d, lr, theme=custom)
        assert "#123456" in result
        assert "#654321" in result

    def test_render_svg_default_theme_when_none(self):
        """render_svg with theme=None should use DEFAULT_THEME."""
        d = _simple_diagram()
        lr = _simple_layout()
        result_default = render_svg(d, lr)
        result_none = render_svg(d, lr, theme=None)
        assert result_default == result_none


# ---------------------------------------------------------------------------
# 3. SVG output structure
# ---------------------------------------------------------------------------


class TestSVGOutputStructure:
    def test_svg_has_background_color_style(self):
        d = _simple_diagram()
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        style = root.get("style", "")
        assert "background-color" in style
        assert "white" in style

    def test_text_elements_have_font_family(self):
        d = _simple_diagram()
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        # Find all text elements in node groups
        node_groups = root.findall(".//*[@data-node-id]")
        assert len(node_groups) >= 1
        for g in node_groups:
            text_els = [
                el for el in g.iter()
                if el.tag in ("text", f"{{{_SVG_NS}}}text")
            ]
            for text_el in text_els:
                ff = text_el.get("font-family", "")
                assert "trebuchet" in ff or "verdana" in ff, (
                    f"text element missing font-family: {ff}"
                )

    def test_subgraph_text_has_font_family(self):
        sg = Subgraph(id="sg1", title="Group", node_ids=("A", "B"))
        d = _simple_diagram(subgraphs=(sg,))
        lr = _simple_layout()
        root = _parse(render_svg(d, lr))
        sg_groups = root.findall(".//*[@data-subgraph-id='sg1']")
        assert len(sg_groups) == 1
        text_els = [
            el for el in sg_groups[0].iter()
            if el.tag in ("text", f"{{{_SVG_NS}}}text")
        ]
        for text_el in text_els:
            ff = text_el.get("font-family", "")
            assert "trebuchet" in ff or "verdana" in ff


# ---------------------------------------------------------------------------
# 4. Coordinate rounding
# ---------------------------------------------------------------------------


class TestCoordinateRounding:
    def test_no_long_decimals_in_svg(self):
        """Rendered SVG should have no float values with >2 decimal places."""
        d = Diagram(
            type=DiagramType.flowchart,
            direction=Direction.TB,
            nodes=(
                Node(id="A", label="Start"),
                Node(id="B", label="Middle"),
                Node(id="C", label="End"),
            ),
            edges=(
                Edge(source="A", target="B"),
                Edge(source="B", target="C"),
            ),
        )
        lr = layout_diagram(d, measure_text)
        result = render_svg(d, lr)
        # Find all numeric values with decimals
        floats = re.findall(r"\d+\.\d+", result)
        for f in floats:
            decimal_part = f.split(".")[1]
            assert len(decimal_part) <= 2, (
                f"Found coordinate with >2 decimal places: {f}"
            )

    def test_rounding_with_layout_pipeline(self):
        """Full pipeline should produce properly rounded coordinates."""
        d = Diagram(
            type=DiagramType.flowchart,
            direction=Direction.LR,
            nodes=(
                Node(id="X", label="Hello World"),
                Node(id="Y", label="Testing"),
            ),
            edges=(Edge(source="X", target="Y"),),
        )
        lr = layout_diagram(d, measure_text)
        result = render_svg(d, lr)
        floats = re.findall(r"\d+\.\d+", result)
        for f in floats:
            decimal_part = f.split(".")[1]
            assert len(decimal_part) <= 2, (
                f"Found coordinate with >2 decimal places: {f}"
            )


# ---------------------------------------------------------------------------
# 5. Integration: visual quality with fixture
# ---------------------------------------------------------------------------


class TestVisualQualityIntegration:
    def test_simple_flowchart_uses_theme_colors(self):
        """Render a simple flowchart and verify it uses mermaid theme colors."""
        from pymermaid.parser import parse_flowchart

        source = "graph TD\n    A[Start] --> B[End]"
        diagram = parse_flowchart(source)
        lr = layout_diagram(diagram, measure_text)
        result = render_svg(diagram, lr)

        # Should use mermaid default colors
        assert "#ECECFF" in result
        assert "#9370DB" in result
        assert "trebuchet ms" in result

    def test_render_with_custom_theme(self):
        """Custom theme colors should appear in output."""
        from pymermaid.parser import parse_flowchart

        custom = Theme(
            node_fill="#abcdef",
            node_stroke="#fedcba",
            edge_stroke="#111111",
        )
        source = "graph TD\n    A --> B"
        diagram = parse_flowchart(source)
        lr = layout_diagram(diagram, measure_text)
        result = render_svg(diagram, lr, theme=custom)

        assert "#abcdef" in result
        assert "#fedcba" in result
