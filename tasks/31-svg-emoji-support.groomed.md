# Task 31: SVG Emoji and Icon Rendering Improvements

**Priority: Low**

## Problem Analysis

### Emoji rendering is broken

When a node label contains emoji characters (e.g. `A["Deploy 🚀"]`), the SVG `<text>` element renders them as placeholder squares on most systems. This happens because:

1. The theme's `font_family` is `"trebuchet ms", verdana, arial, sans-serif` -- none of these fonts contain emoji glyphs.
2. SVG renderers (browsers, rsvg, cairosvg) need an explicit emoji font in the font-family stack to resolve emoji codepoints.
3. The text measurement engine (`_char_width` in `src/pymermaid/measure/text.py`) treats emoji as regular characters at `0.6 * font_size`, which underestimates their width since emoji are typically full-width (1.0 * font_size).

### FA icons work but could be more robust

Font Awesome icons (`fa:fa-tree`) already work via `src/pymermaid/icons.py` -- the `_render_text_with_icons` function in `src/pymermaid/render/svg.py` replaces `fa:fa-*` tokens with inline SVG `<path>` elements. This is solid. No changes needed here for this task.

## Scope

This task focuses exclusively on making **emoji characters** render correctly in SVG output. FA icon support is already implemented (task 20) and working.

### In scope

- Add emoji-capable fonts to the font-family CSS fallback chain
- Fix text measurement for emoji characters (width estimation)
- Detect emoji characters in labels for measurement purposes

### Out of scope

- Embedding SVG emoji paths (Twemoji etc.) -- over-engineered for this use case
- `:shortcode:` syntax parsing -- different feature, not needed for standard emoji rendering
- Changes to FA icon rendering (already works)

## Implementation Plan

### 1. Add emoji font-family fallback

In `src/pymermaid/render/svg.py`, the `_render_text` function and the CSS in `_build_style_css` use the theme's `font_family`. When rendering text that contains emoji, append emoji-capable fonts to the font-family stack.

Specifically, when building the CSS `<style>` block, add emoji fonts to all text selectors:

```
"Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", "Twemoji Mozilla"
```

These should be appended after the existing font-family, not replace it. This can be done in `_build_style_css` or by modifying the theme's default `font_family`.

The simplest approach: update the `DEFAULT_THEME.font_family` in `src/pymermaid/theme.py` to include emoji fonts at the end. This way all text rendering automatically picks them up.

### 2. Fix emoji width estimation in text measurement

In `src/pymermaid/measure/text.py`, add an `_is_emoji` helper function that detects common emoji Unicode ranges. Emoji characters should be measured at `1.0 * font_size` width (they are square glyphs), similar to how CJK characters are already handled.

Key emoji Unicode ranges to detect:
- Emoticons: U+1F600-U+1F64F
- Misc Symbols and Pictographs: U+1F300-U+1F5FF
- Transport/Map: U+1F680-U+1F6FF
- Supplemental Symbols: U+1F900-U+1F9FF
- Symbols and Pictographs Extended-A: U+1FA00-U+1FA6F, U+1FA70-U+1FAFF
- Dingbats: U+2700-U+27BF
- Misc Symbols: U+2600-U+26FF
- Common single-codepoint emoji: U+2139, U+2190-U+21FF, U+23E9-U+23F3, U+25AA-U+25FE, etc.

Note: Some emoji are multi-codepoint sequences (e.g. flag emoji, skin tone variants with ZWJ). For width estimation, treating each codepoint individually and filtering zero-width joiners (U+200D) and variation selectors (U+FE0E, U+FE0F) is sufficient -- they contribute zero additional width.

### 3. Update `_char_width` to handle emoji

Modify the `_char_width` function in `src/pymermaid/measure/text.py` to check `_is_emoji(ch)` and return `font_size * 1.0` for emoji characters, before the default `0.6` fallback. Also return `0.0` for zero-width joiners and variation selectors.

## Dependencies

- No other tasks need to be `.done.md` first. The text measurement and SVG rendering modules are already stable.
- Task 20 (FA icons) is already complete and this task does not modify that code.

## Acceptance Criteria

- [ ] `from pymermaid.measure.text import _is_emoji` works and correctly identifies common emoji characters
- [ ] `_is_emoji("\U0001F680")` returns `True` (rocket emoji)
- [ ] `_is_emoji("A")` returns `False`
- [ ] `_char_width("\U0001F680", 16.0)` returns `16.0` (full font_size width)
- [ ] `_char_width("\u200D", 16.0)` returns `0.0` (zero-width joiner)
- [ ] `_char_width("\uFE0F", 16.0)` returns `0.0` (variation selector)
- [ ] The default theme's `font_family` includes at least one of: `Apple Color Emoji`, `Segoe UI Emoji`, `Noto Color Emoji`
- [ ] SVG output for a label containing emoji includes emoji font names in the CSS font-family declaration
- [ ] `TextMeasurer().measure("Hello \U0001F680")` returns a width greater than `TextMeasurer().measure("Hello X")` (emoji is wider than a regular char)
- [ ] `uv run pytest tests/test_emoji.py` passes with all tests green
- [ ] Existing tests (`uv run pytest tests/test_icons.py tests/test_text_measurement.py tests/test_rendering.py`) still pass (no regressions)

## Test Scenarios

### Unit: Emoji detection (`_is_emoji`)
- Common emoji (rocket, check mark, fire, face) return True
- ASCII letters, digits, punctuation return False
- CJK characters return False (handled separately by `_is_cjk`)
- Dingbats (U+2700 range) return True
- Misc symbols (U+2600 range) return True

### Unit: Emoji width measurement (`_char_width`)
- Emoji character returns `font_size * 1.0`
- Zero-width joiner (U+200D) returns `0.0`
- Variation selector U+FE0F returns `0.0`
- Variation selector U+FE0E returns `0.0`
- Regular ASCII character still returns expected width (no regression)
- CJK character still returns `font_size * 1.0` (no regression)

### Unit: Text measurement with emoji (`TextMeasurer.measure`)
- Label `"Deploy \U0001F680"` measured width includes full-width emoji contribution
- Label with multiple emoji measures wider than same label without emoji
- Multi-line label with emoji on one line measures correctly

### Integration: SVG rendering with emoji
- Render a flowchart with `A["Deploy \U0001F680"] --> B["Done \u2705"]`
- Verify SVG output contains emoji font in CSS font-family
- Verify the `<text>` element contains the emoji characters (not stripped)
- Verify node width accommodates the emoji (wider than same text without emoji)

### Regression: Existing functionality preserved
- FA icon labels still render with inline SVG paths (not broken by emoji changes)
- CJK text measurement unchanged
- Plain ASCII labels unchanged
