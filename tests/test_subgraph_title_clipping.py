"""Tests for subgraph title clipping and boundary width fix (Task 39).

Verifies that subgraph boundary rects are wide enough to fit the title text,
and that the title text has proper left margin from the rect edge.
"""

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
from pymermaid.layout import layout_diagram
from pymermaid.measure import measure_text
from pymermaid.measure.text import _line_width
from pymermaid.parser.flowchart import parse_flowchart
from pymermaid.render import render_svg

_SVG_NS = "http://www.w3.org/2000/svg"

# Subgraph title font size used in the renderer and layout
_TITLE_FONT_SIZE = 12.0
_TITLE_LEFT_MARGIN = 8.0
_TITLE_H_PADDING = 16.0

def _measure(text: str, font_size: float) -> tuple[float, float]:
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

def _parse_svg(svg_str: str) -> ET.Element:
    return ET.fromstring(svg_str)

def _get_subgraph_rect_and_text(root: ET.Element, sg_id: str):
    """Return (rect_element, text_element) for a subgraph."""
    g = root.findall(f".//*[@data-subgraph-id='{sg_id}']")
    assert len(g) == 1, f"Expected 1 subgraph group for {sg_id}, got {len(g)}"
    g = g[0]
    rects = [el for el in g if el.tag in ("rect", f"{{{_SVG_NS}}}rect")]
    texts = [el for el in g if el.tag in ("text", f"{{{_SVG_NS}}}text")]
    assert len(rects) >= 1
    assert len(texts) >= 1
    return rects[0], texts[0]

# ---------------------------------------------------------------------------
# Layout: subgraph width accommodates title
# ---------------------------------------------------------------------------

class TestSubgraphTitleWidth:
    """Verify that SubgraphLayout.width is at least as wide as the title text."""

    def test_long_title_widens_subgraph(self):
        """A subgraph with a long title and short node IDs should expand."""
        sg = Subgraph(
            id="sg1", title="Very Long Subgraph Title Here", node_ids=("A",)
        )
        d = _make_diagram(["A"], [], subgraphs=(sg,))
        result = layout_diagram(d, _measure)
        sgl = result.subgraphs["sg1"]
        title_w = _line_width("Very Long Subgraph Title Here", _TITLE_FONT_SIZE)
        min_expected = title_w + _TITLE_LEFT_MARGIN + _TITLE_H_PADDING
        assert sgl.width >= min_expected, (
            f"Subgraph width {sgl.width} < minimum for title {min_expected}"
        )

    def test_short_title_does_not_shrink(self):
        """A subgraph with a short title should not shrink below child content."""
        sg = Subgraph(id="sg1", title="X", node_ids=("A", "B"))
        d = _make_diagram(["A", "B"], [("A", "B")], subgraphs=(sg,))
        result = layout_diagram(d, _measure)
        sgl = result.subgraphs["sg1"]
        # Width should be at least as wide as the node content + padding
        nl_a = result.nodes["A"]
        nl_b = result.nodes["B"]
        content_min_x = min(nl_a.x, nl_b.x)
        content_max_x = max(nl_a.x + nl_a.width, nl_b.x + nl_b.width)
        assert sgl.width >= (content_max_x - content_min_x)

    def test_title_from_id_when_no_explicit_title(self):
        """When no title is set, the subgraph ID is used as title."""
        sg = Subgraph(
            id="very_long_subgraph_identifier", title=None, node_ids=("A",)
        )
        d = _make_diagram(["A"], [], subgraphs=(sg,))
        result = layout_diagram(d, _measure)
        sgl = result.subgraphs["very_long_subgraph_identifier"]
        title_w = _line_width("very_long_subgraph_identifier", _TITLE_FONT_SIZE)
        min_expected = title_w + _TITLE_LEFT_MARGIN + _TITLE_H_PADDING
        assert sgl.width >= min_expected

    def test_nested_subgraph_title_width(self):
        """Nested subgraphs should each have width >= their own title."""
        inner = Subgraph(
            id="inner", title="Inner Subgraph Title", node_ids=("A", "B")
        )
        outer = Subgraph(
            id="outer",
            title="Outer Subgraph Title Which Is Longer",
            node_ids=("C",),
            subgraphs=(inner,),
        )
        d = _make_diagram(
            ["A", "B", "C"], [("A", "B"), ("B", "C")], subgraphs=(outer,)
        )
        result = layout_diagram(d, _measure)

        for sg_id, sg_title in [
            ("inner", "Inner Subgraph Title"),
            ("outer", "Outer Subgraph Title Which Is Longer"),
        ]:
            sgl = result.subgraphs[sg_id]
            title_w = _line_width(sg_title, _TITLE_FONT_SIZE)
            min_expected = title_w + _TITLE_LEFT_MARGIN + _TITLE_H_PADDING
            assert sgl.width >= min_expected, (
                f"Subgraph '{sg_id}' width {sgl.width} < min {min_expected}"
            )

# ---------------------------------------------------------------------------
# Renderer: title text has left margin and fits in rect
# ---------------------------------------------------------------------------

