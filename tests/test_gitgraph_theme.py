"""Tests for gitGraph theme support (issue 79)."""

import xml.etree.ElementTree as ET

from merm import render_diagram
from merm.layout.gitgraph import layout_gitgraph
from merm.parser.gitgraph import parse_gitgraph
from merm.render.gitgraph import render_gitgraph_svg
from merm.theme import DARK_THEME, DEFAULT_THEME, FOREST_THEME, NEUTRAL_THEME, Theme

BASIC_SOURCE = "gitGraph\n   commit\n   commit\n"

MULTI_BRANCH_SOURCE = (
    "gitGraph\n"
    "   commit\n"
    "   branch develop\n"
    "   checkout develop\n"
    "   commit\n"
    "   checkout main\n"
    "   merge develop\n"
)

TAGGED_SOURCE = 'gitGraph\n   commit tag: "v1.0"\n'


def _render_with_theme(source: str, theme: Theme | None = None) -> str:
    graph = parse_gitgraph(source)
    layout = layout_gitgraph(graph)
    return render_gitgraph_svg(graph, layout, theme=theme)


class TestGitGraphThemeParameter:
    """Test that render_gitgraph_svg accepts and uses theme parameter."""

    def test_accepts_none_theme(self):
        svg = _render_with_theme(BASIC_SOURCE, theme=None)
        assert "<svg" in svg

    def test_accepts_default_theme(self):
        svg = _render_with_theme(BASIC_SOURCE, theme=DEFAULT_THEME)
        assert "<svg" in svg

    def test_accepts_dark_theme(self):
        svg = _render_with_theme(BASIC_SOURCE, theme=DARK_THEME)
        assert "<svg" in svg

    def test_accepts_forest_theme(self):
        svg = _render_with_theme(BASIC_SOURCE, theme=FOREST_THEME)
        assert "<svg" in svg

    def test_accepts_neutral_theme(self):
        svg = _render_with_theme(BASIC_SOURCE, theme=NEUTRAL_THEME)
        assert "<svg" in svg

    def test_valid_xml_with_all_themes(self):
        for theme in [DEFAULT_THEME, DARK_THEME, FOREST_THEME, NEUTRAL_THEME]:
            svg = _render_with_theme(MULTI_BRANCH_SOURCE, theme=theme)
            ET.fromstring(svg)  # Should not raise


class TestDarkThemeApplied:
    """Verify dark theme colors appear in the SVG output."""

    def test_background_rect_present(self):
        svg = _render_with_theme(BASIC_SOURCE, theme=DARK_THEME)
        assert 'class="gitgraph-background"' in svg
        assert DARK_THEME.background_color in svg

    def test_no_background_rect_for_default(self):
        svg = _render_with_theme(BASIC_SOURCE, theme=DEFAULT_THEME)
        assert 'class="gitgraph-background"' not in svg

    def test_text_color_in_style(self):
        svg = _render_with_theme(BASIC_SOURCE, theme=DARK_THEME)
        assert DARK_THEME.text_color in svg

    def test_font_family_in_style(self):
        svg = _render_with_theme(BASIC_SOURCE, theme=DARK_THEME)
        assert DARK_THEME.font_family in svg

    def test_branch_colors_use_theme(self):
        svg = _render_with_theme(MULTI_BRANCH_SOURCE, theme=DARK_THEME)
        # Primary branch should use node_stroke from dark theme
        assert DARK_THEME.node_stroke in svg

    def test_merge_line_uses_theme_edge_stroke(self):
        svg = _render_with_theme(MULTI_BRANCH_SOURCE, theme=DARK_THEME)
        assert DARK_THEME.edge_stroke in svg

    def test_tag_uses_theme_colors(self):
        svg = _render_with_theme(TAGGED_SOURCE, theme=DARK_THEME)
        assert DARK_THEME.subgraph_fill in svg
        assert DARK_THEME.subgraph_stroke in svg


class TestForestThemeApplied:
    """Verify forest theme colors appear in the SVG output."""

    def test_branch_colors_use_theme(self):
        svg = _render_with_theme(MULTI_BRANCH_SOURCE, theme=FOREST_THEME)
        assert FOREST_THEME.node_stroke in svg

    def test_text_color(self):
        svg = _render_with_theme(BASIC_SOURCE, theme=FOREST_THEME)
        assert FOREST_THEME.text_color in svg


class TestRenderDiagramIntegration:
    """Test that render_diagram passes theme to gitgraph renderer."""

    def test_render_diagram_with_theme_kwarg(self):
        svg = render_diagram(BASIC_SOURCE, theme=DARK_THEME)
        assert "<svg" in svg
        assert DARK_THEME.background_color in svg

    def test_render_diagram_with_theme_name_string(self):
        svg = render_diagram(BASIC_SOURCE, theme="dark")
        assert DARK_THEME.background_color in svg

    def test_render_diagram_with_init_directive(self):
        source = (
            "%%{init: {'theme': 'dark'}}%%\n"
            "gitGraph\n"
            "   commit\n"
        )
        svg = render_diagram(source)
        assert DARK_THEME.background_color in svg

    def test_render_diagram_theme_kwarg_overrides_directive(self):
        source = (
            "%%{init: {'theme': 'dark'}}%%\n"
            "gitGraph\n"
            "   commit\n"
        )
        svg = render_diagram(source, theme="forest")
        # Forest theme has white background, dark has dark background
        assert DARK_THEME.background_color not in svg

    def test_render_diagram_default_theme_no_background(self):
        svg = render_diagram(BASIC_SOURCE)
        assert 'class="gitgraph-background"' not in svg

    def test_render_diagram_all_themes_produce_valid_xml(self):
        for theme_name in ["default", "dark", "forest", "neutral"]:
            svg = render_diagram(MULTI_BRANCH_SOURCE, theme=theme_name)
            ET.fromstring(svg)


class TestCustomTheme:
    """Test with a custom Theme instance."""

    def test_custom_theme_colors_applied(self):
        custom = Theme(
            node_stroke="#ff0000",
            edge_stroke="#00ff00",
            text_color="#0000ff",
            background_color="#111111",
            subgraph_fill="#222222",
            subgraph_stroke="#333333",
        )
        svg = _render_with_theme(TAGGED_SOURCE, theme=custom)
        assert "#111111" in svg  # background
        assert "#0000ff" in svg  # text color
        assert "#ff0000" in svg  # branch color (node_stroke)
        assert "#222222" in svg  # tag fill
        assert "#333333" in svg  # tag stroke
