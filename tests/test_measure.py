"""Tests for the text measurement engine."""

from __future__ import annotations

import time

import pytest

from pymermaid.measure import TextMeasurer, measure_text

# ---------- Heuristic single-line measurement ----------


class TestHeuristicSingleLine:
    def test_normal_ascii_letters(self):
        """ASCII letters (not narrow/wide) use font_size * 0.6."""
        m = TextMeasurer(font_size=10)
        w, h = m.measure("abc")
        assert w == pytest.approx(10 * 0.6 * 3)
        assert h == pytest.approx(10 * 1.4)

    def test_narrow_chars(self):
        """Narrow chars (i, l, .) use font_size * 0.35."""
        m = TextMeasurer(font_size=10)
        for ch in "iltfj1!|.":
            w, _ = m.measure(ch)
            assert w == pytest.approx(10 * 0.35), f"char {ch!r}"

    def test_wide_chars(self):
        """Wide chars (m, W, @) use font_size * 0.75."""
        m = TextMeasurer(font_size=10)
        for ch in "mwMW@":
            w, _ = m.measure(ch)
            assert w == pytest.approx(10 * 0.75), f"char {ch!r}"

    def test_mixed_string(self):
        """Total width is sum of individual char widths."""
        m = TextMeasurer(font_size=10)
        # "imW" => narrow(i) + normal(doesn't exist: 'm' is wide!) + wide(W)
        # Actually: i=narrow, m=wide, W=wide
        w, _ = m.measure("imW")
        expected = 10 * 0.35 + 10 * 0.75 + 10 * 0.75
        assert w == pytest.approx(expected)

    def test_digits(self):
        """Digit 1 is narrow, others are normal width."""
        m = TextMeasurer(font_size=10)
        w1, _ = m.measure("1")
        assert w1 == pytest.approx(10 * 0.35)
        w0, _ = m.measure("0")
        assert w0 == pytest.approx(10 * 0.6)
        w9, _ = m.measure("9")
        assert w9 == pytest.approx(10 * 0.6)

    def test_space_uses_default_width(self):
        m = TextMeasurer(font_size=10)
        w, _ = m.measure(" ")
        assert w == pytest.approx(10 * 0.6)


# ---------- Multi-line measurement ----------


class TestMultiLine:
    def test_newline_split(self):
        m = TextMeasurer(font_size=10)
        w, h = m.measure("ab\ncd")
        # Both lines have same width (2 normal chars)
        assert w == pytest.approx(10 * 0.6 * 2)
        assert h == pytest.approx(10 * 1.4 * 2)

    def test_br_split(self):
        m = TextMeasurer(font_size=10)
        w, h = m.measure("ab<br/>cd")
        assert w == pytest.approx(10 * 0.6 * 2)
        assert h == pytest.approx(10 * 1.4 * 2)

    def test_mixed_delimiters(self):
        m = TextMeasurer(font_size=10)
        w, h = m.measure("ab<br/>cd\nef")
        assert h == pytest.approx(10 * 1.4 * 3)

    def test_single_line_height(self):
        m = TextMeasurer(font_size=14)
        _, h = m.measure("hello")
        assert h == pytest.approx(14 * 1.4)

    def test_width_is_widest_line(self):
        m = TextMeasurer(font_size=10)
        # "abcd" (4 normal) vs "ab" (2 normal)
        w, _ = m.measure("abcd\nab")
        assert w == pytest.approx(10 * 0.6 * 4)


# ---------- Markdown stripping ----------


