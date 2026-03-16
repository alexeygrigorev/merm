"""Text measurement engine for node sizing and layout.

Provides the TextMeasurer class and a convenience measure_text function
for estimating text dimensions using either heuristic character-width
ratios or font-based glyph metrics.
"""

import re
from dataclasses import dataclass

# Narrow characters: less visual width
_NARROW_CHARS = frozenset("iltfj1!|.")

# Wide characters: more visual width
_WIDE_CHARS = frozenset("mwMW@")

# Markdown marker patterns to strip for measurement.
# Order matters: longest markers first (*** before ** before *).
_MARKDOWN_RE = re.compile(
    r"\*\*\*(.*?)\*\*\*"  # ***bold italic***
    r"|__(.+?)__"  # __bold__
    r"|\*\*(.*?)\*\*"  # **bold**
    r"|_(.+?)_"  # _italic_
    r"|\*(.*?)\*"  # *italic*
)

# Multi-line delimiters
_LINE_SPLIT_RE = re.compile(r"<br/>|\n")

def _is_cjk(ch: str) -> bool:
    """Return True if the character is in a CJK Unicode range."""
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0xF900 <= cp <= 0xFAFF
    )

# Zero-width joiners and variation selectors contribute no width.
_ZERO_WIDTH = frozenset({0x200D, 0xFE0E, 0xFE0F})

def _is_emoji(ch: str) -> bool:
    """Return True if the character is an emoji codepoint.

    Covers the most common emoji Unicode ranges.  Does not handle
    multi-codepoint sequences (ZWJ, skin-tone modifiers) -- those are
    handled by giving zero width to ZWJ and variation selectors.
    """
    cp = ord(ch)
    return (
        0x1F600 <= cp <= 0x1F64F  # Emoticons
        or 0x1F300 <= cp <= 0x1F5FF  # Misc Symbols and Pictographs
        or 0x1F680 <= cp <= 0x1F6FF  # Transport and Map
        or 0x1F900 <= cp <= 0x1F9FF  # Supplemental Symbols
        or 0x1FA00 <= cp <= 0x1FA6F  # Symbols Extended-A
        or 0x1FA70 <= cp <= 0x1FAFF  # Symbols Extended-A (cont.)
        or 0x2600 <= cp <= 0x26FF  # Misc Symbols
        or 0x2700 <= cp <= 0x27BF  # Dingbats
        or 0x2300 <= cp <= 0x23FF  # Misc Technical (includes ⏩ etc.)
        or 0x25A0 <= cp <= 0x25FF  # Geometric Shapes
        or 0x2139 == cp  # Information source ℹ
        or 0x2190 <= cp <= 0x21FF  # Arrows
    )

def _strip_markdown(text: str) -> str:
    """Remove markdown bold/italic markers, keeping the inner text."""

    def _replace(m: re.Match[str]) -> str:
        # Return whichever group matched (they are mutually exclusive)
        for g in m.groups():
            if g is not None:
                return g
        return ""

    return _MARKDOWN_RE.sub(_replace, text)

def _char_width(ch: str, font_size: float) -> float:
    """Return the estimated width of a single character."""
    cp = ord(ch)
    if cp in _ZERO_WIDTH:
        return 0.0
    if _is_cjk(ch):
        return font_size * 1.0
    if _is_emoji(ch):
        return font_size * 1.0
    if ch in _NARROW_CHARS:
        return font_size * 0.35
    if ch in _WIDE_CHARS:
        return font_size * 0.75
    return font_size * 0.6

def _line_width(text: str, font_size: float) -> float:
    """Return the estimated pixel width of a single line of text.

    Handles ``fa:fa-<name>`` icon tokens by treating each as a square
    character whose width equals *font_size*, plus a small gap.
    """
    from merm.icons import _FA_TOKEN_RE

    # Replace icon tokens with a placeholder character, accumulating icon widths
    icon_width = 0.0
    clean = text
    for m in _FA_TOKEN_RE.finditer(text):
        # Each icon occupies 1.5x font_size width + a 5px gap
        icon_width += font_size * 1.5 + 5.0
    # Remove icon tokens from text for character-width measurement
    clean = _FA_TOKEN_RE.sub("", text)
    char_w = sum(_char_width(ch, font_size) for ch in clean)
    return char_w + icon_width

