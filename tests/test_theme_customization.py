"""Tests for issue 77: theme customization.

Covers built-in themes, directive parsing, render_diagram/render_to_file/
render_to_png theme parameter, and CLI --theme flag.
"""

import sys
from pathlib import Path

import pytest

from merm import render_diagram, render_to_file, render_to_png
from merm.theme import (
    DARK_THEME,
    DEFAULT_THEME,
    FOREST_THEME,
    NEUTRAL_THEME,
    THEMES,
    Theme,
    get_theme,
)

_SIMPLE_FLOWCHART = "graph TD\n    A[Start] --> B[End]"


# ---------------------------------------------------------------------------
# 1. Theme definitions
# ---------------------------------------------------------------------------

class TestThemeDefinitions:
    def test_themes_dict_has_four_keys(self):
        assert set(THEMES.keys()) == {"default", "dark", "forest", "neutral"}

    def test_get_theme_default(self):
        assert get_theme("default") is DEFAULT_THEME

    def test_get_theme_dark(self):
        theme = get_theme("dark")
        assert theme is DARK_THEME
        assert theme.background_color != "white"

    def test_get_theme_forest(self):
        theme = get_theme("forest")
        assert theme is FOREST_THEME
        # Green-ish node fill
        assert "cde498" in theme.node_fill.lower()

    def test_get_theme_neutral(self):
        theme = get_theme("neutral")
        assert theme is NEUTRAL_THEME
        # Grey-ish node fill
        assert "eee" in theme.node_fill.lower()

    def test_get_theme_case_sensitive(self):
        with pytest.raises(ValueError):
            get_theme("DARK")

    def test_get_theme_empty_string(self):
        with pytest.raises(ValueError):
            get_theme("")

    def test_get_theme_nonexistent(self):
        with pytest.raises(ValueError, match="Unknown theme"):
            get_theme("nonexistent")

    def test_all_themes_are_frozen(self):
        for name, theme in THEMES.items():
            with pytest.raises(AttributeError):
                theme.node_fill = "#000"  # type: ignore[misc]

    def test_all_themes_have_distinct_node_fill(self):
        fills = [t.node_fill for t in THEMES.values()]
        assert len(set(fills)) == len(fills), "All themes must have distinct node_fill"


# ---------------------------------------------------------------------------
# 2. Directive parsing
# ---------------------------------------------------------------------------

class TestDirectiveParsing:
    def test_single_quotes(self):
        source = "%%{init: {'theme': 'dark'}}%%\ngraph TD\n    A --> B"
        svg = render_diagram(source)
        assert DARK_THEME.background_color in svg

    def test_double_quotes(self):
        source = '%%{init: {"theme": "forest"}}%%\ngraph TD\n    A --> B'
        svg = render_diagram(source)
        assert FOREST_THEME.node_fill in svg

    def test_extra_whitespace(self):
        source = '%%{ init: { "theme": "neutral" } }%%\ngraph TD\n    A --> B'
        svg = render_diagram(source)
        assert NEUTRAL_THEME.node_fill in svg

    def test_no_directive_uses_default(self):
        svg = render_diagram(_SIMPLE_FLOWCHART)
        assert DEFAULT_THEME.node_fill in svg

    def test_directive_stripped_before_parsing(self):
        """Source with directive should not cause a parse error."""
        source = "%%{init: {'theme': 'dark'}}%%\ngraph TD\n    A --> B"
        svg = render_diagram(source)
        assert "<svg" in svg

    def test_directive_on_first_line(self):
        source = "%%{init: {'theme': 'dark'}}%%\ngraph TD\n A --> B"
        svg = render_diagram(source)
        assert DARK_THEME.node_fill in svg

    def test_directive_with_leading_whitespace(self):
        source = "  %%{init: {'theme': 'dark'}}%%\ngraph TD\n A --> B"
        svg = render_diagram(source)
        assert DARK_THEME.node_fill in svg

    def test_unknown_theme_in_directive_raises(self):
        source = "%%{init: {'theme': 'bogus'}}%%\ngraph TD\n A --> B"
        with pytest.raises(ValueError, match="Unknown theme"):
            render_diagram(source)


