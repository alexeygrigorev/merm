"""Tests for Font Awesome icon support (task 20)."""

import xml.etree.ElementTree as ET

import pytest

from pymermaid.icons import (
    LabelSegment,
    get_icon_path,
    has_icons,
    icon_count,
    parse_label,
)
from pymermaid.measure.text import TextMeasurer, measure_text

# ---------------------------------------------------------------------------
# Icon registry tests
# ---------------------------------------------------------------------------

class TestIconRegistry:
    """Tests for the icon registry lookups."""

    def test_known_icon_returns_tuple(self):
        result = get_icon_path("car")
        assert result is not None
        path_d, w, h = result
        assert isinstance(path_d, str)
        assert len(path_d) > 10  # non-trivial path data
        assert isinstance(w, int)
        assert isinstance(h, int)

    def test_unknown_icon_returns_none(self):
        assert get_icon_path("nonexistent-icon-xyz") is None

    def test_minimum_icon_count(self):
        """The registry must contain at least 60 icons."""
        assert icon_count() >= 60

    @pytest.mark.parametrize(
        "name",
        [
            "car", "home", "user", "check", "times", "star", "heart",
            "bell", "search", "cog", "trash", "plus", "minus",
            "arrow-right", "arrow-left", "envelope", "phone", "lock",
            "camera", "file", "folder", "download", "upload", "cloud",
            "database", "code", "terminal", "bug", "wrench", "globe",
            "clock", "calendar", "comment", "link", "bolt", "fire",
            "shield", "flag", "tag", "bookmark", "eye", "ban",
            "exclamation-triangle", "info-circle", "check-circle",
            "times-circle",
        ],
    )
    def test_required_icons_present(self, name: str):
        """Each icon listed in the task spec must be in the registry."""
        result = get_icon_path(name)
        assert result is not None, f"Icon '{name}' not found in registry"

    def test_viewbox_dimensions_positive(self):
        """All icons must have positive viewBox dimensions."""
        result = get_icon_path("home")
        assert result is not None
        _, w, h = result
        assert w > 0
        assert h > 0

    def test_icon_path_is_nonempty_string(self):
        result = get_icon_path("user")
        assert result is not None
        path_d, _, _ = result
        assert isinstance(path_d, str)
        assert len(path_d) > 0

# ---------------------------------------------------------------------------
# Label parsing tests
# ---------------------------------------------------------------------------

class TestLabelParsing:
    """Tests for parsing labels with fa:fa-* tokens."""

    def test_icon_only(self):
        segments = parse_label("fa:fa-car")
        assert len(segments) == 1
        assert segments[0] == LabelSegment(kind="icon", value="car")

    def test_icon_plus_text(self):
        segments = parse_label("fa:fa-car Car")
        assert len(segments) == 2
        assert segments[0] == LabelSegment(kind="icon", value="car")
        assert segments[1] == LabelSegment(kind="text", value=" Car")

    def test_text_plus_icon(self):
        segments = parse_label("Drive fa:fa-car")
        assert len(segments) == 2
        assert segments[0] == LabelSegment(kind="text", value="Drive ")
        assert segments[1] == LabelSegment(kind="icon", value="car")

    def test_multiple_icons(self):
        segments = parse_label("fa:fa-check Done fa:fa-star")
        assert len(segments) == 3
        assert segments[0] == LabelSegment(kind="icon", value="check")
        assert segments[1] == LabelSegment(kind="text", value=" Done ")
        assert segments[2] == LabelSegment(kind="icon", value="star")

    def test_no_icons_returns_text(self):
        segments = parse_label("Hello World")
        assert len(segments) == 1
        assert segments[0] == LabelSegment(kind="text", value="Hello World")

    def test_has_icons_true(self):
        assert has_icons("fa:fa-car Car") is True

    def test_has_icons_false(self):
        assert has_icons("Just text") is False

    def test_hyphenated_icon_name(self):
        segments = parse_label("fa:fa-arrow-right Go")
        assert segments[0] == LabelSegment(kind="icon", value="arrow-right")

    def test_icon_between_text(self):
        segments = parse_label("Go fa:fa-arrow-right Now")
        assert len(segments) == 3
        assert segments[0].kind == "text"
        assert segments[1].kind == "icon"
        assert segments[2].kind == "text"

# ---------------------------------------------------------------------------
# Text measurement with icons
# ---------------------------------------------------------------------------

class TestMeasurementWithIcons:
    """Tests that text measurement properly accounts for icon tokens."""

    def test_icon_adds_width(self):
        """A label with an icon should be wider than just text."""
        measurer = TextMeasurer()
        w_text, _ = measurer.measure("Car")
        w_icon, _ = measurer.measure("fa:fa-car Car")
        assert w_icon > w_text

    def test_icon_only_has_positive_width(self):
        measurer = TextMeasurer()
        w, h = measurer.measure("fa:fa-car")
        assert w > 0
        assert h > 0

    def test_icon_width_scales_with_font_size(self):
        measurer = TextMeasurer()
        w_small, _ = measurer.measure("fa:fa-car", font_size=12.0)
        w_large, _ = measurer.measure("fa:fa-car", font_size=24.0)
        assert w_large > w_small

    def test_convenience_function_handles_icons(self):
        w, h = measure_text("fa:fa-check Done")
        assert w > 0
        assert h > 0

