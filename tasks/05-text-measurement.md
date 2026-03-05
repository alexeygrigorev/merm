# 05 - Text Measurement Engine

## Goal
Measure the pixel dimensions of text labels for node sizing and layout. This is the critical challenge that normally requires a browser.

## Tasks

### Heuristic Mode (zero dependencies)
- [ ] Implement character width estimation:
  - Default ratio: `char_width = font_size * 0.6` for normal-width chars
  - Narrow chars (i, l, t, f, j, 1, !, |, .): `font_size * 0.35`
  - Wide chars (m, w, M, W, @): `font_size * 0.75`
  - CJK chars: `font_size * 1.0`
- [ ] Implement `measure_text(text, font_size, font_family) -> (width, height)`
  - Width: sum of character widths
  - Height: `font_size * 1.2 * num_lines`
- [ ] Handle multi-line text (split on `<br/>` and `\n`)
- [ ] Handle basic markdown stripping for measurement (bold/italic markers don't contribute width)

### Font-based Mode (optional, with fonttools)
- [ ] Load TTF/OTF font files using `fonttools`
- [ ] Extract glyph advance widths from `hmtx` table
- [ ] Build character width lookup table (cache per font)
- [ ] Compute text width by summing glyph advances, scaled to font size
- [ ] Cache font data to avoid repeated parsing
- [ ] Bundled default font metrics (extract width table from a standard sans-serif font and embed as Python dict) so font files aren't required at runtime

### Configuration
- [ ] `TextMeasurer` class with configurable mode (heuristic vs font-based)
- [ ] Default font size: 14px (matches mermaid default)
- [ ] Default font family: "Open Sans" / sans-serif (matches mermaid default)
- [ ] Configurable padding for nodes (default: 8px horizontal, 4px vertical)

## Acceptance Criteria
- Heuristic mode: text widths within 20% of browser-rendered widths for ASCII text
- Font-based mode: text widths within 5% of browser-rendered widths
- No required external dependencies (fonttools is optional)
- Benchmark: measure 1000 labels in < 10ms

## Dependencies
None - standalone module.

## Estimated Complexity
Medium - the heuristic mode is straightforward; font-based mode requires understanding TTF tables.
