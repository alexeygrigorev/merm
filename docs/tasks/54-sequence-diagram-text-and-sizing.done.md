# Task 54: Sequence Diagram Text Rendering and Box Sizing

## Problem

Sequence diagrams with long text and `<br/>` tags render incorrectly. Observed in `flink_late_event.mmd` and `flink_late_upsert.mmd`.

### Issues

1. **`<br/>` rendered as literal text** -- Note boxes display raw `<br/>` as visible characters instead of creating line breaks. E.g. "watermark = 00:02<br/>window [00:00, 00:10) not published yet<br/>A added to window" shows the `<br/>` tags as plain text.

2. **Text overflows right edge of diagram** -- Long note text runs past the right side of the SVG viewport and gets clipped. "A added to w..." is cut off, "upsert via PRIMARY KEY<br/>corrected f..." is cut off.

3. **Note boxes don't resize to fit content** -- Yellow note boxes are too narrow for their text. Text overflows past the box boundary.

4. **Message labels overflow left edge** -- Long message labels like "seconds pass, phone reconnects" and "Event A (ts=14:00:07, on time)" extend past the left edge of the SVG viewport.

5. **Labels overlap lifelines** -- Message labels and annotations like "(late)" and "PU=79, trips=2)" overlap with dashed participant lifelines, making them hard to read.

6. **SVG viewBox doesn't encompass all content** -- The viewport is too small for the actual rendered content, causing clipping on both sides.

## Scope

This task fixes text handling and sizing in the sequence diagram pipeline. It does NOT add new diagram features or change parsing of non-text elements.

## Key Files

### Source files to modify

- `/home/alexey/git/pymermaid/src/pymermaid/render/sequence.py` -- SVG renderer. The `_render_note()` function (line ~305) sets `text.text = nl.text` as a single text element. This must be changed to split on `<br/>` and emit multiple `<tspan>` elements with appropriate `dy` offsets. Same pattern applies to `_render_message()` (line ~280) for message label text.
- `/home/alexey/git/pymermaid/src/pymermaid/layout/sequence.py` -- Layout engine. The `_process_note()` function (line ~248) uses `measure_fn(note.text, _FONT_SIZE)` which measures the full text including literal `<br/>` characters as width. Must split on `<br/>` first, measure each line independently, use the widest line for width, and sum heights for total height. The `_NOTE_WIDTH = 120.0` constant may also be too small. The viewBox calculation at the bottom (line ~328) only considers participant positions, not note or message positions.
- `/home/alexey/git/pymermaid/src/pymermaid/parser/sequence.py` -- Parser. The parser correctly preserves `<br/>` in note text (it stores the raw string). No changes expected here unless you discover a parsing bug.

### Test fixtures

- `/home/alexey/git/pymermaid/tests/fixtures/corpus/sequence/flink_late_event.mmd` -- Contains notes with `<br/>` and long text like "watermark = 00:02<br/>window [00:00, 00:10) not published yet<br/>A added to window"
- `/home/alexey/git/pymermaid/tests/fixtures/corpus/sequence/flink_late_upsert.mmd` -- Contains "upsert via PRIMARY KEY<br/>corrected from 1 to 2"
- `/home/alexey/git/pymermaid/tests/fixtures/corpus/sequence/notes.mmd` -- Simple notes without `<br/>`

### Existing tests

- `/home/alexey/git/pymermaid/tests/test_sequence.py` -- Existing sequence diagram tests (parser, layout, renderer). Your new tests go in a NEW file (see below).

### Entry point for rendering

```python
from pymermaid import render_diagram

svg_str = render_diagram(open("fixture.mmd").read())
```

## Acceptance Criteria

Each criterion below is a concrete assertion that a test can verify.

- [ ] `<br/>` in note text is rendered as multi-line text using `<tspan>` elements with `dy` attributes, NOT as literal `<br/>` strings in the SVG output
- [ ] `<br/>` in message labels is rendered as multi-line text using `<tspan>` elements, NOT as literal strings
- [ ] When rendering `flink_late_event.mmd`, no `<text>` element in the SVG contains the literal substring `<br/>`
- [ ] When rendering `flink_late_upsert.mmd`, no `<text>` element in the SVG contains the literal substring `<br/>`
- [ ] Note `<rect>` elements are at least as wide as their contained text (for each note group, `rect.width >= max line text width`)
- [ ] Note `<rect>` elements are tall enough for all lines (height accommodates N lines with line spacing)
- [ ] The SVG `viewBox` encompasses all `<rect>` and `<text>` elements: no element's bounding box extends past the viewBox boundary (with the existing 20px padding)
- [ ] When rendering `notes.mmd`, notes without `<br/>` still render correctly as single-line text
- [ ] When rendering `flink_late_event.mmd`, all message label text is within the SVG viewBox (no negative-x clipping)
- [ ] `uv run pytest tests/test_sequence_text_sizing.py` passes with all tests green