def _wrap_line(text: str, font_size: float, max_width: float) -> list[str]:
    """Wrap a single line of text into multiple lines to fit within *max_width*.

    Splits on word boundaries. Returns a list of lines.
    """
    if _line_width(text, font_size) <= max_width:
        return [text]

    words = text.split()
    if not words:
        return [text]

    lines: list[str] = []
    current_line = words[0]

    for word in words[1:]:
        test_line = current_line + " " + word
        if _line_width(test_line, font_size) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)
    return lines

@dataclass
class TextMeasurer:
    """Measures text dimensions for layout purposes.

    Supports two modes:
    - ``"heuristic"`` (default): character-width estimation using calibrated ratios.
      Zero external dependencies.
    - ``"font"``: accurate glyph-advance measurement using ``fonttools``.
      Requires the ``fonts`` optional dependency group.

    Args:
        mode: Measurement mode (``"heuristic"`` or ``"font"``).
        font_size: Default font size in pixels.
        font_family: Default font family name.
        padding_h: Horizontal padding (each side) for node text measurement.
        padding_v: Vertical padding (each side) for node text measurement.
    """

    mode: str = "heuristic"
    font_size: float = 16.0
    font_family: str = '"trebuchet ms", verdana, arial, sans-serif'
    padding_h: float = 15.0
    padding_v: float = 10.0

    def __post_init__(self) -> None:
        if self.mode == "font":
            try:
                import fontTools  # noqa: F401
            except ImportError:
                raise ImportError(
                    "Font-based text measurement requires the 'fonttools' package. "
                    "Install it with: uv add merm[fonts]"
                ) from None
        elif self.mode != "heuristic":
            raise ValueError(
                f"Unknown measurement mode {self.mode!r}; "
                "expected 'heuristic' or 'font'"
            )

    def measure(
        self,
        text: str,
        font_size: float | None = None,
        font_family: str | None = None,
        max_width: float = 0.0,
    ) -> tuple[float, float]:
        """Measure the pixel dimensions of *text*.

        Args:
            text: The text to measure.  May contain ``\\n`` and ``<br/>``
                line breaks, and markdown bold/italic markers.
            font_size: Override the default font size.
            font_family: Override the default font family (currently unused
                in heuristic mode but stored for future font-based mode).
            max_width: If > 0, wrap text to fit within this width.

        Returns:
            A ``(width, height)`` tuple of floats.
        """
        fs = font_size if font_size is not None else self.font_size

        # Strip markdown markers before measuring
        stripped = _strip_markdown(text)

        # Split on multi-line delimiters
        lines = _LINE_SPLIT_RE.split(stripped)

        if not lines:
            lines = [""]

        # Wrap long lines if max_width is set
        if max_width > 0:
            wrapped: list[str] = []
            for line in lines:
                wrapped.extend(_wrap_line(line, fs, max_width))
            lines = wrapped

        width = max(_line_width(line, fs) for line in lines)
        height = fs * 1.4 * len(lines)
        return (width, height)

    def measure_node_text(
        self,
        text: str,
        font_size: float | None = None,
        font_family: str | None = None,
    ) -> tuple[float, float]:
        """Measure text dimensions with node padding applied.

        Returns ``(width + 2*padding_h, height + 2*padding_v)``.
        """
        w, h = self.measure(text, font_size=font_size, font_family=font_family)
        return (w + 2 * self.padding_h, h + 2 * self.padding_v)

def measure_text(
    text: str,
    font_size: float = 16.0,
    font_family: str = '"trebuchet ms", verdana, arial, sans-serif',
) -> tuple[float, float]:
    """Convenience function: measure *text* using the heuristic measurer.

    Args:
        text: Text to measure.
        font_size: Font size in pixels.
        font_family: Font family name (reserved for future use).

    Returns:
        A ``(width, height)`` tuple of floats.
    """
    measurer = TextMeasurer(
        mode="heuristic", font_size=font_size, font_family=font_family
    )
    return measurer.measure(text)
