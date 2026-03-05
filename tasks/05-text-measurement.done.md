# 05 - Text Measurement Engine

## Goal
Measure the pixel dimensions of text labels for node sizing and layout. This is the critical challenge that normally requires a browser.

## Scope

This task implements the `pymermaid.measure` module with two modes:

1. **Heuristic mode** (zero dependencies) -- character-width estimation using calibrated ratios.
2. **Font-based mode** (optional, requires `fonttools`) -- accurate glyph-advance measurement from TTF/OTF files.

The module must expose a `TextMeasurer` class and a convenience function `measure_text()`. Both modes must handle multi-line text and basic markdown stripping.

## Dependencies

- Task 01 (project setup) -- `.done.md`
- Task 02 (comparison test infra) -- `.done.md`
- Task 03 (IR data model) -- `.done.md`
- Task 04 (flowchart parser) -- `.done.md`

## Tasks

### Heuristic Mode (zero dependencies)
- [ ] Implement character width estimation:
  - Default ratio: `char_width = font_size * 0.6` for normal-width chars
  - Narrow chars (i, l, t, f, j, 1, !, |, .): `font_size * 0.35`
  - Wide chars (m, w, M, W, @): `font_size * 0.75`
  - CJK chars (Unicode ranges U+4E00-U+9FFF, U+3400-U+4DBF, U+F900-U+FAFF): `font_size * 1.0`
- [ ] Implement `measure_text(text, font_size, font_family) -> (width, height)`
  - Width: sum of character widths for the widest line
  - Height: `font_size * 1.2 * num_lines`
- [ ] Handle multi-line text (split on `<br/>` and `\n`)
- [ ] Handle basic markdown stripping for measurement (bold `**` / `__` and italic `*` / `_` markers do not contribute width)

### Font-based Mode (optional, with fonttools)
- [ ] Load TTF/OTF font files using `fonttools`
- [ ] Extract glyph advance widths from `hmtx` table
- [ ] Build character width lookup table (cache per font)
- [ ] Compute text width by summing glyph advances, scaled to font size
- [ ] Cache font data to avoid repeated parsing
- [ ] Bundled default font metrics (extract width table from a standard sans-serif font and embed as Python dict) so font files are not required at runtime

### Configuration
- [ ] `TextMeasurer` class with configurable mode (heuristic vs font-based)
- [ ] Default font size: 14px (matches mermaid default)
- [ ] Default font family: "Open Sans" / sans-serif (matches mermaid default)
- [ ] Configurable padding for nodes (default: 8px horizontal, 4px vertical)

## Acceptance Criteria

- [ ] `from pymermaid.measure import TextMeasurer, measure_text` works
- [ ] `TextMeasurer` can be constructed with no arguments (defaults to heuristic mode, font_size=14, font_family="sans-serif")
- [ ] `TextMeasurer(mode="heuristic")` explicitly selects heuristic mode
- [ ] `measure_text("Hello", font_size=14)` returns a `(width, height)` tuple of floats
- [ ] Single-line width equals the sum of per-character widths (narrow/normal/wide categories applied correctly)
- [ ] Multi-line text split on `\n`: height equals `font_size * 1.2 * num_lines`, width equals the widest line
- [ ] Multi-line text split on `<br/>`: same behavior as `\n` splitting
- [ ] Markdown markers `**bold**` measured as width of `bold` only (markers stripped)
- [ ] Markdown markers `*italic*` measured as width of `italic` only (markers stripped)
- [ ] Nested markdown `***bold italic***` measured as width of `bold italic` only
- [ ] Underscore markdown `__bold__` and `_italic_` also stripped correctly
- [ ] CJK characters (e.g., U+4E2D) use `font_size * 1.0` width
- [ ] Narrow characters (`i`, `l`, `t`, `f`, `j`, `1`, `!`, `|`, `.`) use `font_size * 0.35` width
- [ ] Wide characters (`m`, `w`, `M`, `W`, `@`) use `font_size * 0.75` width
- [ ] Empty string returns `(0.0, font_size * 1.2)` -- one line of height, zero width
- [ ] `TextMeasurer` accepts `padding_h` and `padding_v` keyword arguments (defaults 8 and 4)
- [ ] A method `measure_node_text(text, font_size)` returns `(width + 2*padding_h, height + 2*padding_v)`
- [ ] When `fonttools` is installed, `TextMeasurer(mode="font")` does not raise
- [ ] When `fonttools` is not installed, `TextMeasurer(mode="font")` raises `ImportError` with a clear message
- [ ] `uv run pytest tests/test_measure.py` passes with all tests green
- [ ] No new required dependencies added to `pyproject.toml` (fonttools remains optional under `[project.optional-dependencies] fonts`)

## Test Scenarios

### Unit: TextMeasurer construction
- Default construction uses heuristic mode
- Explicit `mode="heuristic"` works
- Custom `font_size` and `font_family` are stored
- Custom `padding_h` and `padding_v` are stored and used

### Unit: Heuristic single-line measurement
- ASCII letters use default width ratio (font_size * 0.6)
- Narrow chars (`i`, `l`, `.`) use font_size * 0.35
- Wide chars (`m`, `W`, `@`) use font_size * 0.75
- Mixed string: verify total width equals sum of individual char widths
- Digits: `0`-`9` where `1` is narrow and others are default
- Space character uses default width

### Unit: Multi-line measurement
- `"line1\nline2"` -- height is `font_size * 1.2 * 2`, width is max of two line widths
- `"line1<br/>line2"` -- same behavior as `\n`
- `"line1<br/>line2\nline3"` -- three lines total (both delimiters recognized)
- Single line with no delimiters -- height is `font_size * 1.2 * 1`

### Unit: Markdown stripping
- `"**bold**"` measured same as `"bold"`
- `"*italic*"` measured same as `"italic"`
- `"***both***"` measured same as `"both"`
- `"__underscored__"` measured same as `"underscored"`
- `"_single_"` measured same as `"single"`
- Plain text with no markdown -- unchanged
- Mixed: `"hello **world**"` measured same as `"hello world"`

### Unit: CJK text measurement
- A single CJK character at font_size=14 has width 14.0
- A string of 3 CJK characters has width 42.0

### Unit: Edge cases
- Empty string returns `(0.0, font_size * 1.2)`
- Whitespace-only string measures the spaces
- Very long single line (1000 chars) returns correct sum
- Text with only markdown markers `"****"` returns zero width

### Unit: Node text measurement with padding
- `measure_node_text("Hi", 14)` returns `(width + 16, height + 8)` with default padding
- Custom padding values are applied correctly

### Unit: Convenience function
- `measure_text("Hello", font_size=14)` works without constructing TextMeasurer
- Returns same result as `TextMeasurer().measure("Hello")`

### Unit: Font-based mode (conditional)
- Skip if `fonttools` not installed
- If installed: `TextMeasurer(mode="font")` constructs successfully
- If not installed: `TextMeasurer(mode="font")` raises `ImportError`

### Performance
- Measure 1000 labels with heuristic mode in under 50ms (generous bound; spec says 10ms)

## Estimated Complexity
Medium - the heuristic mode is straightforward; font-based mode requires understanding TTF tables.
