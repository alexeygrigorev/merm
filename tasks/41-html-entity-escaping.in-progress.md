# Task 41: Fix HTML Entity Rendering in Labels

## Problem

HTML entities like `&amp;` in mermaid source are not being decoded before label text is placed into SVG elements. Because `xml.etree.ElementTree` automatically XML-escapes text set via `.text`, the `&amp;` from the source becomes `&amp;amp;` in the SVG output, rendering as the literal string "&amp;" instead of "&".

### PNG Evidence

- `docs/comparisons/text/special_chars_pymermaid.png` -- shows "Ampersand &amp; stuff" instead of "Ampersand & stuff"

### Root Cause

The parser's `_decode_entities()` in `src/pymermaid/parser/flowchart.py` only handles Mermaid-specific numeric entity codes (`#35;` style). It does not decode standard HTML entities (`&amp;`, `&lt;`, `&gt;`, `&quot;`, `&#123;`, etc.). The fix should use `html.unescape()` from Python's standard library to decode HTML entities in label text during parsing, so that `xml.etree` then applies a single correct XML escape when writing.

### Key technical detail

After `html.unescape()`, literal `<` and `>` characters in the decoded text will be correctly re-escaped by `xml.etree` to `&lt;` and `&gt;` in the SVG source. This is correct XML behavior -- browsers and SVG renderers will display them as `<` and `>`.

## Scope

- Add `html.unescape()` call to the parser's label decoding pipeline (both node labels and edge labels)
- Ensure existing `_decode_entities()` for Mermaid-specific codes still works (it can run before or after `html.unescape`)
- No changes needed in the SVG renderer -- `xml.etree` handles XML escaping automatically

## Acceptance Criteria

- [ ] Parsing `A["Ampersand &amp; stuff"]` produces a node with label `Ampersand & stuff` (decoded ampersand)
- [ ] Parsing `A["Angle &lt; &gt; brackets"]` produces a node with label `Angle < > brackets` (decoded angle brackets)
- [ ] Parsing `A["Quote &quot;here&quot;"]` produces a node with label `Quote "here"` (decoded quotes)
- [ ] Mermaid-specific entity codes like `A["Hash #35; mark"]` still decode to `Hash # mark`
- [ ] In the SVG output, `&` in a label appears as `&amp;` (single XML escape, not `&amp;amp;`)
- [ ] In the SVG output, `<` in a label appears as `&lt;` (single XML escape, not `&amp;lt;`)
- [ ] Edge labels with HTML entities are also decoded correctly
- [ ] `uv run pytest` passes with no regressions

### PNG Verification (mandatory)

- [ ] Render `tests/fixtures/corpus/text/special_chars.mmd` to SVG then to PNG with cairosvg and visually verify that the top node displays "Ampersand & stuff" (not "&amp; stuff") and the bottom node displays "Angle < > brackets"

## Test Scenarios

### Unit: HTML entity decoding in parser

- Parse `A["Ampersand &amp; stuff"]` -- verify `node.label == "Ampersand & stuff"`
- Parse `A["&lt;tag&gt;"]` -- verify `node.label == "<tag>"`
- Parse `A["&quot;quoted&quot;"]` -- verify `node.label == '"quoted"'`
- Parse `A["&#38; numeric"]` -- verify `node.label == "& numeric"` (numeric HTML entity)
- Parse `A["Hash #35; mark"]` -- verify `node.label == "Hash # mark"` (Mermaid entity still works)

### Unit: SVG output correctness

- Render a diagram with `&amp;` in a label, parse the SVG XML, extract the text element content, verify it equals `Ampersand & stuff` (after XML parsing decodes `&amp;` back to `&`)
- Render a diagram with `<` in a label, verify the raw SVG contains `&lt;` (not `&amp;lt;`)

### Integration: PNG rendering

- Render `text/special_chars.mmd` to SVG, convert to PNG with cairosvg, confirm no rendering errors

## Dependencies

- None (all prerequisite tasks through task 19 are done)

## Files Likely to Change

- `src/pymermaid/parser/flowchart.py` -- add `html.unescape()` to label decoding
- `tests/test_flowchart_parser.py` -- add entity decoding tests
- New or existing test file for SVG output verification
