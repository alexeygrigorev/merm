"""Tests for pie chart IR, parser, renderer, and integration."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from pymermaid import render_diagram
from pymermaid.ir.pie import PieChart, PieSlice
from pymermaid.parser.flowchart import ParseError
from pymermaid.parser.pie import parse_pie
from pymermaid.render.pie import render_pie_svg

FIXTURES = Path(__file__).parent / "fixtures" / "corpus" / "pie"

# ---------------------------------------------------------------------------
# IR unit tests
# ---------------------------------------------------------------------------

class TestPieChartIR:
    def test_create_with_title_and_slices(self):
        chart = PieChart(
            title="Fruits",
            show_data=False,
            slices=(
                PieSlice("Apple", 50),
                PieSlice("Banana", 30),
                PieSlice("Cherry", 20),
            ),
        )
        assert chart.title == "Fruits"
        assert chart.show_data is False
        assert len(chart.slices) == 3
        assert chart.slices[0].label == "Apple"
        assert chart.slices[0].value == 50

    def test_create_with_empty_title_and_show_data(self):
        chart = PieChart(title="", show_data=True, slices=(PieSlice("X", 1),))
        assert chart.title == ""
        assert chart.show_data is True

# ---------------------------------------------------------------------------
# Parser unit tests
# ---------------------------------------------------------------------------

class TestParsePieBasics:
    def test_basic_fixture(self):
        text = (FIXTURES / "basic.mmd").read_text()
        chart = parse_pie(text)
        assert chart.title == "Favorite Pets"
        assert chart.show_data is False
        assert len(chart.slices) == 3
        assert chart.slices[0] == PieSlice("Dogs", 386)
        assert chart.slices[1] == PieSlice("Cats", 85)
        assert chart.slices[2] == PieSlice("Rats", 15)

    def test_show_data_fixture(self):
        text = (FIXTURES / "show_data.mmd").read_text()
        chart = parse_pie(text)
        assert chart.show_data is True
        assert chart.title == "Project Time Allocation"
        assert len(chart.slices) == 5

    def test_no_title_fixture(self):
        text = (FIXTURES / "no_title.mmd").read_text()
        chart = parse_pie(text)
        assert chart.title == ""
        assert len(chart.slices) == 2

    def test_single_slice_fixture(self):
        text = (FIXTURES / "single_slice.mmd").read_text()
        chart = parse_pie(text)
        assert len(chart.slices) == 1
        assert chart.slices[0].value == 100

class TestParsePieEdgeCases:
    def test_comments_stripped(self):
        text = (
            'pie title Test\n    %% a comment\n'
            '    "A" : 10\n    %% another\n    "B" : 20'
        )
        chart = parse_pie(text)
        assert len(chart.slices) == 2

    def test_extra_blank_lines(self):
        text = 'pie title Test\n\n    "A" : 10\n\n    "B" : 20\n\n'
        chart = parse_pie(text)
        assert len(chart.slices) == 2

    def test_float_values(self):
        text = 'pie\n    "X" : 3.14\n    "Y" : 2.72'
        chart = parse_pie(text)
        assert chart.slices[0].value == pytest.approx(3.14)
        assert chart.slices[1].value == pytest.approx(2.72)

    def test_negative_value_raises(self):
        # The regex only matches non-negative numbers, so a negative value
        # line with quotes will be caught as malformed
        text = 'pie\n    "Bad" : -5'
        with pytest.raises(ParseError):
            parse_pie(text)

    def test_no_slices_raises(self):
        text = "pie title Foo"
        with pytest.raises(ParseError, match="No slices"):
            parse_pie(text)

    def test_empty_input_raises(self):
        with pytest.raises(ParseError, match="Empty input"):
            parse_pie("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ParseError, match="Empty input"):
            parse_pie("   \n  ")

    def test_missing_quotes_raises(self):
        text = 'pie\n    Bad : 10'
        with pytest.raises(ParseError):
            parse_pie(text)

# ---------------------------------------------------------------------------
# Renderer unit tests
# ---------------------------------------------------------------------------

class TestRenderPieSVGStructure:
    def test_svg_wrapper(self):
        chart = PieChart(
            title="Test",
            show_data=False,
            slices=(PieSlice("A", 50), PieSlice("B", 30), PieSlice("C", 20)),
        )
        svg = render_pie_svg(chart)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")

    def test_three_slices_have_three_paths(self):
        chart = PieChart(
            title="Test",
            show_data=False,
            slices=(PieSlice("A", 50), PieSlice("B", 30), PieSlice("C", 20)),
        )
        svg = render_pie_svg(chart)
        assert svg.count('class="pie-slice"') == 3

    def test_single_slice_renders_circle(self):
        chart = PieChart(
            title="One",
            show_data=False,
            slices=(PieSlice("Only", 100),),
        )
        svg = render_pie_svg(chart)
        assert "<circle" in svg
        assert "<path" not in svg

    def test_title_renders_text(self):
        chart = PieChart(
            title="My Title",
            show_data=False,
            slices=(PieSlice("A", 1),),
        )
        svg = render_pie_svg(chart)
        assert "My Title" in svg
        assert 'class="pie-title"' in svg

    def test_no_title_no_title_text(self):
        chart = PieChart(
            title="",
            show_data=False,
            slices=(PieSlice("A", 1),),
        )
        svg = render_pie_svg(chart)
        assert 'class="pie-title"' not in svg

    def test_valid_xml(self):
        chart = PieChart(
            title="XML Test",
            show_data=False,
            slices=(PieSlice("A", 50), PieSlice("B", 50)),
        )
        svg = render_pie_svg(chart)
        ET.fromstring(svg)  # Should not raise

    def test_show_data_includes_raw_values(self):
        chart = PieChart(
            title="Data",
            show_data=True,
            slices=(PieSlice("X", 60), PieSlice("Y", 40)),
        )
        svg = render_pie_svg(chart)
        assert "(60)" in svg
        assert "(40)" in svg

    def test_show_data_false_no_raw_values(self):
        chart = PieChart(
            title="Data",
            show_data=False,
            slices=(PieSlice("X", 60), PieSlice("Y", 40)),
        )
        svg = render_pie_svg(chart)
        assert "(60)" not in svg
        assert "(40)" not in svg

class TestRenderPieGeometry:
    def test_equal_slices_have_equal_arcs(self):
        """Two 50/50 slices should each sweep 180 degrees."""
        chart = PieChart(
            title="",
            show_data=False,
            slices=(PieSlice("A", 50), PieSlice("B", 50)),
        )
        svg = render_pie_svg(chart)
        # Extract path d attributes
        paths = re.findall(r'd="([^"]+)"', svg)
        assert len(paths) == 2

        for d in paths:
            # Arc command: A rx ry rotation large-arc sweep-flag x y
            arc_match = re.search(r"A (\d+) (\d+) (\d+) (\d+) (\d+)", d)
            assert arc_match is not None
            large_arc_flag = int(arc_match.group(4))
            # 180 degrees is exactly the boundary; neither large nor small arc
            # For exactly 180, large_arc should be 0 (sweep <= 180)
            assert large_arc_flag == 0

    def test_75_25_split(self):
        """75/25 split: first wedge 270 deg (large arc), second 90 deg (small)."""
        chart = PieChart(
            title="",
            show_data=False,
            slices=(PieSlice("A", 75), PieSlice("B", 25)),
        )
        svg = render_pie_svg(chart)
        paths = re.findall(r'd="([^"]+)"', svg)
        assert len(paths) == 2

        # First path should have large-arc-flag = 1 (270 > 180)
        arc0 = re.search(r"A (\d+) (\d+) (\d+) (\d+) (\d+)", paths[0])
        assert arc0 is not None
        assert int(arc0.group(4)) == 1  # large arc

        # Second path should have large-arc-flag = 0 (90 < 180)
        arc1 = re.search(r"A (\d+) (\d+) (\d+) (\d+) (\d+)", paths[1])
        assert arc1 is not None
        assert int(arc1.group(4)) == 0  # small arc

# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestRenderDiagramDispatch:
    def test_dispatch_with_title(self):
        svg = render_diagram('pie title X\n    "A" : 1')
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_dispatch_without_title(self):
        svg = render_diagram('pie\n    "A" : 60\n    "B" : 40')
        assert "<svg" in svg
        assert "</svg>" in svg

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