## Test Scenarios

All tests go in `/home/alexey/git/pymermaid/tests/test_sequence_text_sizing.py`.

Use `xml.etree.ElementTree` to parse the SVG output. Use `from pymermaid import render_diagram` to render fixtures.

### Helper: parse SVG and extract elements

Write a helper that takes a `.mmd` fixture path, renders it, and returns the parsed `ET.Element` root. All tests below use this helper.

### Unit: br tag conversion in notes

- Render `flink_late_event.mmd`. Find all `<text>` elements inside `.seq-note` groups. Assert none of them contain the literal string `<br/>` in their `.text` or any child's `.text`/`.tail`.
- Render `flink_late_event.mmd`. Find note text elements. For a note with `<br/>`, assert it contains multiple `<tspan>` children (one per line).
- Render `flink_late_upsert.mmd`. Assert the note "upsert via PRIMARY KEY<br/>corrected from 1 to 2" renders as two `<tspan>` lines.

### Unit: br tag conversion in message labels

- Render a sequence diagram with a message label containing `<br/>`. Assert the label `<text>` element contains `<tspan>` children, not a literal `<br/>` string.

### Unit: note box sizing

- Render `flink_late_event.mmd`. For every `.seq-note` group, extract the `<rect>` width and the text content width (approximate: longest line character count * font_size * 0.6). Assert `rect width >= text_content_width`.
- Render `flink_late_upsert.mmd`. Same assertion.

### Unit: note box height for multi-line notes

- Render `flink_late_event.mmd`. For notes that contain `<br/>`, count the number of lines (split on `<br/>`). Assert the `<rect>` height is at least `num_lines * line_height + padding`.

### Unit: viewBox encompasses all elements

- Render `flink_late_event.mmd`. Parse the `viewBox` attribute into (vb_x, vb_y, vb_w, vb_h). Find all `<rect>` elements and assert each rect's x >= vb_x and x+width <= vb_x+vb_w. Find all `<text>` elements and assert each text's x >= vb_x (approximate: text_x - estimated_half_width >= vb_x for center-anchored text).
- Render `flink_late_upsert.mmd`. Same assertion.

### Unit: notes.mmd still works (regression)

- Render `notes.mmd`. Assert SVG is produced without errors. Assert note text elements contain expected strings ("Alice starts", "Shared note", "Bob replies"). Assert no `<tspan>` elements in notes (since there are no `<br/>` tags).

### Unit: message labels within viewBox

- Render `flink_late_event.mmd`. Parse viewBox. Find all `.seq-message` text elements. Assert each text element's x coordinate is >= viewBox x origin.

## Methodology

**TDD -- write failing tests FIRST, then fix code.**

1. Create `/home/alexey/git/pymermaid/tests/test_sequence_text_sizing.py` with all test functions above
2. Run `uv run pytest tests/test_sequence_text_sizing.py -v` and confirm the tests FAIL (this validates the tests catch real bugs)
3. Fix the code in `layout/sequence.py` and `render/sequence.py`
4. Run `uv run pytest tests/test_sequence_text_sizing.py -v` and confirm all tests PASS
5. Run `uv run pytest tests/test_sequence.py -v` to confirm no regressions in existing tests
6. Run `uv run pytest` to confirm no regressions project-wide

## Implementation Hints

### Splitting `<br/>` in the renderer

In `_render_note()` in `render/sequence.py`, replace the single `text.text = nl.text` with logic like:

```python
lines = nl.text.split("<br/>")
if len(lines) == 1:
    text.text = lines[0]
else:
    line_height = 16  # approximate
    start_y = nl.y + nl.height / 2 - (len(lines) - 1) * line_height / 2
    for i, line in enumerate(lines):
        tspan = ET.SubElement(text_el, "tspan")
        tspan.set("x", ...)
        tspan.set("dy", "0" if i == 0 else str(line_height))
        tspan.text = line
```

### Fixing text measurement in layout

In `_process_note()` in `layout/sequence.py`, split on `<br/>` before measuring:

```python
lines = note.text.split("<br/>")
line_widths = [measure_fn(line, _FONT_SIZE)[0] for line in lines]
text_w = max(line_widths)
text_h = len(lines) * measure_fn("X", _FONT_SIZE)[1]
```

### Fixing viewBox calculation

In `layout_sequence()`, after computing all element positions, scan notes and messages to find the true bounding box:

```python
max_right = total_w
for nl in notes_layout:
    max_right = max(max_right, nl.x + nl.width)
min_left = 0
for nl in notes_layout:
    min_left = min(min_left, nl.x)
# Also consider message label text widths
total_w = max_right - min_left
```

## Dependencies

None. This task is independent of other tasks.

## Estimated Complexity

Medium -- touches sequence diagram text measurement, note box sizing, message label positioning, and viewBox calculation across two files (layout and render).