class TestMarkdownStripping:
    def test_bold_double_star(self):
        m = TextMeasurer(font_size=10)
        w_plain, _ = m.measure("bold")
        w_md, _ = m.measure("**bold**")
        assert w_md == pytest.approx(w_plain)

    def test_italic_single_star(self):
        m = TextMeasurer(font_size=10)
        w_plain, _ = m.measure("italic")
        w_md, _ = m.measure("*italic*")
        assert w_md == pytest.approx(w_plain)

    def test_bold_italic_triple_star(self):
        m = TextMeasurer(font_size=10)
        w_plain, _ = m.measure("both")
        w_md, _ = m.measure("***both***")
        assert w_md == pytest.approx(w_plain)

    def test_bold_underscore(self):
        m = TextMeasurer(font_size=10)
        w_plain, _ = m.measure("underscored")
        w_md, _ = m.measure("__underscored__")
        assert w_md == pytest.approx(w_plain)

    def test_italic_underscore(self):
        m = TextMeasurer(font_size=10)
        w_plain, _ = m.measure("single")
        w_md, _ = m.measure("_single_")
        assert w_md == pytest.approx(w_plain)

    def test_plain_text_unchanged(self):
        m = TextMeasurer(font_size=10)
        w1, _ = m.measure("hello world")
        w2, _ = m.measure("hello world")
        assert w1 == pytest.approx(w2)

    def test_mixed_markdown(self):
        m = TextMeasurer(font_size=10)
        w_plain, _ = m.measure("hello world")
        w_md, _ = m.measure("hello **world**")
        assert w_md == pytest.approx(w_plain)


# ---------- CJK text ----------


class TestCJK:
    def test_single_cjk_char(self):
        m = TextMeasurer(font_size=14)
        w, _ = m.measure("\u4e2d")  # U+4E2D (CJK char)
        assert w == pytest.approx(14.0)

    def test_three_cjk_chars(self):
        m = TextMeasurer(font_size=14)
        w, _ = m.measure("\u4e2d\u6587\u5b57")
        assert w == pytest.approx(42.0)


# ---------- Edge cases ----------


class TestEdgeCases:
    def test_empty_string(self):
        m = TextMeasurer(font_size=14)
        w, h = m.measure("")
        assert w == pytest.approx(0.0)
        assert h == pytest.approx(14 * 1.4)

    def test_whitespace_only(self):
        m = TextMeasurer(font_size=10)
        w, _ = m.measure("   ")
        assert w == pytest.approx(10 * 0.6 * 3)

    def test_very_long_line(self):
        m = TextMeasurer(font_size=10)
        text = "a" * 1000
        w, h = m.measure(text)
        assert w == pytest.approx(10 * 0.6 * 1000)
        assert h == pytest.approx(10 * 1.4)

    def test_only_markdown_markers(self):
        """Text with only markdown markers '****' returns zero width."""
        m = TextMeasurer(font_size=10)
        w, _ = m.measure("****")
        assert w == pytest.approx(0.0)


# ---------- Node text measurement with padding ----------


class TestNodeTextMeasurement:
    def test_default_padding(self):
        m = TextMeasurer(font_size=14)
        w_text, h_text = m.measure("Hi")
        w_node, h_node = m.measure_node_text("Hi")
        assert w_node == pytest.approx(w_text + 30)
        assert h_node == pytest.approx(h_text + 20)

    def test_custom_padding(self):
        m = TextMeasurer(font_size=14, padding_h=20, padding_v=10)
        w_text, h_text = m.measure("Hi")
        w_node, h_node = m.measure_node_text("Hi")
        assert w_node == pytest.approx(w_text + 40)
        assert h_node == pytest.approx(h_text + 20)


# ---------- Convenience function ----------


class TestConvenienceFunction:
    def test_same_as_measurer(self):
        result_fn = measure_text("Hello", font_size=14)
        result_cls = TextMeasurer(font_size=14).measure("Hello")
        assert result_fn[0] == pytest.approx(result_cls[0])
        assert result_fn[1] == pytest.approx(result_cls[1])


# ---------- Font-based mode (conditional) ----------


class TestFontMode:
    def test_font_mode_import(self):
        """Font mode raises ImportError if fonttools is not installed."""
        try:
            import fontTools  # noqa: F401

            # fonttools is available -- should construct fine
            m = TextMeasurer(mode="font")
            assert m.mode == "font"
        except ImportError:
            # fonttools not installed -- should raise ImportError
            with pytest.raises(ImportError, match="fonttools"):
                TextMeasurer(mode="font")


# ---------- Performance ----------


class TestPerformance:
    def test_heuristic_performance(self):
        """Measure 1000 labels in under 50ms."""
        m = TextMeasurer()
        labels = [f"Node label {i}" for i in range(1000)]
        start = time.perf_counter()
        for label in labels:
            m.measure(label)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.050, f"Took {elapsed:.3f}s, expected < 0.050s"
