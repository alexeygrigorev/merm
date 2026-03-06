# Task 40: Fix Long Text Wrapping and Node Sizing

## Problem

Long text labels overflow outside node boundaries. Text wraps but the wrapped lines overlap each other and overflow above the node rect. The second node (target) renders as an empty box with no text.

### PNG Evidence

- `docs/comparisons/text/long_text_pymermaid.svg` — rendered to PNG shows:
  1. First node: text "A longer label that should be handled correctly by the renderer" wraps but lines overlap each other and overflow above the rect top
  2. Second node: completely empty, no text visible
- `docs/comparisons/text/multiline_pymermaid.svg` — rendered to PNG shows:
  1. First node: "First line" and "Two" overlap, "Second line" and "Three" overlap — text lines are stacked on top of each other instead of vertically spaced
  2. Second node: empty box, no text

### Root Cause

Text wrapping creates multiple `<tspan>` or `<text>` elements but:
- Line spacing between wrapped lines is too small (lines overlap)
- Node height doesn't expand to fit multiple lines of text
- Text vertical position doesn't account for the number of lines (centered on single-line position)

## Acceptance Criteria

- [ ] Long text wraps within the node boundary without overflow
- [ ] Wrapped lines have adequate vertical spacing (no overlap)
- [ ] Node rect height expands to fit all lines of wrapped text
- [ ] Text block is vertically centered within the expanded node
- [ ] Both source and target nodes display their text
- [ ] `uv run pytest` passes with no regressions

### PNG Verification (mandatory)
- [ ] Render `text/long_text` to PNG — all text readable, no overlap, both nodes have text
- [ ] Render `text/multiline` to PNG — all lines visible and vertically spaced
- [ ] Render `text/quoted_labels` to PNG — labels fully visible

## Dependencies
- None