class TestSubgraphTitleRendering:
    """Verify SVG output has title text with proper margins."""

    def test_title_text_x_has_margin(self):
        """Title text x should be rect_x + margin (at least 8px)."""
        sg = Subgraph(id="sg1", title="My Subgraph", node_ids=("A", "B"))
        d = _make_diagram(["A", "B"], [("A", "B")], subgraphs=(sg,))
        layout = layout_diagram(d, _measure)
        svg = render_svg(d, layout)
        root = _parse_svg(svg)
        rect_el, text_el = _get_subgraph_rect_and_text(root, "sg1")
        rect_x = float(rect_el.get("x"))
        text_x = float(text_el.get("x"))
        assert text_x >= rect_x + 8.0, (
            f"Title text x={text_x} should be >= rect_x + 8 = {rect_x + 8.0}"
        )

    def test_title_text_fits_in_rect(self):
        """Title text right edge should be within the rect right edge."""
        sg = Subgraph(
            id="sg1", title="Database Layer", node_ids=("A", "B")
        )
        d = _make_diagram(["A", "B"], [("A", "B")], subgraphs=(sg,))
        layout = layout_diagram(d, _measure)
        svg = render_svg(d, layout)
        root = _parse_svg(svg)
        rect_el, text_el = _get_subgraph_rect_and_text(root, "sg1")
        rect_x = float(rect_el.get("x"))
        rect_w = float(rect_el.get("width"))
        text_x = float(text_el.get("x"))
        title_w = _line_width("Database Layer", _TITLE_FONT_SIZE)
        # Title text starts at text_x and extends title_w to the right
        assert text_x + title_w <= rect_x + rect_w, (
            f"Title right edge {text_x + title_w} > rect right edge {rect_x + rect_w}"
        )

# ---------------------------------------------------------------------------
# Integration: corpus fixture rendering
# ---------------------------------------------------------------------------

class TestCorpusSubgraphTitleVisibility:
    """End-to-end tests parsing corpus fixtures and checking title visibility."""

    FIXTURES = [
        ("tests/fixtures/corpus/subgraphs/single_subgraph.mmd", "sg1", "My Subgraph"),
        ("tests/fixtures/corpus/subgraphs/nested_subgraphs.mmd", "outer", "Outer"),
        ("tests/fixtures/corpus/subgraphs/nested_subgraphs.mmd", "inner", "Inner"),
        ("tests/fixtures/corpus/subgraphs/sibling_subgraphs.mmd", "left", "Left Side"),
        (
            "tests/fixtures/corpus/subgraphs/sibling_subgraphs.mmd",
            "right", "Right Side",
        ),
        (
            "tests/fixtures/corpus/subgraphs/subgraph_with_title.mmd",
            "title1", "Database Layer",
        ),
        (
            "tests/fixtures/corpus/subgraphs/subgraph_with_title.mmd",
            "title2", "App Layer",
        ),
        ("tests/fixtures/corpus/subgraphs/cross_boundary_edges.mmd", "sg1", "Group 1"),
        ("tests/fixtures/corpus/subgraphs/cross_boundary_edges.mmd", "sg2", "Group 2"),
    ]

    @pytest.mark.parametrize("fixture,sg_id,title", FIXTURES)
    def test_title_fits_in_boundary(self, fixture, sg_id, title):
        """Subgraph boundary rect is wide enough for the title text."""
        with open(fixture) as f:
            text = f.read()

        # Handle both 'graph' and 'flowchart' keywords
        diagram = parse_flowchart(text)
        layout = layout_diagram(diagram, measure_text)
        svg = render_svg(diagram, layout)
        root = _parse_svg(svg)

        rect_el, text_el = _get_subgraph_rect_and_text(root, sg_id)
        rect_x = float(rect_el.get("x"))
        rect_w = float(rect_el.get("width"))
        text_x = float(text_el.get("x"))

        # Title text should start inside the rect with margin
        assert text_x >= rect_x, (
            f"[{sg_id}] Title text x={text_x} < rect x={rect_x}"
        )

        # Title text should fit within the rect
        title_w = _line_width(title, _TITLE_FONT_SIZE)
        assert text_x + title_w <= rect_x + rect_w, (
            f"[{sg_id}] Title right edge {text_x + title_w} "
            f"> rect right edge {rect_x + rect_w}"
        )

    @pytest.mark.parametrize("fixture", [
        "tests/fixtures/corpus/subgraphs/single_subgraph.mmd",
        "tests/fixtures/corpus/subgraphs/nested_subgraphs.mmd",
        "tests/fixtures/corpus/subgraphs/sibling_subgraphs.mmd",
        "tests/fixtures/corpus/subgraphs/subgraph_with_title.mmd",
        "tests/fixtures/corpus/subgraphs/cross_boundary_edges.mmd",
        "tests/fixtures/corpus/subgraphs/subgraph_direction.mmd",
    ])
    def test_renders_valid_svg(self, fixture):
        """All corpus subgraph fixtures produce valid SVG."""
        with open(fixture) as f:
            text = f.read()
        diagram = parse_flowchart(text)
        layout = layout_diagram(diagram, measure_text)
        svg = render_svg(diagram, layout)
        root = _parse_svg(svg)
        assert root.tag in ("svg", f"{{{_SVG_NS}}}svg")
