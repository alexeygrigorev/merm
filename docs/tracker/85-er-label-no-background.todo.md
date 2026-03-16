# Issue 85: ER diagram edge labels lack opaque backgrounds

## Problem

In ER diagrams with dashed relationship lines, the edge labels ("may own", "lives at", etc.) do not have opaque background rectangles. The dashed lines show through the label text, reducing readability.

Flowchart edge labels already have gray background rectangles that occlude the edge line behind them. ER diagram labels should do the same.

Reproduction: `tests/fixtures/corpus/er/dashed_lines.mmd`

## Acceptance criteria

- ER relationship labels must have an opaque background rectangle behind the text
- The background must occlude the relationship line where it passes behind the label
- Label text must be clearly readable against the background
- The background style should be consistent with flowchart edge labels
- Existing tests must continue to pass
