"""Tests for emoji rendering support (task 31)."""

from __future__ import annotations

import pytest

from pymermaid.measure.text import (
    TextMeasurer,
    _char_width,
    _is_cjk,
    _is_emoji,
)
from pymermaid.theme import DEFAULT_THEME

# ---------------------------------------------------------------------------
# Unit: _is_emoji detection
# ---------------------------------------------------------------------------

class TestIsEmoji:
    """Verify _is_emoji correctly identifies emoji codepoints."""

    @pytest.mark.parametrize(
        "ch",
        [
            "\U0001F680",  # rocket
            "\u2705",      # white check mark
            "\U0001F525",  # fire
            "\U0001F600",  # grinning face
            "\U0001F4A9",  # pile of poo (Misc Symbols and Pictographs)
            "\u2764",      # heavy black heart (Dingbats area)
            "\u2702",      # scissors (Dingbats)
            "\u2600",      # sun (Misc Symbols)
            "\u26A0",      # warning sign (Misc Symbols)
            "\u2139",      # information source
        ],
    )
    def test_emoji_detected(self, ch: str) -> None:
        assert _is_emoji(ch) is True

    @pytest.mark.parametrize(
        "ch",
        [
            "A",
            "z",
            "0",
            "!",
            " ",
            "@",
        ],
    )
    def test_ascii_not_emoji(self, ch: str) -> None:
        assert _is_emoji(ch) is False

    def test_cjk_not_emoji(self) -> None:
        """CJK characters are handled by _is_cjk, not _is_emoji."""
        assert _is_emoji("\u4e00") is False
        assert _is_cjk("\u4e00") is True

    def test_dingbats_detected(self) -> None:
        # U+2702 SCISSORS is in the Dingbats range
        assert _is_emoji("\u2702") is True

    def test_misc_symbols_detected(self) -> None:
        # U+2614 UMBRELLA WITH RAIN DROPS
        assert _is_emoji("\u2614") is True


# ---------------------------------------------------------------------------
# Unit: _char_width for emoji and zero-width characters
# ---------------------------------------------------------------------------

class TestCharWidthEmoji:
    """Verify _char_width handles emoji and zero-width chars correctly."""

    def test_emoji_full_width(self) -> None:
        assert _char_width("\U0001F680", 16.0) == 16.0

    def test_emoji_scales_with_font_size(self) -> None:
        assert _char_width("\U0001F680", 24.0) == 24.0

    def test_zero_width_joiner(self) -> None:
        assert _char_width("\u200D", 16.0) == 0.0

    def test_variation_selector_fe0f(self) -> None:
        assert _char_width("\uFE0F", 16.0) == 0.0

    def test_variation_selector_fe0e(self) -> None:
        assert _char_width("\uFE0E", 16.0) == 0.0

    def test_regular_ascii_unchanged(self) -> None:
        # Regular char: 0.6 * font_size
        assert _char_width("A", 16.0) == pytest.approx(9.6)

    def test_cjk_unchanged(self) -> None:
        assert _char_width("\u4e00", 16.0) == 16.0

    def test_narrow_unchanged(self) -> None:
        assert _char_width("i", 16.0) == pytest.approx(5.6)


# ---------------------------------------------------------------------------
# Unit: TextMeasurer with emoji
# ---------------------------------------------------------------------------

class TestTextMeasurerEmoji:
    """Verify TextMeasurer.measure accounts for emoji width."""

    def test_emoji_wider_than_regular_char(self) -> None:
        m = TextMeasurer()
        w_emoji, _ = m.measure("Hello \U0001F680")
        w_plain, _ = m.measure("Hello X")
        assert w_emoji > w_plain

    def test_multiple_emoji_wider(self) -> None:
        m = TextMeasurer()
        w_one, _ = m.measure("\U0001F680")
        w_two, _ = m.measure("\U0001F680\U0001F525")
        assert w_two > w_one

    def test_multiline_with_emoji(self) -> None:
        m = TextMeasurer()
        w, h = m.measure("Deploy \U0001F680<br/>Done")
        # Should have 2 lines
        assert h == pytest.approx(16.0 * 1.4 * 2)
        # Width should be at least the emoji line
        w_line, _ = m.measure("Deploy \U0001F680")
        assert w >= w_line


# ---------------------------------------------------------------------------
# Integration: Theme font-family includes emoji fonts
# ---------------------------------------------------------------------------

class TestThemeEmojiFonts:
    """Verify the default theme includes emoji font families."""

    def test_apple_color_emoji_in_font_family(self) -> None:
        assert "Apple Color Emoji" in DEFAULT_THEME.font_family

    def test_segoe_ui_emoji_in_font_family(self) -> None:
        assert "Segoe UI Emoji" in DEFAULT_THEME.font_family

    def test_noto_color_emoji_in_font_family(self) -> None:
        assert "Noto Color Emoji" in DEFAULT_THEME.font_family

    def test_original_fonts_preserved(self) -> None:
        """Emoji fonts are appended, not replacing the original stack."""
        assert "trebuchet ms" in DEFAULT_THEME.font_family
        assert "verdana" in DEFAULT_THEME.font_family


# ---------------------------------------------------------------------------
# Integration: SVG rendering with emoji
# ---------------------------------------------------------------------------

class TestSvgEmojiRendering:
    """Verify SVG output includes emoji fonts and preserves emoji chars."""

    def test_svg_contains_emoji_font_in_css(self) -> None:
        from pymermaid import render_diagram

        svg = render_diagram('graph TD\n    A["Deploy"] --> B["Done"]')
        assert "Apple Color Emoji" in svg
        assert "Segoe UI Emoji" in svg

    def test_svg_preserves_emoji_in_text(self) -> None:
        from pymermaid import render_diagram

        svg = render_diagram(
            'graph TD\n    A["Deploy \U0001F680"]'
            ' --> B["Done \u2705"]'
        )
        assert "\U0001F680" in svg
        assert "\u2705" in svg

    def test_emoji_node_wider_than_plain(self) -> None:
        """Node with emoji should be wider than same text without emoji."""
        import re

        from pymermaid import render_diagram

        svg_emoji = render_diagram('graph TD\n    A["Deploy \U0001F680"]')
        svg_plain = render_diagram('graph TD\n    A["Deploy X"]')

        # Extract the width of node A's rect from both SVGs
        def _extract_node_width(svg: str) -> float:
            # Find the rect inside the node group
            match = re.search(
                r'data-node-id="A".*?<rect[^>]*width="([^"]+)"',
                svg,
                re.DOTALL,
            )
            assert match is not None, "Could not find node rect in SVG"
            return float(match.group(1))

        w_emoji = _extract_node_width(svg_emoji)
        w_plain = _extract_node_width(svg_plain)
        assert w_emoji > w_plain