# ---------------------------------------------------------------------------
# SVG rendering with icons
# ---------------------------------------------------------------------------

class TestSVGRenderingWithIcons:
    """Tests for SVG output when labels contain FA icons."""

    def _render_flowchart(self, source: str) -> str:
        from pymermaid import render_diagram
        return render_diagram(source)

    def test_icon_renders_path_element(self):
        svg = self._render_flowchart('graph TD\n    A["fa:fa-car Car"]')
        root = ET.fromstring(svg)
        # Should contain a <path> element with icon data inside a <g class="fa-icon">
        paths = root.findall(".//{http://www.w3.org/2000/svg}g[@class='fa-icon']")
        # The icon group should exist
        assert len(paths) > 0, "Expected at least one fa-icon group in SVG"

    def test_icon_has_fill_color(self):
        svg = self._render_flowchart('graph TD\n    A["fa:fa-heart Love"]')
        root = ET.fromstring(svg)
        icon_groups = root.findall(
            ".//{http://www.w3.org/2000/svg}g[@class='fa-icon']"
        )
        assert len(icon_groups) > 0
        path = icon_groups[0].find("{http://www.w3.org/2000/svg}path")
        assert path is not None
        fill = path.get("fill")
        assert fill is not None
        assert fill != ""

    def test_unknown_icon_renders_name_as_text(self):
        svg = self._render_flowchart('graph TD\n    A["fa:fa-nonexistent"]')
        root = ET.fromstring(svg)
        # Should render "nonexistent" as plain text somewhere
        all_text = "".join(
            el.text or ""
            for el in root.iter("{http://www.w3.org/2000/svg}text")
        )
        assert "nonexistent" in all_text

    def test_icon_only_label_renders(self):
        svg = self._render_flowchart('graph TD\n    A["fa:fa-check"]')
        # Should not raise and should contain SVG content
        assert "<svg" in svg
        root = ET.fromstring(svg)
        icon_groups = root.findall(
            ".//{http://www.w3.org/2000/svg}g[@class='fa-icon']"
        )
        assert len(icon_groups) > 0

    def test_text_plus_icon_renders_both(self):
        svg = self._render_flowchart('graph TD\n    A["Start fa:fa-star"]')
        root = ET.fromstring(svg)
        # Should have both text and icon
        all_text = "".join(
            el.text or ""
            for el in root.iter("{http://www.w3.org/2000/svg}text")
        )
        assert "Start " in all_text
        icon_groups = root.findall(
            ".//{http://www.w3.org/2000/svg}g[@class='fa-icon']"
        )
        assert len(icon_groups) > 0

    def test_multiple_icons_in_label(self):
        svg = self._render_flowchart(
            'graph TD\n    A["fa:fa-check Done fa:fa-star"]'
        )
        root = ET.fromstring(svg)
        icon_groups = root.findall(
            ".//{http://www.w3.org/2000/svg}g[@class='fa-icon']"
        )
        assert len(icon_groups) >= 2

# ---------------------------------------------------------------------------
# Integration: full pipeline
# ---------------------------------------------------------------------------

class TestIntegration:
    """Full pipeline integration tests with icon labels."""

    def test_flowchart_with_icons_full_pipeline(self):
        from pymermaid import render_diagram

        source = """graph LR
    A["fa:fa-home Home"] --> B["fa:fa-cog Settings"]
    B --> C["fa:fa-user Profile"]
"""
        svg = render_diagram(source)
        assert "<svg" in svg
        root = ET.fromstring(svg)
        icon_groups = root.findall(
            ".//{http://www.w3.org/2000/svg}g[@class='fa-icon']"
        )
        # Should have 3 icons (one per node)
        assert len(icon_groups) == 3

    def test_mixed_icon_and_plain_nodes(self):
        from pymermaid import render_diagram

        source = """graph TD
    A["fa:fa-car Car"] --> B["Plain text"]
    B --> C["fa:fa-star"]
"""
        svg = render_diagram(source)
        root = ET.fromstring(svg)
        icon_groups = root.findall(
            ".//{http://www.w3.org/2000/svg}g[@class='fa-icon']"
        )
        # A has 1 icon, C has 1 icon => 2 total
        assert len(icon_groups) == 2

    def test_node_sizing_with_icon(self):
        """Nodes with icons should be sized appropriately (not too small)."""
        from pymermaid.ir import Diagram, DiagramType, Direction, Node, NodeShape
        from pymermaid.layout import layout_diagram
        from pymermaid.measure.text import TextMeasurer

        diagram = Diagram(
            type=DiagramType.flowchart,
            direction=Direction.TB,
            nodes=[
                Node(id="A", label="fa:fa-car Car", shape=NodeShape.rect),
                Node(id="B", label="Car", shape=NodeShape.rect),
            ],
            edges=[],
        )
        measurer = TextMeasurer()
        layout = layout_diagram(diagram, measure_fn=measurer.measure)
        # Node A (with icon) should be at least as wide as node B (text only)
        assert layout.nodes["A"].width >= layout.nodes["B"].width
