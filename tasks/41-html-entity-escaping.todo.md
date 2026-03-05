# Task 41: Fix HTML Entity Rendering in Labels

## Problem

HTML entities like `&amp;` are rendered literally as text instead of being decoded. The label "Ampersand & stuff" renders as "Ampersand &amp; stuff" in the SVG output.

### PNG Evidence

- `docs/comparisons/text/special_chars_pymermaid.svg` — rendered to PNG shows "Ampersand &amp; stuff" instead of "Ampersand & stuff"

### Root Cause

The label text is being XML-escaped twice, or HTML entities from the mermaid source are not being decoded before being placed in SVG text elements. The `&` in the original mermaid source becomes `&amp;` in the IR, and then when placed in SVG it becomes `&amp;amp;` or the literal string `&amp;` is displayed.

## Acceptance Criteria

- [ ] `&` in labels renders as `&` (not `&amp;`)
- [ ] `<` and `>` in labels render as `<` and `>` (not escaped)
- [ ] Other HTML entities are properly decoded
- [ ] XML-special characters in labels are properly escaped for SVG (single escape, not double)
- [ ] `uv run pytest` passes with no regressions

### PNG Verification (mandatory)
- [ ] Render `text/special_chars` to PNG — "Ampersand & stuff" and "Angle < > brackets" display correctly

## Test Scenarios

### Unit: Entity decoding
- Label containing `&` renders as `&` in SVG text
- Label containing `<` renders properly (escaped once for XML)
- Label containing `"` renders as a quote

## Dependencies
- None