# ---------------------------------------------------------------------------
# 3. render_diagram with theme parameter
# ---------------------------------------------------------------------------

class TestRenderDiagramTheme:
    def test_theme_string_dark(self):
        svg = render_diagram(_SIMPLE_FLOWCHART, theme="dark")
        assert DARK_THEME.background_color in svg
        assert DARK_THEME.node_fill in svg

    def test_theme_string_default(self):
        svg = render_diagram(_SIMPLE_FLOWCHART, theme="default")
        assert DEFAULT_THEME.node_fill in svg

    def test_theme_instance(self):
        custom = Theme(node_fill="#abc123")
        svg = render_diagram(_SIMPLE_FLOWCHART, theme=custom)
        assert "#abc123" in svg

    def test_explicit_overrides_directive(self):
        source = "%%{init: {'theme': 'dark'}}%%\ngraph TD\n A --> B"
        svg = render_diagram(source, theme="neutral")
        assert NEUTRAL_THEME.node_fill in svg
        # Dark theme node_fill should NOT be present
        assert DARK_THEME.node_fill not in svg

    def test_invalid_theme_name_raises(self):
        with pytest.raises(ValueError, match="Unknown theme"):
            render_diagram(_SIMPLE_FLOWCHART, theme="bogus")


# ---------------------------------------------------------------------------
# 4. render_to_file and render_to_png with theme
# ---------------------------------------------------------------------------

class TestRenderToFileTheme:
    def test_render_to_file_with_theme(self, tmp_path: Path):
        out = tmp_path / "out.svg"
        render_to_file(_SIMPLE_FLOWCHART, out, theme="dark")
        content = out.read_text()
        assert DARK_THEME.node_fill in content
        assert DARK_THEME.background_color in content

    def test_render_to_png_with_theme(self):
        png = render_to_png(_SIMPLE_FLOWCHART, theme="dark")
        assert len(png) > 0
        # PNG magic bytes
        assert png[:4] == b"\x89PNG"


# ---------------------------------------------------------------------------
# 5. CLI --theme flag
# ---------------------------------------------------------------------------

class TestCLITheme:
    """Tests for the CLI --theme flag.

    Uses the merm.cli module directly (via _build_parser and main)
    to avoid needing a __main__.py or installed entry point.
    """

    def test_help_shows_theme(self):
        from merm.cli import _build_parser

        parser = _build_parser()
        # argparse prints help to stdout and raises SystemExit
        import io
        help_text = io.StringIO()
        parser.print_help(help_text)
        assert "--theme" in help_text.getvalue()

    def test_valid_theme_accepted(self, tmp_path: Path):
        from merm.cli import main

        input_file = tmp_path / "input.mmd"
        input_file.write_text(_SIMPLE_FLOWCHART)
        output_file = tmp_path / "out.svg"
        sys.argv = [
            "merm",
            "--theme", "dark",
            str(input_file),
            "-o", str(output_file),
        ]
        main()
        content = output_file.read_text()
        assert DARK_THEME.node_fill in content

    def test_invalid_theme_rejected(self):
        from merm.cli import _build_parser

        parser = _build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--theme", "invalid", "input.mmd"])
        assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# 6. Visual: PNG rendering of all themes
# ---------------------------------------------------------------------------

class TestVisualPNGAllThemes:
    def test_all_themes_produce_distinct_pngs(self):
        """Each theme should produce a non-empty PNG with distinct content."""
        pngs: dict[str, bytes] = {}
        for name in THEMES:
            png = render_to_png(_SIMPLE_FLOWCHART, theme=name)
            assert len(png) > 100, f"Theme {name!r} produced suspiciously small PNG"
            assert png[:4] == b"\x89PNG", f"Theme {name!r} did not produce valid PNG"
            pngs[name] = png

        # All PNGs should be different (different colors = different bytes)
        # At minimum, dark theme (with dark bg) should differ from default
        assert pngs["dark"] != pngs["default"], (
            "Dark and default themes produced identical PNGs"
        )
        assert pngs["forest"] != pngs["default"], (
            "Forest and default themes produced identical PNGs"
        )
